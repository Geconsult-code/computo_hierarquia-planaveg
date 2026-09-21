"""UF e bioma (limites IBGE) para polígonos de projeto.

``Limites.celulas(geom)`` divide um polígono nas células UF x bioma (soma das células = polígono).
O que ficar fora dos limites vira a célula ("FORA", "FORA") ou (uf, "FORA"), para que nenhuma área
se perca silenciosamente.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.strtree import STRtree

from .geometria import area_ha, diferenca_robusta, intersecao_robusta, reparar, so_poligonos, uniao_robusta

MIN_HA = 1e-6


class Limites:
    def __init__(self, gdf_uf, campo_uf, gdf_bioma, campo_bioma):
        self.uf_nomes = gdf_uf[campo_uf].astype(str).tolist()
        self.uf_geoms, _ = reparar(gdf_uf.geometry.values)
        self.uf_tree = STRtree(self.uf_geoms)
        self.bio_nomes = gdf_bioma[campo_bioma].astype(str).tolist()
        self.bio_geoms, _ = reparar(gdf_bioma.geometry.values)
        self.bio_tree = STRtree(self.bio_geoms)

    def _partes(self, g, geoms, tree, nomes):
        x0, y0, x1, y1 = g.bounds
        e = 1e-6
        saida = []
        for k in tree.query(g, predicate="intersects"):
            recorte = shapely.clip_by_rect(geoms[k], x0 - e, y0 - e, x1 + e, y1 + e)
            if recorte is None or recorte.is_empty:
                continue
            c = so_poligonos(intersecao_robusta([g], [recorte])[0])
            if c is not None and area_ha([c])[0] > MIN_HA:
                saida.append((nomes[k], c))
        return saida

    def _resto(self, g, partes):
        if not partes:
            return g
        r = so_poligonos(diferenca_robusta([g], [uniao_robusta([p for _, p in partes])])[0])
        return r if r is not None and area_ha([r])[0] > MIN_HA else None

    def celulas(self, g):
        """Lista de (uf, bioma, geometria)."""
        cel = []
        por_uf = self._partes(g, self.uf_geoms, self.uf_tree, self.uf_nomes)
        for uf, gu in por_uf:
            por_bio = self._partes(gu, self.bio_geoms, self.bio_tree, self.bio_nomes)
            for bio, gub in por_bio:
                cel.append((uf, bio, gub))
            r = self._resto(gu, por_bio)
            if r is not None:
                cel.append((uf, "FORA", r))
        r = self._resto(g, por_uf)
        if r is not None:
            cel.append(("FORA", "FORA", r))
        return cel
