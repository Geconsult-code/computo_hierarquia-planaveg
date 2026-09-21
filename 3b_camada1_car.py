"""Passo 3b - Camada 1 (VS legalmente protegida, critério de governança): classes 9, 10 e 11 (APP, AUR e RL dos imóveis do CAR)

Objetivo: aplica a hierarquia do Anexo 1 às classes do CAR. A área da classe é a VS QUALIFICADA dentro da APP, da AUR ou da RL dos imóveis
selecionados do CAR (Habilitados, Analisados, Não analisados). Não refaz os cruzamentos: parte das peças do cruzamento VS x CAR
(Cruzamento_Espacial_Vegetacao_Secundaria/VS-Cadastro_Ambiental_Rural) e as subtrai das classes de maior prioridade.

Regras (config_computo, confirmadas em 21/09/2026):
    * os imóveis Habilitados precedem os Analisados e os Não analisados em qualquer classe; dentro de cada grupo a classe manda:
      APP (9) > AUR (10) > RL (11). Ordem de cálculo: APP, AUR e RL dos Habilitados; depois APP, AUR e RL dos Analisados + Não analisados;
    * entre Analisados e Não analisados a categoria desempata dentro da classe (Analisados > Não analisados); na mesma categoria, a
      sobreposição entre imóveis fica com o menor cod_imovel (o cruzamento não traz a data de cadastro);
    * as peças de um mesmo imóvel se sobrepõem no cruzamento (temas de APP sobrepostos, duplicatas): são unidas por imóvel antes da precedência;
    * cada bloco subtrai as classes 1, 3, 4, 5, 6, 7 e 8 (líquidas, na versão da VS) e os blocos do CAR anteriores da mesma UF;
    * duas versões da VS: vs22q (2022 qualificada) e vs2224q (2022 qualificada; Amazônia e Cerrado pela 2024 qualificada).

Processamento por UF (uma UF, uma versão, as três classes), com retomada: cada UF x versão concluída deixa um marcador em
Tier9_APP/_por_uf. Quando todas as UFs das duas versões estão prontas, o script consolida (GeoPackages, resumos, conferências e acumulados).

Saídas:
    Tier9_APP/P1_APP_CAR_Maio2026.gpkg, Tier10_AUR/P1_AUR_CAR_Maio2026.gpkg, Tier11_RL/P1_RL_CAR_Maio2026.gpkg
        P1_<classe>_vs22q, P1_<classe>_vs2224q   partes líquidas (polígonos simples) por imóvel x UF x bioma (IBGE); disjuntas entre si e
                                                 das classes de maior prioridade. Atributos: classe, categoria, cod_imovel, bioma_vs, ano,
                                                 uf_car (UF do imóvel), uf e bioma (limites IBGE), area_ha
    T<n>_resumo.csv, T<n>_resumo_uf.csv, T<n>_resumo_uf_bioma.csv, T<n>_conferencias.csv (n = 9, 10, 11)
    T9_acumulado_classes_1_3_4_5_6_7_8_9.csv, T10_..._10.csv, T11_..._11.csv (área líquida acumulada por versão, UF e bioma)

Execução:  python 3b_camada1_car.py [UF ...] [--versao vs22q|vs2224q] [--conferencia auto|leve|completa] [--refazer] [--consolidar]
    sem UF: as 27 UFs, nas duas versões. Exige as classes 1, 3, 4, 5, 6, 7 e 8 já processadas. Memória: as UFs grandes (PA, MT, GO, MG)
    pedem alguns GB (as peças e as classes 6 a 8 na caixa da UF). Log: Tier9_APP/_log_passo3b_car.txt.
"""
from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd
import pyogrio

import config_computo as cfg
from computo import anteriores
from computo import car
from computo import governanca as gov
from computo import io_dados as io
from computo.territorio import CelulasUFBioma

ROTULO_PREFIXO = {"APP": "T9", "AUR": "T10", "RL": "T11"}
ACUM_ENTRADA = cfg.SAIDA_TIER8 / "T8_acumulado_classes_1_3_4_5_6_7_8.csv"
ACUM_SAIDA = {"APP": "T9_acumulado_classes_1_3_4_5_6_7_8_9.csv", "AUR": "T10_acumulado_classes_1_3_4_5_6_7_8_9_10.csv",
              "RL": "T11_acumulado_classes_1_3_4_5_6_7_8_9_10_11.csv"}
