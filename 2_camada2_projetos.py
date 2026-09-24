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
Implementado na v0.4.0: classe 4, OUTROS_PROJETOS (por ora só os embargos PANGIA; ICMBio adiado).
    Só a VS DENTRO do embargo entra (decisão de 20/09/2026). Subtrai as classes 1 e 3 e resolve a sobreposição entre embargos
    (o mais antigo fica com a área). A geometria da classe depende da versão da VS (vs22q, vs2224q): há um conjunto de
    polígonos líquidos por versão.
Implementado na v0.5.0 (mantido na v0.6.0): classe 5, OR (Observatório da Restauração, ORR 2025; 4 polígonos dissolvidos por bioma).
    Área TOTAL dos polígonos (com ou sem VS, como as classes 1 e 3); subtrai as classes 1, 3 e 4, esta na versão da VS em cálculo
    (o líquido da classe 5 tem um conjunto por versão). VS como atributo.

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

Saídas da classe 4 (em config_computo.SAIDA_TIER4):
    P2_Outros_Projetos_PANGIA_20260920.gpkg
        P2_OUTROS_PROJETOS_poligonos  embargos inteiros (referência) + VS no embargo, sobreposições e área líquida por versão
        P2_OUTROS_PROJETOS_vs22q      polígonos líquidos (VS 2022), disjuntos entre si e das classes 1 e 3
        P2_OUTROS_PROJETOS_vs2224q    idem, VS 2022-2024
    T4_resumo.csv, T4_resumo_uf_bioma.csv, T4_areas_uf_bioma.csv, T4_conferencias.csv,
    T4_acumulado_classes_1_3_4.csv (área líquida acumulada das classes 1, 3 e 4, por versão, UF e bioma)

Saídas da classe 5 (em config_computo.SAIDA_TIER5):
    P2_OR_2025.gpkg
        P2_OR_poligonos  os 4 polígonos inteiros + sobreposições e área líquida por versão + UF/bioma + VS (inteira e líquida)
        P2_OR_vs22q      partes líquidas (polígonos simples), disjuntas entre si e das classes 1, 3 e 4 (versão vs22q)
        P2_OR_vs2224q    idem, versão vs2224q
    T5_resumo.csv, T5_resumo_uf_bioma.csv, T5_areas_uf_bioma.csv, T5_conferencias.csv,
    T5_acumulado_classes_1_3_4_5.csv (área líquida acumulada das classes 1, 3, 4 e 5, por versão, UF e bioma)

Execução:  python 2_camada2_projetos.py [RECOOPERAR] [CAR_REGULARIZACAO] [OUTROS_PROJETOS] [OR]   (sem argumento: todas, na ordem)
Cada classe grava o próprio log na sua pasta (_log_passo2.txt, _log_passo2_car.txt, _log_passo2_outros.txt, _log_passo2_or.txt).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import shapely
from shapely.strtree import STRtree

import config_computo as cfg
from computo import anteriores
from computo import embargos as emb
from computo import geometria as geo
from computo import io_dados as io
from computo.hierarquia import liquido_por_precedencia, subtrair_precedentes
from computo.territorio import Limites, resumo_uf_bioma_por_poligono, tabela_celulas
from computo.vs import PedacosVS, area_vs   # noqa: F401

CLASSES_IMPLEMENTADAS = ["RECOOPERAR", "CAR_REGULARIZACAO", "OUTROS_PROJETOS", "OR"]
ARQ_IN = "IN_Recooperar_2026.gpkg"
ARQ_OUT = anteriores.ARQ_OUT_RECOOPERAR
ARQ_IN_CAR = "IN_CAR_Regularizacao_Junho26.gpkg"
ARQ_VS_CAR = "IN_CAR_Regularizacao_Junho26_VS.gpkg"
ARQ_OUT_CAR = anteriores.ARQ_OUT_CAR_REG
ARQ_IN_EMB = "IN_Embargos_PANGIA_20260920.gpkg"
ARQ_VS_EMB = "IN_Embargos_PANGIA_20260920_VS.gpkg"
ARQ_OUT_EMB = anteriores.ARQ_OUT_EMB
ARQ_IN_OR = "IN_OR_2026.gpkg"
ARQ_VS_OR = "IN_OR_2026_VS.gpkg"
ARQ_OUT_OR = anteriores.ARQ_OUT_OR


def _carregar_limites():
    return anteriores.carregar_limites()


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


def _arquivos_classes(versao=None):
    """Arquivo e camada de cada classe já processada (ver computo/anteriores.py). A classe 4 e as seguintes têm um conjunto por versão da VS."""
    return anteriores.arquivos_classes(versao)


def _geoms_por_classe(codigo, versao=None):
    """Lista de (classe, geometrias líquidas disjuntas) das classes ativas de maior prioridade já processadas.

    ``versao`` (vs22q | vs2224q) é necessária quando entre as anteriores há classe cuja geometria depende da versão da VS (a 4 em diante)."""
    return anteriores.geoms_por_classe(codigo, versao)


