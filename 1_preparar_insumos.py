"""Passo 1 - Preparar insumos

Objetivo: aplica a elegibilidade de cada fonte, padroniza CRS (EPSG:4674) e campos, repara geometrias
e gera o insumo elegível de cada classe (prefixo IN_), sempre com os POLÍGONOS INTEIROS.

Implementado nesta versão (v0.2.0): RECOOPERAR (IBAMA 2026), Tier-1.
    - Elegibilidade por categoria (config_computo.ELEGIBILIDADE_RECOOPERAR).
    - Campos harmonizados, sem dados pessoais (config_computo.CAMPOS_RECOOPERAR / COLUNAS_PESSOAIS_RECOOPERAR).
    - ano_inicio (cadeia dt_projeto > dt_assinat > dt_documen [proxy]) e ano_infracao.
    - Atributos de VS (vs22q_*, vs2224q_*) mantidos na tabela de cada polígono.
Ainda não implementado: CAR Regularização, ICMBio (adiado), OR, TI, UC, ProManguezal, PANGIA.

Entradas: FONTES["recooperar"]["arquivo"] (Projetos_com_VegSec\\IBAMA_Projetos_Recooperar_2026_com_VegSec.gpkg).
Saídas (em config_computo.SAIDA_INSUMOS):
    IN_Recooperar_2026.gpkg           camada IN_RECOOPERAR (elegíveis, polígonos inteiros)
    IN_Recooperar_2026_resumo.csv     por categoria: total x elegível (nº, ha, VS)
    IN_Recooperar_2026_excluidos.csv  polígonos fora do cômputo e o motivo
    _log_passo1.txt

Execução:  python 1_preparar_insumos.py [recooperar]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config_computo as cfg
from computo import elegibilidade as el
from computo import geometria as geo
from computo import io_dados as io

FONTES_IMPLEMENTADAS = ["recooperar"]
NOME_ARQ = "IN_Recooperar_2026"


def _col(g, nome):
    return g[nome] if nome in g.columns else pd.Series([pd.NA] * len(g), index=g.index, dtype="string")


def _colunas_vs(g):
    return [c for c in g.columns if any(c.startswith(p + "_") for p in cfg.VS_VERSOES)]


def preparar_recooperar(log):
    import geopandas as gpd

    fonte = cfg.FONTES["recooperar"]
    arq = cfg.RAIZ / fonte["arquivo"]
    if not arq.exists():
        raise FileNotFoundError(f"Não encontrei {arq}. Rode incorporar_vegsec_projetos.py antes.")
    E = cfg.ELEGIBILIDADE_RECOOPERAR
    log(f"lendo {arq}")
    partes = []
    for categoria in cfg.PRECEDENCIA_RECOOPERAR:
        camada = fonte["camadas"][categoria]
        g = io.ler_camada(arq, camada)
        g["categoria"] = categoria
        g["camada_orig"] = camada
        # geometrias: repara; polígono sem geometria não tem área e sai (registrado em excluidos)
        geoms, invalida = geo.reparar(g.geometry.values)
        g["geometry"] = geoms
        g["geom_reparada_p1"] = invalida.astype(int)
        elg = el.filtrar_recooperar(g, categoria, E, E["campo_status"], E["campo_etapa"])
        sem_geom = np.array([x is None or x.is_empty for x in geoms])
        elg.loc[sem_geom, "elegivel"] = 0
        elg.loc[sem_geom, "motivo"] = "sem geometria"
        g["elegivel_computo"] = elg["elegivel"]
        g["motivo_elegibilidade"] = elg["motivo"]
        g["area_ha_geo"] = geo.area_ha(geoms)
        log(f"  {categoria:14s} {len(g):5d} polígonos | elegíveis {int(elg['elegivel'].sum()):5d} | sem geometria {int(sem_geom.sum())} | reparadas {int(invalida.sum())}")
        partes.append(g)
    tudo = pd.concat(partes, ignore_index=True)
    tudo = gpd.GeoDataFrame(tudo, geometry="geometry", crs=f"EPSG:{cfg.CRS_TRABALHO}")

    # ---- campos harmonizados (sem dados pessoais) ----
    ph = cfg.PLACEHOLDERS
    out = pd.DataFrame(index=tudo.index)
    sigla = tudo["categoria"].map(cfg.SIGLA_CATEGORIA)
    out["id_proj"] = "REC26-" + sigla + "-" + tudo["fid_orig"].astype("Int64").astype(str).str.zfill(6)
    out["fonte_dado"] = "IBAMA_Recooperar_2026"
    out["categoria"] = tudo["categoria"]
    out["categoria_nome"] = tudo["categoria"].map(cfg.NOME_CATEGORIA)
    out["camada_orig"] = tudo["camada_orig"]
    out["arquivo_orig"] = tudo["arquivo_orig"]
    out["fid_orig"] = tudo["fid_orig"]
    for novo, origem in cfg.CAMPOS_RECOOPERAR.items():
        out[novo] = el.limpar_placeholders(_col(tudo, origem), ph)
    out["area_decl_ha"] = pd.to_numeric(_col(tudo, "area_ha"), errors="coerce")
    out["area_ha_geo"] = tudo["area_ha_geo"]
    out["ano_inicio"], out["ano_inicio_fonte"] = el.ano_inicio(tudo, cfg.ANO_INICIO_CADEIA, cfg.DATAS_SENTINELA, cfg.ANO_MIN, cfg.ANO_MAX)
    out["ano_infracao"] = el.ano_de_campo(tudo, "dt_autuaca", cfg.DATAS_SENTINELA, cfg.ANO_MIN, cfg.ANO_MAX)
    out["elegivel_computo"] = tudo["elegivel_computo"].astype(int)
    out["motivo_elegibilidade"] = tudo["motivo_elegibilidade"]
    out["geom_reparada"] = tudo["geom_reparada_p1"]
    vs = _colunas_vs(tudo)
    for c in vs:
        out[c] = tudo[c]
    res = gpd.GeoDataFrame(out, geometry=tudo.geometry.values, crs=tudo.crs)
    assert not [c for c in cfg.COLUNAS_PESSOAIS_RECOOPERAR if c in res.columns], "dado pessoal vazou para o insumo"
    assert res["id_proj"].is_unique, "id_proj repetido"

    # ---- saídas ----
    cfg.SAIDA_INSUMOS.mkdir(parents=True, exist_ok=True)
    elegiveis = res[res["elegivel_computo"] == 1].copy()
    excluidos = res[res["elegivel_computo"] == 0].drop(columns="geometry")
    io.gravar_camada(elegiveis, cfg.SAIDA_INSUMOS / f"{NOME_ARQ}.gpkg", "IN_RECOOPERAR", primeira=True)

    cols_ex = ["id_proj", "categoria", "status_recuperacao", "etapa_processo", "motivo_elegibilidade", "area_ha_geo",
               "processo_sei", "fid_orig"] + [c for c in vs if c.endswith("_area_ha")]
    excluidos[cols_ex].to_csv(cfg.SAIDA_INSUMOS / f"{NOME_ARQ}_excluidos.csv", index=False, encoding="utf-8-sig")

    linhas = []
    for cat in cfg.PRECEDENCIA_RECOOPERAR + ["TOTAL"]:
        sub = res if cat == "TOTAL" else res[res["categoria"] == cat]
        el_ = sub[sub["elegivel_computo"] == 1]
        linha = {"categoria": cat, "n_total": len(sub), "n_elegiveis": len(el_),
                 "area_total_ha": sub["area_ha_geo"].sum(), "area_elegivel_ha": el_["area_ha_geo"].sum()}
        for p in cfg.VS_VERSOES:
            linha[f"{p}_total_ha"] = sub[f"{p}_area_ha"].sum()
            linha[f"{p}_elegivel_ha"] = el_[f"{p}_area_ha"].sum()
        linhas.append(linha)
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_INSUMOS / f"{NOME_ARQ}_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo.round(1).to_string(index=False))
    log(f"IN_RECOOPERAR: {len(elegiveis)} polígonos elegíveis, {elegiveis['area_ha_geo'].sum():,.1f} ha (soma dos polígonos inteiros)")
    log(f"gravado: {cfg.SAIDA_INSUMOS / (NOME_ARQ + '.gpkg')}")
    return res


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pedidas = argv or FONTES_IMPLEMENTADAS
    cfg.SAIDA_INSUMOS.mkdir(parents=True, exist_ok=True)
    arq_log = cfg.SAIDA_INSUMOS / "_log_passo1.txt"

    def log(m):
        io.log(m, arq_log)

    log("Passo 1 - Preparar insumos")
    for f in pedidas:
        if f not in FONTES_IMPLEMENTADAS:
            log(f"fonte '{f}': ainda não implementada (pendente).")
            return 1
    if "recooperar" in pedidas:
        preparar_recooperar(log)
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
