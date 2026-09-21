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
    raise NotImplementedError("classes 3 a 11: a implementar (peça a peça, com STRtree)")


def aplicar_hierarquia(uf: str) -> None:
    raise NotImplementedError