def _geoms_classes_anteriores(codigo):
    """Geometrias líquidas (disjuntas) das classes ativas de maior prioridade já processadas."""
    por_classe = _geoms_por_classe(codigo)
    geoms = np.concatenate([g for _, g in por_classe]) if por_classe else np.array([], dtype=object)
    return geoms, [c for c, _ in por_classe]


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


def classe_outros_projetos(log, so_primeiros=None):
    """Classe 4: embargos PANGIA. A área da classe é a VS dentro do embargo (por versão da VS).

    so_primeiros: uso interno de teste (só os N primeiros embargos); não usar no cômputo."""
    import geopandas as gpd
    import pyogrio

    P = list(cfg.VS_VERSOES)
    arq_in, arq_vs = cfg.SAIDA_INSUMOS / ARQ_IN_EMB, cfg.SAIDA_INSUMOS / ARQ_VS_EMB
    for a in (arq_in, arq_vs):
        if not a.exists():
            raise FileNotFoundError(f"Não encontrei {a}. Rode 1_preparar_insumos.py embargos_pangia antes.")
    cfg.SAIDA_TIER4.mkdir(parents=True, exist_ok=True)
    g = io.ler_camada(arq_in, "IN_EMBARGOS_PANGIA")
    if so_primeiros:
        g = g.iloc[:so_primeiros].reset_index(drop=True)
    n = len(g)
    ids = g["id_proj"].to_numpy()
    emb_geoms = np.array(g.geometry.values, dtype=object)
    log(f"IN_EMBARGOS_PANGIA: {n} embargos com VS em alguma versão")
    por_classe = _geoms_por_classe("OUTROS_PROJETOS")
    prec = np.concatenate([x for _, x in por_classe])
    log(f"classes anteriores subtraídas: {[c for c, _ in por_classe]} ({len(prec)} polígonos líquidos)")

    # precedência entre embargos (E2): mais antigo primeiro, depois FID
    dias = (pd.to_datetime(g["data_embargo"], errors="coerce") - pd.Timestamp("1970-01-01")).dt.days.fillna(1e9).to_numpy()
    ranking = pd.DataFrame({"dt": dias, "fid": g["fid_orig"].astype(int), "i": np.arange(n)}).sort_values(["dt", "fid", "i"]).reset_index(drop=True)
    prioridade = np.empty(n, dtype=int)
    prioridade[ranking["i"].to_numpy()] = np.arange(n)

    log("carregando limites IBGE...")
    lim = _carregar_limites()
    R = {}
    for p in P:
        log(f"--- {p} ({cfg.VS_VERSOES[p]}) ---")
        d = pyogrio.read_dataframe(str(arq_vs), layer=f"{p}_pedacos", columns=["id_proj"])
        G = emb.uniao_por_id(d, ids)                                   # VS dentro de cada embargo
        vivo = np.array([x is not None for x in G])
        a_vs = geo.area_ha(G)
        log(f"embargos com VS: {int(vivo.sum())} | VS nos embargos (soma, antes de subtrair) {a_vs.sum():,.1f} ha")
        # 1) subtrai as classes anteriores, uma por vez (a soma é a mesma; separar mostra o efeito de cada classe)
        atual = G.copy()
        retiradas = {}
        for cod, gp in por_classe:
            iv = np.where(np.array([x is not None for x in atual]))[0]
            rest, ret = subtrair_precedentes(atual[iv], gp)
            atual[iv] = rest
            r = np.zeros(n)
            r[iv] = ret
            retiradas[cod] = r
            log(f"  sobreposição com {cod}: {r.sum():,.2f} ha em {(r > 0).sum()} embargos")
        sobre_prec = sum(retiradas.values())
        # 2) sobreposição entre embargos: a área fica com o mais antigo
        iv = np.where(np.array([x is not None for x in atual]))[0]
        liquidos = np.array([None] * n, dtype=object)
        sobre_intra = np.zeros(n)
        n_prec = np.zeros(n, dtype=int)
        if len(iv):
            pv = np.argsort(np.argsort(prioridade[iv]))
            liq_v, sob_v, np_v = liquido_por_precedencia(atual[iv], pv)
            liquidos[iv], sobre_intra[iv], n_prec[iv] = liq_v, sob_v, np_v
        a_liq = geo.area_ha(liquidos)
        log(f"  sobreposição entre embargos: {sobre_intra.sum():,.2f} ha | líquida {a_liq.sum():,.1f} ha")
        # 3) UF x bioma
        log("  UF x bioma:")
        cel = tabela_celulas(G, liquidos, lim, log=log, cada=1000)
        principais = resumo_uf_bioma_por_poligono(cel, n)
        R[p] = dict(G=G, vivo=vivo, a_vs=a_vs, retiradas=retiradas, sobre_prec=sobre_prec, sobre_intra=sobre_intra, n_prec=n_prec,
                    liquidos=liquidos, a_liq=a_liq, cel=cel, principais=principais)

    # ---- tabela de polígonos (embargos inteiros como referência) ----
    pol = g.reset_index(drop=True).copy()
    pol["prec_ordem"] = prioridade + 1
    for p in P:
        r = R[p]
        pol[f"{p}_area_vs_embargo_ha"] = r["a_vs"]
        for cod, v in r["retiradas"].items():
            pol[f"{p}_sobreposta_{cod.lower()}_ha"] = v
        pol[f"{p}_sobreposta_classes_anteriores_ha"] = r["sobre_prec"]
        pol[f"{p}_n_precedentes_sobrepostos"] = r["n_prec"]
        pol[f"{p}_sobreposta_na_classe_ha"] = r["sobre_intra"]
        pol[f"{p}_area_liquida_ha"] = r["a_liq"]
        pr = r["principais"]
        pol[f"{p}_uf_principal"] = [x[0] for x in pr]
        pol[f"{p}_ufs"] = [x[1] for x in pr]
        pol[f"{p}_bioma_principal"] = [x[2] for x in pr]
        pol[f"{p}_biomas"] = [x[3] for x in pr]
        pol[f"{p}_uf_diverge_fonte"] = [int(x[0] is not None and f is not None and not pd.isna(f) and x[0] not in str(f))
                                         for x, f in zip(pr, g["uf_fonte"].to_numpy())]
        pol[f"{p}_area_fora_ibge_ha"] = r["cel"][(r["cel"]["uf"] == "FORA") | (r["cel"]["bioma"] == "FORA")].groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0.0).to_numpy()
    pol = gpd.GeoDataFrame(pol, geometry="geometry", crs=g.crs)

    # ---- saídas ----
    out = cfg.SAIDA_TIER4 / ARQ_OUT_EMB
    io.gravar_camada(pol, out, "P2_OUTROS_PROJETOS_poligonos", primeira=True)
    liqs = {}
    for p in P:
        r = R[p]
        m = np.array([x is not None for x in r["liquidos"]])
        liq = gpd.GeoDataFrame(
            pd.DataFrame({"id_proj": ids[m], "num_tad": g["num_tad"].to_numpy()[m], "serie_tad": g["serie_tad"].to_numpy()[m],
                          "data_embargo": g["data_embargo"].to_numpy()[m], "uf_principal": pol[f"{p}_uf_principal"].to_numpy()[m],
                          "bioma_principal": pol[f"{p}_bioma_principal"].to_numpy()[m], "area_liquida_ha": r["a_liq"][m]}),
            geometry=list(r["liquidos"][m]), crs=g.crs)
        liqs[p] = liq
        io.gravar_camada(liq, out, f"P2_OUTROS_PROJETOS_{p}")

    longas = []
    for p in P:
        c = R[p]["cel"].copy()
        c["id_proj"] = ids[c["i"].to_numpy()]
        c["versao"] = p
        longas.append(c)
    cel_all = pd.concat(longas, ignore_index=True)
    cel_all = cel_all.rename(columns={"area_completa_ha": "area_vs_embargo_ha"})
    cel_all[["id_proj", "versao", "uf", "bioma", "area_vs_embargo_ha", "area_liquida_ha"]].to_csv(
        cfg.SAIDA_TIER4 / "T4_areas_uf_bioma.csv", index=False, encoding="utf-8-sig")
    agg = cel_all.groupby(["versao", "uf", "bioma"], as_index=False)[["area_vs_embargo_ha", "area_liquida_ha"]].sum()
    agg["n_embargos"] = cel_all.groupby(["versao", "uf", "bioma"])["id_proj"].nunique().to_numpy()
    agg = agg[["versao", "uf", "bioma", "n_embargos", "area_vs_embargo_ha", "area_liquida_ha"]]
    agg.to_csv(cfg.SAIDA_TIER4 / "T4_resumo_uf_bioma.csv", index=False, encoding="utf-8-sig")

    def _linha(nome, sub, p):
        r = {"grupo": nome, "n_embargos": int((sub[f"{p}_area_vs_embargo_ha"] > 0).sum()),
             "area_embargos_inteiros_ha": sub.loc[sub[f"{p}_area_vs_embargo_ha"] > 0, "area_ha_geo"].sum(),
             "vs_nos_embargos_ha": sub[f"{p}_area_vs_embargo_ha"].sum()}
        for cod in [c for c, _ in por_classe]:
            r[f"sobreposicao_{cod.lower()}_ha"] = sub[f"{p}_sobreposta_{cod.lower()}_ha"].sum()
        r["sobreposicao_entre_embargos_ha"] = sub[f"{p}_sobreposta_na_classe_ha"].sum()
        r["area_liquida_ha"] = sub[f"{p}_area_liquida_ha"].sum()
        return r

    linhas = []
    for p in P:
        linhas.append(_linha(f"{p}/TOTAL", pol, p))
        for u in sorted(pol[f"{p}_uf_principal"].dropna().unique()):
            linhas.append(_linha(f"{p}/uf/{u}", pol[pol[f"{p}_uf_principal"] == u], p))
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_TIER4 / "T4_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo[resumo["grupo"].str.endswith("/TOTAL")].round(1).to_string(index=False))

    # acumulado das classes 1, 3 e 4 (líquidas, sem dupla contagem entre classes), por versão
    def _prep(caminho, classe, cols_cat):
        a = pd.read_csv(caminho)
        a["classe"] = classe
        a["categoria"] = a[cols_cat] if isinstance(cols_cat, str) else a["categoria"]
        a = a.groupby(["classe", "categoria", "uf", "bioma"], as_index=False)[["area_liquida_ha", "vs22q_liquida_ha", "vs2224q_liquida_ha"]].sum()
        return pd.DataFrame({"classe": a["classe"], "categoria": a["categoria"], "uf": a["uf"], "bioma": a["bioma"],
                             "area_liquida_vs22q_ha": a["area_liquida_ha"], "vs_liquida_vs22q_ha": a["vs22q_liquida_ha"],
                             "area_liquida_vs2224q_ha": a["area_liquida_ha"], "vs_liquida_vs2224q_ha": a["vs2224q_liquida_ha"]})

    partes = []
    r1, r3 = cfg.SAIDA_TIER1 / "T1_resumo_categoria_uf_bioma.csv", cfg.SAIDA_TIER3 / "T3_resumo_categoria_tema_uf_bioma.csv"
    if r1.exists():
        partes.append(_prep(r1, "1 RECOOPERAR", "categoria"))
    if r3.exists():
        partes.append(_prep(r3, "3 SICAR_REGULARIZACAO", "categoria"))
    a4 = {p: agg[agg["versao"] == p].set_index(["uf", "bioma"])["area_liquida_ha"] for p in P}
    idx = sorted(set(a4["vs22q"].index) | set(a4["vs2224q"].index))
    a4d = pd.DataFrame(idx, columns=["uf", "bioma"])
    a4d.insert(0, "categoria", "embargo_pangia")
    a4d.insert(0, "classe", "4 OUTROS_PROJETOS")
    for p in P:
        v = a4[p].reindex(idx).fillna(0.0).to_numpy()
        a4d[f"area_liquida_{p}_ha"] = v
        a4d[f"vs_liquida_{p}_ha"] = v          # a área da classe 4 é a própria VS
    partes.append(a4d[partes[0].columns] if partes else a4d)
    acum = pd.concat(partes, ignore_index=True)
    acum.to_csv(cfg.SAIDA_TIER4 / "T4_acumulado_classes_1_3_4.csv", index=False, encoding="utf-8-sig")
    tot = acum.groupby("classe")[[c for c in acum.columns if c.endswith("_ha")]].sum()
    log("\nacumulado (área líquida, sem dupla contagem entre classes):\n" + tot.round(1).to_string()
        + "\n  total vs22q " + f"{tot['area_liquida_vs22q_ha'].sum():,.1f} ha | total vs2224q {tot['area_liquida_vs2224q_ha'].sum():,.1f} ha")

    # ---- conferências independentes ----
    conf = []

    def chk(nome, valor, limite, obs=""):
        conf.append({"conferencia": nome, "valor": valor, "limite": limite, "ok": bool(abs(valor) <= limite), "obs": obs})

    R_prec = geo.uniao_robusta(list(prec))
    for p in P:
        r = R[p]
        G, vivo, a_vs, a_liq, cel = r["G"], r["vivo"], r["a_vs"], r["a_liq"], r["cel"]
        tol = max(1e-3, 5e-7 * float(a_vs.sum()))   # soma geodésica não é exatamente aditiva ao cortar arestas
        chk(f"{p}: VS no embargo - (sobreposta classes anteriores + entre embargos + líquida) (ha, max por embargo)",
            float(np.abs(a_vs - r["sobre_prec"] - r["sobre_intra"] - a_liq).max()), 1e-3, "identidade de área por embargo")
        U = geo.uniao_robusta(list(G[vivo]))
        esp = geo.so_poligonos(geo.diferenca_robusta([U], [R_prec])[0]) if (U is not None and R_prec is not None) else U
        a_esp = geo.area_ha([esp])[0] if esp is not None else 0.0
        chk(f"{p}: área líquida - área (união da VS nos embargos - união das classes anteriores) (ha)", float(a_liq.sum() - a_esp), tol,
            "soma dos líquidos x cálculo independente por união")
        lg = liqs[p].geometry.values
        tree = STRtree(lg)
        ii, jj = tree.query(lg, predicate="intersects")
        m = ii < jj
        ov = geo.area_ha(geo.intersecao_robusta(lg[ii[m]], lg[jj[m]])) if m.any() else np.array([0.0])
        chk(f"{p}: sobreposição entre polígonos líquidos (ha)", float(ov.sum()), 1e-3)
        tp = STRtree(prec)
        ii, jj = tp.query(lg, predicate="intersects")
        ov2 = geo.area_ha(geo.intersecao_robusta(lg[ii], prec[jj])) if len(ii) else np.array([0.0])
        chk(f"{p}: sobreposição dos líquidos com as classes 1 e 3 (ha)", float(ov2.sum()), 1e-3)
        soma_cel = cel.groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0).to_numpy()
        chk(f"{p}: VS no embargo - soma das células UF x bioma (ha, max por embargo)", float(np.abs(a_vs - soma_cel).max()), 0.01)
        fora = float(cel.loc[(cel["uf"] == "FORA") | (cel["bioma"] == "FORA"), "area_completa_ha"].sum())
        chk(f"{p}: VS fora dos limites IBGE de UF ou bioma (ha)", fora, 0.0005 * float(a_vs.sum()),
            f"{fora:,.1f} ha ficam como UF/bioma 'FORA'; tolerância 0,05% da área")
        d = np.abs(g[f"{p}_area_ha"].to_numpy(float) - a_vs)
        chk(f"{p}: atributo da VS (passo 1) x VS recalculada nos embargos (ha, max por embargo)", float(d.max()), 0.01)
        dentro = geo.area_ha([geo.so_poligonos(x) if x is not None else None for x in
                              geo.diferenca_robusta(list(G[vivo]), list(emb_geoms[vivo]))]).sum()
        chk(f"{p}: VS fora do polígono do embargo (ha)", float(dentro), 1e-3, "a VS da classe está toda dentro do embargo")
        chk(f"{p}: embargos com VS sem UF principal", float((vivo & pol[f"{p}_uf_principal"].isna().to_numpy()).sum()), 0)
        chk(f"{p}: embargos com UF calculada diferente da UF da fonte", float(pol[f"{p}_uf_diverge_fonte"].sum()), 0.02 * int(vivo.sum()),
            "informativo (limite: 2% dos embargos): UF pelos limites do IBGE x campo 'uf' do embargo")
        chk(f"{p}: geometrias líquidas inválidas", float((~shapely.is_valid(lg)).sum()), 0)
    pessoais = [c for c in pol.columns if c in cfg.COLUNAS_PESSOAIS_PANGIA or any(k in c.lower() for k in ("cpf", "cnpj", "nome_", "editor"))]
    chk("colunas com possível dado pessoal nas saídas", float(len(pessoais)), 0, str(pessoais))
    conf = pd.DataFrame(conf)
    conf.to_csv(cfg.SAIDA_TIER4 / "T4_conferencias.csv", index=False, encoding="utf-8-sig")
    log("\n" + conf.to_string(index=False))
    if not conf["ok"].all():
        log("ATENÇÃO: há conferências fora do limite (ver T4_conferencias.csv).")
    log(f"gravado: {out}")
    return pol, liqs, cel_all, resumo, conf


