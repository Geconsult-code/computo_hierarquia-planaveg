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


def tabela_celulas(geoms, liquidos, lim, vs_pedacos=None, versoes=(), log=None, cada=200):
    """Uma linha por polígono x UF x bioma: área completa, área líquida e VS (completa e líquida) por versão.

    geoms     : polígonos inteiros (None = polígono sem área: não gera linhas);  liquidos : geometria líquida de cada um
    vs_pedacos: {versão: PedacosVS};  versoes: lista de prefixos (vs22q, vs2224q). Sem versões, só as áreas
                (classe 4: a geometria já é a própria VS, por isso não há o que recalcular).
    """
    import pandas as pd

    from .vs import area_vs

    n = len(geoms)
    colunas = ["i", "uf", "bioma", "area_completa_ha", "area_liquida_ha"] + [f"{p}_{t}_ha" for p in versoes for t in ("completa", "liquida")]
    linhas = []
    for i in range(n):
        G, N = geoms[i], liquidos[i]
        if G is None:
            continue
        U = {p: vs_pedacos[p].uniao_em(G) for p in versoes}
        for uf, bio, C in lim.celulas(G):
            NC = None
            if N is not None:
                NC = so_poligonos(intersecao_robusta([N], [C])[0])
            linha = {"i": i, "uf": uf, "bioma": bio, "area_completa_ha": area_ha([C])[0],
                     "area_liquida_ha": area_ha([NC])[0] if NC is not None else 0.0}
            for p in versoes:
                linha[f"{p}_completa_ha"] = area_vs(U[p], C)
                linha[f"{p}_liquida_ha"] = area_vs(U[p], NC) if NC is not None else 0.0
            linhas.append(linha)
        if log and ((i + 1) % cada == 0 or i + 1 == n):
            log(f"  {i + 1}/{n} polígonos")
    return pd.DataFrame(linhas, columns=colunas)


def resumo_uf_bioma_por_poligono(cel, n):
    """(uf_principal, ufs, bioma_principal, biomas) por polígono, a partir de ``tabela_celulas``."""
    def _lista(sub, col):
        s = sub.groupby(col)["area_completa_ha"].sum().sort_values(ascending=False)
        s = s[s > 1e-6]
        return ";".join(s.index), (s.index[0] if len(s) else None)

    saida = {}
    for i, sub in cel.groupby("i"):
        u_lista, u_prin = _lista(sub, "uf")
        b_lista, b_prin = _lista(sub, "bioma")
        saida[i] = (u_prin, u_lista, b_prin, b_lista)
    return [saida.get(i, (None,) * 4) for i in range(n)]
