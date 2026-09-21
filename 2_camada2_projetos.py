"""Passo 2 - Camada 2 (projetos)

Objetivo: aplica a hierarquia entre projetos: Recooperar > SICAR-regularização > Outros projetos > OR
(MonitoRAD desativado). Conta a ÁREA INTEIRA do projeto (com ou sem VS detectável).

Implementado nesta versão (v0.2.0): classe 1, RECOOPERAR (Tier-1).
    A classe 1 não subtrai nenhuma outra. Dentro dela, polígonos das quatro categorias que se
    sobrepõem são contados uma vez, na categoria de maior precedência (config_computo.PRECEDENCIA_RECOOPERAR).
    Cada polígono elegível continua INTEIRO e com os atributos de VS na tabela; a área líquida
    (sem dupla contagem) vai em colunas próprias e em uma camada de polígonos líquidos disjuntos.
Ainda não implementado: classes 3 (SICAR-regularização), 4 (Outros projetos) e 5 (OR).

Entradas: SAIDA_INSUMOS/IN_Recooperar_2026.gpkg (passo 1); peças VS x projeto (FONTES["recooperar"]["cruzamento"]);
          IBGE_Limite_Estados e IBGE_Limite_Biomas.
Saídas (em config_computo.SAIDA_TIER1):
    P2_Recooperar_2026.gpkg
        P2_RECOOPERAR_poligonos  polígonos inteiros elegíveis + área líquida + UF/bioma + VS (inteira e líquida)
        P2_RECOOPERAR            polígonos líquidos, disjuntos (é o que as classes seguintes subtraem)
    T1_resumo.csv                       por categoria e total
    T1_resumo_categoria_uf_bioma.csv    categoria x UF x bioma (áreas aditivas)
    T1_areas_uf_bioma.csv               polígono x UF x bioma (tabela longa)
    T1_conferencias.csv                 verificações independentes (área, VS, sobreposição zero)
    _log_passo2.txt

Execução:  python 2_camada2_projetos.py [RECOOPERAR]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import shapely
from shapely.strtree import STRtree

import config_computo as cfg
from computo import geometria as geo
from computo import io_dados as io
from computo.hierarquia import liquido_por_precedencia
from computo.territorio import Limites
from computo.vs import PedacosVS, area_vs

CLASSES_IMPLEMENTADAS = ["RECOOPERAR"]
ARQ_IN = "IN_Recooperar_2026.gpkg"
ARQ_OUT = "P2_Recooperar_2026.gpkg"


def _carregar_limites():
    e, b = cfg.FONTES["estados"], cfg.FONTES["biomas"]
    uf = io.ler_camada(cfg.RAIZ / e["arquivo"], e["camada"])
    bio = io.ler_camada(cfg.RAIZ / b["arquivo"], b["camada"])
    return Limites(uf, e["campo_uf"], bio, b["campo"])


def _carregar_vs():
    fonte = cfg.FONTES["recooperar"]
    camadas = list(fonte["camadas"].values())
    return {p: PedacosVS(io.ler_pedacos_vs(cfg.RAIZ / arq, camadas)) for p, arq in fonte["cruzamento"].items()}


def classe_recooperar(log, so_categorias=None):
    import geopandas as gpd

    P = list(cfg.VS_VERSOES)
    arq_in = cfg.SAIDA_INSUMOS / ARQ_IN
    if not arq_in.exists():
        raise FileNotFoundError(f"Não encontrei {arq_in}. Rode 1_preparar_insumos.py antes.")
    cfg.SAIDA_TIER1.mkdir(parents=True, exist_ok=True)
    g = io.ler_camada(arq_in, "IN_RECOOPERAR")
    if so_categorias:                       # uso interno de teste
        g = g[g["categoria"].isin(so_categorias)].reset_index(drop=True)
    n = len(g)
    log(f"IN_RECOOPERAR: {n} polígonos elegíveis")
    geoms = np.array(g.geometry.values, dtype=object)

    # ---- 1) área líquida: sobreposição dentro da classe resolvida por precedência ----
    ordem_cat = {c: i for i, c in enumerate(cfg.PRECEDENCIA_RECOOPERAR)}
    ano = g["ano_inicio"].astype("float").fillna(9999).to_numpy()
    chave = pd.DataFrame({"cat": g["categoria"].map(ordem_cat), "ano": ano, "fid": g["fid_orig"].astype(int), "i": np.arange(n)})
    ranking = chave.sort_values(["cat", "ano", "fid", "i"]).reset_index(drop=True)
    prioridade = np.empty(n, dtype=int)
    prioridade[ranking["i"].to_numpy()] = np.arange(n)
    liquidos, sobreposta, n_prec = liquido_por_precedencia(geoms, prioridade)
    a_bruta = g["area_ha_geo"].to_numpy(float)
    a_liq = geo.area_ha(liquidos)
    log(f"soma dos polígonos inteiros {a_bruta.sum():,.1f} ha | sobreposição interna removida {sobreposta.sum():,.1f} ha | líquida {a_liq.sum():,.1f} ha")

    # ---- 2) UF x bioma e VS (inteira e líquida) por célula ----
    log("carregando limites IBGE e peças de VS...")
    lim = _carregar_limites()
    vs = _carregar_vs()
    linhas = []
    for i in range(n):
        G, N = geoms[i], liquidos[i]
        U = {p: vs[p].uniao_em(G) for p in P}
        for uf, bio, C in lim.celulas(G):
            NC = None
            if N is not None:
                NC = geo.so_poligonos(geo.intersecao_robusta([N], [C])[0])
            linha = {"i": i, "uf": uf, "bioma": bio, "area_completa_ha": geo.area_ha([C])[0],
                     "area_liquida_ha": geo.area_ha([NC])[0] if NC is not None else 0.0}
            for p in P:
                linha[f"{p}_completa_ha"] = area_vs(U[p], C)
                linha[f"{p}_liquida_ha"] = area_vs(U[p], NC) if NC is not None else 0.0
            linhas.append(linha)
        if (i + 1) % 200 == 0 or i + 1 == n:
            log(f"  {i + 1}/{n} polígonos")
    cel = pd.DataFrame(linhas)

    # ---- 3) atributos por polígono ----
    def _resumo_lista(sub, col):
        s = sub.groupby(col)["area_completa_ha"].sum().sort_values(ascending=False)
        s = s[s > 1e-6]
        return ";".join(s.index), (s.index[0] if len(s) else None)

    principais = {}
    for i, sub in cel.groupby("i"):
        u_lista, u_prin = _resumo_lista(sub, "uf")
        b_lista, b_prin = _resumo_lista(sub, "bioma")
        principais[i] = (u_prin, u_lista, b_prin, b_lista)
    novos = pd.DataFrame(index=range(n))
    novos["prec_ordem"] = prioridade + 1
    novos["n_precedentes_sobrepostos"] = n_prec
    novos["area_sobreposta_ha"] = sobreposta
    novos["area_liquida_ha"] = a_liq
    novos["uf_principal"] = [principais.get(i, (None,) * 4)[0] for i in range(n)]
    novos["ufs"] = [principais.get(i, (None,) * 4)[1] for i in range(n)]
    novos["bioma_principal"] = [principais.get(i, (None,) * 4)[2] for i in range(n)]
    novos["biomas"] = [principais.get(i, (None,) * 4)[3] for i in range(n)]
    # divergência = a UF principal calculada não aparece no campo de UF da fonte (que pode listar mais de uma)
    novos["uf_diverge_fonte"] = [int(u is not None and f is not None and not pd.isna(f) and u not in str(f))
                                 for u, f in zip(novos["uf_principal"], g["uf_fonte"].to_numpy())]
    soma = cel.groupby("i").sum(numeric_only=True)
    for p in P:
        novos[f"{p}_completa_recalc_ha"] = soma[f"{p}_completa_ha"].reindex(range(n)).fillna(0.0).to_numpy()
        novos[f"{p}_liq_ha"] = soma[f"{p}_liquida_ha"].reindex(range(n)).fillna(0.0).to_numpy()

    pol = g.reset_index(drop=True).copy()
    for c in novos.columns:
        pol[c] = novos[c].to_numpy()
    pol = gpd.GeoDataFrame(pol, geometry="geometry", crs=g.crs)

    # camada líquida (disjunta)
    mask = np.array([x is not None for x in liquidos])
    liq = gpd.GeoDataFrame(
        pol.loc[mask, ["id_proj", "categoria", "categoria_nome", "status_recuperacao", "ano_inicio", "ano_inicio_fonte",
                       "uf_principal", "bioma_principal", "area_liquida_ha"] + [f"{p}_liq_ha" for p in P]].reset_index(drop=True),
        geometry=list(liquidos[mask]), crs=g.crs)

    # ---- 4) saídas ----
    out = cfg.SAIDA_TIER1 / ARQ_OUT
    io.gravar_camada(pol, out, "P2_RECOOPERAR_poligonos", primeira=True)
    io.gravar_camada(liq, out, "P2_RECOOPERAR")

    cel["id_proj"] = pol["id_proj"].to_numpy()[cel["i"].to_numpy()]
    cel["categoria"] = pol["categoria"].to_numpy()[cel["i"].to_numpy()]
    cols = ["id_proj", "categoria", "uf", "bioma", "area_completa_ha", "area_liquida_ha"] + [f"{p}_{t}_ha" for p in P for t in ("completa", "liquida")]
    cel[cols].to_csv(cfg.SAIDA_TIER1 / "T1_areas_uf_bioma.csv", index=False, encoding="utf-8-sig")
    agg = cel.groupby(["categoria", "uf", "bioma"], as_index=False)[[c for c in cols if c.endswith("_ha")]].sum()
    agg["n_poligonos"] = cel.groupby(["categoria", "uf", "bioma"])["id_proj"].nunique().to_numpy()
    agg.to_csv(cfg.SAIDA_TIER1 / "T1_resumo_categoria_uf_bioma.csv", index=False, encoding="utf-8-sig")

    linhas = []
    for cat in cfg.PRECEDENCIA_RECOOPERAR + ["TOTAL"]:
        sub = pol if cat == "TOTAL" else pol[pol["categoria"] == cat]
        r = {"categoria": cat, "n_poligonos": len(sub), "area_poligonos_inteiros_ha": sub["area_ha_geo"].sum(),
             "sobreposicao_removida_ha": sub["area_sobreposta_ha"].sum(), "area_liquida_ha": sub["area_liquida_ha"].sum()}
        for p in P:
            r[f"{p}_atributo_poligonos_ha"] = sub[f"{p}_area_ha"].sum()
            r[f"{p}_liquida_ha"] = sub[f"{p}_liq_ha"].sum()
        linhas.append(r)
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_TIER1 / "T1_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo.round(1).to_string(index=False))

    # ---- 5) conferências independentes ----
    conf = []

    def chk(nome, valor, limite, obs=""):
        conf.append({"conferencia": nome, "valor": valor, "limite": limite, "ok": bool(abs(valor) <= limite), "obs": obs})

    uniao = geo.uniao_robusta(list(geoms))
    a_uniao = geo.area_ha([uniao])[0] if uniao is not None else 0.0
    chk("area liquida - area da uniao (ha)", a_liq.sum() - a_uniao, 1e-3, "soma dos polígonos líquidos x união independente")
    tree = STRtree(liq.geometry.values)
    ii, jj = tree.query(liq.geometry.values, predicate="intersects")
    m = ii < jj
    ov = geo.area_ha(geo.intersecao_robusta(liq.geometry.values[ii[m]], liq.geometry.values[jj[m]])) if m.any() else np.array([0.0])
    chk("sobreposicao entre polígonos líquidos (ha)", float(ov.sum()), 1e-3)
    chk("area inteira - soma das celulas UF x bioma (ha, max por polígono)",
        float(np.abs(pol["area_ha_geo"].to_numpy() - cel.groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0).to_numpy()).max()), 0.01)
    fora = float(cel.loc[(cel["uf"] == "FORA") | (cel["bioma"] == "FORA"), "area_completa_ha"].sum())
    chk("area fora dos limites IBGE de UF ou bioma (ha)", fora, 0.0005 * float(a_bruta.sum()),
        f"{fora:,.1f} ha ficam como bioma/UF 'FORA' (faixa costeira/mar); tolerância 0,05% da área")
    for p in P:
        d = np.abs(pol[f"{p}_area_ha"].to_numpy(float) - pol[f"{p}_completa_recalc_ha"].to_numpy(float))
        chk(f"{p}: atributo da VS x recalculo por peças (ha, max por polígono)", float(d.max()), 0.01,
            "o atributo incorporado no passo anterior deve coincidir com o recálculo")
        chk(f"{p}: VS líquida <= VS soma dos polígonos (ha)", float(min(0.0, pol[f'{p}_area_ha'].sum() - pol[f'{p}_liq_ha'].sum())), 0.0)
    chk("polígonos sem UF principal", float(pol["uf_principal"].isna().sum()), 0)
    chk("geometrias líquidas inválidas", float((~shapely.is_valid(liq.geometry.values)).sum()), 0)
    conf = pd.DataFrame(conf)
    conf.to_csv(cfg.SAIDA_TIER1 / "T1_conferencias.csv", index=False, encoding="utf-8-sig")
    log("\n" + conf.to_string(index=False))
    if not conf["ok"].all():
        log("ATENÇÃO: há conferências fora do limite (ver T1_conferencias.csv).")
    log(f"gravado: {out}")
    return pol, liq, cel, resumo, conf


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pedidas = [a.upper() for a in argv] or CLASSES_IMPLEMENTADAS
    cfg.SAIDA_TIER1.mkdir(parents=True, exist_ok=True)
    arq_log = cfg.SAIDA_TIER1 / "_log_passo2.txt"

    def log(m):
        io.log(m, arq_log)

    log("Passo 2 - Camada 2 (projetos)")
    for c in pedidas:
        if c not in CLASSES_IMPLEMENTADAS:
            log(f"classe '{c}': ainda não implementada.")
            return 1
    if "RECOOPERAR" in pedidas:
        classe_recooperar(log)
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
