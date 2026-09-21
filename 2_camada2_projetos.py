"""Passo 2 - Camada 2 (projetos)

Objetivo: aplica a hierarquia entre projetos: Recooperar > SICAR-regularização > Outros projetos > OR
(MonitoRAD desativado). Conta a ÁREA INTEIRA do projeto (com ou sem VS detectável).

Implementado nesta versão (v0.2.0): classe 1, RECOOPERAR (Tier-1).
    A classe 1 não subtrai nenhuma outra. Dentro dela, polígonos das quatro categorias que se
    sobrepõem são contados uma vez, na categoria de maior precedência (config_computo.PRECEDENCIA_RECOOPERAR).
    Cada polígono elegível continua INTEIRO e com os atributos de VS na tabela; a área líquida
    (sem dupla contagem) vai em colunas próprias e em uma camada de polígonos líquidos disjuntos.
Implementado na v0.3.0: classe 3, SICAR-REGULARIZAÇÃO (CAR_REGULARIZACAO; área a recompor de APP e RL).
    Subtrai a classe 1 (líquido do Recooperar, P2_RECOOPERAR) e resolve a sobreposição dentro da classe por
    precedência (APP > RL averbada > RL aprovada não averbada > RL proposta). Polígonos inteiros, com VS na tabela.
Ainda não implementado: classes 4 (Outros projetos) e 5 (OR).

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
Saídas da classe 3 (em config_computo.SAIDA_TIER3):
    P2_CAR_Regularizacao_Junho26.gpkg
        P2_CAR_REGULARIZACAO_poligonos  polígonos inteiros + sobreposição com a classe 1 e dentro da classe + líquida + UF/bioma + VS
        P2_CAR_REGULARIZACAO            polígonos líquidos (disjuntos entre si e da classe 1)
    T3_resumo.csv, T3_resumo_categoria_tema_uf_bioma.csv, T3_areas_uf_bioma.csv, T3_conferencias.csv,
    T3_acumulado_classes_1_e_3.csv (área líquida acumulada das classes já processadas, por UF e bioma)

Execução:  python 2_camada2_projetos.py [RECOOPERAR] [CAR_REGULARIZACAO]   (sem argumento: todas, na ordem)
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
from computo.hierarquia import liquido_por_precedencia, subtrair_precedentes
from computo.territorio import Limites, resumo_uf_bioma_por_poligono, tabela_celulas
from computo.vs import PedacosVS, area_vs   # noqa: F401

CLASSES_IMPLEMENTADAS = ["RECOOPERAR", "CAR_REGULARIZACAO"]
ARQ_IN = "IN_Recooperar_2026.gpkg"
ARQ_OUT = "P2_Recooperar_2026.gpkg"
ARQ_IN_CAR = "IN_CAR_Regularizacao_Junho26.gpkg"
ARQ_VS_CAR = "IN_CAR_Regularizacao_Junho26_VS.gpkg"
ARQ_OUT_CAR = "P2_CAR_Regularizacao_Junho26.gpkg"


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
    cel = tabela_celulas(geoms, liquidos, lim, vs, P, log)

    # ---- 3) atributos por polígono ----
    principais = dict(enumerate(resumo_uf_bioma_por_poligono(cel, n)))
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


def _pedacos_car():
    arq = cfg.SAIDA_INSUMOS / ARQ_VS_CAR
    if not arq.exists():
        raise FileNotFoundError(f"Não encontrei {arq}. Rode 1_preparar_insumos.py car_regularizacao antes.")
    import pyogrio
    saida = {}
    for p in cfg.VS_VERSOES:
        d = pyogrio.read_dataframe(str(arq), layer=f"{p}_pedacos", columns=["id_proj"])
        saida[p] = PedacosVS(np.array(d.geometry.values, dtype=object))
    return saida


def _geoms_classes_anteriores(codigo):
    """Geometrias líquidas (disjuntas) das classes ativas de maior prioridade já processadas."""
    arquivos = {"RECOOPERAR": (cfg.SAIDA_TIER1 / ARQ_OUT, "P2_RECOOPERAR")}
    geoms, usados = [], []
    for c in cfg.precedentes(codigo):
        if c not in arquivos:
            raise NotImplementedError(f"classe anterior {c} ainda não processada (necessária para subtrair)")
        arq, camada = arquivos[c]
        if not arq.exists():
            raise FileNotFoundError(f"Não encontrei {arq}. Rode a classe {c} antes.")
        g = io.ler_camada(arq, camada)
        geoms.extend(list(g.geometry.values))
        usados.append(c)
    return np.array(geoms, dtype=object), usados


def classe_car_regularizacao(log):
    import geopandas as gpd

    P = list(cfg.VS_VERSOES)
    arq_in = cfg.SAIDA_INSUMOS / ARQ_IN_CAR
    if not arq_in.exists():
        raise FileNotFoundError(f"Não encontrei {arq_in}. Rode 1_preparar_insumos.py car_regularizacao antes.")
    cfg.SAIDA_TIER3.mkdir(parents=True, exist_ok=True)
    g = io.ler_camada(arq_in, "IN_CAR_REG")
    n = len(g)
    log(f"IN_CAR_REG: {n} polígonos elegíveis")
    geoms = np.array(g.geometry.values, dtype=object)
    a_bruta = g["area_ha_geo"].to_numpy(float)

    # ---- 1) subtrai as classes de maior prioridade (Recooperar) ----
    prec, usados = _geoms_classes_anteriores("SICAR_REGULARIZACAO")
    log(f"classes anteriores subtraídas: {usados} ({len(prec)} polígonos líquidos)")
    restantes, sobre_prec = subtrair_precedentes(geoms, prec)
    log(f"sobreposição com as classes anteriores: {sobre_prec.sum():,.2f} ha em {(sobre_prec > 0).sum()} polígonos")

    # ---- 2) sobreposição dentro da classe: precedência por tema e fid ----
    ordem_tema = {t: i for i, t in enumerate(cfg.PRECEDENCIA_CAR_REG)}
    chave = pd.DataFrame({"tema": g["cod_tema"].map(ordem_tema).fillna(len(ordem_tema)), "fid": g["fid_orig"].astype(int),
                          "cat": g["categoria"].map({"app": 0, "rl": 1}), "i": np.arange(n)})
    ranking = chave.sort_values(["cat", "tema", "fid", "i"]).reset_index(drop=True)
    prioridade = np.empty(n, dtype=int)
    prioridade[ranking["i"].to_numpy()] = np.arange(n)
    vivos = np.array([x is not None for x in restantes])
    liquidos = np.array([None] * n, dtype=object)
    sobre_intra = np.zeros(n)
    n_prec = np.zeros(n, dtype=int)
    if vivos.any():
        iv = np.where(vivos)[0]
        pv = np.argsort(np.argsort(prioridade[iv]))          # prioridade única e compacta no subconjunto
        liq_v, sob_v, np_v = liquido_por_precedencia(restantes[iv], pv)
        liquidos[iv] = liq_v
        sobre_intra[iv] = sob_v
        n_prec[iv] = np_v
    a_liq = geo.area_ha(liquidos)
    log(f"soma dos polígonos inteiros {a_bruta.sum():,.1f} ha | sobreposição com classes anteriores {sobre_prec.sum():,.2f} ha | "
        f"sobreposição dentro da classe {sobre_intra.sum():,.2f} ha | líquida {a_liq.sum():,.1f} ha")

    # ---- 3) UF x bioma e VS (inteira e líquida) ----
    log("carregando limites IBGE e peças de VS...")
    lim = _carregar_limites()
    vs = _pedacos_car()
    cel = tabela_celulas(geoms, liquidos, lim, vs, P, log)
    principais = resumo_uf_bioma_por_poligono(cel, n)

    novos = pd.DataFrame(index=range(n))
    novos["prec_ordem"] = prioridade + 1
    novos["area_sobreposta_classes_anteriores_ha"] = sobre_prec
    novos["n_precedentes_sobrepostos"] = n_prec
    novos["area_sobreposta_na_classe_ha"] = sobre_intra
    novos["area_liquida_ha"] = a_liq
    novos["uf_principal"] = [x[0] for x in principais]
    novos["ufs"] = [x[1] for x in principais]
    novos["bioma_principal"] = [x[2] for x in principais]
    novos["biomas"] = [x[3] for x in principais]
    novos["area_fora_ibge_ha"] = cel[(cel["uf"] == "FORA") | (cel["bioma"] == "FORA")].groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0.0).to_numpy()
    novos["uf_diverge_car"] = [int(u is not None and u != f) for u, f in zip(novos["uf_principal"], g["uf_car"].to_numpy())]
    soma = cel.groupby("i").sum(numeric_only=True)
    for p in P:
        novos[f"{p}_completa_recalc_ha"] = soma[f"{p}_completa_ha"].reindex(range(n)).fillna(0.0).to_numpy()
        novos[f"{p}_liq_ha"] = soma[f"{p}_liquida_ha"].reindex(range(n)).fillna(0.0).to_numpy()
    pol = g.reset_index(drop=True).copy()
    for c in novos.columns:
        pol[c] = novos[c].to_numpy()
    pol = gpd.GeoDataFrame(pol, geometry="geometry", crs=g.crs)
    mask = np.array([x is not None for x in liquidos])
    liq = gpd.GeoDataFrame(
        pol.loc[mask, ["id_proj", "categoria", "categoria_nome", "cod_tema", "cod_imovel", "uf_car", "uf_principal", "bioma_principal",
                       "area_liquida_ha"] + [f"{p}_liq_ha" for p in P]].reset_index(drop=True),
        geometry=list(liquidos[mask]), crs=g.crs)

    # ---- 4) saídas ----
    out = cfg.SAIDA_TIER3 / ARQ_OUT_CAR
    io.gravar_camada(pol, out, "P2_CAR_REGULARIZACAO_poligonos", primeira=True)
    io.gravar_camada(liq, out, "P2_CAR_REGULARIZACAO")
    cel["id_proj"] = pol["id_proj"].to_numpy()[cel["i"].to_numpy()]
    cel["categoria"] = pol["categoria"].to_numpy()[cel["i"].to_numpy()]
    cel["cod_tema"] = pol["cod_tema"].to_numpy()[cel["i"].to_numpy()]
    cols = ["id_proj", "categoria", "cod_tema", "uf", "bioma", "area_completa_ha", "area_liquida_ha"] + [f"{p}_{t}_ha" for p in P for t in ("completa", "liquida")]
    cel[cols].to_csv(cfg.SAIDA_TIER3 / "T3_areas_uf_bioma.csv", index=False, encoding="utf-8-sig")
    valores = [c for c in cols if c.endswith("_ha")]
    agg = cel.groupby(["categoria", "cod_tema", "uf", "bioma"], as_index=False)[valores].sum()
    agg["n_poligonos"] = cel.groupby(["categoria", "cod_tema", "uf", "bioma"])["id_proj"].nunique().to_numpy()
    agg.to_csv(cfg.SAIDA_TIER3 / "T3_resumo_categoria_tema_uf_bioma.csv", index=False, encoding="utf-8-sig")

    def _linha(nome, sub):
        r = {"grupo": nome, "n_poligonos": len(sub), "area_poligonos_inteiros_ha": sub["area_ha_geo"].sum(),
             "sobreposicao_classes_anteriores_ha": sub["area_sobreposta_classes_anteriores_ha"].sum(),
             "sobreposicao_na_classe_ha": sub["area_sobreposta_na_classe_ha"].sum(), "area_liquida_ha": sub["area_liquida_ha"].sum()}
        for p in P:
            r[f"{p}_atributo_poligonos_ha"] = sub[f"{p}_area_ha"].sum()
            r[f"{p}_liquida_ha"] = sub[f"{p}_liq_ha"].sum()
        return r

    linhas = [_linha(c, pol[pol["categoria"] == c]) for c in ("app", "rl")]
    linhas += [_linha(f"  rl/{t}", pol[pol["cod_tema"] == t]) for t in cfg.PRECEDENCIA_CAR_REG[1:]]
    linhas += [_linha(f"  uf/{u}", pol[pol["uf_car"] == u]) for u in sorted(pol["uf_car"].unique())]
    linhas.append(_linha("TOTAL", pol))
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_TIER3 / "T3_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo.round(1).to_string(index=False))

    # acumulado das classes já processadas (líquidas, sem dupla contagem entre classes)
    r1 = cfg.SAIDA_TIER1 / "T1_resumo_categoria_uf_bioma.csv"
    acum = []
    if r1.exists():
        a1 = pd.read_csv(r1)
        a1 = a1.rename(columns={"vs22q_liquida_ha": "vs22q_liquida_ha", "vs2224q_liquida_ha": "vs2224q_liquida_ha"})
        a1["classe"] = "1 RECOOPERAR"
        acum.append(a1[["classe", "categoria", "uf", "bioma", "area_liquida_ha", "vs22q_liquida_ha", "vs2224q_liquida_ha"]])
    a3 = agg.copy()
    a3["classe"] = "3 SICAR_REGULARIZACAO"
    a3 = a3.rename(columns={f"{p}_liquida_ha": f"{p}_liquida_ha" for p in P})
    acum.append(a3[["classe", "categoria", "uf", "bioma", "area_liquida_ha", "vs22q_liquida_ha", "vs2224q_liquida_ha"]])
    acum = pd.concat(acum, ignore_index=True)
    acum.to_csv(cfg.SAIDA_TIER3 / "T3_acumulado_classes_1_e_3.csv", index=False, encoding="utf-8-sig")
    tot = acum.groupby("classe")[["area_liquida_ha", "vs22q_liquida_ha", "vs2224q_liquida_ha"]].sum()
    log("\nacumulado (área líquida, sem dupla contagem entre classes):\n" + tot.round(1).to_string()
        + f"\n  total {tot['area_liquida_ha'].sum():,.1f} ha")

    # ---- 5) conferências independentes ----
    conf = []

    def chk(nome, valor, limite, obs=""):
        conf.append({"conferencia": nome, "valor": valor, "limite": limite, "ok": bool(abs(valor) <= limite), "obs": obs})

    chk("area inteira - (sobreposta classes anteriores + na classe + liquida) (ha, max por polígono)",
        float(np.abs(a_bruta - sobre_prec - sobre_intra - a_liq).max()), 1e-3, "identidade de área por polígono")
    U = geo.uniao_robusta(list(geoms))
    R = geo.uniao_robusta(list(prec))
    liq_esp = geo.so_poligonos(geo.diferenca_robusta([U], [R])[0]) if (U is not None and R is not None) else U
    a_esp = geo.area_ha([liq_esp])[0] if liq_esp is not None else 0.0
    chk("area liquida - area (uniao dos polígonos - uniao das classes anteriores) (ha)", a_liq.sum() - a_esp, 1e-3,
        "soma dos líquidos x cálculo independente por união")
    tree = STRtree(liq.geometry.values)
    ii, jj = tree.query(liq.geometry.values, predicate="intersects")
    m = ii < jj
    ov = geo.area_ha(geo.intersecao_robusta(liq.geometry.values[ii[m]], liq.geometry.values[jj[m]])) if m.any() else np.array([0.0])
    chk("sobreposicao entre polígonos líquidos da classe (ha)", float(ov.sum()), 1e-3)
    tp = STRtree(prec)
    ii, jj = tp.query(liq.geometry.values, predicate="intersects")
    ov2 = geo.area_ha(geo.intersecao_robusta(liq.geometry.values[ii], prec[jj])) if len(ii) else np.array([0.0])
    chk("sobreposicao dos líquidos com as classes anteriores (ha)", float(ov2.sum()), 1e-3)
    chk("area inteira - soma das celulas UF x bioma (ha, max por polígono)",
        float(np.abs(a_bruta - cel.groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0).to_numpy()).max()), 0.01)
    fora = float(cel.loc[(cel["uf"] == "FORA") | (cel["bioma"] == "FORA"), "area_completa_ha"].sum())
    chk("area fora dos limites IBGE de UF ou bioma (ha)", fora, 0.0005 * float(a_bruta.sum()),
        f"{fora:,.2f} ha ficam como bioma/UF 'FORA'; tolerância 0,05% da área")
    for p in P:
        d = np.abs(pol[f"{p}_area_ha"].to_numpy(float) - pol[f"{p}_completa_recalc_ha"].to_numpy(float))
        chk(f"{p}: atributo da VS (passo 1) x recalculo por peças (ha, max por polígono)", float(d.max()), 0.01)
        chk(f"{p}: VS líquida <= VS inteira, por polígono (ha, pior caso)",
            float(min(0.0, (pol[f"{p}_completa_recalc_ha"] - pol[f"{p}_liq_ha"]).min())), 1e-6)
    chk("polígonos sem UF principal", float(pol["uf_principal"].isna().sum()), 0)
    chk("polígonos com UF calculada diferente da UF do código do imóvel", float(pol["uf_diverge_car"].sum()), 0.01 * n,
        "informativo (limite: 1% dos polígonos): divergência entre a UF pelos limites do IBGE e o prefixo do cod_imovel; "
        "inclui polígonos cuja maior parte cai fora do território (ver area_fora_ibge_ha)")
    chk("geometrias líquidas inválidas", float((~shapely.is_valid(liq.geometry.values)).sum()), 0)
    conf = pd.DataFrame(conf)
    conf.to_csv(cfg.SAIDA_TIER3 / "T3_conferencias.csv", index=False, encoding="utf-8-sig")
    log("\n" + conf.to_string(index=False))
    if not conf["ok"].all():
        log("ATENÇÃO: há conferências fora do limite (ver T3_conferencias.csv).")
    log(f"gravado: {out}")
    return pol, liq, cel, resumo, conf


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pedidas = [a.upper() for a in argv] or CLASSES_IMPLEMENTADAS
    cfg.SAIDA_TIER1.mkdir(parents=True, exist_ok=True)
    arq_log = cfg.SAIDA_TIER1 / "_log_passo2.txt"
    if pedidas == ["CAR_REGULARIZACAO"]:
        cfg.SAIDA_TIER3.mkdir(parents=True, exist_ok=True)
        arq_log = cfg.SAIDA_TIER3 / "_log_passo2_car.txt"

    def log(m):
        io.log(m, arq_log)

    log("Passo 2 - Camada 2 (projetos)")
    for c in pedidas:
        if c not in CLASSES_IMPLEMENTADAS:
            log(f"classe '{c}': ainda não implementada.")
            return 1
    if "RECOOPERAR" in pedidas:
        classe_recooperar(log)
    if "CAR_REGULARIZACAO" in pedidas:
        classe_car_regularizacao(log)
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
