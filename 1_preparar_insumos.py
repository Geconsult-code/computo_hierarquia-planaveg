"""Passo 1 - Preparar insumos

Objetivo: aplica a elegibilidade de cada fonte, padroniza CRS (EPSG:4674) e campos, repara geometrias
e gera o insumo elegível de cada classe (prefixo IN_), sempre com os POLÍGONOS INTEIROS.

Implementado nesta versão (v0.6.0): RECOOPERAR (IBAMA 2026, Tier-1), CAR_REGULARIZACAO (classe 3), EMBARGOS_PANGIA (classe 4), OR (classe 5),
TI (classe 6), UC (classe 7) e MANGUEZAL (classe 8).
    RECOOPERAR
    - Elegibilidade por categoria (config_computo.ELEGIBILIDADE_RECOOPERAR).
    - Campos harmonizados, sem dados pessoais (config_computo.CAMPOS_RECOOPERAR / COLUNAS_PESSOAIS_RECOOPERAR).
    - ano_inicio (cadeia dt_projeto > dt_assinat > dt_documen [proxy]) e ano_infracao.
    - Atributos de VS (vs22q_*, vs2224q_*) mantidos na tabela de cada polígono.
    CAR_REGULARIZACAO
    - Área a recompor de APP e RL dos imóveis "Analisado, em regularização ambiental" (ELEGIBILIDADE_CAR_REG).
    - Polígonos inteiros; VS qualificada (2 versões) cruzada aqui com as camadas brutas do INPE (VS_CAMADAS):
      atributos vs22q_*/vs2224q_* na tabela e peças "VS x polígono" em arquivo próprio (usadas no passo 2).
    EMBARGOS_PANGIA (classe 4, Outros projetos)
    - Embargos IBAMA/PANGIA de 20/09/2026 (50.674 polígonos, sem campo de status: entram todos) com campos sem dados
      pessoais (CAMPOS_EMBARGO_PANGIA). Só os embargos com VS qualificada dentro seguem; a classe 4 conta a VS DENTRO do embargo.
    - As peças "VS x embargo" vêm do cruzamento já feito (FONTES["embargos_pangia"]["cruzamento"], duas versões) e são
      conferidas contra o arquivo de embargos (chave num_tad + serie_tad + seq_tad; peça dentro do polígono).
    OR (classe 5, Observatório da Restauração)
    - ORR 2026 (86.281 polígonos em nível de projeto, EPSG:4674 no próprio arquivo; trocado do ORR 2025 - 4 feições dissolvidas por
      bioma - em 24/09/2026), AREA TOTAL dos polígonos, com ou sem VS, TODOS os status (decisão do usuário). Como o arquivo não traz
      VS, ela é cruzada aqui com as camadas brutas do INPE (VS_CAMADAS): as partes dos polígonos são agrupadas em células de
      CELULA_VS_OR_GRAUS (uma leitura de VS por célula e camada); atributos vs22q_*/vs2224q_* e peças em arquivo próprio.
    TI, UC e MANGUEZAL (classes 6 a 8, Governança: a área da classe é a VS qualificada DENTRO do território)
    - Peças "VS x território" dos cruzamentos já feitos (FONTES["ti"|"uc"|"manguezal"]["cruzamento"], uma por versão da VS), reparadas.
    - TI: só as fases delimitada, declarada, homologada e regularizada (ELEGIBILIDADE_TI). UC: só limite = "uc" (a zona de amortecimento,
      limite = "za", sai). APAs: só a área pública = APA menos os imóveis do CAR (CAR total dissolvido por UF, FONTES["car_total"]),
      recuperando como pública a parte disso que é imóvel público do SIGEF (FONTES["sigef_publico_apa"], decisão de 24/09/2026):
      a parte que continua privada fica registrada e a VS nela conta, se for o caso, como APP, AUR ou RL. Manguezal: toda a VS do ProManguezal.
Ainda não implementado: ICMBio (adiado).

Entradas: FONTES["recooperar"]["arquivo"] (Projetos_com_VegSec\\IBAMA_Projetos_Recooperar_2026_com_VegSec.gpkg);
          FONTES["sicar_regularizacao"]["arquivo"] e as camadas de VS (Vegetacao_Secundaria_INPE).
Saídas (em config_computo.SAIDA_INSUMOS):
    IN_Recooperar_2026.gpkg           camada IN_RECOOPERAR (elegíveis, polígonos inteiros)
    IN_Recooperar_2026_resumo.csv     por categoria: total x elegível (nº, ha, VS)
    IN_Recooperar_2026_excluidos.csv  polígonos fora do cômputo e o motivo
    IN_CAR_Regularizacao_Junho26.gpkg        camada IN_CAR_REG (elegíveis, polígonos inteiros, atributos de VS)
    IN_CAR_Regularizacao_Junho26_VS.gpkg     peças VS x polígono (vs22q_pedacos, vs2224q_pedacos)
    IN_CAR_Regularizacao_Junho26_resumo.csv / _excluidos.csv
    IN_Embargos_PANGIA_20260920.gpkg         camada IN_EMBARGOS_PANGIA (embargos inteiros com VS em alguma versão; atributos de VS)
    IN_Embargos_PANGIA_20260920_VS.gpkg      peças VS x embargo (vs22q_pedacos, vs2224q_pedacos)
    IN_Embargos_PANGIA_20260920_resumo.csv / _excluidos.csv (embargos sem VS)
    IN_OR_2026.gpkg                          camada IN_OR (86 mil polígonos inteiros, atributos de VS)
    IN_OR_2026_VS.gpkg                       peças VS x ORR (vs22q_pedacos, vs2224q_pedacos)
    IN_OR_2026_resumo.csv / _excluidos.csv
    IN_TI_FUNAI20260507.gpkg, IN_UC_CNUC20260507.gpkg, IN_Manguezal_ProManguezal20260508.gpkg
                                             peças elegíveis por versão (camadas vs22q_pedacos e vs2224q_pedacos)
    IN_<TI|UC|Manguezal>_..._resumo.csv / _excluidos.csv
    _log_passo1.txt

Execução:  python 1_preparar_insumos.py [recooperar] [car_regularizacao] [embargos_pangia] [or] [ti] [uc] [manguezal]   (sem argumento: todas)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import config_computo as cfg
from computo import elegibilidade as el
from computo import embargos as emb
from computo import geometria as geo
from computo import governanca as gov
from computo import io_dados as io
from computo import vs as vsm

FONTES_IMPLEMENTADAS = ["recooperar", "car_regularizacao", "embargos_pangia", "or", "ti", "uc", "manguezal"]
NOME_ARQ = "IN_Recooperar_2026"
NOME_ARQ_CAR = "IN_CAR_Regularizacao_Junho26"
NOME_ARQ_EMB = "IN_Embargos_PANGIA_20260920"
NOME_ARQ_OR = "IN_OR_2026"
NOME_ARQ_TI = "IN_TI_FUNAI20260507"
NOME_ARQ_UC = "IN_UC_CNUC20260507"
NOME_ARQ_MANGUEZAL = "IN_Manguezal_ProManguezal20260508"


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


def preparar_car_regularizacao(log):
    """Classe 3: área a recompor de APP e RL (SICAR, imóveis em regularização ambiental)."""
    import time

    import geopandas as gpd

    fonte = cfg.FONTES["sicar_regularizacao"]
    arq = cfg.RAIZ / fonte["arquivo"]
    if not arq.exists():
        raise FileNotFoundError(f"Não encontrei {arq}.")
    E = cfg.ELEGIBILIDADE_CAR_REG
    log(f"lendo {arq}")
    partes = []
    for cat, chave in (("app", "recompor_app"), ("rl", "recompor_rl")):
        camada = fonte["camadas"][chave]
        g = io.ler_camada(arq, camada, com_fid=True)
        g["categoria"] = cat
        g["camada_orig"] = camada
        geoms, invalida = geo.reparar(g.geometry.values)
        g["geometry"] = geoms
        g["geom_reparada_p1"] = invalida.astype(int)
        g["area_ha_geo"] = geo.area_ha(geoms)
        elg = el.filtrar_car_regularizacao(g, E, g["area_ha_geo"])
        sem_geom = np.array([x is None or x.is_empty for x in geoms])
        elg.loc[sem_geom, "elegivel"] = 0
        elg.loc[sem_geom, "motivo"] = "sem geometria"
        g["elegivel_computo"] = elg["elegivel"]
        g["motivo_elegibilidade"] = elg["motivo"]
        log(f"  {cat:4s} {len(g):5d} polígonos | elegíveis {int(elg['elegivel'].sum()):5d} | sem geometria {int(sem_geom.sum())} | reparadas {int(invalida.sum())}")
        partes.append(g)
    tudo = pd.concat(partes, ignore_index=True)
    tudo = gpd.GeoDataFrame(tudo, geometry="geometry", crs=f"EPSG:{cfg.CRS_TRABALHO}")

    # atributos do imóvel (uma linha por cod_imovel; o mesmo código pode aparecer em várias feições)
    imo = io.ler_camada(arq, fonte["camadas"]["imoveis"]).drop(columns="geometry")
    imo = imo.drop_duplicates("cod_imovel").set_index("cod_imovel")

    out = pd.DataFrame(index=tudo.index)
    sigla = tudo["categoria"].str.upper()
    out["id_proj"] = "CARREG-" + sigla + "-" + tudo["fid_orig"].astype(str).str.zfill(6)
    out["fonte_dado"] = "SICAR_Regularizacao_Junho26"
    out["categoria"] = tudo["categoria"]
    out["categoria_nome"] = tudo["categoria"].map(cfg.NOME_CAR_REG)
    out["camada_orig"] = tudo["camada_orig"]
    out["fid_orig"] = tudo["fid_orig"]
    for novo, origem in cfg.CAMPOS_CAR_REG.items():
        out[novo] = tudo[origem]
    out["uf_car"] = tudo["cod_imovel"].str[:2]
    out["municipio_car"] = tudo["cod_imovel"].map(imo["municipio"]) if "municipio" in imo else pd.NA
    out["mod_fiscal"] = tudo["cod_imovel"].map(imo["mod_fiscal"]) if "mod_fiscal" in imo else pd.NA
    out["area_imovel_ha"] = tudo["cod_imovel"].map(pd.to_numeric(imo["num_area"], errors="coerce")) if "num_area" in imo else pd.NA
    out["area_decl_ha"] = pd.to_numeric(_col(tudo, "num_area"), errors="coerce")     # não confiável em RL (ver docs)
    out["area_ha_geo"] = tudo["area_ha_geo"]
    out["elegivel_computo"] = tudo["elegivel_computo"].astype(int)
    out["motivo_elegibilidade"] = tudo["motivo_elegibilidade"]
    out["geom_reparada"] = tudo["geom_reparada_p1"]
    res = gpd.GeoDataFrame(out, geometry=tudo.geometry.values, crs=tudo.crs)
    assert res["id_proj"].is_unique, "id_proj repetido"
    pessoais = [c for c in res.columns if any(k in c.lower() for k in ("cpf", "cnpj", "nome_", "editor"))]
    assert not pessoais, f"possível dado pessoal nas saídas: {pessoais}"

    # ---- VS qualificada (2 versões) nos polígonos elegíveis: peças + atributos ----
    ele = res[res["elegivel_computo"] == 1].copy().reset_index(drop=True)
    log(f"VS x {len(ele)} polígonos elegíveis ({ele['cod_imovel'].nunique()} imóveis)")
    ped = {}
    for p in cfg.VS_VERSOES:
        t0 = time.time()
        log(f"{p} ({cfg.VS_VERSOES[p]}):")
        ped[p] = vsm.pedacos_em_poligonos(ele.geometry.values, ele["id_proj"].to_numpy(), ele["cod_imovel"].to_numpy(),
                                          cfg.VS_CAMADAS[p], cfg.RAIZ, log=log)
        at = vsm.atributos_vs(ped[p], ele["id_proj"], ele["area_ha_geo"], cfg.BIOMAS_VS)
        for c in at.columns:
            ele[f"{p}_{c}"] = at[c].to_numpy()
        log(f"  {p}: {len(ped[p])} peças, VS nos polígonos (soma dos atributos) {ele[f'{p}_area_ha'].sum():,.1f} ha ({time.time() - t0:.0f}s)")
    vs_cols = [c for c in ele.columns if any(c.startswith(p + "_") for p in cfg.VS_VERSOES)]
    # VS também nos não elegíveis (colunas vazias) só para o CSV de excluídos: não é calculada

    # ---- saídas ----
    cfg.SAIDA_INSUMOS.mkdir(parents=True, exist_ok=True)
    io.gravar_camada(ele, cfg.SAIDA_INSUMOS / f"{NOME_ARQ_CAR}.gpkg", "IN_CAR_REG", primeira=True)
    arq_vs = cfg.SAIDA_INSUMOS / f"{NOME_ARQ_CAR}_VS.gpkg"
    for k, p in enumerate(cfg.VS_VERSOES):
        d = ped[p].copy()
        d["area_ha"] = geo.area_ha(d["geometry"].values)
        io.gravar_camada(gpd.GeoDataFrame(d, geometry="geometry", crs=res.crs), arq_vs, f"{p}_pedacos", primeira=(k == 0))
    exc = res[res["elegivel_computo"] == 0].drop(columns="geometry")
    exc[["id_proj", "categoria", "cod_tema", "cod_imovel", "status_car", "motivo_elegibilidade", "area_ha_geo", "fid_orig"]].to_csv(
        cfg.SAIDA_INSUMOS / f"{NOME_ARQ_CAR}_excluidos.csv", index=False, encoding="utf-8-sig")
    linhas = []
    for chave in ["app", "rl", "TOTAL"]:
        sub = res if chave == "TOTAL" else res[res["categoria"] == chave]
        e_ = ele if chave == "TOTAL" else ele[ele["categoria"] == chave]
        r = {"categoria": chave, "n_total": len(sub), "n_elegiveis": len(e_), "area_total_ha": sub["area_ha_geo"].sum(),
             "area_elegivel_ha": e_["area_ha_geo"].sum()}
        for p in cfg.VS_VERSOES:
            r[f"{p}_elegivel_ha"] = e_[f"{p}_area_ha"].sum()
        linhas.append(r)
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_INSUMOS / f"{NOME_ARQ_CAR}_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo.round(1).to_string(index=False))
    log(f"IN_CAR_REG: {len(ele)} polígonos elegíveis, {ele['area_ha_geo'].sum():,.1f} ha (soma dos polígonos inteiros)")
    log(f"gravado: {cfg.SAIDA_INSUMOS / (NOME_ARQ_CAR + '.gpkg')}")
    return ele, ped


def preparar_embargos_pangia(log):
    """Classe 4: embargos PANGIA com VS qualificada dentro (a classe conta só a VS dentro do embargo)."""
    import time

    import geopandas as gpd

    fonte = cfg.FONTES["embargos_pangia"]
    arq = cfg.RAIZ / fonte["arquivo"]
    if not arq.exists():
        raise FileNotFoundError(f"Não encontrei {arq}.")
    E = cfg.ELEGIBILIDADE_EMBARGO_PANGIA
    lidas = sorted(set(cfg.CAMPOS_EMBARGO_PANGIA.values()) | {"dat_embarg"})      # as colunas pessoais nem são lidas
    log(f"lendo {arq}")
    g = io.ler_camada(arq, fonte["camada"], colunas=lidas, com_fid=True)
    geoms, invalida = geo.reparar(g.geometry.values)
    g["geometry"] = geoms
    sem_geom = np.array([x is None or x.is_empty for x in geoms])
    log(f"  {len(g)} embargos | sem geometria {int(sem_geom.sum())} | reparados {int(invalida.sum())}")
    h = emb.harmonizar(g, cfg.CAMPOS_EMBARGO_PANGIA, cfg.PLACEHOLDERS_PANGIA, cfg.DATAS_SENTINELA, cfg.ANO_MIN, cfg.ANO_MAX)
    out = pd.DataFrame(index=g.index)
    out["id_proj"] = "EMB-" + g["fid_orig"].astype(str).str.zfill(6)
    out["fonte_dado"] = "IBAMA_PANGIA_20260920"
    out["categoria"] = "embargo_pangia"
    out["categoria_nome"] = cfg.NOME_EMBARGO_PANGIA
    out["fid_orig"] = g["fid_orig"]
    for c in h.columns:
        out[c] = h[c]
    out["area_ha_geo"] = geo.area_ha(geoms)
    out["geom_reparada"] = invalida.astype(int)
    assert out["id_proj"].is_unique, "id_proj repetido"
    chaves = out.set_index("fid_orig")[["id_proj", "num_tad", "serie_tad", "seq_tad"]]
    assert chaves.index.is_unique

    # ---- peças VS x embargo (cruzamento já feito) e atributos de VS ----
    ped, at = {}, {}
    for p, rel in fonte["cruzamento"].items():
        t0 = time.time()
        f = cfg.RAIZ / rel
        if not f.exists():
            raise FileNotFoundError(f"Não encontrei {f}. Rode o cruzamento VS x embargos antes.")
        log(f"{p} ({cfg.VS_VERSOES[p]}): lendo {f.name}")
        d = emb.ler_pedacos_cruzamento(f, fonte["camada_cruzamento"], chaves, E["area_min_ha"])
        # cada peça tem de estar dentro do embargo a que pertence (a chave sozinha não pega arquivo reordenado)
        pos = pd.Series(np.arange(len(out)), index=out["id_proj"])
        alvo = geoms[pos.loc[d["id_proj"]].to_numpy()]
        fora = geo.area_ha([geo.so_poligonos(x) for x in geo.diferenca_robusta(d["geometry"].values, alvo)])
        assert fora.sum() < 1e-3, f"{p}: {fora.sum():.4f} ha de peças fora do embargo a que pertencem"
        ped[p] = d
        a = emb.uniao_por_id(d, out["id_proj"])
        area_vs = geo.area_ha(a)
        out[f"{p}_tem"] = (area_vs > 0).astype(int)
        out[f"{p}_area_ha"] = area_vs
        out[f"{p}_pct"] = np.where(out["area_ha_geo"] > 0, area_vs / out["area_ha_geo"] * 100.0, 0.0)
        out[f"{p}_n_pol"] = d.drop_duplicates(["id_proj", "vs_camada", "vs_id"]).groupby("id_proj").size().reindex(out["id_proj"]).fillna(0).astype(int).to_numpy()
        for b in cfg.BIOMAS_VS:
            sb = d[d["vs_bioma"] == b]
            ub = emb.uniao_por_id(sb, out["id_proj"]) if len(sb) else np.array([None] * len(out), dtype=object)
            out[f"{p}_ha_{b.lower()}"] = geo.area_ha(ub)
        log(f"  {p}: {len(d)} peças em {int(out[f'{p}_tem'].sum())} embargos, VS nos embargos (soma das uniões) {area_vs.sum():,.1f} ha "
            f"(peças fora do embargo {fora.sum():.6f} ha; {time.time() - t0:.0f}s)")
    res = gpd.GeoDataFrame(out, geometry=geoms, crs=g.crs)
    pessoais = [c for c in res.columns if c in cfg.COLUNAS_PESSOAIS_PANGIA or any(k in c.lower() for k in ("cpf", "cnpj", "nome_", "editor"))]
    assert not pessoais, f"possível dado pessoal nas saídas: {pessoais}"

    # ---- saídas ----
    tem = np.zeros(len(res), dtype=bool)
    for p in cfg.VS_VERSOES:
        tem |= res[f"{p}_tem"].to_numpy() == 1
    tem &= ~sem_geom
    ele = res[tem].copy().reset_index(drop=True)
    cfg.SAIDA_INSUMOS.mkdir(parents=True, exist_ok=True)
    io.gravar_camada(ele, cfg.SAIDA_INSUMOS / f"{NOME_ARQ_EMB}.gpkg", "IN_EMBARGOS_PANGIA", primeira=True)
    arq_vs = cfg.SAIDA_INSUMOS / f"{NOME_ARQ_EMB}_VS.gpkg"
    for k, p in enumerate(cfg.VS_VERSOES):
        d = ped[p].copy()
        d["area_ha"] = geo.area_ha(d["geometry"].values)
        io.gravar_camada(gpd.GeoDataFrame(d, geometry="geometry", crs=res.crs), arq_vs, f"{p}_pedacos", primeira=(k == 0))
    exc = res[~tem].drop(columns="geometry").copy()
    exc["motivo_elegibilidade"] = np.where(sem_geom[~tem], "sem geometria", "sem VS qualificada dentro do embargo (vs22q e vs2224q)")
    exc[["id_proj", "num_tad", "serie_tad", "uf_fonte", "data_embargo", "area_ha_geo", "motivo_elegibilidade", "fid_orig"]].to_csv(
        cfg.SAIDA_INSUMOS / f"{NOME_ARQ_EMB}_excluidos.csv", index=False, encoding="utf-8-sig")
    linhas = []
    for chave in ["TOTAL"] + sorted(res["uf_fonte"].dropna().unique()):
        sub = res if chave == "TOTAL" else res[res["uf_fonte"] == chave]
        e_ = sub[tem[sub.index]]
        r = {"grupo": chave if chave == "TOTAL" else f"uf/{chave}", "n_embargos": len(sub), "n_com_vs": len(e_),
             "area_embargos_ha": sub["area_ha_geo"].sum(), "area_embargos_com_vs_ha": e_["area_ha_geo"].sum()}
        for p in cfg.VS_VERSOES:
            r[f"n_com_{p}"] = int(sub[f"{p}_tem"].sum())
            r[f"{p}_vs_nos_embargos_ha"] = sub[f"{p}_area_ha"].sum()
        linhas.append(r)
    resumo = pd.DataFrame(linhas)
    resumo.to_csv(cfg.SAIDA_INSUMOS / f"{NOME_ARQ_EMB}_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo.head(1).round(1).to_string(index=False))
    log(f"IN_EMBARGOS_PANGIA: {len(ele)} embargos com VS ({len(res) - len(ele)} sem VS ficam fora), "
        f"{ele['area_ha_geo'].sum():,.1f} ha de embargos inteiros (referência: a classe 4 conta só a VS dentro deles)")
    log(f"gravado: {cfg.SAIDA_INSUMOS / (NOME_ARQ_EMB + '.gpkg')}")
    return ele, ped


def preparar_or(log):
    """Classe 5: Observatório da Restauração (área total dos polígonos; VS como atributo).

    Desde o ORR 2026 (24/09/2026), a fonte vem no nível de projeto (86 mil polígonos, sem campo 'hierarquia' e sem 'id_proj'
    único - ao contrário do ORR 2025, que trazia só 4 feições dissolvidas por bioma). Por decisão do usuário, entram TODOS os
    polígonos, sem filtro de status (o arquivo não traz mais 'hierarquia'; o campo 'ProjAtivo', quando existir, também não
    filtra nada). `fid_orig` vem do FID do próprio GeoPackage (com_fid=True em `io.ler_camada`), único por definição, e serve
    de base para um `id_proj` único (o ORR 2025 usava só o bioma, porque tinha 1 polígono por bioma)."""
    import geopandas as gpd
    import shapely

    fonte = cfg.FONTES["or"]
    arq = cfg.RAIZ / fonte["arquivo"]
    if not arq.exists():
        raise FileNotFoundError(f"Não encontrei {arq}.")
    E = cfg.ELEGIBILIDADE_OR
    campo_bioma = fonte.get("campo_bioma", "Bioma")
    campo_area = fonte.get("campo_area", "Area_ha")
    log(f"lendo {arq}")
    g = io.ler_camada(arq, fonte["camada"], com_fid=True)
    geoms, invalida = geo.reparar(g.geometry.values)
    sem_geom = np.array([x is None or x.is_empty for x in geoms])
    area = geo.area_ha(geoms)
    motivo = np.where(sem_geom, "sem geometria", np.where(area <= E["area_min_ha"], "área desprezível", ""))
    faltam = sorted(set(g[campo_bioma]) - set(cfg.BIOMA_IBGE_PARA_VS))
    assert not faltam, f"bioma sem correspondência em BIOMA_IBGE_PARA_VS: {faltam}"
    bioma_vs = g[campo_bioma].map(cfg.BIOMA_IBGE_PARA_VS)
    n_partes = np.array([len(shapely.get_parts(x)) if x is not None else 0 for x in geoms])
    out = pd.DataFrame(index=g.index)
    out["fid_orig"] = g["fid_orig"].astype("Int64")
    out["id_proj"] = "ORR-" + bioma_vs + "-" + out["fid_orig"].astype(str)
    out["fonte_dado"] = Path(fonte["arquivo"]).stem
    out["categoria"] = "or"
    out["categoria_nome"] = cfg.NOME_OR
    out["camada_orig"] = fonte["camada"]
    out["bioma_fonte"] = g[campo_bioma]
    out["area_decl_ha"] = pd.to_numeric(g[campo_area], errors="coerce")
    out["area_ha_geo"] = area
    out["n_partes"] = n_partes
    out["elegivel_computo"] = (motivo == "").astype(int)
    out["motivo_elegibilidade"] = motivo
    out["geom_reparada"] = invalida.astype(int)
    assert out["id_proj"].is_unique, "id_proj repetido"
    log(f"  {len(g)} polígonos | elegíveis {int(out['elegivel_computo'].sum())} | reparados {int(invalida.sum())} | "
        f"{int(n_partes.sum())} partes | área {area.sum():,.1f} ha (declarada {out['area_decl_ha'].sum():,.1f} ha)")
    ele = gpd.GeoDataFrame(out, geometry=geoms, crs=g.crs)
    ele = ele[ele["elegivel_computo"] == 1].copy().reset_index(drop=True)

    # ---- VS qualificada (2 versões): partes dos polígonos agrupadas em células ----
    cel = cfg.CELULA_VS_OR_GRAUS
    partes, ids, grupos = [], [], []
    for pid, gm in zip(ele["id_proj"], ele.geometry.values):
        ps = shapely.get_parts(gm)
        cx, cy = shapely.get_x(shapely.centroid(ps)), shapely.get_y(shapely.centroid(ps))
        partes.extend(list(ps))
        ids.extend([pid] * len(ps))
        grupos.extend([f"{int(np.floor(x / cel))}_{int(np.floor(y / cel))}" for x, y in zip(cx, cy)])
    log(f"VS x {len(partes)} partes em {len(set(grupos))} células de {cel} grau")
    ped = {}
    for p in cfg.VS_VERSOES:
        t0 = time.time()
        log(f"{p} ({cfg.VS_VERSOES[p]}):")
        ped[p] = vsm.pedacos_em_poligonos(np.array(partes, dtype=object), np.array(ids), np.array(grupos), cfg.VS_CAMADAS[p], cfg.RAIZ, log=log)
        at = vsm.atributos_vs(ped[p], ele["id_proj"], ele["area_ha_geo"], cfg.BIOMAS_VS)
        for c in at.columns:
            ele[f"{p}_{c}"] = at[c].to_numpy()
        log(f"  {p}: {len(ped[p])} peças, VS nos polígonos {ele[f'{p}_area_ha'].sum():,.1f} ha ({time.time() - t0:.0f}s)")

    # ---- saídas ----
    cfg.SAIDA_INSUMOS.mkdir(parents=True, exist_ok=True)
    io.gravar_camada(ele, cfg.SAIDA_INSUMOS / f"{NOME_ARQ_OR}.gpkg", "IN_OR", primeira=True)
    arq_vs = cfg.SAIDA_INSUMOS / f"{NOME_ARQ_OR}_VS.gpkg"
    for k, p in enumerate(cfg.VS_VERSOES):
        d = ped[p].copy()
        d["area_ha"] = geo.area_ha(d["geometry"].values)
        io.gravar_camada(gpd.GeoDataFrame(d, geometry="geometry", crs=g.crs), arq_vs, f"{p}_pedacos", primeira=(k == 0))
    exc = out[out["elegivel_computo"] == 0]
    exc[["id_proj", "bioma_fonte", "area_ha_geo", "motivo_elegibilidade", "fid_orig"]].to_csv(
        cfg.SAIDA_INSUMOS / f"{NOME_ARQ_OR}_excluidos.csv", index=False, encoding="utf-8-sig")
    linhas = []
    for _, r in ele.iterrows():
        linha = {"id_proj": r["id_proj"], "bioma": r["bioma_fonte"], "n_partes": r["n_partes"], "area_ha_geo": r["area_ha_geo"], "area_decl_ha": r["area_decl_ha"]}
        for p in cfg.VS_VERSOES:
            linha[f"{p}_area_ha"] = r[f"{p}_area_ha"]
            linha[f"{p}_pct"] = r[f"{p}_pct"]
        linhas.append(linha)
    resumo = pd.DataFrame(linhas)
    tot = {"id_proj": "TOTAL", "bioma": "", **{c: resumo[c].sum() for c in resumo.columns if c not in ("id_proj", "bioma", "vs22q_pct", "vs2224q_pct")}}
    for p in cfg.VS_VERSOES:
        tot[f"{p}_pct"] = tot[f"{p}_area_ha"] / tot["area_ha_geo"] * 100.0
    resumo = pd.concat([resumo, pd.DataFrame([tot])], ignore_index=True)
    resumo.to_csv(cfg.SAIDA_INSUMOS / f"{NOME_ARQ_OR}_resumo.csv", index=False, encoding="utf-8-sig")
    log("\n" + resumo.round(1).to_string(index=False))
    log(f"IN_OR: {len(ele)} polígonos, {ele['area_ha_geo'].sum():,.1f} ha (área total, com ou sem VS)")
    log(f"gravado: {cfg.SAIDA_INSUMOS / (NOME_ARQ_OR + '.gpkg')}")
    return ele, ped


# ---------------------------------------------------------------------------
# Classes 6 a 8 (Governança): TI, UC e ProManguezal
# ---------------------------------------------------------------------------
_TERRITORIOS = {
    "ti": dict(nome=NOME_ARQ_TI, prefixo="TI", rotulo="Terras Indígenas (FUNAI 07/05/2026)",
               colunas=["terrai_cod", "terrai_nom", "etnia_nome", "uf_sigla", "fase_ti", "vs_id", "vs_ano", "vs_bioma", "area_ha"],
               grupo=["fase_ti"], id_terr="terrai_cod"),
    "uc": dict(nome=NOME_ARQ_UC, prefixo="UC", rotulo="Unidades de Conservação (CNUC 07/05/2026)",
               colunas=["cd_cnuc", "uc_id", "nome_uc", "grupo", "categoria", "esfera", "uf", "cria_ano", "limite", "vs_id", "vs_ano", "vs_bioma", "area_ha"],
               grupo=["grupo", "categoria"], id_terr="cd_cnuc"),
    "manguezal": dict(nome=NOME_ARQ_MANGUEZAL, prefixo="MG", rotulo="ProManguezal (IBAMA 08/05/2026)",
                      colunas=["Id", "vs_id", "vs_ano", "vs_bioma", "area_ha"], grupo=[], id_terr=None),   # Id vem zerado no ProManguezal
}


def _fechar_versao(chave, T, regras, p, d, excluidos, resumo, arq_out, primeira, log):
    """Última etapa de uma versão da VS: identificador da peça, conferência com o cruzamento, gravação e resumos."""
    import geopandas as gpd

    d["id_peca"] = [f"{T['prefixo']}-{p}-{n:07d}" for n in range(1, len(d) + 1)]
    # conferência com a área gravada no cruzamento (o cruzamento e o recálculo geodésico devem coincidir)
    ok = d["area_ha_arq"].notna() & (d["area_original_ha"] > 0)
    dif = float((d.loc[ok, "area_original_ha"] - d.loc[ok, "area_ha_arq"]).abs().max()) if ok.any() else 0.0
    log(f"  {p}: eleitas {len(d):,} peças, {d['area_ha_geo'].sum():,.1f} ha (VS dentro do território); dif. máx. de área x arquivo {dif:.4f} ha")
    gdf = gpd.GeoDataFrame(d.drop(columns=["geometry"]), geometry=geo.para_multi_lista(d["geometry"].values), crs=f"EPSG:{cfg.CRS_TRABALHO}")
    io.gravar_camada(gdf, arq_out, f"{p}_pedacos", primeira=primeira)
    grp = T["grupo"] or []
    resumo.append({"versao": p, "grupo": "TOTAL", "n_pecas": len(d), "n_territorios": d[T["id_terr"]].nunique() if T["id_terr"] else None,
                   "vs_arquivo_ha": float(d["area_original_ha"].sum()), "vs_elegivel_ha": float(d["area_ha_geo"].sum())})
    for k, sub in (d.groupby(grp) if grp else []):
        k = k if isinstance(k, tuple) else (k,)
        resumo.append({"versao": p, "grupo": " | ".join(map(str, k)), "n_pecas": len(sub), "n_territorios": sub[T["id_terr"]].nunique() if T["id_terr"] else None,
                       "vs_arquivo_ha": float(sub["area_original_ha"].sum()), "vs_elegivel_ha": float(sub["area_ha_geo"].sum())})
    if chave == "uc":
        apa_d = d[d["apa"]]
        resumo.append({"versao": p, "grupo": "APA (área pública)", "n_pecas": len(apa_d), "n_territorios": apa_d["cd_cnuc"].nunique(),
                       "vs_arquivo_ha": float(apa_d["area_original_ha"].sum()), "vs_elegivel_ha": float(apa_d["area_ha_geo"].sum()),
                       "area_privada_retirada_ha": float(apa_d["area_privada_ha"].sum())})


def preparar_territorio(chave, log):
    """Insumo das classes 6 a 8: peças "VS x território" elegíveis, por versão da VS.

    Fase 1: lê o cruzamento de cada versão e aplica a elegibilidade. Fase 2 (só UC): tira das APAs a área privada, lendo o CAR total
    UMA vez por UF para as duas versões (é a etapa mais pesada). Fase 3: grava."""
    T = _TERRITORIOS[chave]
    fonte = cfg.FONTES[chave]
    regras = {"ti": cfg.ELEGIBILIDADE_TI, "uc": cfg.ELEGIBILIDADE_UC, "manguezal": cfg.ELEGIBILIDADE_MANGUEZAL}[chave]
    cfg.SAIDA_INSUMOS.mkdir(parents=True, exist_ok=True)
    arq_out = cfg.SAIDA_INSUMOS / f"{T['nome']}.gpkg"
    log(f"{T['rotulo']}: peças VS x território de cada versão da VS")
    resumo, excluidos, dados = [], [], {}
    for p in cfg.VS_VERSOES:
        caminho = cfg.RAIZ / fonte["cruzamento"][p]
        d, info = gov.ler_pedacos(caminho, fonte["camada_cruzamento"], T["colunas"], regras["area_min_ha"])
        log(f"--- {p} ---  lidas {info['n_lidas']:,} peças ({info['n_reparadas']} geometrias reparadas; {info['n_vazias']} vazias; {info['n_micro']} micro)")
        d["area_original_ha"] = d["area_ha_geo"]
        if chave == "ti":
            eleg, motivo = gov.elegiveis_ti(d, regras)
        elif chave == "uc":
            eleg, motivo = gov.elegiveis_uc(d, regras)
        else:
            eleg, motivo = np.ones(len(d), dtype=bool), np.array([""] * len(d), dtype=object)
        fora = d[~eleg].assign(motivo=motivo[~eleg])
        for m, sub in fora.groupby("motivo"):
            excluidos.append({"versao": p, "motivo": m, "n_pecas": len(sub), "area_ha": float(sub["area_ha_geo"].sum())})
            log(f"  fora: {m}: {len(sub):,} peças, {sub['area_ha_geo'].sum():,.1f} ha")
        d = d[eleg].reset_index(drop=True)
        if chave == "uc":
            d["apa"] = gov.eh_apa(d, regras)
            d["area_privada_ha"] = 0.0
        dados[p] = d

    if chave == "uc":
        # APAs: só a área pública (APA menos o CAR total); as duas versões juntas, para ler cada UF uma vez
        ia = {p: np.where(dados[p]["apa"].to_numpy())[0] for p in dados}
        juntas = np.concatenate([dados[p]["geometry"].values[ia[p]] for p in dados])
        log(f"APAs: {len(juntas):,} peças nas duas versões; subtraindo o CAR total (área privada)")
        pub, ret = gov.apa_area_publica(juntas, log=log)
        ini = 0
        for p in dados:
            d, k = dados[p], len(ia[p])
            d.loc[d.index[ia[p]], "geometry"] = pd.Series(list(pub[ini:ini + k]), index=d.index[ia[p]], dtype=object)
            d.loc[d.index[ia[p]], "area_privada_ha"] = ret[ini:ini + k]
            ini += k
            d["area_ha_geo"] = geo.area_ha(d["geometry"].values)
            apa = d["apa"].to_numpy()
            log(f"  {p}: APAs {d.loc[apa, 'area_original_ha'].sum():,.1f} ha de VS; {ret[ini - k:ini].sum():,.1f} ha privados (CAR) retirados; "
                f"área pública {d.loc[apa, 'area_ha_geo'].sum():,.1f} ha")
            vazias = np.array([g is None or g.is_empty for g in d["geometry"]]) | (d["area_ha_geo"].to_numpy() <= regras["area_min_ha"])
            if vazias.any():
                sub = d[vazias]
                excluidos.append({"versao": p, "motivo": "APA inteira dentro de imóveis do CAR (área privada)", "n_pecas": len(sub),
                                  "area_ha": float(sub["area_original_ha"].sum())})
                log(f"  {p}: fora: APA inteira dentro de imóveis do CAR: {len(sub):,} peças, {sub['area_original_ha'].sum():,.1f} ha")
            dados[p] = d[~vazias].reset_index(drop=True)

    for k, p in enumerate(dados):
        _fechar_versao(chave, T, regras, p, dados[p], excluidos, resumo, arq_out, k == 0, log)
    pd.DataFrame(resumo).to_csv(cfg.SAIDA_INSUMOS / f"{T['nome']}_resumo.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(excluidos, columns=["versao", "motivo", "n_pecas", "area_ha"]).to_csv(cfg.SAIDA_INSUMOS / f"{T['nome']}_excluidos.csv", index=False, encoding="utf-8-sig")
    log(f"gravado: {arq_out}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pedidas = [a.lower() for a in argv] or FONTES_IMPLEMENTADAS
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
    if "car_regularizacao" in pedidas:
        preparar_car_regularizacao(log)
    if "embargos_pangia" in pedidas:
        preparar_embargos_pangia(log)
    if "or" in pedidas:
        preparar_or(log)
    for chave in ("ti", "uc", "manguezal"):
        if chave in pedidas:
            preparar_territorio(chave, log)
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
