"""Utilitários geométricos (esqueleto).

A implementar, reaproveitando o padrão robusto dos repositórios anteriores:
- reparar(geom): válida passa; senão make_valid em try/except; senão buffer(0); senão descarta.
- so_poligonos(geom): extrai só Polygon/MultiPolygon (evita erro mixed-dimension).
- area_ha_geodesica(geom): pyproj.Geod(ellps="GRS80"), com conferência em EPSG:6933.
- coordenada_absurda(geom): descarta vértices finitos porém fora do bbox do Brasil.
"""
from __future__ import annotations


def reparar(geom):
    raise NotImplementedError


def so_poligonos(geom):
    raise NotImplementedError


def area_ha_geodesica(geom) -> float:
    raise NotImplementedError


def coordenada_absurda(geom) -> bool:
    raise NotImplementedError
