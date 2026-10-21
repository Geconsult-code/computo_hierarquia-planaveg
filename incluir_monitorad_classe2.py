"""Inclusão incremental do MonitoRAD (IBAMA) como classe 2 da hierarquia, sem refazer o cômputo.

Mesmo princípio de incluir_icmbio_classe4.py: cada classe k > 2 já é a sua fonte menos as classes 1..k-1. Sendo
Δ = MonitoRAD - classe 1 (Recooperar), a nova classe k é a classe k atual menos Δ - o mesmo resultado de recalcular
tudo, porque a classe 2 não existia (estava desativada) e a classe 1 não muda.

Entrada (em config_computo.SAIDA_INSUMOS):
    IN_MonitoRAD_2026.gpkg, camada IN_MONITORAD - 2.361 polígonos "Com indício de recuperação" sem sobreposição interna
    (consolidar_monitorad.py; decisões de 20/10/2026): qualquer `value`; recortados pelo polígono do próprio embargo;
    na sobreposição entre embargos fica o mais antigo. Entra pela ÁREA TOTAL do polígono, sem cruzamento com a VS
    (decisão de 20/10/2026), por isso Δ é o mesmo nas duas versões da VS.

O que o script faz:
    1. Δ = cada polígono do MonitoRAD menos a classe 1 (P2_RECOOPERAR).
    2. Classe 2: grava SAIDA_TIER2/P2_MonitoRAD_2026.gpkg, camadas P2_MONITORAD (Δ, polígonos líquidos com
       id_proj "MRAD-nnnnn", UF e bioma principais, area_liquida_ha) e P2_MONITORAD_poligonos (polígonos inteiros
       com a área líquida e a parte sobreposta ao Recooperar).
    3. Classes 3 a 11: subtrai Δ, no próprio arquivo, das camadas que as classes seguintes e o reporte final leem:
       P2_CAR_REGULARIZACAO (uma vez - não depende da versão), e por versão P2_OUTROS_PROJETOS_<v> (PANGIA e ICMBio),
       P2_OR_<v>, P1_TI_<v>, P1_UC_<v>, P1_MANGUEZAL_<v>, P1_APP/AUR/RL_<v> (nacionais) e os _por_uf\\P1_APP/AUR/RL_<v>_<UF>.
    4. Conferência independente: relê as feições alteradas e confirma que a interseção restante com Δ é zero.

Saídas (em config_computo.SAIDA_TIER2): MonitoRAD_incremental_resumo.csv, _alteracoes.csv, _estado.json (retomada:
rodar de novo nunca subtrai duas vezes) e _log_monitorad_incremental.txt.
Os resumos T3..T11_*.csv e as colunas de área das camadas *_poligonos das classes seguintes NÃO são refeitos: os
totais atualizados ficam no resumo acima e no reporte final, que deve ser gerado depois.

Uso (env geo; PLANAVEG_RAIZ aponta para a cópia de trabalho - nunca para o backup):
    $env:PLANAVEG_RAIZ = "D:\\PLANAVEG_TEMP"           (PowerShell; no cmd: set PLANAVEG_RAIZ=D:\\PLANAVEG_TEMP)
    python incluir_monitorad_classe2.py               # simulação: calcula Δ e as áreas a tirar, não grava nada
    python incluir_monitorad_classe2.py --executar    # grava
Opções: --versoes vs22q vs2224q   --classes SICAR_REGULARIZACAO OUTROS_PROJETOS OR TI UC MANGUEZAL APP AUR RL
Depois: python gerar_geopackages_finais.py MONITORAD SICAR_REGULARIZACAO OUTROS_PROJETOS OR TI UC MANGUEZAL APP AUR RL
        python gerar_geopackages_finais.py --so-total
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio
from shapely.strtree import STRtree

import config_computo as cfg
from computo import anteriores
from computo import geometria as geo
from computo import io_dados as io
import incluir_icmbio_classe4 as base   # subtração/conferência no GeoPackage (sqlite), já validadas na inclusão do ICMBio

ARQ_IN = cfg.SAIDA_INSUMOS / "IN_MonitoRAD_2026.gpkg"
CAMADA_IN = "IN_MONITORAD"
VERSOES = list(cfg.VS_VERSOES)
CLASSES = ["SICAR_REGULARIZACAO", "OUTROS_PROJETOS", "OR", "TI", "UC", "MANGUEZAL", "APP", "AUR", "RL"]
SEM_VERSAO = {"SICAR_REGULARIZACAO"}
ARQ_T2 = cfg.SAIDA_TIER2 / anteriores.ARQ_OUT_MONITORAD
ARQ_LOG = cfg.SAIDA_TIER2 / "_log_monitorad_incremental.txt"
ARQ_ESTADO = cfg.SAIDA_TIER2 / "MonitoRAD_incremental_estado.json"
ARQ_RESUMO = cfg.SAIDA_TIER2 / "MonitoRAD_incremental_resumo.csv"
ARQ_ALTER = cfg.SAIDA_TIER2 / "MonitoRAD_incremental_alteracoes.csv"
MIN_HA = base.MIN_HA
TOL = base.TOL_CONFERENCIA_HA


def log(msg):
    io.log(msg, ARQ_LOG)


def ler_estado():
    return json.loads(ARQ_ESTADO.read_text(encoding="utf-8")) if ARQ_ESTADO.exists() else {}


def marcar(estado, chave):
    estado[chave] = time.strftime("%Y-%m-%d %H:%M:%S")
    ARQ_ESTADO.write_text(json.dumps(estado, indent=1, ensure_ascii=False), encoding="utf-8")


def calcular_delta(mr):
    """Para cada polígono do MonitoRAD: a parte fora da classe 1 (Recooperar). Devolve (Δ, sobreposta ao Recooperar)."""
    arq, camada = anteriores.arquivos_classes()["RECOOPERAR"]
    xmin, ymin, xmax, ymax = mr.total_bounds
    rec = io.ler_camada(arq, camada, colunas=["id_proj"], bbox=(xmin, ymin, xmax, ymax))
    todas = np.array(rec.geometry.values, dtype=object)
    tree = STRtree(todas) if len(todas) else None
    liq = np.empty(len(mr), dtype=object)
    sobre = np.zeros(len(mr))
    for i, g in enumerate(mr.geometry.values):
        idx = tree.query(g, predicate="intersects") if tree is not None else []
        if len(idx) == 0:
            liq[i] = g
            continue
        u = geo.uniao_robusta([todas[k] for k in idx])
        inter = geo.so_poligonos(geo.intersecao_robusta([g], [u])[0])
        sobre[i] = geo.area_ha_geodesica(inter) if inter is not None else 0.0
        liq[i] = geo.so_poligonos(geo.diferenca_robusta([g], [u])[0])
    area = np.nan_to_num(geo.area_ha(liq), nan=0.0)
    return liq, area, sobre


def gravar_classe2(mr, liq, area, sobre, lim, executar):
    cfg.SAIDA_TIER2.mkdir(parents=True, exist_ok=True)
    ok = (area > MIN_HA) & np.array([g is not None for g in liq])
    ufs, bios = base.uf_bioma_principal([liq[i] for i in np.flatnonzero(ok)], lim)
    sel = mr[ok]
    net = gpd.GeoDataFrame({
        "id_proj": sel["id_monitorad"].values,
        "seq_tad": sel["seq_tad"].values,
        "data_embargo": sel["dat_embarg"].values,
        "uf_principal": ufs, "bioma_principal": bios,
        "area_liquida_ha": area[ok],
    }, geometry=geo.para_multi_lista(liq[ok]), crs="EPSG:4674")
    pol = mr.drop(columns="geometry").copy()
    pol["id_proj"] = pol["id_monitorad"]
    pol["area_ha_geo"] = geo.area_ha(mr.geometry.values)
    pol["sobreposta_recooperar_ha"] = sobre
    pol["area_liquida_ha"] = area
    pol["elegivel_computo"] = 1
    pol = gpd.GeoDataFrame(pol, geometry=mr.geometry.values, crs="EPSG:4674")
    log(f"  classe 2: {len(net)} polígonos líquidos, {net['area_liquida_ha'].sum():,.2f} ha "
        f"(sobreposta ao Recooperar: {sobre.sum():,.2f} ha)")
    if executar:
        if ARQ_T2.exists():
            ARQ_T2.unlink()
        pyogrio.write_dataframe(net, str(ARQ_T2), layer="P2_MONITORAD", driver="GPKG", promote_to_multi=True)
        pyogrio.write_dataframe(pol, str(ARQ_T2), layer="P2_MONITORAD_poligonos", driver="GPKG", promote_to_multi=True,
                                append=True)
    return net


def alvos(versao, classes):
    """[(rótulo, arquivo, camada, chave_estado)]; SICAR_REGULARIZACAO só na 1a versão (é a mesma camada)."""
    out = []
    for rot, arq, camada in base.alvos(versao, classes):
        cls = rot.split("_")[0] if rot.split("_")[0] in ("APP", "AUR", "RL") else rot
        if cls in SEM_VERSAO:
            if versao != VERSOES[0]:
                continue
            out.append((rot, arq, camada, f"comum|{rot}"))
        else:
            out.append((rot, arq, camada, f"{versao}|{rot}"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inclui o MonitoRAD como classe 2 e subtrai das classes 3 a 11")
    ap.add_argument("--executar", action="store_true")
    ap.add_argument("--versoes", nargs="+", choices=VERSOES, default=VERSOES)
    ap.add_argument("--classes", nargs="+", choices=CLASSES, default=CLASSES)
    a = ap.parse_args(argv)
    if not ARQ_IN.exists():
        print(f"Entrada não encontrada: {ARQ_IN}", file=sys.stderr)
        return 1
    cfg.SAIDA_TIER2.mkdir(parents=True, exist_ok=True)
    log(f"=== incluir_monitorad_classe2 ({'EXECUÇÃO' if a.executar else 'SIMULAÇÃO'}) | RAIZ = {cfg.RAIZ}")
    mr = io.ler_camada(ARQ_IN, CAMADA_IN)
    mr["geometry"], _ = geo.reparar(mr.geometry.values)
    log(f"MonitoRAD: {len(mr)} polígonos, {geo.area_ha(mr.geometry.values).sum():,.2f} ha")
    lim = anteriores.carregar_limites()
    estado = ler_estado() if a.executar else {}
    t0 = time.time()
    if "classe2" in estado:
        log(f"  classe 2: já gravada em {estado['classe2']} - leio o Δ gravado")
        net = io.ler_camada(ARQ_T2, "P2_MONITORAD")
    else:
        liq, area, sobre = calcular_delta(mr)
        net = gravar_classe2(mr, liq, area, sobre, lim, a.executar)
        if a.executar:
            marcar(estado, "classe2")
    entra = float(net["area_liquida_ha"].sum())
    resumo = [dict(versao="todas", rotulo="MONITORAD", arquivo=str(ARQ_T2), camada="P2_MONITORAD", candidatas=len(mr),
                   alteradas=len(net), apagadas=0, area_antes_ha=0.0, area_removida_ha=-entra, area_depois_ha=entra,
                   intersecao_medida_ha=0.0, residual_ha=0.0)]
    alteracoes = []
    dg = np.array(geo.para_multi_lista(net.geometry.values), dtype=object)
    tree = STRtree(dg)
    for v in a.versoes:
        log(f"--- versão {v}")
        for rotulo, arq, camada, chave in alvos(v, a.classes):
            if chave in estado:
                log(f"  {rotulo:20s}: já feito em {estado[chave]}")
                continue
            if not Path(arq).exists():
                log(f"  {rotulo:20s}: arquivo não encontrado ({arq}) - pulei")
                continue
            t1 = time.time()
            vv = "todas" if chave.startswith("comum|") else v
            r = base.subtrair_camada(arq, camada, dg, tree, a.executar, alteracoes, rotulo, vv)
            r["residual_ha"] = base.conferir_camada(arq, camada, dg, tree) if a.executar else float("nan")
            resumo.append(r)
            ok = "" if not a.executar else ("  conferência OK" if r["residual_ha"] < TOL
                                            else f"  ATENÇÃO: ainda sobrepõe {r['residual_ha']:.4f} ha")
            log(f"  {rotulo:20s}: {r['alteradas']} recortadas, {r['apagadas']} apagadas, "
                f"-{r['area_removida_ha']:,.2f} ha (interseção medida {r['intersecao_medida_ha']:,.2f}) "
                f"[{time.time() - t1:.0f}s]{ok}")
            if a.executar:
                marcar(estado, chave)

    def gravar_csv(linhas, arq, chave):
        df = pd.DataFrame(linhas)
        if a.executar and arq.exists():
            antigo = pd.read_csv(arq, sep=";", decimal=",", encoding="utf-8-sig")
            df = pd.concat([antigo, df], ignore_index=True).drop_duplicates(subset=chave, keep="last")
        destino = arq if a.executar else arq.with_name(arq.stem + "_SIMULACAO.csv")
        df.to_csv(destino, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    gravar_csv(resumo, ARQ_RESUMO, ["versao", "rotulo"])
    if alteracoes:
        gravar_csv(alteracoes, ARQ_ALTER, ["versao", "rotulo", "fid"])
    nacionais = set(a.classes)
    sicar = sum(r["area_removida_ha"] for r in resumo if r["rotulo"] == "SICAR_REGULARIZACAO")
    for v in a.versoes:
        sai = sicar + sum(r["area_removida_ha"] for r in resumo if r["versao"] == v and r["rotulo"] in nacionais)
        log(f"BALANÇO {v} (camadas tratadas nesta execução): classe 2 +{entra:,.2f} ha; classes 3-11 -{sai:,.2f} ha; "
            f"total do cômputo +{entra - sai:,.2f} ha")
    log(f"fim ({(time.time() - t0) / 60:.1f} min). " + ("" if a.executar else "SIMULAÇÃO: nada foi gravado."))
    if a.executar:
        log("Próximo passo: python gerar_geopackages_finais.py MONITORAD SICAR_REGULARIZACAO OUTROS_PROJETOS OR TI UC "
            "MANGUEZAL APP AUR RL e depois --so-total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
