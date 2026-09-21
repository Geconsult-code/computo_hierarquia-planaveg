"""Classes 9 a 11 (CAR: APP, AUR e RL dos imóveis selecionados): leitura das peças, união por imóvel, precedências e conferências.

As peças vêm dos cruzamentos já calculados (``cfg.FONTES['car_cruzamentos']``): VS qualificada x APP/AUR/RL dos imóveis selecionados de cada
categoria (Habilitados, Analisados, Não analisados), uma peça por tema do CAR x feição de VS. Duas coisas do dado moldam o método:

* as peças se SOBREPÕEM dentro do mesmo imóvel (temas de APP sobrepostos, duplicatas exatas): a soma de ``area_ha`` é várias vezes a área
  da união. Por isso, antes de qualquer precedência, as peças de cada imóvel (categoria, cod_imovel, bioma da VS, ano) são unidas;
* cada UF ocupa um bloco contínuo de FIDs em cada camada, e o processamento é por UF (uma UF, uma versão da VS, as três classes).

Precedência (config_computo, confirmada em 21/09/2026): os imóveis Habilitados precedem os Analisados e os Não analisados em qualquer classe;
dentro de cada grupo a classe manda (APP > AUR > RL); entre Analisados e Não analisados a categoria desempata dentro da classe (Analisados >
Não analisados) e, na mesma categoria, vence o menor cod_imovel. O cálculo segue "blocos" na ordem APP-Habilitados, AUR-Habilitados,
RL-Habilitados, APP-(Analisados e Não analisados), AUR-(idem), RL-(idem); cada bloco subtrai as classes 1, 3, 4, 5, 6, 7 e 8 (líquidas, na
versão da VS) e os blocos anteriores da mesma UF. Os resultados são reunidos por classe (9 APP, 10 AUR, 11 RL).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.errors import GEOSException
from shapely.strtree import STRtree

import config_computo as cfg
from . import anteriores
from . import geometria as geo
from . import governanca as gov
from . import io_dados as io
from .hierarquia import liquido_por_precedencia, subtrair_grandes

CLASSES = ["APP", "AUR", "RL"]
CATEGORIAS = list(cfg.CAR_CATEGORIAS_PRECEDENCIA)
GRUPOS = [list(g) for g in cfg.CAR_GRUPOS_PRECEDENCIA]
ROTULOS = {"APP": "9 APP", "AUR": "10 AUR", "RL": "11 RL"}
PASTAS = {"APP": cfg.SAIDA_TIER9, "AUR": cfg.SAIDA_TIER10, "RL": cfg.SAIDA_TIER11}
ARQUIVOS = {"APP": anteriores.ARQ_OUT_APP, "AUR": anteriores.ARQ_OUT_AUR, "RL": anteriores.ARQ_OUT_RL}
CHAVE_IMOVEL = ["categoria", "cod_imovel", "bioma_vs", "ano"]
COLUNAS_LEITURA = ["uf", "cod_imovel", "bioma", "ano", "des_condic", "area_ha"]
MIN_HA = 1e-6
LIMITE_PECAS_CONFERENCIA_COMPLETA = 200_000     # acima disso, a conferência por união independente só roda com --conferencia completa


def blocos():
    """[(classe, índice do grupo, código do bloco)] na ordem de processamento: grupo a grupo e, em cada grupo, APP, AUR e RL."""
    return [(cl, gi, f"{cl}_{cfg.CAR_ROTULOS_GRUPOS[gi]}") for gi in range(len(GRUPOS)) for cl in CLASSES]


# ---------------------------------------------------------------------------
# Leitura por UF (índice de FIDs)
# ---------------------------------------------------------------------------
def arquivo_cruzamento(versao_arq: str, categoria: str) -> Path:
    c = cfg.FONTES["car_cruzamentos"]
    return cfg.RAIZ / c["pasta"] / c[versao_arq].format(categoria=categoria)


def _abrir_leitura(arquivo):
    """SQLite só para leitura (não cria arquivos auxiliares na pasta dos dados)."""
    try:
        return sqlite3.connect(Path(arquivo).resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return sqlite3.connect(str(arquivo))


def indice_fids(arquivo, camada) -> dict:
    """{uf: (fid_min, fid_max, n)} de uma camada de cruzamento (uma varredura da tabela; o resultado é guardado em disco)."""
    arquivo = Path(arquivo)
    st = arquivo.stat()
    cache_arq = cfg.SAIDA_TIER9 / "_indice_fids_car.json"
    chave = f"{arquivo.name}|{camada}"
    cache = {}
    if cache_arq.exists():
        try:
            cache = json.loads(cache_arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
    e = cache.get(chave)
    if e and e.get("tam") == st.st_size and e.get("mtime") == int(st.st_mtime):
        return {uf: tuple(v) for uf, v in e["ufs"].items()}
    con = _abrir_leitura(arquivo)
    try:
        linhas = con.execute(f'SELECT uf, MIN(fid), MAX(fid), COUNT(*) FROM "{camada}" GROUP BY uf').fetchall()
    finally:
        con.close()
    ufs = {uf: (int(a), int(b), int(n)) for uf, a, b, n in linhas}
    cache[chave] = {"tam": st.st_size, "mtime": int(st.st_mtime), "ufs": ufs}
    cfg.SAIDA_TIER9.mkdir(parents=True, exist_ok=True)
    cache_arq.write_text(json.dumps(cache), encoding="utf-8")
    return ufs


def ler_pecas_camada(versao_arq, categoria, classe, uf):
    """Peças de uma UF em uma camada (categoria x classe): DataFrame com ``geometry`` (objetos), ``categoria``, ``classe``."""
    arq = arquivo_cruzamento(versao_arq, categoria)
    camada = cfg.FONTES["car_cruzamentos"]["camada"].format(classe=classe, categoria=categoria)
    if not arq.exists():
        raise FileNotFoundError(f"Não encontrei {arq}")
    idx = indice_fids(arq, camada).get(uf)
    vazio = pd.DataFrame(columns=COLUNAS_LEITURA + ["geometry", "categoria", "classe"])
    if idx is None:
        return vazio
    a, b, n = idx
    where = f"fid >= {a} AND fid <= {b}" if b - a + 1 == n else f"uf = '{uf}'"
    g = io.ler_camada(arq, camada, colunas=COLUNAS_LEITURA, where=where)
    d = pd.DataFrame(g.drop(columns="geometry")).reset_index(drop=True)
    d["geometry"] = list(g.geometry.values)
    d["categoria"] = categoria
    d["classe"] = classe
    return d


def ler_pecas_uf(uf, versoes):
    """{versão da VS: peças (DataFrame)} de todas as categorias e classes da UF.

    vs22q = VS 2022 qualificada. vs2224q = VS 2022 qualificada nos biomas que a 2024 não cobre + VS 2024 qualificada (Amazônia e Cerrado)."""
    def _ler(versao_arq):
        partes = [ler_pecas_camada(versao_arq, cat, cl, uf) for cat in CATEGORIAS for cl in CLASSES]
        partes = [p for p in partes if len(p)]
        return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=COLUNAS_LEITURA + ["geometry", "categoria", "classe"])

    saida = {}
    d22 = _ler("2022q")
    if "vs22q" in versoes:
        saida["vs22q"] = d22
    if "vs2224q" in versoes:
        d24 = _ler("2024")
        bio24 = cfg.FONTES["car_cruzamentos"]["biomas_2024"]
        saida["vs2224q"] = pd.concat([d22[~d22["bioma"].isin(bio24)], d24], ignore_index=True)
    return saida


def preparar_pecas(d):
    """Geometrias reparadas (2D, só polígonos), colunas padronizadas e área geodésica. Devolve (DataFrame, info)."""
    d = d.rename(columns={"bioma": "bioma_vs", "uf": "uf_car", "area_ha": "area_ha_arq"}).reset_index(drop=True)
    if len(d) == 0:
        return d.assign(area_ha_geo=np.array([], dtype=float)), {"n_lidas": 0, "n_vazias": 0, "n_reparadas": 0}
    geoms, inval = geo.reparar(np.array(d["geometry"].values, dtype=object))
    ok = np.array([g is not None and not g.is_empty for g in geoms])
    d["geometry"] = list(geoms)
    n0 = len(d)
    d = d[ok].reset_index(drop=True)
    d["area_ha_geo"] = geo.area_ha(np.array(d["geometry"].values, dtype=object))
    return d, {"n_lidas": n0, "n_vazias": int((~ok).sum()), "n_reparadas": int(inval.sum())}


# ---------------------------------------------------------------------------
# União por imóvel e precedência
# ---------------------------------------------------------------------------
GRADE = 1e-9     # graus (~0,1 mm): grade da união com precisão fixa


def uniao_grade(geoms):
    """União com precisão fixa (grade de 1e-9 grau). A união comum do GEOS, com peças duplicadas e sobrepostas, às vezes descarta trechos
    inteiros SEM lançar erro (no AC, 3 ha em 4 imóveis; achado pela conferência independente); com grade a sobreposição é robusta."""
    g = np.array([x for x in geoms if x is not None and not x.is_empty], dtype=object)
    if len(g) == 0:
        return None
    if len(g) == 1:
        return g[0]
    try:
        u = shapely.union_all(g, grid_size=GRADE)
    except GEOSException:
        u = shapely.union_all(np.array([shapely.make_valid(x) for x in g], dtype=object), grid_size=GRADE)
    return geo.so_poligonos(u)


def uniao_verificada(pecas):
    """(união das peças, nº de peças cuja cobertura precisou ser corrigida). A união usa grade e é conferida: cada peça deve estar dentro dela."""
    g = np.array([x for x in pecas if x is not None and not x.is_empty], dtype=object)
    u = uniao_grade(g)
    if u is None or len(g) < 2:
        return u, 0
    corrigidas = 0
    for _ in range(2):
        try:
            r = shapely.difference(g, u)
        except GEOSException:
            r = geo.diferenca_robusta(g, np.array([u] * len(g), dtype=object))
        cand = np.where(np.array([x is not None and not x.is_empty for x in r]) & (shapely.area(np.array(r, dtype=object)) > 1e-11))[0]
        if len(cand) == 0:
            break
        a = geo.area_ha(r[cand])
        lim = np.maximum(1e-4, 1e-6 * geo.area_ha(g[cand]))
        viol = cand[a > lim]
        if len(viol) == 0:
            break
        corrigidas += len(viol)
        u = uniao_grade([u] + list(r[viol]))
    return u, corrigidas


def unir_por_imovel(d):
    """Uma linha por (categoria, cod_imovel, bioma da VS, ano): a união das peças do imóvel na classe.

    Colunas: categoria, cod_imovel, bioma_vs, ano, uf_car, des_condic, n_pecas, area_pecas_arq_ha, area_pecas_geo_ha, geometry (a união)."""
    geoms = np.array(d["geometry"].values, dtype=object)
    a_arq = d["area_ha_arq"].to_numpy(float)
    a_geo = d["area_ha_geo"].to_numpy(float)
    grupos = d.groupby(CHAVE_IMOVEL, sort=True, dropna=False).indices
    ug, primeira, n_p, s_arq, s_geo, n_corr = [], [], [], [], [], 0
    for _, pos in grupos.items():
        primeira.append(pos[0])
        n_p.append(len(pos))
        s_arq.append(float(a_arq[pos].sum()))
        s_geo.append(float(a_geo[pos].sum()))
        if len(pos) == 1:
            ug.append(geoms[pos[0]])
        else:
            un, nc = uniao_verificada(geoms[pos])
            n_corr += nc
            ug.append(geo.so_poligonos(un) if un is not None else None)
    primeira = np.array(primeira, dtype=int)
    u = d.iloc[primeira][CHAVE_IMOVEL + ["uf_car", "des_condic"]].reset_index(drop=True)
    u["n_pecas"] = n_p
    u["area_pecas_arq_ha"] = s_arq
    u["area_pecas_geo_ha"] = s_geo
    u["geometry"] = ug
    vazio = np.array([g is None or g.is_empty for g in ug])
    return u[~vazio].reset_index(drop=True), int(vazio.sum()), n_corr


def ordem_precedencia(u) -> np.ndarray:
    """Posição única de cada imóvel na precedência (0 = maior): categoria, cod_imovel, bioma da VS, ano."""
    pos = {c: i for i, c in enumerate(CATEGORIAS)}
    cat = u["categoria"].map(pos).fillna(len(CATEGORIAS)).to_numpy(int)
    return gov._rank(pd.DataFrame({
        "cat": cat, "cod": u["cod_imovel"].astype(str).to_numpy(), "bioma": u["bioma_vs"].astype(str).to_numpy(),
        "ano": pd.to_numeric(u["ano"], errors="coerce").fillna(0).to_numpy(), "i": np.arange(len(u))}))


# ---------------------------------------------------------------------------
# Conferências independentes
# ---------------------------------------------------------------------------
def sobrepoe(a, b):
    """Pares (i, j) de a x b cujos INTERIORES se sobrepõem (toque na divisa não conta) e a área da interseção (ha)."""
    if len(a) == 0 or len(b) == 0:
        return np.array([], int), np.array([], int), np.array([])
    ii, jj = STRtree(b).query(a, predicate="intersects")
    if len(ii) == 0:
        return ii, jj, np.array([])
    ok = shapely.relate_pattern(a[ii], b[jj], "T********")
    ii, jj = ii[ok], jj[ok]
    return ii, jj, (geo.area_ha(geo.intersecao_robusta(a[ii], b[jj])) if len(ii) else np.array([]))


def sobreposicao_com_grandes(partes, grandes) -> float:
    """Área (ha) em que as ``partes`` se sobrepõem a ``grandes`` (polígonos que podem ter milhões de vértices).

    Cada par que se toca é conferido com ``grandes[j]`` recortado pela caixa da parte (a interseção não muda e o custo cai muito)."""
    partes = np.array(partes, dtype=object)
    grandes = np.array([g for g in np.atleast_1d(np.array(grandes, dtype=object)) if g is not None and not g.is_empty], dtype=object)
    if len(partes) == 0 or len(grandes) == 0:
        return 0.0
    ii, jj = STRtree(grandes).query(partes, predicate="intersects")
    total, e = 0.0, 1e-6
    for i, j in zip(ii, jj):
        x0, y0, x1, y1 = partes[i].bounds
        c = geo.clip_seguro(grandes[j], x0 - e, y0 - e, x1 + e, y1 + e)
        if c is None or c.is_empty:
            continue
        r = geo.so_poligonos(geo.intersecao_robusta([partes[i]], [c])[0])
        if r is not None:
            a = geo.area_ha([r])[0]
            total += a if a > 1e-4 else 0.0     # abaixo de 1 m2 é ruído de coordenadas na divisa
    return total


def liquido_independente(geoms, prec):
    """(área da união das peças, área da união das peças menos a união de ``prec``) em ha, por componente conexo.

    Cálculo que não usa a união por imóvel nem a precedência. A união é dividida em componentes; em cada um, subtrai-se só o que o toca,
    com cada precedente recortado pela caixa do componente (as classes 6 a 8 têm polígonos com milhões de vértices)."""
    geoms = np.array([g for g in geoms if g is not None and not g.is_empty], dtype=object)
    U = uniao_grade(geoms)
    if U is None:
        return 0.0, 0.0
    comps = shapely.get_parts(U)
    a_U = float(geo.area_ha(comps).sum())
    prec = np.array([g for g in prec if g is not None and not g.is_empty], dtype=object)
    if len(prec) == 0:
        return a_U, a_U
    ii, jj = STRtree(prec).query(comps, predicate="intersects")
    tocados = np.unique(ii)
    livres = np.setdiff1d(np.arange(len(comps)), tocados)
    total = float(geo.area_ha(comps[livres]).sum()) if len(livres) else 0.0
    ordem = np.argsort(ii, kind="stable")
    ii, jj = ii[ordem], jj[ordem]
    if len(ii):
        inicios = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
        fins = np.r_[inicios[1:], len(ii)]
        e = 1e-6
        for a, b in zip(inicios, fins):
            g = comps[ii[a]]
            x0, y0, x1, y1 = g.bounds
            cortes = [geo.clip_seguro(prec[j], x0 - e, y0 - e, x1 + e, y1 + e) for j in jj[a:b]]
            Up = geo.uniao_robusta([c for c in cortes if c is not None and not c.is_empty])
            r = geo.so_poligonos(geo.diferenca_robusta([g], [Up])[0]) if Up is not None else g
            total += float(geo.area_ha([r])[0]) if r is not None else 0.0
    return a_U, total


# ---------------------------------------------------------------------------
# Uma classe, uma UF, uma versão da VS
# ---------------------------------------------------------------------------
def processar_classe(classe, d, prior, cel, tag, log=None, conferencia="auto"):
    """Classe do CAR em uma UF e versão da VS.

    d      : peças da classe (``preparar_pecas``);  prior : lista de (classe, polígonos líquidos disjuntos) das classes de maior prioridade
    Devolve dict: ``partes`` (GeoDataFrame das partes líquidas por UF x bioma), ``unidades`` (tabela por imóvel, sem geometria),
    ``liquidos`` (partes líquidas, para as classes seguintes), ``conferencias`` (lista de dicts)."""
    import geopandas as gpd

    def lg(m):
        if log:
            log(m)

    conf = []

    def chk(nome, valor, limite, obs=""):
        conf.append({"conferencia": f"{tag}: {nome}", "valor": float(valor), "limite": float(limite), "ok": bool(abs(valor) <= limite), "obs": obs})

    u, n_vazias, n_corr = unir_por_imovel(d)
    n = len(u)
    geoms = np.array(u["geometry"].values, dtype=object)
    a_uni = geo.area_ha(geoms)
    a_pec = u["area_pecas_geo_ha"].to_numpy(float)
    sobre_imovel = a_pec - a_uni
    sobre_imovel = np.where(np.abs(sobre_imovel) < 1e-6, 0.0, sobre_imovel)          # ruído geodésico (-0.0)
    lg(f"  {len(d):,} peças -> {n:,} imóveis x bioma (união por imóvel: {sobre_imovel.sum():,.1f} ha de sobreposição interna"
       + (f"; cobertura corrigida em {n_corr:,} peças" if n_corr else "") + ")")
    atual, retiradas = geoms.copy(), {}
    for cod, gp in prior:
        iv = np.where(np.array([x is not None for x in atual]))[0]
        r = np.zeros(n)
        if len(iv):
            rest, ret = subtrair_grandes(atual[iv], gp)
            atual[iv] = rest
            r[iv] = ret
        retiradas[cod] = r
        lg(f"  sobreposição com {cod}: {r.sum():,.2f} ha ({int((r > 0).sum()):,} imóveis)")
    sobre_prec = sum(retiradas.values()) if retiradas else np.zeros(n)
    iv = np.where(np.array([x is not None for x in atual]))[0]
    liquidos = np.array([None] * n, dtype=object)
    sobre_classe = np.zeros(n)
    n_prec = np.zeros(n, dtype=int)
    if len(iv):
        pri = ordem_precedencia(u)
        liq_v, sob_v, np_v = liquido_por_precedencia(atual[iv], pri[iv])
        liquidos[iv], sobre_classe[iv], n_prec[iv] = liq_v, sob_v, np_v
    a_liq = geo.area_ha(liquidos)
    lg(f"  sobreposição entre imóveis da classe: {sobre_classe.sum():,.2f} ha | líquida {a_liq.sum():,.1f} ha")
    # UF x bioma (IBGE), partes simples
    fr = cel.fragmentar(liquidos)
    partes, idx_parte = shapely.get_parts(np.array(fr["geometry"].values, dtype=object), return_index=True)
    fr_p = fr.iloc[idx_parte].reset_index(drop=True)
    i_un = fr_p["i"].to_numpy(int)
    camada = u.drop(columns=["geometry", "n_pecas", "area_pecas_arq_ha", "area_pecas_geo_ha", "des_condic"]).iloc[i_un].reset_index(drop=True)
    camada.insert(0, "classe", classe)
    camada["uf"] = fr_p["uf"].to_numpy()
    camada["bioma"] = fr_p["bioma"].to_numpy()
    camada["area_ha"] = geo.area_ha(partes)
    gdf = gpd.GeoDataFrame(camada, geometry=partes, crs=f"EPSG:{cfg.CRS_TRABALHO}")
    # tabela por imóvel (sem geometria)
    t = u.drop(columns="geometry").copy()
    t["classe"] = classe
    t["area_uniao_imovel_ha"] = a_uni
    t["sobreposta_no_imovel_ha"] = sobre_imovel
    for cod, v in retiradas.items():
        t[f"sobreposta_{cod.lower()}_ha"] = v
    t["sobreposta_classes_anteriores_ha"] = sobre_prec
    t["n_precedentes_na_classe"] = n_prec
    t["sobreposta_na_classe_ha"] = sobre_classe
    t["area_liquida_ha"] = a_liq

    # ---- conferências ----
    tol_p = np.maximum(1e-3, 1e-6 * a_pec)
    resid = np.abs(a_pec - sobre_imovel - sobre_prec - sobre_classe - a_liq)
    chk("área das peças - (sobreposição no imóvel + classes anteriores + na classe + líquida): excesso sobre a tolerância (ha, pior imóvel)",
        float(np.max(np.maximum(resid - tol_p, 0.0))) if n else 0.0, 1e-9,
        f"identidade de área por imóvel; pior resíduo {resid.max() if n else 0:.6f} ha (tolerância por imóvel: 1e-3 ha ou 1e-6 da área)")
    tol = max(1e-3, 5e-7 * float(a_uni.sum()))
    chk("soma dos fragmentos UF x bioma - área líquida (ha)", float(camada["area_ha"].sum() - a_liq.sum()), tol, "a divisão por UF e bioma não perde nem cria área")
    fora = float(camada.loc[(camada["uf"] == "FORA") | (camada["bioma"] == "FORA"), "area_ha"].sum())
    chk("área fora dos limites IBGE de UF ou bioma (ha)", fora, max(0.0005 * float(a_uni.sum()), 1e-3), f"{fora:,.3f} ha ficam como 'FORA'; tolerância 0,05%")
    chk("fragmentos sem UF ou bioma", float(camada["uf"].isna().sum() + camada["bioma"].isna().sum()), 0)
    chk("geometrias líquidas inválidas", float((~shapely.is_valid(partes)).sum()), 0)
    chk("área líquida > união do imóvel: excesso sobre a tolerância (ha, pior imóvel)",
        float(np.max(np.maximum(a_liq - a_uni - np.maximum(1e-3, 1e-6 * a_uni), 0.0))) if n else 0.0, 1e-9)
    chk("soma de area_ha do arquivo - soma da área geodésica recalculada das peças (ha)",
        float(d["area_ha_arq"].sum() - d["area_ha_geo"].sum()), max(1e-3, 1e-6 * float(d["area_ha_geo"].sum())),
        "as áreas gravadas no cruzamento são as geodésicas (GRS80)")
    prec_todos = np.concatenate([g for _, g in prior]) if prior else np.array([], dtype=object)
    chk("sobreposição dos líquidos com as classes anteriores (ha)", sobreposicao_com_grandes(partes, prec_todos), 1e-2,
        "cada par que se toca é conferido com o polígono anterior recortado pela caixa da parte")
    completa = conferencia == "completa" or (conferencia == "auto" and len(d) <= LIMITE_PECAS_CONFERENCIA_COMPLETA)
    if completa:
        ii, jj, ar = sobrepoe(partes, partes)
        m = ii < jj
        chk("sobreposição entre fragmentos líquidos (ha)", float(ar[m].sum()) if len(ar) and m.any() else 0.0, 1e-3)
        a_U, a_esp = liquido_independente(np.array(d["geometry"].values, dtype=object), prec_todos)
        chk("área líquida - área (união das peças - união das classes anteriores) (ha)", float(a_liq.sum() - a_esp), max(1e-2, 1e-6 * a_U),
            "soma dos líquidos x cálculo independente por união (não usa a união por imóvel nem a precedência)")
    else:
        lg("  conferências por união independente omitidas" + (f" ({len(d):,} peças > {LIMITE_PECAS_CONFERENCIA_COMPLETA:,}; use --conferencia completa)" if conferencia == "auto" else " (--conferencia leve)"))
    return {"partes": gdf, "unidades": t, "liquidos": np.array(partes, dtype=object), "conferencias": conf,
            "n_vazias_uniao": n_vazias, "completa": completa}


def processar_uf_versao(uf, versao, pecas, cel, log=None, conferencia="auto"):
    """Os seis blocos do CAR de uma UF em uma versão da VS. ``pecas`` = DataFrame de ``ler_pecas_uf`` (já com ``preparar_pecas``).

    Devolve {classe: dict(partes, unidades, conferencias, liquidos)} com os blocos de cada classe reunidos (só as classes que têm peças)."""
    import geopandas as gpd

    if len(pecas) == 0:
        return {}
    todas = np.array(pecas["geometry"].values, dtype=object)
    x0, y0, x1, y1 = shapely.total_bounds(todas)
    bbox = (x0 - 1e-3, y0 - 1e-3, x1 + 1e-3, y1 + 1e-3)
    fixas = anteriores.geoms_por_classe("APP", versao, bbox=bbox)          # classes 1, 3, 4, 5, 6, 7 e 8 (das saídas anteriores)
    if log:
        log("  classes anteriores na caixa da UF: " + ", ".join(f"{c} {len(g):,}" for c, g in fixas))
    partes = {c: [] for c in CLASSES}
    unidades = {c: [] for c in CLASSES}
    conf = {c: [] for c in CLASSES}
    do_car = []
    for classe, gi, cod in blocos():
        d = pecas[(pecas["classe"] == classe) & pecas["categoria"].isin(GRUPOS[gi])].reset_index(drop=True)
        if len(d) == 0:
            continue
        rotulo = "+".join(GRUPOS[gi])
        if log:
            log(f"{uf} {versao} {classe} ({rotulo}): {len(d):,} peças")
        r = processar_classe(classe, d, list(fixas) + do_car, cel, f"{versao} {uf} {classe} ({rotulo})", log=log, conferencia=conferencia)
        do_car = do_car + [(cod, r["liquidos"])]
        partes[classe].append(r["partes"])
        unidades[classe].append(r["unidades"])
        conf[classe] += r["conferencias"]
        del r
        gov._devolver_memoria()
    saida = {}
    for classe in CLASSES:
        if not unidades[classe]:
            continue
        gs = [g for g in partes[classe] if len(g)]
        gdf = gpd.GeoDataFrame(pd.concat(gs, ignore_index=True), geometry="geometry", crs=f"EPSG:{cfg.CRS_TRABALHO}") if gs else partes[classe][0]
        saida[classe] = {"partes": gdf, "unidades": pd.concat(unidades[classe], ignore_index=True), "conferencias": conf[classe]}
    return saida