POR_UF = cfg.SAIDA_TIER9 / "_por_uf"


def _pasta_uf(classe):
    return car.PASTAS[classe] / "_por_uf"


def _marcador(versao, uf):
    return POR_UF / f"ok_{versao}_{uf}.txt"


def _resumir(unidades: pd.DataFrame) -> pd.DataFrame:
    agg = dict(n_pecas=("n_pecas", "sum"), n_imoveis=("cod_imovel", "nunique"),
               area_pecas_arquivo_ha=("area_pecas_arq_ha", "sum"), sobreposta_no_imovel_ha=("sobreposta_no_imovel_ha", "sum"),
               area_uniao_imovel_ha=("area_uniao_imovel_ha", "sum"))
    for c in unidades.columns:
        if c.startswith("sobreposta_") and c.endswith("_ha") and c not in ("sobreposta_no_imovel_ha", "sobreposta_na_classe_ha", "sobreposta_classes_anteriores_ha"):
            agg[c] = (c, "sum")
    agg.update(sobreposta_classes_anteriores_ha=("sobreposta_classes_anteriores_ha", "sum"),
               sobreposta_na_classe_ha=("sobreposta_na_classe_ha", "sum"), area_liquida_ha=("area_liquida_ha", "sum"))
    return unidades.groupby(["classe", "categoria"], as_index=False).agg(**agg)


def processar_uf(uf, versoes, cel, log, conferencia, refazer):
    """Lê as peças da UF uma vez e processa as versões pedidas. Devolve as versões concluídas."""
    pend = [p for p in versoes if refazer or not _marcador(p, uf).exists()]
    if not pend:
        log(f"{uf}: já concluída ({', '.join(versoes)})")
        return []
    log(f"=== {uf} ({', '.join(pend)}) ===")
    brutas = car.ler_pecas_uf(uf, pend)
    feitas = []
    for p in pend:
        d, info = car.preparar_pecas(brutas[p])
        log(f"{uf} {p}: {info['n_lidas']:,} peças lidas ({info['n_reparadas']:,} reparadas, {info['n_vazias']:,} vazias descartadas)")
        res = car.processar_uf_versao(uf, p, d, cel, log=log, conferencia=conferencia)
        conf, unid = [], []
        for classe, r in res.items():
            pasta = _pasta_uf(classe)
            pasta.mkdir(parents=True, exist_ok=True)
            arq = pasta / f"P1_{classe}_{p}_{uf}.gpkg"
            if arq.exists():
                arq.unlink()
            if len(r["partes"]):
                io.gravar_camada(r["partes"], arq, f"P1_{classe}_{p}", primeira=True)
            unid.append(r["unidades"])
            conf += [{"classe": classe, "uf_car": uf, "versao": p, **c} for c in r["conferencias"]]
        POR_UF.mkdir(parents=True, exist_ok=True)
        if unid:
            u = pd.concat(unid, ignore_index=True)
            res_ub = pd.concat([r["partes"].drop(columns="geometry") for r in res.values() if len(r["partes"])], ignore_index=True)
            _resumir(u).assign(versao=p, uf_car=uf).to_csv(POR_UF / f"resumo_{p}_{uf}.csv", index=False, encoding="utf-8-sig")
            (res_ub.groupby(["classe", "categoria", "uf", "bioma"], as_index=False)["area_ha"].sum()
             .rename(columns={"area_ha": "area_liquida_ha"}).assign(versao=p, uf_car=uf)
             .to_csv(POR_UF / f"resumo_uf_bioma_{p}_{uf}.csv", index=False, encoding="utf-8-sig"))
        pd.DataFrame(conf).to_csv(POR_UF / f"conferencias_{p}_{uf}.csv", index=False, encoding="utf-8-sig")
        falhas = [c for c in conf if not c["ok"]]
        for c in falhas:
            log(f"  ATENÇÃO conferência fora do limite: {c['conferencia']} valor {c['valor']:.6g} (limite {c['limite']:.3g})")
        _marcador(p, uf).write_text("ok" if not falhas else f"conferências fora do limite: {len(falhas)}", encoding="utf-8")
        feitas.append(p)
        del res, d, unid
        gov._devolver_memoria()
    del brutas
    gov._devolver_memoria()
    return feitas


