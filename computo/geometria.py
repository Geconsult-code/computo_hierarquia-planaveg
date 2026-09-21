"""Utilitários geométricos (padrão robusto dos repositórios anteriores).

- ``reparar``: válida passa; senão make_valid; senão buffer(0); mantém só polígonos.
- ``so_poligonos``: extrai Polygon/MultiPolygon (evita erro mixed-dimension em GeometryCollection).
- ``area_ha`` / ``area_ha_geodesica``: pyproj.Geod(ellps="GRS80"); mesmo padrão dos outros repositórios.
- ``intersecao_robusta`` / ``diferenca_robusta``: operações em lote com plano B por par (grid_size).
- ``coordenada_absurda``: vértice finito porém fora da caixa do Brasil.
"""
from __future__ import annotations

import numpy as np
import shapely
from pyproj import Geod
from shapely.errors import GEOSException

GEOD = Geod(ellps="GRS80")
LOTE = 4000
BRASIL_BBOX = (-75.0, -35.0, -28.0, 6.0)   # lon_min, lat_min, lon_max, lat_max (folgado)


def area_ha_geodesica(geom) -> float:
    if geom is None or geom.is_empty:
        return 0.0
    try:
        return abs(GEOD.geometry_area_perimeter(geom)[0]) / 10000.0
    except Exception:
        return float("nan")


def area_ha(geoms) -> np.ndarray:
    return np.array([area_ha_geodesica(g) for g in geoms], dtype="float64")


def so_poligonos(g):
    if g is None or g.is_empty:
        return None
    t = g.geom_type
    if t in ("Polygon", "MultiPolygon"):
        return g
    if t == "GeometryCollection":
        partes = []
        for p in g.geoms:
            q = so_poligonos(p)
            if q is not None:
                partes.extend(list(q.geoms) if q.geom_type == "MultiPolygon" else [q])
        if not partes:
            return None
        return partes[0] if len(partes) == 1 else shapely.MultiPolygon(partes)
    return None


def para_multi(g):
    if g is None or g.is_empty:
        return g
    return shapely.MultiPolygon([g]) if g.geom_type == "Polygon" else g


def para_multi_lista(geoms) -> np.ndarray:
    """``para_multi`` em lote (vetor de objetos shapely)."""
    return np.array([para_multi(g) for g in geoms], dtype=object)


def reparar(geoms):
    """Devolve (geometrias reparadas 2D só-polígono, vetor booleano 'era inválida')."""
    arr = np.array(shapely.force_2d(np.array(geoms, dtype=object)), dtype=object)
    validas = np.array([g is not None and not g.is_empty for g in arr])
    invalidas = np.zeros(len(arr), dtype=bool)
    if validas.any():
        invalidas[validas] = ~shapely.is_valid(arr[validas])
    for i in np.where(invalidas)[0]:
        try:
            arr[i] = shapely.make_valid(arr[i])
        except GEOSException:
            arr[i] = arr[i].buffer(0)
    for i in np.where(validas)[0]:
        arr[i] = so_poligonos(arr[i])
    return arr, invalidas


def coordenada_absurda(geom) -> bool:
    if geom is None or geom.is_empty:
        return False
    x0, y0, x1, y1 = geom.bounds
    a, b, c, d = BRASIL_BBOX
    return bool(x0 < a or x1 > c or y0 < b or y1 > d)


def _op_um(op, a, b):
    nome = {"intersection": shapely.intersection, "difference": shapely.difference}[op]
    tentativas = (
        lambda: nome(a, b),
        lambda: nome(shapely.make_valid(a), shapely.make_valid(b)),
        lambda: nome(a, b, grid_size=1e-9),
        lambda: nome(a, b, grid_size=1e-7),
        lambda: nome(a, b, grid_size=1e-5),
    )
    for t in tentativas:
        try:
            return t()
        except GEOSException:
            continue
    return None


def _lote(op, a, b):
    a = np.asarray(a, dtype=object)
    b = np.asarray(b, dtype=object)
    out = np.empty(len(a), dtype=object)
    f = {"intersection": shapely.intersection, "difference": shapely.difference}[op]
    for i in range(0, len(a), LOTE):
        j = min(i + LOTE, len(a))
        try:
            out[i:j] = f(a[i:j], b[i:j])
        except GEOSException:
            for k in range(i, j):
                out[k] = _op_um(op, a[k], b[k])
    return out


def intersecao_robusta(a, b):
    return _lote("intersection", a, b)


def diferenca_robusta(a, b):
    return _lote("difference", a, b)


def uniao_robusta(geoms):
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]
    try:
        return shapely.union_all(geoms)
    except GEOSException:
        return shapely.union_all([shapely.make_valid(g) for g in geoms], grid_size=1e-9)