def classe_or(log):
    """Classe 5: Observatório da Restauração. Área total dos polígonos; subtrai as classes 1, 3 e 4 (por versão da VS).

    Desde o ORR 2026, ``IN_OR`` traz um polígono por projeto (86 mil, contra 4 do ORR 2025 dissolvido por bioma) e projetos
    podem se sobrepor entre si (submissões distintas cobrindo a mesma área); a precedência entre eles é só o ``fid_orig``
    (menor primeiro), como não há outro critério nos dados de origem."""
    import geopandas as gpd
    import pyogrio

    P = list(cfg.VS_VERSOES)
    arq_in, arq_vs = cfg.SAIDA_INSUMOS / ARQ_IN_OR, cfg.SAIDA_INSUMOS / ARQ_VS_OR
    for a in (arq_in, arq_vs):
        if not a.exists():
            raise FileNotFoundError(f"Não encontrei {a}. Rode 1_preparar_insumos.py or antes.")
    cfg.SAIDA_TIER5.mkdir(parents=True, exist_ok=True)
    g = io.ler_camada(arq_in, "IN_OR")
    n = len(g)
    ids = g["id_proj"].to_numpy()
    geoms = np.array(g.geometry.values, dtype=object)
    a_bruta = g["area_ha_geo"].to_numpy(float)
    log(f"IN_OR: {n} polígonos, {a_bruta.sum():,.1f} ha (área total)")
    vs = {p: PedacosVS(np.array(pyogrio.read_dataframe(str(arq_vs), layer=f"{p}_pedacos", columns=["id_proj"]).geometry.values, dtype=object)) for p in P}
    lim = _carregar_limites()
    # sobreposição entre projetos do ORR: esperada > 0 desde o ORR 2026 (nível de projeto); precedência pelo FID de origem
    prioridade = np.argsort(np.argsort(g["fid_orig"].astype(int).to_numpy() * 10 + np.arange(n)))
    R, liqs = {}, {}
    for p in P:
        log(f"--- {p} ({cfg.VS_VERSOES[p]}) ---")
        por_classe = _geoms_por_classe("OR", p)
        prec = np.concatenate([x for _, x in por_classe])
        log(f"classes anteriores subtraídas: {[c for c, _ in por_classe]} ({len(prec)} polígonos líquidos)")
        atual, retiradas = geoms.copy(), {}
        for cod, gp in por_classe:
            iv = np.where(np.array([x is not None for x in atual]))[0]
            rest, ret = subtrair_precedentes(atual[iv], gp)
            atual[iv] = rest
            r = np.zeros(n)
            r[iv] = ret
            retiradas[cod] = r
            log(f"  sobreposição com {cod}: {r.sum():,.2f} ha")
        sobre_prec = sum(retiradas.values())
        iv = np.where(np.array([x is not None for x in atual]))[0]
        liquidos = np.array([None] * n, dtype=object)
        sobre_intra = np.zeros(n)
        n_prec = np.zeros(n, dtype=int)
        if len(iv):
            pv = np.argsort(np.argsort(prioridade[iv]))
            liq_v, sob_v, np_v = liquido_por_precedencia(atual[iv], pv)
            liquidos[iv], sobre_intra[iv], n_prec[iv] = liq_v, sob_v, np_v
        a_liq = geo.area_ha(liquidos)
        log(f"  sobreposição entre polígonos do ORR: {sobre_intra.sum():,.2f} ha | líquida {a_liq.sum():,.1f} ha")
        log("  UF x bioma e VS:")
        cel = tabela_celulas(geoms, liquidos, lim, {p: vs[p]}, [p], log=log, cada=1000)
        R[p] = dict(prec=prec, retiradas=retiradas, sobre_prec=sobre_prec, sobre_intra=sobre_intra, n_prec=n_prec, liquidos=liquidos,
                    a_liq=a_liq, cel=cel, principais=resumo_uf_bioma_por_poligono(cel, n))

    # ---- tabela de polígonos ----
    pol = g.reset_index(drop=True).copy()
    pol["prec_ordem"] = prioridade + 1
    for p in P:
        r = R[p]
        for cod, v in r["retiradas"].items():
            pol[f"{p}_sobreposta_{cod.lower()}_ha"] = v
        pol[f"{p}_sobreposta_classes_anteriores_ha"] = r["sobre_prec"]
        pol[f"{p}_n_precedentes_sobrepostos"] = r["n_prec"]
        pol[f"{p}_sobreposta_na_classe_ha"] = r["sobre_intra"]
        pol[f"{p}_area_liquida_ha"] = r["a_liq"]
        pr = r["principais"]
        pol[f"{p}_uf_principal"], pol[f"{p}_ufs"] = [x[0] for x in pr], [x[1] for x in pr]
        pol[f"{p}_bioma_principal"], pol[f"{p}_biomas"] = [x[2] for x in pr], [x[3] for x in pr]
        c = r["cel"]
        pol[f"{p}_area_fora_ibge_ha"] = c[(c["uf"] == "FORA") | (c["bioma"] == "FORA")].groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0.0).to_numpy()
        soma = c.groupby("i").sum(numeric_only=True)
        pol[f"{p}_completa_recalc_ha"] = soma[f"{p}_completa_ha"].reindex(range(n)).fillna(0.0).to_numpy()
        pol[f"{p}_liq_ha"] = soma[f"{p}_liquida_ha"].reindex(range(n)).fillna(0.0).to_numpy()
    pol = gpd.GeoDataFrame(pol, geometry="geometry", crs=g.crs)

    # ---- saídas ----
    out = cfg.SAIDA_TIER5 / ARQ_OUT_OR
    io.gravar_camada(pol, out, "P2_OR_poligonos", primeira=True)
    for p in P:
        r = R[p]
        linhas = []
        for i in range(n):
            if r["liquidos"][i] is None:
                continue
            for k, parte in enumerate(shapely.get_parts(r["liquidos"][i])):
                linhas.append((ids[i], g["bioma_fonte"].iloc[i], k, parte))
        d = pd.DataFrame(linhas, columns=["id_proj", "bioma_fonte", "parte", "geometry"])
        d["area_ha"] = geo.area_ha(d["geometry"].values)
        liqs[p] = gpd.GeoDataFrame(d, geometry="geometry", crs=g.crs)      # partes simples: as classes seguintes recortam peça a peça
        io.gravar_camada(liqs[p], out, f"P2_OR_{p}")

    longas = []
    for p in P:
        c = R[p]["cel"].copy()
        c["id_proj"] = ids[c["i"].to_numpy()]
        c["bioma_fonte"] = g["bioma_fonte"].to_numpy()[c["i"].to_numpy()]
        c["versao"] = p
        c = c.rename(columns={f"{p}_completa_ha": "vs_inteira_ha", f"{p}_liquida_ha": "vs_liquida_ha"})
        longas.append(c)
    cel_all = pd.concat(longas, ignore_index=True)
    cols = ["id_proj", "bioma_fonte", "versao", "uf", "bioma", "area_completa_ha", "area_liquida_ha", "vs_inteira_ha", "vs_liquida_ha"]
    cel_all[cols].to_csv(cfg.SAIDA_TIER5 / "T5_areas_uf_bioma.csv", index=False, encoding="utf-8-sig")
    agg = cel_all.groupby(["versao", "uf", "bioma"], as_index=False)[["area_completa_ha", "area_liquida_ha", "vs_inteira_ha", "vs_liquida_ha"]].sum()
    agg.to_csv(cfg.SAIDA_TIER5 / "T5_resumo_uf_bioma.csv", index=False, encoding="utf-8-sig")

    linhas = []
    for p in P:
        for nome, sub in [("TOTAL", pol)] + [(f"bioma/{b}", pol[pol["bioma_fonte"] == b]) for b in sorted(pol["bioma_fonte"].unique())]:
            r = {"grupo": f"{p}/{nome}", "n_poligonos": len(sub), "area_poligonos_inteiros_ha": sub["area_ha_geo"].sum()}
            for cod in R[P[0]]["retiradas"]:
                r[f"sobreposicao_{cod.lower()}_ha"] = sub[f"{p}_sobreposta_{cod.lower()}_ha"].sum()
            r["sobreposicao_na_classe_ha"] = sub[f"{p}_sobreposta_na_classe_ha"].sum()
            r["area_liquida_ha"] = sub[f"{p}_area_liquida_ha"].sum()
            r["vs_atributo_poligonos_ha"] = sub[f"{p}_area_ha"].sum()
            r["vs_liquida_ha"] = sub[f"{p}_liq_ha"].sum()
            linhas.append(r)
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_TIER5 / "T5_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo[resumo["grupo"].str.endswith("/TOTAL")].round(1).to_string(index=False))

    # acumulado das classes 1, 3, 4 e 5 (parte do acumulado já gravado pela classe 4)
    a4 = cfg.SAIDA_TIER4 / "T4_acumulado_classes_1_3_4.csv"
    if not a4.exists():
        raise FileNotFoundError(f"Não encontrei {a4}. Rode a classe OUTROS_PROJETOS antes.")
    acum = pd.read_csv(a4)
    ag = {p: agg[agg["versao"] == p].set_index(["uf", "bioma"]) for p in P}
    idx = sorted(set(ag["vs22q"].index) | set(ag["vs2224q"].index))
    a5 = pd.DataFrame(idx, columns=["uf", "bioma"])
    a5.insert(0, "categoria", "or")
    a5.insert(0, "classe", "5 OR")
    for p in P:
        d = ag[p].reindex(idx).fillna(0.0)
        a5[f"area_liquida_{p}_ha"] = d["area_liquida_ha"].to_numpy()
        a5[f"vs_liquida_{p}_ha"] = d["vs_liquida_ha"].to_numpy()
    acum = pd.concat([acum, a5[acum.columns]], ignore_index=True)
    acum.to_csv(cfg.SAIDA_TIER5 / "T5_acumulado_classes_1_3_4_5.csv", index=False, encoding="utf-8-sig")
    tot = acum.groupby("classe")[[c for c in acum.columns if c.endswith("_ha")]].sum()
    log("\nacumulado (área líquida, sem dupla contagem entre classes):\n" + tot.round(1).to_string()
        + f"\n  total vs22q {tot['area_liquida_vs22q_ha'].sum():,.1f} ha | total vs2224q {tot['area_liquida_vs2224q_ha'].sum():,.1f} ha")

    # ---- conferências independentes ----
    conf = []

    def chk(nome, valor, limite, obs=""):
        conf.append({"conferencia": nome, "valor": valor, "limite": limite, "ok": bool(abs(valor) <= limite), "obs": obs})

    chk("área geodésica - área declarada no arquivo (ha, soma dos polígonos)", float(a_bruta.sum() - g["area_decl_ha"].sum()), 0.001 * float(a_bruta.sum()),
        "o campo de área do ORR foi calculado em projeção equivalente; devem coincidir dentro de 0,1%")
    U = geo.uniao_robusta(list(geoms))
    sobre_bruta = float(a_bruta.sum() - geo.area_ha([U])[0])
    chk("soma dos polígonos - área da união (ha): sobreposição entre projetos do ORR", sobre_bruta, 0.5 * float(a_bruta.sum()),
        "informativo desde o ORR 2026 (nível de projeto): diferente do ORR 2025 (4 polígonos dissolvidos por bioma, sem sobreposição "
        "por construção), projetos podem se sobrepor entre si (submissões distintas na mesma área); a área líquida abaixo já trata "
        "essa sobreposição pela precedência de fid_orig, então o valor aqui é só para acompanhar a magnitude")
    for p in P:
        r = R[p]
        a_liq, cel, prec = r["a_liq"], r["cel"], r["prec"]
        tol = max(1e-3, 5e-7 * float(a_bruta.sum()))
        chk(f"{p}: área inteira - (sobreposta classes anteriores + na classe + líquida) (ha, max por polígono)",
            float(np.abs(a_bruta - r["sobre_prec"] - r["sobre_intra"] - a_liq).max()), 1e-3, "identidade de área por polígono")
        R_prec = geo.uniao_robusta(list(prec))
        esp = geo.so_poligonos(geo.diferenca_robusta([U], [R_prec])[0]) if (U is not None and R_prec is not None) else U
        a_esp = geo.area_ha([esp])[0] if esp is not None else 0.0
        chk(f"{p}: área líquida - área (união do ORR - união das classes 1, 3 e 4) (ha)", float(a_liq.sum() - a_esp), tol, "soma dos líquidos x cálculo independente por união")
        lg = liqs[p].geometry.values
        tree = STRtree(lg)
        ii, jj = tree.query(lg, predicate="intersects")
        m = ii < jj
        ov = geo.area_ha(geo.intersecao_robusta(lg[ii[m]], lg[jj[m]])) if m.any() else np.array([0.0])
        chk(f"{p}: sobreposição entre partes líquidas (ha)", float(ov.sum()), 1e-3)
        tp = STRtree(prec)
        ii, jj = tp.query(lg, predicate="intersects")
        ov2 = geo.area_ha(geo.intersecao_robusta(lg[ii], prec[jj])) if len(ii) else np.array([0.0])
        chk(f"{p}: sobreposição dos líquidos com as classes 1, 3 e 4 (ha)", float(ov2.sum()), 1e-3)
        chk(f"{p}: área inteira - soma das células UF x bioma (ha, max por polígono)",
            float(np.abs(a_bruta - cel.groupby("i")["area_completa_ha"].sum().reindex(range(n)).fillna(0).to_numpy()).max()), tol)
        fora = float(cel.loc[(cel["uf"] == "FORA") | (cel["bioma"] == "FORA"), "area_completa_ha"].sum())
        chk(f"{p}: área fora dos limites IBGE de UF ou bioma (ha)", fora, 0.0005 * float(a_bruta.sum()), f"{fora:,.3f} ha ficam como 'FORA'; tolerância 0,05%")
        d = np.abs(pol[f"{p}_area_ha"].to_numpy(float) - pol[f"{p}_completa_recalc_ha"].to_numpy(float))
        chk(f"{p}: atributo da VS (passo 1) x recálculo por peças (ha, max por polígono)", float(d.max()), 0.01)
        chk(f"{p}: VS líquida <= VS inteira, por polígono (ha, pior caso)", float(min(0.0, (pol[f"{p}_completa_recalc_ha"] - pol[f"{p}_liq_ha"]).min())), 1e-6)
        chk(f"{p}: polígonos sem UF principal", float(pol[f"{p}_uf_principal"].isna().sum()), 0)
        chk(f"{p}: geometrias líquidas inválidas", float((~shapely.is_valid(lg)).sum()), 0)
    conf = pd.DataFrame(conf)
    conf.to_csv(cfg.SAIDA_TIER5 / "T5_conferencias.csv", index=False, encoding="utf-8-sig")
    log("\n" + conf.to_string(index=False))
    if not conf["ok"].all():
        log("ATENÇÃO: há conferências fora do limite (ver T5_conferencias.csv).")
    log(f"gravado: {out}")
    return pol, liqs, cel_all, resumo, conf


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pedidas = [a.upper() for a in argv] or CLASSES_IMPLEMENTADAS
    for c in pedidas:
        if c not in CLASSES_IMPLEMENTADAS:
            print(f"classe '{c}': ainda não implementada.")
            return 1
    # cada classe grava o log na própria pasta (o comando sem argumento roda todas, na ordem da hierarquia)
    classes = [
        ("RECOOPERAR", classe_recooperar, cfg.SAIDA_TIER1, "_log_passo2.txt"),
        ("CAR_REGULARIZACAO", classe_car_regularizacao, cfg.SAIDA_TIER3, "_log_passo2_car.txt"),
        ("OUTROS_PROJETOS", classe_outros_projetos, cfg.SAIDA_TIER4, "_log_passo2_outros.txt"),
        ("OR", classe_or, cfg.SAIDA_TIER5, "_log_passo2_or.txt"),
    ]
    for nome, funcao, pasta, arq in classes:
        if nome not in pedidas:
            continue
        pasta.mkdir(parents=True, exist_ok=True)
        arq_log = pasta / arq

        def log(m, _a=arq_log):
            io.log(m, _a)

        log(f"Passo 2 - Camada 2 (projetos) - classe {nome}")
        funcao(log)
        log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
