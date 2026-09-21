"""Passo 3 - Camada 1 (VS legalmente protegida, critério de governança)

Objetivo: aplica a hierarquia do Anexo 1 às classes de governança. A área da classe é a VS QUALIFICADA dentro do território.
Não refaz os cruzamentos: parte das peças "VS x território" do passo 1 (IN_TI_..., IN_UC_..., IN_Manguezal_...), uma por versão da VS
(vs22q, vs2224q), e as subtrai das classes de maior prioridade.

Implementado na v0.6.0: classes 6 (TI), 7 (UC) e 8 (MANGUEZAL).
    TI        fases delimitada, declarada, homologada e regularizada (FUNAI 07/05/2026). Sobreposição entre TIs: fase mais avançada primeiro.
    UC        limite da UC (a zona de amortecimento fica fora). APAs: só a área pública (APA menos o CAR total, feito no passo 1).
              Sobreposição entre UCs: proteção integral > uso sustentável; fora da APA > APA; federal > estadual > municipal; mais antiga.
    MANGUEZAL ProManguezal (IBAMA 08/05/2026), toda a VS.
    Cada classe subtrai as de maior prioridade já processadas (1, 3, 4, 5 e, para UC e MANGUEZAL, as classes 6 e 7), na versão da VS.
    As classes 9 a 11 (APP, AUR, RL dos imóveis do CAR; por UF, com a precedência Habilitados > Analisados > Não analisados) estão em
    3b_camada1_car.py (v0.7.0), que parte das saídas deste passo.

Entradas (passo 1): SAIDA_INSUMOS/IN_TI_FUNAI20260507.gpkg, IN_UC_CNUC20260507.gpkg, IN_Manguezal_ProManguezal20260508.gpkg (camadas
    <versão>_pedacos); classes 1, 3, 4 e 5 (passo 2); IBGE_Limite_Estados e IBGE_Limite_Biomas.

Saídas (em config_computo.SAIDA_TIER6, SAIDA_TIER7 e SAIDA_TIER8):
    P1_<classe>_<data>.gpkg
        P1_TI_vs22q, P1_TI_vs2224q  (idem UC e MANGUEZAL)  partes líquidas (polígonos simples), uma por peça x UF x bioma, com os atributos
                                    do território; disjuntas entre si e das classes de maior prioridade
        P1_TI_pecas_vs22q, ...      tabela (sem geometria): uma linha por peça de VS x território, com as áreas retiradas por classe
    T<n>_resumo.csv, T<n>_resumo_uf_bioma.csv, T<n>_conferencias.csv,
    T<n>_acumulado_classes_....csv (área líquida acumulada das classes já processadas, por versão, UF e bioma)

Execução:  python 3_camada1_vs_governanca.py [TI] [UC] [MANGUEZAL]   (sem argumento: as três, na ordem)
    Exige o passo 1 (ti, uc, manguezal) e as classes 1, 3, 4 e 5 já processadas. O log de cada classe fica na pasta dela.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import shapely
from shapely.strtree import STRtree

import config_computo as cfg
from computo import anteriores
from computo import geometria as geo
from computo import governanca as gov
from computo import io_dados as io
from computo.hierarquia import liquido_por_precedencia, subtrair_precedentes
from computo.territorio import CelulasUFBioma

CLASSES_IMPLEMENTADAS = ["TI", "UC", "MANGUEZAL"]
COLUNAS_ENTRADA = ["area_ha_arq", "area_ha_geo", "area_original_ha", "geom_reparada"]   # ficam só na tabela de peças

_CLASSES = {
    "TI": dict(ordem=6, pasta=cfg.SAIDA_TIER6, arq_in="IN_TI_FUNAI20260507.gpkg", arq_out=anteriores.ARQ_OUT_TI, log="_log_passo3_ti.txt",
               id_terr="terrai_cod", regras=cfg.ELEGIBILIDADE_TI, acum_in="T5_acumulado_classes_1_3_4_5.csv",
               acum_out="T6_acumulado_classes_1_3_4_5_6.csv", rotulo="6 TI"),
    "UC": dict(ordem=7, pasta=cfg.SAIDA_TIER7, arq_in="IN_UC_CNUC20260507.gpkg", arq_out=anteriores.ARQ_OUT_UC, log="_log_passo3_uc.txt",
               id_terr="cd_cnuc", regras=cfg.ELEGIBILIDADE_UC, acum_in="T6_acumulado_classes_1_3_4_5_6.csv",
               acum_out="T7_acumulado_classes_1_3_4_5_6_7.csv", rotulo="7 UC"),
    "MANGUEZAL": dict(ordem=8, pasta=cfg.SAIDA_TIER8, arq_in="IN_Manguezal_ProManguezal20260508.gpkg", arq_out=anteriores.ARQ_OUT_MANGUEZAL,
                      log="_log_passo3_manguezal.txt", id_terr=None,   # o campo Id do ProManguezal vem zerado: não identifica polígonos
                      regras=cfg.ELEGIBILIDADE_MANGUEZAL, acum_in="T7_acumulado_classes_1_3_4_5_6_7.csv", acum_out="T8_acumulado_classes_1_3_4_5_6_7_8.csv", rotulo="8 MANGUEZAL"),
}
_PASTAS_ACUM = {"T5": cfg.SAIDA_TIER5, "T6": cfg.SAIDA_TIER6, "T7": cfg.SAIDA_TIER7}


def _categoria(codigo, d):
    """Rótulo de categoria de cada peça (para os resumos)."""
    if codigo == "TI":
        return d["fase_ti"].astype(str).to_numpy()
    if codigo == "UC":
        apa = d["apa"].to_numpy(bool)
        return np.where(apa, d["grupo"].astype(str) + " - APA (área pública)", d["grupo"].astype(str))
    return np.array(["Manguezal"] * len(d), dtype=object)


def _prioridade(codigo, d, regras):
    if codigo == "TI":
        return gov.prioridade_ti(d, regras)
    if codigo == "UC":
        return gov.prioridade_uc(d, regras)
    return gov.prioridade_manguezal(d)


def _sobrepoe(a, b):
    """Pares (i, j) de a x b cujos INTERIORES se sobrepõem (toque na divisa não conta) e a área da interseção (ha)."""
    if len(a) == 0 or len(b) == 0:
        return np.array([], int), np.array([], int), np.array([])
    tree = STRtree(b)
    ii, jj = tree.query(a, predicate="intersects")
    if len(ii) == 0:
        return ii, jj, np.array([])
    ok = shapely.relate_pattern(a[ii], b[jj], "T********")
    ii, jj = ii[ok], jj[ok]
    ar = geo.area_ha(geo.intersecao_robusta(a[ii], b[jj])) if len(ii) else np.array([])
    return ii, jj, ar


def liquido_independente(geoms, prec):
    """Área (ha) de (união das peças - união das classes anteriores), por cálculo independente da cadeia peça a peça.

    A união das peças é dividida em componentes conexos; em cada um subtrai-se só a união das classes anteriores que o tocam.
    (Uma diferença única entre as duas uniões, que cobrem o país inteiro, estoura a memória.) Como a sobreposição entre peças só ocorre
    dentro de um componente, a soma dos líquidos das peças do componente é a área dele menos as classes anteriores."""
    geoms = np.array([g for g in geoms if g is not None and not g.is_empty], dtype=object)
    U = geo.uniao_robusta(list(geoms))
    if U is None:
        return 0.0, 0.0
    comps = shapely.get_parts(U)
    a_U = float(geo.area_ha(comps).sum())
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
        for a, b in zip(inicios, fins):
            Up = geo.uniao_robusta(list(prec[jj[a:b]]))
            r = geo.so_poligonos(geo.diferenca_robusta([comps[ii[a]]], [Up])[0]) if Up is not None else comps[ii[a]]
            total += float(geo.area_ha([r])[0]) if r is not None else 0.0
    return a_U, total


def classe_territorio(codigo, log):
    """Classes 6 a 8: TI, UC e Manguezal (governança). Área = VS no território; subtrai as classes de maior prioridade."""
    import geopandas as gpd
    import pyogrio

    C = _CLASSES[codigo]
    P = list(cfg.VS_VERSOES)
    arq_in = cfg.SAIDA_INSUMOS / C["arq_in"]
    if not arq_in.exists():
        raise FileNotFoundError(f"Não encontrei {arq_in}. Rode 1_preparar_insumos.py {codigo.lower()} antes.")
    pasta = C["pasta"]
    pasta.mkdir(parents=True, exist_ok=True)
    out = pasta / C["arq_out"]
    pref = f"T{C['ordem']}"
    lim = anteriores.carregar_limites()
    log("células UF x bioma (uma vez)")
    cel = CelulasUFBioma(lim)
    log(f"  {len(cel.geoms)} células")
    conf = []

    def chk(nome, valor, limite, obs=""):
        conf.append({"conferencia": nome, "valor": valor, "limite": limite, "ok": bool(abs(valor) <= limite), "obs": obs})

    resumos, resumos_ub, acum_novas = [], [], []
    for k, p in enumerate(P):
        log(f"--- {codigo} {p} ({cfg.VS_VERSOES[p]}) ---")
        d = io.ler_camada(arq_in, f"{p}_pedacos")
        if codigo == "UC":
            d = d.rename(columns={"uf": "uf_cnuc"})          # 'uf' fica reservado à UF do IBGE (células)
        n = len(d)
        geoms = np.array(d.geometry.values, dtype=object)
        a_bruta = d["area_ha_geo"].to_numpy(float)
        log(f"peças: {n:,}; VS no território {a_bruta.sum():,.1f} ha")
        # 1) classes de maior prioridade (líquidos por versão), uma de cada vez
        por_classe = anteriores.geoms_por_classe(codigo, p)
        cods_prec = [c for c, _ in por_classe]
        prec = np.concatenate([x for _, x in por_classe]) if por_classe else np.array([], dtype=object)
        log(f"classes anteriores subtraídas: {cods_prec} ({len(prec):,} polígonos líquidos)")
        atual, retiradas = geoms.copy(), {}
        for cod, gp in por_classe:
            iv = np.where(np.array([x is not None for x in atual]))[0]
            rest, ret = subtrair_precedentes(atual[iv], gp)
            atual[iv] = rest
            r = np.zeros(n)
            r[iv] = ret
            retiradas[cod] = r
            log(f"  sobreposição com {cod}: {r.sum():,.2f} ha ({int((r > 0).sum()):,} peças)")
        del por_classe
        sobre_prec = sum(retiradas.values()) if retiradas else np.zeros(n)
        # 2) sobreposição entre territórios da própria classe
        iv = np.where(np.array([x is not None for x in atual]))[0]
        liquidos = np.array([None] * n, dtype=object)
        sobre_intra = np.zeros(n)
        n_prec = np.zeros(n, dtype=int)
        if len(iv):
            pri = _prioridade(codigo, d, C["regras"])
            pv = np.argsort(np.argsort(pri[iv]))
            liq_v, sob_v, np_v = liquido_por_precedencia(atual[iv], pv)
            liquidos[iv], sobre_intra[iv], n_prec[iv] = liq_v, sob_v, np_v
        a_liq = geo.area_ha(liquidos)
        log(f"  sobreposição entre territórios da classe: {sobre_intra.sum():,.2f} ha | líquida {a_liq.sum():,.1f} ha")
        # 3) UF x bioma: fragmentos do líquido, já em partes simples
        log("  UF x bioma")
        fr = cel.fragmentar(liquidos)
        partes, idx_parte = shapely.get_parts(np.array(fr["geometry"].values, dtype=object), return_index=True)
        fr_p = fr.iloc[idx_parte].reset_index(drop=True)
        i_peca = fr_p["i"].to_numpy(int)
        atrib = d.drop(columns=["geometry"] + [c for c in COLUNAS_ENTRADA if c in d.columns]).reset_index(drop=True)
        cat = _categoria(codigo, d)
        camada = atrib.iloc[i_peca].reset_index(drop=True)
        camada["categoria"] = cat[i_peca]
        camada["uf"] = fr_p["uf"].to_numpy()
        camada["bioma"] = fr_p["bioma"].to_numpy()
        camada["area_ha"] = geo.area_ha(partes)
        gdf = gpd.GeoDataFrame(camada, geometry=partes, crs=f"EPSG:{cfg.CRS_TRABALHO}")
        io.gravar_camada(gdf, out, f"P1_{codigo}_{p}", primeira=(k == 0))
        # tabela de peças (sem geometria)
        pec = atrib.copy()
        pec["categoria"] = cat
        pec["area_vs_original_ha"] = d["area_original_ha"].to_numpy(float)
        pec["area_vs_no_territorio_ha"] = a_bruta
        for cod, v in retiradas.items():
            pec[f"sobreposta_{cod.lower()}_ha"] = v
        pec["sobreposta_classes_anteriores_ha"] = sobre_prec
        pec["n_precedentes_na_classe"] = n_prec
        pec["sobreposta_na_classe_ha"] = sobre_intra
        pec["area_liquida_ha"] = a_liq
        pyogrio.write_dataframe(pec, str(out), layer=f"P1_{codigo}_pecas_{p}", driver="GPKG", append=True)
        # resumos
        agg = dict(n_pecas=("id_peca", "size"),
                   vs_no_territorio_ha=("area_vs_no_territorio_ha", "sum"),
                   sobreposta_classes_anteriores_ha=("sobreposta_classes_anteriores_ha", "sum"),
                   sobreposta_na_classe_ha=("sobreposta_na_classe_ha", "sum"), area_liquida_ha=("area_liquida_ha", "sum"))
        for cod in retiradas:
            agg[f"sobreposta_{cod.lower()}_ha"] = (f"sobreposta_{cod.lower()}_ha", "sum")
        if codigo == "UC":
            agg["area_privada_apa_retirada_ha"] = ("area_privada_ha", "sum")
        if C["id_terr"]:
            agg["n_territorios"] = (C["id_terr"], "nunique")
        rs = pec.groupby("categoria").agg(**agg).reset_index()
        tot = rs.drop(columns="categoria").sum(numeric_only=True)
        if C["id_terr"]:
            tot["n_territorios"] = pec[C["id_terr"]].nunique()
        else:
            rs["n_territorios"] = np.nan
            tot["n_territorios"] = np.nan
        rs = pd.concat([rs, pd.DataFrame([{"categoria": "TOTAL", **tot.to_dict()}])], ignore_index=True)
        rs.insert(0, "versao", p)
        resumos.append(rs)
        ub = camada.groupby(["uf", "bioma", "categoria"], as_index=False)["area_ha"].sum().rename(columns={"area_ha": "area_liquida_ha"})
        ub.insert(0, "versao", p)
        resumos_ub.append(ub)
        log("\n" + rs.round(1).to_string(index=False))
        del pec, atrib, cat, fr, fr_p, i_peca, gdf, rs, ub
        gov._devolver_memoria()

        # ---- conferências independentes (por versão) ----
        tol = max(1e-3, 5e-7 * float(a_bruta.sum()))
        # tolerância por peça: 1e-3 ha ou 1e-6 da área (a diferença entre polígonos grandes tem ruído de ~1e-8 da área)
        tol_p = np.maximum(1e-3, 1e-6 * a_bruta)
        resid = np.abs(a_bruta - sobre_prec - sobre_intra - a_liq)
        chk(f"{p}: área da peça - (sobreposta às classes anteriores + na classe + líquida): excesso sobre a tolerância (ha, pior peça)",
            float(np.max(np.maximum(resid - tol_p, 0.0))), 1e-9, f"identidade de área por peça; pior resíduo {resid.max():.6f} ha (tolerância por peça: 1e-3 ha ou 1e-6 da área)")
        chk(f"{p}: soma dos fragmentos UF x bioma - área líquida (ha)", float(camada["area_ha"].sum() - a_liq.sum()), tol,
            "a divisão por UF e bioma não perde nem cria área")
        fora = float(camada.loc[(camada["uf"] == "FORA") | (camada["bioma"] == "FORA"), "area_ha"].sum())
        chk(f"{p}: área fora dos limites IBGE de UF ou bioma (ha)", fora, 0.0005 * float(a_bruta.sum()), f"{fora:,.3f} ha ficam como 'FORA'; tolerância 0,05%")
        chk(f"{p}: fragmentos sem UF ou bioma", float(camada["uf"].isna().sum() + camada["bioma"].isna().sum()), 0)
        chk(f"{p}: geometrias líquidas inválidas", float((~shapely.is_valid(partes)).sum()), 0)
        ii, jj, ar = _sobrepoe(partes, partes)
        m = ii < jj
        chk(f"{p}: sobreposição entre fragmentos líquidos (ha)", float(ar[m].sum()) if len(ar) and m.any() else 0.0, 1e-3)
        ii, jj, ar = _sobrepoe(partes, prec)
        chk(f"{p}: sobreposição dos líquidos com as classes anteriores (ha)", float(ar.sum()) if len(ar) else 0.0, 1e-3)
        # independente: área da união das peças - área da união das classes anteriores (por componente conexo)
        a_U, a_esp = liquido_independente(geoms, prec)
        chk(f"{p}: área líquida - área (união das peças - união das classes anteriores) (ha)", float(a_liq.sum() - a_esp),
            max(1e-2, 1e-6 * a_U), "soma dos líquidos x cálculo independente por união")
        chk(f"{p}: área líquida > VS no território: excesso sobre a tolerância (ha, pior peça)",
            float(np.max(np.maximum(a_liq - a_bruta - tol_p, 0.0))), 1e-9, f"maior excesso {float(np.max(a_liq - a_bruta)):.6f} ha (ruído geométrico)")
        if codigo == "UC":
            apa = d["apa"].to_numpy(bool)
            a_ori = d.loc[apa, "area_original_ha"].to_numpy(float)
            chk(f"{p}: APAs com área pública > VS original da APA: excesso sobre a tolerância (ha, pior peça)",
                float(np.max(np.maximum(a_bruta[apa] - a_ori - np.maximum(1e-3, 1e-6 * a_ori), 0.0))) if apa.any() else 0.0, 1e-9)
        # acumulado
        nova = camada.groupby(["categoria", "uf", "bioma"], as_index=False)["area_ha"].sum()
        nova.insert(0, "classe", C["rotulo"])
        nova = nova.rename(columns={"area_ha": f"area_liquida_{p}_ha"})
        nova[f"vs_liquida_{p}_ha"] = nova[f"area_liquida_{p}_ha"]            # a área da classe é a própria VS
        acum_novas.append(nova.set_index(["classe", "categoria", "uf", "bioma"]))
        del d, geoms, atual, liquidos, partes, prec, camada, nova, ii, jj, ar
        gov._devolver_memoria()

    # ---- saídas ----
    resumo = pd.concat(resumos, ignore_index=True)
    resumo.to_csv(pasta / f"{pref}_resumo.csv", index=False, encoding="utf-8-sig")
    pd.concat(resumos_ub, ignore_index=True).to_csv(pasta / f"{pref}_resumo_uf_bioma.csv", index=False, encoding="utf-8-sig")
    a_in = _PASTAS_ACUM[C["acum_in"][:2]] / C["acum_in"]
    if not a_in.exists():
        raise FileNotFoundError(f"Não encontrei {a_in}. Rode as classes anteriores antes.")
    acum = pd.read_csv(a_in)
    novas = pd.concat(acum_novas, axis=1).fillna(0.0).reset_index()
    for c in acum.columns:
        if c not in novas.columns:
            novas[c] = 0.0
    acum = pd.concat([acum, novas[acum.columns]], ignore_index=True)
    acum.to_csv(pasta / C["acum_out"], index=False, encoding="utf-8-sig")
    tot = acum.groupby("classe")[[c for c in acum.columns if c.endswith("_ha")]].sum()
    log("\nacumulado (área líquida, sem dupla contagem entre classes):\n" + tot.round(1).to_string()
        + "".join(f"\n  total {p} {tot[f'area_liquida_{p}_ha'].sum():,.1f} ha" for p in P))
    conf = pd.DataFrame(conf)
    conf.to_csv(pasta / f"{pref}_conferencias.csv", index=False, encoding="utf-8-sig")
    log("\n" + conf.to_string(index=False))
    if not conf["ok"].all():
        log(f"ATENÇÃO: há conferências fora do limite (ver {pref}_conferencias.csv).")
    log(f"gravado: {out}")
    return resumo, conf


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pedidas = [a.upper() for a in argv] or CLASSES_IMPLEMENTADAS
    for c in pedidas:
        if c not in CLASSES_IMPLEMENTADAS:
            print(f"classe '{c}': não é deste script; as classes APP, AUR e RL (CAR) são do passo 3b: python 3b_camada1_car.py")
            return 1
    for codigo in CLASSES_IMPLEMENTADAS:
        if codigo not in pedidas:
            continue
        C = _CLASSES[codigo]
        C["pasta"].mkdir(parents=True, exist_ok=True)
        arq_log = C["pasta"] / C["log"]

        def log(m, _a=arq_log):
            io.log(m, _a)

        log(f"Passo 3 - Camada 1 (governança) - classe {codigo}")
        classe_territorio(codigo, log)
        log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
