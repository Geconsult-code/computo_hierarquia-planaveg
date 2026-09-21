"""Vegetação secundária (VS) dentro de geometrias de projeto, a partir das peças do cruzamento.

As peças (VS x projeto) podem se repetir quando projetos se sobrepõem; por isso a VS de uma
geometria é sempre a área da UNIÃO das peças que a intersectam, recortada pela própria geometria.
"""
from __future__ import annotations

import numpy as np
from shapely.strtree import STRtree

from .geometria import area_ha, intersecao_robusta, so_poligonos, uniao_robusta


class PedacosVS:
    def __init__(self, geoms):
        self.g = np.array([x for x in geoms if x is not None and not x.is_empty], dtype=object)
        self.tree = STRtree(self.g) if len(self.g) else None

    def uniao_em(self, geom):
        """União das peças que intersectam ``geom`` (None se não houver)."""
        if self.tree is None or geom is None:
            return None
        idx = self.tree.query(geom, predicate="intersects")
        return uniao_robusta(list(self.g[idx])) if len(idx) else None


def area_vs(uniao, cel) -> float:
    """Área (ha) da VS (união de peças) dentro de ``cel``."""
    if uniao is None or cel is None or cel.is_empty:
        return 0.0
    i = so_poligonos(intersecao_robusta([uniao], [cel])[0])
    return float(area_ha([i])[0]) if i is not None else 0.0
