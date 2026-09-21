"""Aplicação da hierarquia do Anexo 1.

Princípio: cada classe subtrai as classes de ordem menor (config_computo.precedentes). O recorte é
feito PEÇA A PEÇA com índice espacial (STRtree): para cada peça, subtrai-se apenas a união das
geometrias precedentes que a intersectam. Nunca dissolver o estado inteiro (custo proibitivo).

``liquido_por_precedencia`` resolve a sobreposição DENTRO de uma classe (ex.: as quatro categorias
do Recooperar): a área sobreposta fica com o polígono de maior precedência e o restante é contado
como líquido. Os polígonos líquidos são disjuntos e somam a área da união.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.strtree import STRtree

from .geometria import area_ha, diferenca_robusta, intersecao_robusta, so_poligonos, uniao_robusta

MIN_INTER_HA = 1e-6   # interseção menor que 0,01 m2 é tratada como toque


def liquido_por_precedencia(geoms, prioridade):
    """
    geoms      : array de polígonos válidos (EPSG:4674)
    prioridade : array numérico único por polígono (menor = maior precedência)
    Devolve (liquidos, sobreposta_ha, n_precedentes): geometrias líquidas (None se vazio), área
    retirada de cada polígono (ha) e nº de polígonos precedentes com que há sobreposição real.
    """
    geoms = np.array(geoms, dtype=object)
    prioridade = np.asarray(prioridade)
    if len(set(prioridade.tolist())) != len(prioridade):
        raise ValueError("'prioridade' deve ser única por polígono")
    n = len(geoms)
    liquidos = geoms.copy()
    n_prec = np.zeros(n, dtype=int)
    tree = STRtree(geoms)
    ii, jj = tree.query(geoms, predicate="intersects")
    m = prioridade[jj] < prioridade[ii]           # j precede i
    ii, jj = ii[m], jj[m]
    if len(ii):
        a_int = area_ha(intersecao_robusta(geoms[ii], geoms[jj]))
        real = a_int > MIN_INTER_HA
        ii, jj = ii[real], jj[real]
    ordem = np.argsort(ii, kind="stable")
    ii, jj = ii[ordem], jj[ordem]
    if len(ii):
        inicios = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
        fins = np.r_[inicios[1:], len(ii)]
        for a, b in zip(inicios, fins):
            i = ii[a]
            js = jj[a:b]
            n_prec[i] = len(js)
            u = uniao_robusta(list(geoms[js]))
            liquidos[i] = so_poligonos(diferenca_robusta([geoms[i]], [u])[0])
    a_liq = area_ha([g for g in liquidos])
    a_bruta = area_ha(geoms)
    sobreposta = np.where(a_bruta - a_liq < MIN_INTER_HA, 0.0, a_bruta - a_liq)
    vazios = a_liq < MIN_INTER_HA
    for i in np.where(vazios)[0]:
        liquidos[i] = None
    return liquidos, sobreposta, n_prec


def subtrair_precedentes(pecas, precedentes):
    """Subtrai de cada peça a união das geometrias das classes de maior prioridade (peça a peça, com STRtree).

    pecas       : array de polígonos válidos (EPSG:4674)
    precedentes : array de polígonos das classes anteriores (podem se sobrepor entre si; o líquido da classe
                  anterior, disjunto, é o que o cômputo usa)
    Devolve (restantes, retirada_ha): geometria restante (None se vazia) e área retirada de cada peça (ha).
    Nunca dissolve todos os precedentes: cada peça só vê os que a intersectam.
    """
    pecas = np.array(pecas, dtype=object)
    restantes = pecas.copy()
    retirada = np.zeros(len(pecas), dtype=float)
    prec = np.array([g for g in precedentes if g is not None and not g.is_empty], dtype=object)
    tocadas = np.array([], dtype=int)
    if len(prec) and len(pecas):
        tree = STRtree(prec)
        ii, jj = tree.query(pecas, predicate="intersects")
        ordem = np.argsort(ii, kind="stable")
        ii, jj = ii[ordem], jj[ordem]
        tocadas = np.unique(ii)      # só as peças que tocam alguma precedente têm a área recalculada
        if len(ii):
            inicios = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
            fins = np.r_[inicios[1:], len(ii)]
            for a, b in zip(inicios, fins):
                i = ii[a]
                u = uniao_robusta(list(prec[jj[a:b]]))
                restantes[i] = so_poligonos(diferenca_robusta([pecas[i]], [u])[0])
    if len(tocadas):
        a_bruta = area_ha(pecas[tocadas])
        a_rest = area_ha([g for g in restantes[tocadas]])
        retirada[tocadas] = np.where(a_bruta - a_rest < MIN_INTER_HA, 0.0, a_bruta - a_rest)
        for k in np.where(a_rest < MIN_INTER_HA)[0]:
            restantes[tocadas[k]] = None
    return restantes, retirada


def subtrair_grandes(pecas, grandes, min_vertices_preparar=200):
    """Subtrai polígonos GRANDES (ex.: o CAR dissolvido de uma UF) de peças pequenas.

    Para cada par peça x parte: se a parte CONTÉM a peça, a peça sai inteira (teste com geometria preparada, rápido);
    senão a parte é recortada pela caixa da peça (clip_by_rect) antes da diferença, para não operar com milhões de vértices.
    ``grandes`` pode ser multipolígonos; são explodidos em partes.
    Devolve (restantes, retirada_ha) como ``subtrair_precedentes``.
    """
    pecas = np.array(pecas, dtype=object)
    restantes = pecas.copy()
    retirada = np.zeros(len(pecas), dtype=float)
    gr = np.array([g for g in np.atleast_1d(np.array(grandes, dtype=object)) if g is not None and not g.is_empty], dtype=object)
    partes = shapely.get_parts(gr) if len(gr) else np.array([], dtype=object)
    vivas = np.array([g is not None and not g.is_empty for g in pecas], dtype=bool)
    if len(partes) == 0 or not vivas.any():
        return restantes, retirada
    idx = np.where(vivas)[0]
    tree = STRtree(partes)
    ii, jj = tree.query(pecas[idx], predicate="intersects")
    ii = idx[ii]
    if len(ii) == 0:
        return restantes, retirada
    tocadas = np.unique(ii)      # a área só é recalculada nas peças que tocam alguma parte (a geodésica é a etapa cara)
    ju = np.unique(jj)
    grandes_ju = partes[ju][shapely.get_num_coordinates(partes[ju]) >= min_vertices_preparar]
    if len(grandes_ju):
        shapely.prepare(grandes_ju)
    try:
        cont = shapely.contains(partes[jj], pecas[ii])
    except Exception:
        cont = np.array([_contem_seguro(partes[j], pecas[i]) for i, j in zip(ii, jj)], dtype=bool)
    dentro = np.unique(ii[cont])
    restantes[dentro] = None
    m = ~np.isin(ii, dentro)
    ii, jj = ii[m], jj[m]
    ordem = np.argsort(ii, kind="stable")
    ii, jj = ii[ordem], jj[ordem]
    if len(ii):
        inicios = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
        fins = np.r_[inicios[1:], len(ii)]
        e = 1e-6
        for a, b in zip(inicios, fins):
            i = ii[a]
            g = pecas[i]
            x0, y0, x1, y1 = g.bounds
            cortes = [shapely.clip_by_rect(partes[j], x0 - e, y0 - e, x1 + e, y1 + e) for j in jj[a:b]]
            u = uniao_robusta([c for c in cortes if c is not None and not c.is_empty])
            if u is not None:
                restantes[i] = so_poligonos(diferenca_robusta([g], [u])[0])
    a_bruta = area_ha(pecas[tocadas])
    a_rest = area_ha([g for g in restantes[tocadas]])
    retirada[tocadas] = np.where(a_bruta - a_rest < MIN_INTER_HA, 0.0, a_bruta - a_rest)
    for k in np.where(a_rest < MIN_INTER_HA)[0]:
        restantes[tocadas[k]] = None
    return restantes, retirada


def _contem_seguro(parte, peca) -> bool:
    try:
        return bool(shapely.contains(parte, peca))
    except Exception:
        return False        # conservador: a peça segue para o recorte exato (reparar uma parte gigante leva minutos)


def aplicar_hierarquia(uf: str) -> None:
    raise NotImplementedError
