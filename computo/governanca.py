"""Classes 6 a 8 (TI, UC, Manguezal): leitura das peças "VS x território", elegibilidade, precedência e área pública das APAs.

Os cruzamentos já calculados (``Cruzamento_Espacial_Vegetacao_Secundaria``) trazem uma peça por território x feição de VS
qualificada (vs_id, vs_ano, vs_bioma). A área da classe é a VS dentro do território; por isso a geometria da classe muda
com a versão da VS (vs22q, vs2224q) e cada versão tem o seu arquivo de peças.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import shapely

import config_computo as cfg
from . import io_dados as io
from .geometria import area_ha, diferenca_robusta, intersecao_robusta, reparar, so_poligonos, uniao_par_robusta, uniao_robusta
from .hierarquia import subtrair_grandes


def ler_pedacos(caminho, camada, colunas, area_min_ha=1e-6):
    """Peças (EPSG:4674, 2D, reparadas) do cruzamento. Devolve (DataFrame com coluna ``geometry`` de objetos shapely, info).

    ``area_ha_arq`` = área da peça gravada no arquivo; ``area_ha_geo`` = área geodésica recalculada. Peças vazias ou com área
    <= ``area_min_ha`` saem (contadas em ``info``)."""
    g = io.ler_camada(caminho, camada, colunas=colunas)
    geoms, inval = reparar(g.geometry.values)
    d = pd.DataFrame(g.drop(columns="geometry")).reset_index(drop=True)
    if "area_ha" in d.columns:
        d = d.rename(columns={"area_ha": "area_ha_arq"})
    d["geometry"] = list(geoms)
    d["geom_reparada"] = inval
    ok = np.array([x is not None and not x.is_empty for x in geoms])
    n0 = len(d)
    d = d[ok].reset_index(drop=True)
    d["area_ha_geo"] = area_ha(d["geometry"].values)
    n1 = len(d)
    d = d[d["area_ha_geo"] > area_min_ha].reset_index(drop=True)
    info = {"n_lidas": n0, "n_vazias": n0 - n1, "n_micro": n1 - len(d), "n_reparadas": int(inval.sum())}
    return d, info


# ---------------------------------------------------------------------------
# Elegibilidade
# ---------------------------------------------------------------------------
def elegiveis_ti(d, regras):
    """(máscara, motivo) - só as fases do relatório entram (delimitada, declarada, homologada, regularizada)."""
    m = d["fase_ti"].isin(regras["fases"]).to_numpy()
    motivo = np.where(m, "", "fase_ti '" + d["fase_ti"].astype(str) + "' fora do relatório (seção 4.1.1)")
    return m, motivo


def elegiveis_uc(d, regras):
    """(máscara, motivo) - só o limite da UC; a zona de amortecimento (limite = 'za') não é UC."""
    lim = d["limite"].astype(str).str.strip().str.lower()
    m = (lim == regras["limite"]).to_numpy()
    motivo = np.where(m, "", "limite '" + d["limite"].astype(str) + "' não é UC (zona de amortecimento)")
    return m, motivo


def eh_apa(d, regras) -> np.ndarray:
    return (d["categoria"].astype(str).str.strip() == regras["categoria_apa"]).to_numpy()


# ---------------------------------------------------------------------------
# Precedência dentro da classe (área sobreposta conta uma vez): menor rank = maior precedência; rank único por peça
# ---------------------------------------------------------------------------
def _rank(chaves: pd.DataFrame) -> np.ndarray:
    chaves = chaves.reset_index(drop=True)
    ordem = chaves.sort_values(list(chaves.columns), kind="mergesort").index.to_numpy()
    rank = np.empty(len(chaves), dtype=int)
    rank[ordem] = np.arange(len(chaves))
    return rank


def _pos(serie: pd.Series, ordem: list) -> np.ndarray:
    m = {v: i for i, v in enumerate(ordem)}
    return serie.map(m).fillna(len(ordem)).to_numpy(dtype=int)


def _num(serie: pd.Series, padrao=10**12) -> np.ndarray:
    return pd.to_numeric(serie, errors="coerce").fillna(padrao).to_numpy()


def prioridade_ti(d, regras) -> np.ndarray:
    """Fase mais avançada primeiro (regularizada > homologada > declarada > delimitada), depois o código da TI, a peça de VS."""
    return _rank(pd.DataFrame({"fase": _pos(d["fase_ti"], regras["fases"]), "cod": _num(d["terrai_cod"]),
                               "vs": _num(d["vs_id"]), "i": np.arange(len(d))}))


def prioridade_uc(d, regras) -> np.ndarray:
    """Proteção integral > uso sustentável; fora da APA > APA; federal > estadual > municipal; mais antiga; código CNUC."""
    ano = pd.to_numeric(d["cria_ano"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce").fillna(9999).to_numpy()
    return _rank(pd.DataFrame({"grupo": _pos(d["grupo"], regras["grupos"]), "apa": eh_apa(d, regras).astype(int),
                               "esfera": _pos(d["esfera"], regras["esferas"]), "ano": ano,
                               "cnuc": d["cd_cnuc"].astype(str).to_numpy(), "vs": _num(d["vs_id"]), "i": np.arange(len(d))}))


def prioridade_manguezal(d) -> np.ndarray:
    return _rank(pd.DataFrame({"id": _num(d["Id"]), "vs": _num(d["vs_id"]), "i": np.arange(len(d))}))


# ---------------------------------------------------------------------------
# APAs: área pública = APA menos os imóveis do CAR, com o SIGEF recuperando de volta os imóveis públicos [decisão 24/09/2026]
# ---------------------------------------------------------------------------
def _sem_none(geoms):
    """Troca ``None`` por um polígono vazio: elemento neutro de difference/intersection/union (``shapely`` propaga ``None``
    como valor ausente, não como geometria vazia - ver ``geometria.uniao_par_robusta``)."""
    vazio = shapely.Polygon()
    return np.array([vazio if g is None else g for g in geoms], dtype=object)


def _pos_processar(geoms):
    """``so_poligonos`` em lote, devolvendo ``None`` onde a geometria ficou vazia (padrão do módulo)."""
    return np.array([so_poligonos(g) for g in geoms], dtype=object)


def sigef_publico_uniao(log=None):
    """União nacional do SIGEF (imóveis públicos em APA, ``cfg.FONTES['sigef_publico_apa']``), ou ``None`` se não configurado."""
    if "sigef_publico_apa" not in cfg.FONTES:
        return None
    fonte = cfg.FONTES["sigef_publico_apa"]
    arq = cfg.RAIZ / fonte["arquivo"]
    sg = io.ler_camada(arq, fonte["camada"])
    partes = partes_do_car(np.array(sg.geometry.values, dtype=object))   # mesmo tratamento de partes grandes/inválidas do CAR
    uniao = uniao_robusta(list(partes)) if len(partes) else None
    if log:
        a = area_ha([uniao])[0] if uniao is not None else 0.0
        log(f"  SIGEF (imóveis públicos em APA): {len(sg):,} parcelas, {a:,.1f} ha (união nacional)")
    return uniao



def dividir_partes_grandes(partes, max_vertices=100_000, grau=0.25):
    """Parte em células de ``grau`` graus as partes com mais de ``max_vertices`` vértices (uma parte do CAR de CE tem 3 milhões).

    Reparar (make_valid) uma parte dessas leva minutos; recortada em células, cada pedaço é pequeno e barato de reparar e de comparar
    com as peças. A união das células é a parte original (o recorte é por retângulo, sem folga)."""
    partes = np.array(partes, dtype=object)
    nv = shapely.get_num_coordinates(partes)
    grandes = np.where(nv > max_vertices)[0]
    if len(grandes) == 0:
        return partes
    saida = [partes[nv <= max_vertices]]
    for i in grandes:
        g = partes[i]
        x0, y0, x1, y1 = g.bounds
        xs = np.arange(np.floor(x0 / grau) * grau, x1, grau)
        ys = np.arange(np.floor(y0 / grau) * grau, y1, grau)
        pedacos = []
        for x in xs:
            faixa = shapely.clip_by_rect(g, x, y0 - 1.0, x + grau, y1 + 1.0)
            if faixa is None or faixa.is_empty:
                continue
            for y in ys:
                c = shapely.clip_by_rect(faixa, x, y, x + grau, y + grau)
                c = so_poligonos(c)
                if c is not None and not c.is_empty:
                    pedacos.append(c)
        if pedacos:
            saida.append(shapely.get_parts(np.array(pedacos, dtype=object)))
    return np.concatenate(saida)


def partes_do_car(geoms):
    """Partes simples e válidas do CAR total de uma UF (as muito grandes são divididas em células antes de reparar)."""
    partes = shapely.get_parts(np.array(geoms, dtype=object))
    partes = dividir_partes_grandes(partes)
    invalidas = ~shapely.is_valid(partes)
    if invalidas.any():
        partes[invalidas] = shapely.make_valid(partes[invalidas])
        partes = shapely.get_parts(partes)
        partes = np.array([so_poligonos(x) for x in partes], dtype=object)
        partes = partes[[x is not None and not x.is_empty for x in partes]]
    return partes


def apa_area_publica(geoms, log=None):
    """Subtrai das peças de APA o CAR total (dissolvido por UF, ``cfg.FONTES['car_total']``), uma UF por vez, e RECUPERA como
    pública a parte do que foi retirado que cai dentro de um imóvel público do SIGEF (``cfg.FONTES['sigef_publico_apa']``,
    quando configurado): pública = (APA - CAR total) ∪ (SIGEF ∩ APA) - decisão do usuário em 24/09/2026, porque uma parcela
    registrada no CAR dentro de uma APA pode ser, na verdade, um imóvel público (o SIGEF marca especificamente essas).

    Devolve (geoms_publicas, retirada_ha): a peça pode ficar inteira, parcial ou vazia (None). ``retirada_ha`` já desconta o
    que foi recuperado pelo SIGEF - é só a parte que continua privada. A VS nela conta, se for o caso, como APP, AUR ou RL
    dos imóveis elegíveis."""
    fonte = cfg.FONTES["car_total"]
    arq = cfg.RAIZ / fonte["arquivo"]
    campo = fonte["campo_uf"]
    atual = np.array(geoms, dtype=object)
    total = np.zeros(len(atual))
    recuperado_total = np.zeros(len(atual))
    sigef_uniao = sigef_publico_uniao(log=log)
    for uf in cfg.UFS:
        car = io.ler_camada(arq, fonte["camada"], colunas=[campo], where=f"{campo} = '{uf}'")
        if len(car) == 0:
            if log:
                log(f"  CAR {uf}: sem feição no arquivo (ignorado)")
            continue
        partes = partes_do_car(np.array(car.geometry.values, dtype=object))
        vivas = np.where([g is not None for g in atual])[0]
        orig = atual[vivas]
        rest, ret = subtrair_grandes(orig, partes)
        recuperado = np.zeros(len(vivas))
        if sigef_uniao is not None and len(vivas):
            retirado = _pos_processar(diferenca_robusta(_sem_none(orig), _sem_none(rest)))            # o que o CAR tirou
            sigef_rep = np.full(len(retirado), sigef_uniao, dtype=object)
            recuperar = _pos_processar(intersecao_robusta(_sem_none(retirado), sigef_rep))            # a parte pública (SIGEF) disso
            recuperado = area_ha(recuperar)
            if recuperado.sum() > 0:
                rest = _pos_processar(uniao_par_robusta(_sem_none(rest), _sem_none(recuperar)))
        atual[vivas] = rest
        total[vivas] += ret - recuperado
        recuperado_total[vivas] += recuperado
        if log:
            msg = f"  CAR {uf}: {len(partes)} partes; {int((ret > 0).sum())} peças tocadas; {ret.sum():,.1f} ha privados retirados"
            if recuperado.sum() > 0:
                msg += f"; {recuperado.sum():,.1f} ha recuperados como públicos (SIGEF)"
            log(msg)
        del car, partes
        _devolver_memoria()
    if log and sigef_uniao is not None:
        log(f"  SIGEF: {recuperado_total.sum():,.1f} ha recuperados como públicos no total (de {(total + recuperado_total).sum():,.1f} "
            f"ha que o CAR teria retirado sem o SIGEF)")
    return atual, total


def _devolver_memoria():
    """Coleta de lixo e, no Linux, devolve ao sistema a memória liberada (as partes do CAR de uma UF grande passam de 1 GB)."""
    import gc
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass
