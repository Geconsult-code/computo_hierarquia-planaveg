"""Inclusão incremental da FUNBIO na classe 4 (Outros projetos), sem refazer as classes 5 a 11 (23/10/2026).

Por que é exato: cada classe k > 4 já é a sua fonte menos as classes 1..k-1. A classe 4 é refeita antes por
``2_camada2_projetos.py OUTROS_PROJETOS`` com cfg.FONTES_OUTROS_PROJETOS = ["icmbio", "funbio"]: o ICMBio sai igual (precede a
FUNBIO) e a FUNBIO entra só com Δ = FUNBIO menos as classes 1, 2, 3 e o ICMBio. Subtraindo Δ das classes 5 a 11 chega-se ao mesmo
resultado de recalcular tudo. As classes 1, 2 e 3 não mudam.

Entrada: Tier4_Outros_Projetos/P2_Outros_Projetos_2026.gpkg, camada P2_OUTROS_PROJETOS_<versão>, feições id_proj 'FUNBIO-%'
         (Δ; a mesma geometria nas duas versões da VS, porque a FUNBIO entra pela área total).
Faz, para cada versão da VS: subtrai Δ, no próprio arquivo, de P2_OR_<v>, P1_TI_<v>, P1_UC_<v>, P1_MANGUEZAL_<v>,
P1_APP/AUR/RL_<v> (nacionais) e _por_uf\\P1_APP/AUR/RL_<v>_<UF>.gpkg, e confere que a interseção restante é zero.
Saídas (Tier4): FUNBIO_incremental_resumo.csv, _alteracoes.csv, _estado.json (retomada), _log_funbio_incremental.txt.

Uso (env geo; PLANAVEG_RAIZ aponta para a cópia de trabalho - nunca para o backup):
    python 2_camada2_projetos.py OUTROS_PROJETOS      # classe 4 com ICMBio e FUNBIO
    python incluir_funbio_classe4.py                 # simulação
    python incluir_funbio_classe4.py --executar      # grava
Depois: python gerar_geopackages_finais.py OUTROS_PROJETOS OR TI UC MANGUEZAL AUR APP RL e --so-total
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.strtree import STRtree

import config_computo as cfg
from computo import anteriores
from computo import geometria as geo
from computo import io_dados as io
import incluir_icmbio_classe4 as base

VERSOES = list(cfg.VS_VERSOES)
CLASSES = ["OR", "TI", "UC", "MANGUEZAL", "APP", "AUR", "RL"]
ARQ_T4 = cfg.SAIDA_TIER4 / anteriores.ARQ_OUT_EMB
ARQ_LOG = cfg.SAIDA_TIER4 / "_log_funbio_incremental.txt"
ARQ_ESTADO = cfg.SAIDA_TIER4 / "FUNBIO_incremental_estado.json"
ARQ_RESUMO = cfg.SAIDA_TIER4 / "FUNBIO_incremental_resumo.csv"
ARQ_ALTER = cfg.SAIDA_TIER4 / "FUNBIO_incremental_alteracoes.csv"
TOL = base.TOL_CONFERENCIA_HA


def log(msg):
    io.log(msg, ARQ_LOG)


def ler_estado():
    return json.loads(ARQ_ESTADO.read_text(encoding="utf-8")) if ARQ_ESTADO.exists() else {}


def marcar(estado, chave):
    estado[chave] = time.strftime("%Y-%m-%d %H:%M:%S")
    ARQ_ESTADO.write_text(json.dumps(estado, indent=1, ensure_ascii=False), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Subtrai das classes 5 a 11 a FUNBIO já incluída na classe 4")
    ap.add_argument("--executar", action="store_true")
    ap.add_argument("--versoes", nargs="+", choices=VERSOES, default=VERSOES)
    ap.add_argument("--classes", nargs="+", choices=CLASSES, default=CLASSES)
    a = ap.parse_args(argv)
    if "funbio" not in cfg.FONTES_OUTROS_PROJETOS:
        print("cfg.FONTES_OUTROS_PROJETOS não inclui a FUNBIO", file=sys.stderr)
        return 1
    log(f"=== incluir_funbio_classe4 ({'EXECUÇÃO' if a.executar else 'SIMULAÇÃO'}) | RAIZ = {cfg.RAIZ}")
    deltas = {}
    for v in VERSOES:
        d = io.ler_camada(ARQ_T4, f"P2_OUTROS_PROJETOS_{v}", where="id_proj LIKE 'FUNBIO-%'")
        deltas[v] = d
        log(f"Δ FUNBIO na classe 4 ({v}): {len(d)} polígonos, {d['area_liquida_ha'].sum():,.2f} ha")
    if len(deltas[VERSOES[0]]) == 0:
        print("Nenhuma feição FUNBIO na classe 4: rode antes 2_camada2_projetos.py OUTROS_PROJETOS", file=sys.stderr)
        return 1
    estado = ler_estado() if a.executar else {}
    resumo, alteracoes = [], []
    t0 = time.time()
    for v in a.versoes:
        log(f"--- versão {v}")
        dg = np.array(geo.para_multi_lista(deltas[v].geometry.values), dtype=object)
        tree = STRtree(dg)
        entra = float(deltas[v]["area_liquida_ha"].sum())
        resumo.append(dict(versao=v, rotulo="OUTROS_PROJETOS (FUNBIO)", arquivo=str(ARQ_T4), camada=f"P2_OUTROS_PROJETOS_{v}",
                           candidatas=len(dg), alteradas=len(dg), apagadas=0, area_antes_ha=0.0, area_removida_ha=-entra,
                           area_depois_ha=entra, intersecao_medida_ha=0.0, residual_ha=0.0))
        for rotulo, arq, camada in base.alvos(v, a.classes):
            chave = f"{v}|{rotulo}"
            if chave in estado:
                log(f"  {rotulo:20s}: já feito em {estado[chave]}")
                continue
            if not Path(arq).exists():
                log(f"  {rotulo:20s}: arquivo não encontrado ({arq}) - pulei")
                continue
            t1 = time.time()
            r = base.subtrair_camada(arq, camada, dg, tree, a.executar, alteracoes, rotulo, v)
            r["residual_ha"] = base.conferir_camada(arq, camada, dg, tree) if a.executar else float("nan")
            resumo.append(r)
            ok = "" if not a.executar else ("  conferência OK" if r["residual_ha"] < TOL
                                            else f"  ATENÇÃO: ainda sobrepõe {r['residual_ha']:.4f} ha")
            log(f"  {rotulo:20s}: {r['alteradas']} recortadas, {r['apagadas']} apagadas, -{r['area_removida_ha']:,.2f} ha "
                f"(interseção medida {r['intersecao_medida_ha']:,.2f}) [{time.time() - t1:.0f}s]{ok}")
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
    for v in a.versoes:
        entra = float(deltas[v]["area_liquida_ha"].sum())
        sai = sum(r["area_removida_ha"] for r in resumo if r["versao"] == v and r["rotulo"] in nacionais)
        log(f"BALANÇO {v}: classe 4 +{entra:,.2f} ha (FUNBIO); classes 5-11 -{sai:,.2f} ha; total do cômputo +{entra - sai:,.2f} ha")
    log(f"fim ({(time.time() - t0) / 60:.1f} min). " + ("" if a.executar else "SIMULAÇÃO: nada foi gravado."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
