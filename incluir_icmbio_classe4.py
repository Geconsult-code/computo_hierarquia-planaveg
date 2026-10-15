"""Inclusão incremental dos projetos do ICMBio na classe 4 (Outros projetos), sem refazer o cômputo.

Por que é exato: cada classe k > 4 já é a sua fonte menos as classes 1..k-1. Sendo Δ a parte do ICMBio que
ainda não está nas classes 1, 3 e 4, a nova classe k é a classe k atual menos Δ - o mesmo resultado de
recalcular tudo. As classes 1 e 3 não mudam.

Entrada (em config_computo.SAIDA_INSUMOS):
    IN_ICMBio_2026.gpkg, camada IN_ICMBIO - 3.655 polígonos sem sobreposição interna (decisões de 14/10/2026):
      - GEF Terrestre (7 camadas): em cada grupo de polígonos sobrepostos fica o maior; nas cópias, o da camada _ORR;
      - Restauração Ecológica (só essa camada do ICMBio_Projetos_Restauracao_2026): mesma regra;
      - entre os dois arquivos fica o GEF (a Restauração Ecológica é recortada por ele).
    Área TOTAL dos polígonos (sem cruzamento com VS): a mesma geometria nas duas versões da VS.

O que o script faz, para cada versão da VS (vs22q, vs2224q):
    1. Δ = cada polígono do ICMBio menos as classes 1 (P2_RECOOPERAR), 3 (P2_CAR_REGULARIZACAO) e 4
       (P2_OUTROS_PROJETOS_<versão>, os embargos PANGIA): o ICMBio só entra no que ainda está livre.
    2. Classe 4: acrescenta Δ à camada P2_OUTROS_PROJETOS_<versão> (id_proj "ICMBIO-nnnnn", UF e bioma
       principais, area_liquida_ha) e grava a camada P2_OUTROS_PROJETOS_ICMBIO_poligonos (polígonos inteiros
       com a área líquida por versão), no mesmo GeoPackage da classe 4.
    3. Classes 5 a 11: subtrai Δ, no próprio arquivo, das camadas que as classes seguintes e o reporte final leem:
       P2_OR_<v>, P1_TI_<v>, P1_UC_<v>, P1_MANGUEZAL_<v>, P1_APP/AUR/RL_<v> (nacionais) e os
       _por_uf\\P1_APP/AUR/RL_<v>_<UF>.gpkg. Só as feições que tocam Δ são alteradas (área recalculada em
       area_ha); as que ficam vazias são apagadas.
    4. Conferência independente: depois de gravar, relê as feições que tocam Δ e confirma que a interseção
       restante é zero; a área tirada de cada camada é comparada com a área de interseção medida antes.

Saídas (em config_computo.SAIDA_TIER4):
    ICMBio_incremental_resumo.csv       por versão x camada: feições alteradas/apagadas, área antes, removida, depois
    ICMBio_incremental_alteracoes.csv   uma linha por feição alterada (arquivo, camada, fid, área antes/depois, uf, bioma)
    ICMBio_incremental_delta.gpkg       Δ por versão (camadas delta_vs22q, delta_vs2224q) - o que foi subtraído
    ICMBio_incremental_estado.json      etapas concluídas (rodar de novo retoma; nada é subtraído duas vezes)
    _log_icmbio_incremental.txt

Os resumos T5..T11_*.csv dos passos 2, 3 e 3b NÃO são refeitos: os totais atualizados ficam no resumo acima e no
reporte final, que deve ser gerado depois (python gerar_geopackages_finais.py, todas as classes exceto 1 e 3).

Uso (env geo; PLANAVEG_RAIZ aponta para a cópia de trabalho - nunca para o backup):
    set PLANAVEG_RAIZ=D:\\PLANAVEG_TEMP
    python incluir_icmbio_classe4.py                 # simulação: calcula Δ e as áreas a tirar, não grava nada
    python incluir_icmbio_classe4.py --executar      # grava
Opções: --versoes vs22q vs2224q   --classes OR TI UC MANGUEZAL APP AUR RL   (padrão: todas)
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import struct
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import shapely
from shapely.strtree import STRtree

import config_computo as cfg
from computo import anteriores
from computo import geometria as geo
from computo import io_dados as io


ARQ_IN = cfg.SAIDA_INSUMOS / "IN_ICMBio_2026.gpkg"
CAMADA_IN = "IN_ICMBIO"
VERSOES = ["vs22q", "vs2224q"]
CLASSES = ["OR", "TI", "UC", "MANGUEZAL", "APP", "AUR", "RL"]
CAR = {"APP": cfg.SAIDA_TIER9, "AUR": cfg.SAIDA_TIER10, "RL": cfg.SAIDA_TIER11}
MIN_HA = 1e-6            # abaixo disso a feição é considerada vazia (0,01 m²)
TOL_CONFERENCIA_HA = 1e-3
ARQ_T4 = cfg.SAIDA_TIER4 / anteriores.ARQ_OUT_EMB
ARQ_LOG = cfg.SAIDA_TIER4 / "_log_icmbio_incremental.txt"
ARQ_ESTADO = cfg.SAIDA_TIER4 / "ICMBio_incremental_estado.json"
ARQ_RESUMO = cfg.SAIDA_TIER4 / "ICMBio_incremental_resumo.csv"
ARQ_ALTER = cfg.SAIDA_TIER4 / "ICMBio_incremental_alteracoes.csv"
ARQ_DELTA = cfg.SAIDA_TIER4 / "ICMBio_incremental_delta.gpkg"


def log(msg):
    io.log(msg, ARQ_LOG)


# ----------------------------------------------------------------------------------------------------------------
# estado (retomada)
# ----------------------------------------------------------------------------------------------------------------
def ler_estado():
    if ARQ_ESTADO.exists():
        return json.loads(ARQ_ESTADO.read_text(encoding="utf-8"))
    return {}


def marcar(estado, chave):
    estado[chave] = time.strftime("%Y-%m-%d %H:%M:%S")
    ARQ_ESTADO.write_text(json.dumps(estado, indent=1, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------------
# 1. Δ por versão
# ----------------------------------------------------------------------------------------------------------------
def calcular_delta(icm, versao):
    """Para cada polígono do ICMBio: a parte fora das classes 1, 3 e 4 (versão). Devolve GeoDataFrame do Δ."""
    arqs = anteriores.arquivos_classes(versao)
    xmin, ymin, xmax, ymax = icm.total_bounds
    prev, sobre = [], {}
    for c in ("RECOOPERAR", "SICAR_REGULARIZACAO", "OUTROS_PROJETOS"):
        arq, camada = arqs[c]
        g = io.ler_camada(arq, camada, colunas=["id_proj"], bbox=(xmin, ymin, xmax, ymax))
        if c == "OUTROS_PROJETOS":   # rodada anterior deste script: o próprio ICMBio não conta como ocupado
            g = g[~g["id_proj"].astype(str).str.startswith("ICMBIO-")]
        geoms = np.array(g.geometry.values, dtype=object)
        prev.append((c, geoms))
    todas = np.concatenate([gs for _, gs in prev]) if prev else np.array([], dtype=object)
    rotulo = np.concatenate([[c] * len(gs) for c, gs in prev]) if prev else np.array([])
    tree = STRtree(todas)
    liq = np.empty(len(icm), dtype=object)
    por_classe = {c: np.zeros(len(icm)) for c, _ in prev}
    for i, g in enumerate(icm.geometry.values):
        idx = tree.query(g, predicate="intersects")
        if len(idx) == 0:
            liq[i] = g
            continue
        for c in por_classe:
            sel = [todas[k] for k in idx if rotulo[k] == c]
            if sel:
                u = geo.uniao_robusta(sel)
                por_classe[c][i] = geo.area_ha_geodesica(geo.so_poligonos(geo.intersecao_robusta([g], [u])[0]))
        u = geo.uniao_robusta([todas[k] for k in idx])
        liq[i] = geo.so_poligonos(geo.diferenca_robusta([g], [u])[0])
    area = geo.area_ha(liq)
    area = np.nan_to_num(area, nan=0.0)
    d = icm.drop(columns="geometry").copy()
    d["area_liquida_ha"] = area
    for c, v in por_classe.items():
        d[f"sobreposta_{c.lower()}_ha"] = v
    d = d.assign(geometry=geo.para_multi_lista(liq))
    d = d[(d["area_liquida_ha"] > MIN_HA) & d.geometry.notna()]
    return d.set_geometry("geometry").set_crs("EPSG:4674")


def uf_bioma_principal(geoms, lim):
    ufs, bios = [], []
    for g in geoms:
        cel = lim.celulas(g)
        if not cel:
            ufs.append("FORA"); bios.append("FORA"); continue
        a = geo.area_ha([c[2] for c in cel])
        k = int(np.argmax(a))
        ufs.append(cel[k][0]); bios.append(cel[k][1])
    return ufs, bios


# ----------------------------------------------------------------------------------------------------------------
# 2. classe 4
# ----------------------------------------------------------------------------------------------------------------
def gravar_classe4(delta, versao, lim, executar):
    camada = f"P2_OUTROS_PROJETOS_{versao}"
    ja = pyogrio.read_dataframe(str(ARQ_T4), layer=camada, columns=["id_proj"], read_geometry=False,
                                where="id_proj LIKE 'ICMBIO-%'")
    if len(ja):
        log(f"  classe 4 {versao}: {len(ja)} feições ICMBio já gravadas em {camada} - não acrescento de novo")
        return 0.0
    ufs, bios = uf_bioma_principal(delta.geometry.values, lim)
    novo = pd.DataFrame({
        "id_proj": [f"ICMBIO-{int(i):05d}" for i in delta["id_icmbio"]],
        "num_tad": None, "serie_tad": None, "data_embargo": None,
        "uf_principal": ufs, "bioma_principal": bios,
        "area_liquida_ha": delta["area_liquida_ha"].values,
    })
    novo = novo.astype({"num_tad": "object", "serie_tad": "object", "data_embargo": "object"})
    import geopandas as gpd
    novo = gpd.GeoDataFrame(novo, geometry=delta.geometry.values, crs="EPSG:4674")
    log(f"  classe 4 {versao}: + {len(novo)} feições ICMBio, {novo['area_liquida_ha'].sum():,.2f} ha")
    if executar:
        pyogrio.write_dataframe(novo, str(ARQ_T4), layer=camada, driver="GPKG", append=True, promote_to_multi=True)
    return float(novo["area_liquida_ha"].sum())


def gravar_poligonos_icmbio(icm, deltas, executar):
    import geopandas as gpd
    t = icm.drop(columns="geometry").copy()
    for v, d in deltas.items():
        m = d.set_index("id_icmbio")
        t[f"{v}_area_liquida_ha"] = t["id_icmbio"].map(m["area_liquida_ha"]).fillna(0.0)
        for c in ("recooperar", "sicar_regularizacao", "outros_projetos"):
            t[f"{v}_sobreposta_{c}_ha"] = t["id_icmbio"].map(m[f"sobreposta_{c}_ha"]).fillna(0.0)
    t = gpd.GeoDataFrame(t, geometry=icm.geometry.values, crs="EPSG:4674")
    if executar:
        pyogrio.write_dataframe(t, str(ARQ_T4), layer="P2_OUTROS_PROJETOS_ICMBIO_poligonos", driver="GPKG",
                                promote_to_multi=True, layer_options={"OVERWRITE": "YES"})


# ----------------------------------------------------------------------------------------------------------------
# 3. classes 5 a 11: subtração no próprio arquivo
# ----------------------------------------------------------------------------------------------------------------
def alvos(versao, classes):
    """[(rótulo, arquivo, camada)] das camadas a alterar."""
    arqs = anteriores.arquivos_classes(versao)
    saida = []
    for c in classes:
        arq, camada = arqs[c]
        saida.append((c, arq, camada))
        if c in CAR:
            for uf in cfg.UFS:
                f = CAR[c] / "_por_uf" / f"P1_{c}_{versao}_{uf}.gpkg"
                if f.exists():
                    saida.append((f"{c}_{uf}", f, camada))
    return saida


# GeoPackage aberto direto pelo SQLite (sem depender das bindings osgeo/GDAL do Python). As funções ST_* que os
# gatilhos do índice espacial (rtree_*) usam são registradas aqui, lendo o envelope do cabeçalho da geometria.
def _cabecalho(blob):
    """(tamanho do cabeçalho GPKG, envelope (minx, maxx, miny, maxy) ou None, vazio?)"""
    flags = blob[3]
    vazio = bool(flags & 0b10000)
    tipo_env = (flags >> 1) & 0b111
    n = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}[tipo_env]
    fmt = "<" if flags & 1 else ">"
    env = struct.unpack(fmt + "d" * n, blob[8:8 + 8 * n]) if n else None
    return 8 + 8 * n, (env[:4] if env else None), vazio


def ler_geom(blob):
    if blob is None:
        return None
    h, _, vazio = _cabecalho(blob)
    if vazio:
        return None
    return shapely.force_2d(shapely.from_wkb(bytes(blob[h:])))


def gravar_geom(g, srs_id):
    x0, y0, x1, y1 = g.bounds
    return b"GP" + bytes([0, 0b00000011]) + struct.pack("<i", srs_id) + struct.pack("<dddd", x0, x1, y0, y1) \
        + shapely.to_wkb(g, byte_order=1, output_dimension=2)


def _env(blob, k):
    if blob is None:
        return None
    _, env, vazio = _cabecalho(blob)
    if vazio:
        return None
    if env is None:
        g = ler_geom(blob)
        x0, y0, x1, y1 = g.bounds
        env = (x0, x1, y0, y1)
    return env[k]


def abrir_gpkg(arq, escrita):
    con = sqlite3.connect(str(arq)) if escrita else sqlite3.connect(Path(arq).resolve().as_uri() + "?mode=ro", uri=True)
    con.create_function("ST_MinX", 1, lambda b: _env(b, 0), deterministic=True)
    con.create_function("ST_MaxX", 1, lambda b: _env(b, 1), deterministic=True)
    con.create_function("ST_MinY", 1, lambda b: _env(b, 2), deterministic=True)
    con.create_function("ST_MaxY", 1, lambda b: _env(b, 3), deterministic=True)
    con.create_function("ST_IsEmpty", 1, lambda b: 1 if b is None or _cabecalho(b)[2] else 0, deterministic=True)
    return con


def _info_camada(con, camada):
    col, srs = con.execute("SELECT column_name, srs_id FROM gpkg_geometry_columns WHERE table_name = ?", (camada,)).fetchone()
    campos = {r[1] for r in con.execute(f'PRAGMA table_info("{camada}")')}
    pk = next(r[1] for r in con.execute(f'PRAGMA table_info("{camada}")') if r[5] == 1)
    return col, srs, campos, pk


def _fids_que_tocam(con, camada, col, delta_geoms):
    rt = f"rtree_{camada}_{col}"
    fids = set()
    for g in delta_geoms:
        x0, y0, x1, y1 = g.bounds
        fids.update(r[0] for r in con.execute(
            f'SELECT id FROM "{rt}" WHERE maxx >= ? AND minx <= ? AND maxy >= ? AND miny <= ?', (x0, x1, y0, y1)))
    return fids


def subtrair_camada(arq, camada, delta_geoms, delta_tree, executar, alteracoes, rotulo, versao):
    """Subtrai Δ das feições de ``camada`` que o tocam. Devolve dict com contagens e áreas."""
    con = abrir_gpkg(arq, executar)
    col, srs, campos, pk = _info_camada(con, camada)
    campo_area = "area_ha" if "area_ha" in campos else ("area_liquida_ha" if "area_liquida_ha" in campos else None)
    fids = _fids_que_tocam(con, camada, col, delta_geoms)
    r = dict(versao=versao, rotulo=rotulo, arquivo=str(arq), camada=camada, candidatas=len(fids),
             alteradas=0, apagadas=0, area_antes_ha=0.0, area_removida_ha=0.0, area_depois_ha=0.0,
             intersecao_medida_ha=0.0)
    if not fids:
        con.close()
        return r
    extra = [c for c in ("uf", "bioma") if c in campos]
    sel = ", ".join([f'"{pk}"', f'"{col}"'] + [f'"{c}"' for c in extra])
    lista = sorted(fids)
    for i in range(0, len(lista), 500):
        bloco = lista[i:i + 500]
        linhas = con.execute(f'SELECT {sel} FROM "{camada}" WHERE "{pk}" IN ({",".join("?" * len(bloco))})', bloco).fetchall()
        for row in linhas:
            fid, blob = row[0], row[1]
            info = dict(zip(extra, row[2:]))
            g = ler_geom(blob)
            if g is None:
                continue
            idx = delta_tree.query(g, predicate="intersects")
            if len(idx) == 0:
                continue
            u = geo.uniao_robusta([delta_geoms[k] for k in idx])
            inter = geo.so_poligonos(geo.intersecao_robusta([g], [u])[0])
            a_int = geo.area_ha_geodesica(inter) if inter is not None else 0.0
            if not a_int or a_int <= MIN_HA:
                continue
            a0 = geo.area_ha_geodesica(g)
            novo = geo.so_poligonos(geo.diferenca_robusta([g], [u])[0])
            a1 = geo.area_ha_geodesica(novo) if novo is not None else 0.0
            r["intersecao_medida_ha"] += a_int
            r["area_antes_ha"] += a0
            r["area_depois_ha"] += a1
            r["area_removida_ha"] += a0 - a1
            alteracoes.append(dict(versao=versao, rotulo=rotulo, arquivo=Path(arq).name, camada=camada, fid=fid,
                                   area_antes_ha=round(a0, 6), area_depois_ha=round(a1, 6),
                                   uf=info.get("uf"), bioma=info.get("bioma"),
                                   acao="apagada" if a1 <= MIN_HA else "recortada"))
            if a1 <= MIN_HA:
                r["apagadas"] += 1
                if executar:
                    con.execute(f'DELETE FROM "{camada}" WHERE "{pk}" = ?', (fid,))
            else:
                r["alteradas"] += 1
                if executar:
                    b = gravar_geom(geo.para_multi(novo), srs)
                    if campo_area:
                        con.execute(f'UPDATE "{camada}" SET "{col}" = ?, "{campo_area}" = ? WHERE "{pk}" = ?', (b, a1, fid))
                    else:
                        con.execute(f'UPDATE "{camada}" SET "{col}" = ? WHERE "{pk}" = ?', (b, fid))
    if executar:
        con.commit()
    con.close()
    return r


def conferir_camada(arq, camada, delta_geoms, delta_tree):
    """Área ainda sobreposta a Δ depois da gravação (deve ser ~0). Usa o índice espacial do arquivo, o que confere
    também que os gatilhos o mantiveram atualizado."""
    con = abrir_gpkg(arq, False)
    col, srs, campos, pk = _info_camada(con, camada)
    fids = sorted(_fids_que_tocam(con, camada, col, delta_geoms))
    total = 0.0
    for i in range(0, len(fids), 500):
        bloco = fids[i:i + 500]
        for (blob,) in con.execute(f'SELECT "{col}" FROM "{camada}" WHERE "{pk}" IN ({",".join("?" * len(bloco))})', bloco):
            g = ler_geom(blob)
            if g is None:
                continue
            idx = delta_tree.query(g, predicate="intersects")
            if len(idx):
                inter = geo.so_poligonos(geo.intersecao_robusta(
                    [g], [geo.uniao_robusta([delta_geoms[k] for k in idx])])[0])
                total += geo.area_ha_geodesica(inter) if inter is not None else 0.0
    con.close()
    return total


# ----------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inclui o ICMBio na classe 4 e subtrai das classes 5 a 11")
    ap.add_argument("--executar", action="store_true")
    ap.add_argument("--versoes", nargs="+", choices=VERSOES, default=VERSOES)
    ap.add_argument("--classes", nargs="+", choices=CLASSES, default=CLASSES)
    a = ap.parse_args(argv)
    if not ARQ_IN.exists():
        print(f"Entrada não encontrada: {ARQ_IN}", file=sys.stderr)
        return 1
    log(f"=== incluir_icmbio_classe4 ({'EXECUÇÃO' if a.executar else 'SIMULAÇÃO'}) | RAIZ = {cfg.RAIZ}")
    icm = io.ler_camada(ARQ_IN, CAMADA_IN)
    icm["geometry"], _ = geo.reparar(icm.geometry.values)
    log(f"ICMBio: {len(icm)} polígonos, {geo.area_ha(icm.geometry.values).sum():,.2f} ha")
    lim = anteriores.carregar_limites()
    estado = ler_estado() if a.executar else {}
    resumo, alteracoes, deltas = [], [], {}
    t0 = time.time()
    for v in a.versoes:
        log(f"--- versão {v}")
        d = calcular_delta(icm, v)
        deltas[v] = d
        log(f"  Δ {v}: {len(d)} polígonos, {d['area_liquida_ha'].sum():,.2f} ha "
            f"(já ocupado pelas classes 1, 3 e 4: {geo.area_ha(icm.geometry.values).sum() - d['area_liquida_ha'].sum():,.2f} ha)")
        if a.executar:
            pyogrio.write_dataframe(d, str(ARQ_DELTA), layer=f"delta_{v}", driver="GPKG", promote_to_multi=True,
                                    append=False)
        chave4 = f"{v}|classe4"
        if chave4 in estado:
            log(f"  classe 4 {v}: já feita em {estado[chave4]}")
        else:
            a4 = gravar_classe4(d, v, lim, a.executar)
            resumo.append(dict(versao=v, rotulo="OUTROS_PROJETOS", arquivo=str(ARQ_T4), camada=f"P2_OUTROS_PROJETOS_{v}",
                               candidatas=len(d), alteradas=len(d), apagadas=0, area_antes_ha=0.0,
                               area_removida_ha=-a4, area_depois_ha=a4, intersecao_medida_ha=0.0, residual_ha=0.0))
            if a.executar:
                marcar(estado, chave4)
        dg = np.array(geo.para_multi_lista(d.geometry.values), dtype=object)
        tree = STRtree(dg)
        for rotulo, arq, camada in alvos(v, a.classes):
            chave = f"{v}|{rotulo}"
            if chave in estado:
                log(f"  {rotulo:10s} {v}: já feito em {estado[chave]}")
                continue
            if not Path(arq).exists():
                log(f"  {rotulo:10s} {v}: arquivo não encontrado ({arq}) - pulei")
                continue
            t1 = time.time()
            r = subtrair_camada(arq, camada, dg, tree, a.executar, alteracoes, rotulo, v)
            r["residual_ha"] = conferir_camada(arq, camada, dg, tree) if a.executar else float("nan")
            resumo.append(r)
            ok = "" if not a.executar else ("  conferência OK" if r["residual_ha"] < TOL_CONFERENCIA_HA
                                            else f"  ATENÇÃO: ainda sobrepõe {r['residual_ha']:.4f} ha")
            log(f"  {rotulo:10s} {v}: {r['alteradas']} recortadas, {r['apagadas']} apagadas, "
                f"-{r['area_removida_ha']:,.2f} ha (interseção medida {r['intersecao_medida_ha']:,.2f}) "
                f"[{time.time() - t1:.0f}s]{ok}")
            if a.executar:
                marcar(estado, chave)
    gravar_poligonos_icmbio(icm, deltas, a.executar)
    def gravar_csv(linhas, arq, chave):
        # numa retomada, junta com o que as rodadas anteriores já gravaram (a mais recente vale)
        df = pd.DataFrame(linhas)
        if a.executar and arq.exists():
            antigo = pd.read_csv(arq, sep=";", decimal=",", encoding="utf-8-sig")
            df = pd.concat([antigo, df], ignore_index=True).drop_duplicates(subset=chave, keep="last")
        destino = arq if a.executar else arq.with_name(arq.stem + "_SIMULACAO.csv")
        df.to_csv(destino, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    if resumo:
        gravar_csv(resumo, ARQ_RESUMO, ["versao", "rotulo"])
    if alteracoes:
        gravar_csv(alteracoes, ARQ_ALTER, ["versao", "rotulo", "fid"])
    # balanço: o que entra na classe 4 tem de ser >= o que sai das demais (a diferença é área nova no cômputo)
    for v in a.versoes:
        rs = [r for r in resumo if r["versao"] == v]
        entra = sum(r["area_depois_ha"] for r in rs if r["rotulo"] == "OUTROS_PROJETOS")
        sai = sum(r["area_removida_ha"] for r in rs if r["rotulo"] in a.classes)   # só as nacionais (por UF é cópia)
        log(f"BALANÇO {v}: classe 4 +{entra:,.2f} ha; classes 5-11 -{sai:,.2f} ha; total do cômputo +{entra - sai:,.2f} ha")
    log(f"fim ({(time.time() - t0) / 60:.1f} min). " + ("" if a.executar else "SIMULAÇÃO: nada foi gravado."))
    if a.executar:
        log("Próximo passo: python gerar_geopackages_finais.py OUTROS_PROJETOS OR TI UC MANGUEZAL APP AUR RL "
            "e depois --so-total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