def _prontas(versoes, ufs=None):
    return all(_marcador(p, uf).exists() for p in versoes for uf in (ufs or cfg.UFS))


def consolidar(versoes, log, manter_por_uf=False, ufs=None):
    """GeoPackages por classe, resumos, conferências e acumulados (exige todas as UFs das versões; ``ufs`` = subconjunto, para testes)."""
    ufs = ufs or list(cfg.UFS)
    if not _prontas(versoes, ufs):
        faltam = [f"{p}:{uf}" for p in versoes for uf in ufs if not _marcador(p, uf).exists()]
        log(f"consolidação adiada: faltam {len(faltam)} UF x versão ({', '.join(faltam[:12])}{'...' if len(faltam) > 12 else ''})")
        return False
    log("=== consolidação ===")
    a_in = ACUM_ENTRADA
    if not a_in.exists():
        raise FileNotFoundError(f"Não encontrei {a_in}. Rode a classe 8 (3_camada1_vs_governanca.py MANGUEZAL) antes.")
    acum = pd.read_csv(a_in)
    P = list(versoes)
    for classe in car.CLASSES:
        pref = ROTULO_PREFIXO[classe]
        pasta = car.PASTAS[classe]
        pasta.mkdir(parents=True, exist_ok=True)
        out = pasta / car.ARQUIVOS[classe]
        # --- GeoPackage: uma camada por versão, com as UFs em sequência ---
        primeira = True
        for p in P:
            n_esp = 0
            for uf in ufs:
                f = _pasta_uf(classe) / f"P1_{classe}_{p}_{uf}.gpkg"
                if not f.exists():
                    continue
                g = pyogrio.read_dataframe(str(f), layer=f"P1_{classe}_{p}")
                n_esp += len(g)
                io.gravar_camada(g, out, f"P1_{classe}_{p}", primeira=primeira)
                primeira = False
                del g
            n_out = pyogrio.read_info(str(out), layer=f"P1_{classe}_{p}")["features"] if out.exists() and n_esp else 0
            log(f"{classe} {p}: {n_out:,} partes gravadas em {out.name}" + ("" if n_out == n_esp else f"  ATENÇÃO: esperado {n_esp:,}"))
        if not manter_por_uf and _pasta_uf(classe).exists():
            for f in _pasta_uf(classe).glob("P1_*.gpkg"):
                f.unlink()
            try:
                _pasta_uf(classe).rmdir()
            except OSError:
                pass
        # --- tabelas ---
        def _junta(nome):
            partes = [pd.read_csv(f) for p in P for uf in ufs if (f := POR_UF / f"{nome}_{p}_{uf}.csv").exists()]
            return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

        res = _junta("resumo")
        res = res[res["classe"] == classe]
        res_ub = _junta("resumo_uf_bioma")
        res_ub = res_ub[res_ub["classe"] == classe]
        conf = _junta("conferencias")
        conf = conf[conf["classe"] == classe]
        num = [c for c in res.columns if c.endswith("_ha") or c in ("n_pecas", "n_imoveis")]
        res.drop(columns="classe").to_csv(pasta / f"{pref}_resumo_uf.csv", index=False, encoding="utf-8-sig")
        tot = res.groupby(["versao", "categoria"], as_index=False)[num].sum()
        geral = res.groupby("versao", as_index=False)[num].sum().assign(categoria="TOTAL")
        pd.concat([tot, geral], ignore_index=True).to_csv(pasta / f"{pref}_resumo.csv", index=False, encoding="utf-8-sig")
        res_ub.drop(columns="classe").to_csv(pasta / f"{pref}_resumo_uf_bioma.csv", index=False, encoding="utf-8-sig")
        conf.to_csv(pasta / f"{pref}_conferencias.csv", index=False, encoding="utf-8-sig")
        if len(conf) and not conf["ok"].all():
            log(f"ATENÇÃO: {int((~conf['ok']).sum())} conferência(s) fora do limite em {classe} (ver {pref}_conferencias.csv).")
        # --- acumulado ---
        novas = []
        for p in P:
            n = (res_ub[res_ub["versao"] == p].groupby(["categoria", "uf", "bioma"], as_index=False)["area_liquida_ha"].sum()
                 .rename(columns={"area_liquida_ha": f"area_liquida_{p}_ha"}))
            n[f"vs_liquida_{p}_ha"] = n[f"area_liquida_{p}_ha"]
            novas.append(n.set_index(["categoria", "uf", "bioma"]))
        nova = pd.concat(novas, axis=1).fillna(0.0).reset_index()
        nova.insert(0, "classe", car.ROTULOS[classe])
        for c in acum.columns:
            if c not in nova.columns:
                nova[c] = 0.0
        acum = pd.concat([acum, nova[acum.columns]], ignore_index=True)
        acum.to_csv(pasta / ACUM_SAIDA[classe], index=False, encoding="utf-8-sig")
        somas = acum.groupby("classe")[[c for c in acum.columns if c.endswith("_ha")]].sum()
        log(f"\n{classe}: acumulado (área líquida, sem dupla contagem entre classes):\n" + somas.round(1).to_string()
            + "".join(f"\n  total {p} {somas[f'area_liquida_{p}_ha'].sum():,.1f} ha" for p in P))
        log("\n" + pd.read_csv(pasta / f"{pref}_resumo.csv").round(1).to_string(index=False))
    return True


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ufs, versoes, conferencia, refazer, so_consolidar, manter = [], list(cfg.VS_VERSOES), "auto", False, False, False
    for a in argv:
        if a.startswith("--versao="):
            versoes = [a.split("=", 1)[1]]
        elif a.startswith("--conferencia="):
            conferencia = a.split("=", 1)[1]
        elif a == "--refazer":
            refazer = True
        elif a == "--consolidar":
            so_consolidar = True
        elif a == "--manter-por-uf":
            manter = True
        elif a.upper() in cfg.UFS:
            ufs.append(a.upper())
        else:
            print(f"argumento desconhecido: {a}")
            return 2
    for p in versoes:
        if p not in cfg.VS_VERSOES:
            print(f"versão '{p}' desconhecida (use {', '.join(cfg.VS_VERSOES)})")
            return 2
    if conferencia not in ("auto", "leve", "completa"):
        print("--conferencia deve ser auto, leve ou completa")
        return 2
    cfg.SAIDA_TIER9.mkdir(parents=True, exist_ok=True)
    arq_log = cfg.SAIDA_TIER9 / "_log_passo3b_car.txt"

    def log(m):
        io.log(m, arq_log)

    log("Passo 3b - Camada 1 (governança) - classes APP, AUR e RL (CAR)")
    falhas = []
    if not so_consolidar:
        lim = anteriores.carregar_limites()
        cel = CelulasUFBioma(lim)
        log(f"células UF x bioma: {len(cel.geoms)}")
        for uf in (ufs or cfg.UFS):
            try:
                processar_uf(uf, versoes, cel, log, conferencia, refazer)
            except Exception:
                log(f"ERRO em {uf}:\n{traceback.format_exc()}")
                falhas.append(uf)
                gov._devolver_memoria()
    todas = list(cfg.VS_VERSOES)
    if so_consolidar and ufs:
        consolidar(todas, log, manter_por_uf=True, ufs=ufs)          # subconjunto de UFs (testes); não apaga os arquivos por UF
    elif _prontas(todas):
        consolidar(todas, log, manter_por_uf=manter)
    else:
        prontas = [f"{p}:{uf}" for p in todas for uf in cfg.UFS if _marcador(p, uf).exists()]
        log(f"UF x versão prontas: {len(prontas)} de {len(todas) * len(cfg.UFS)}; a consolidação roda quando todas estiverem prontas "
            f"(ou com --consolidar).")
    if falhas:
        log(f"UFs com erro: {', '.join(falhas)}")
        return 1
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
