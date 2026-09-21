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


# ---------------------------------------------------------------------------
# VS x polígonos de projeto a partir das camadas de VS brutas (INPE), quando não há cruzamento pronto
# ---------------------------------------------------------------------------
MIN_PEDACO_HA = 1e-6


def pedacos_em_poligonos(geoms, ids, grupos, camadas, raiz, log=None, crs_vs=4674):
    """Peças "VS x polígono": interseção de cada polígono com as feições de VS que o tocam.

    geoms, ids : polígonos (EPSG:4674) e seus identificadores (``id_proj``)
    grupos     : rótulo de agrupamento (ex.: cod_imovel); uma leitura de VS por grupo e camada, com a
                 união do grupo como máscara (a leitura usa o índice espacial do GeoPackage)
    camadas    : lista de (arquivo, camada, bioma, ano) relativa a ``raiz`` (config_computo.VS_CAMADAS[...])
    Devolve DataFrame (id_proj, vs_id, vs_ano, vs_bioma, vs_camada, geometry). A VS é lida como EPSG:``crs_vs``
    mesmo que o arquivo não declare CRS (caso da Mata Atlântica 2022).
    """
    import pandas as pd
    import pyogrio
    import shapely
    from pathlib import Path

    from .geometria import reparar

    geoms = np.array(geoms, dtype=object)
    ids = np.asarray(ids)
    grupos = np.asarray(grupos)
    ordem = {}
    for i, g in enumerate(grupos):
        ordem.setdefault(g, []).append(i)
    linhas = []
    for arq, camada, bioma, ano in camadas:
        caminho = Path(raiz) / arq
        info = pyogrio.read_info(str(caminho), layer=camada)
        tb = info.get("total_bounds")
        bx0, by0, bx1, by1 = tb if tb is not None else (np.nan,) * 4     # sem extensão registrada: não pula camadas
        n_leituras = n_pedacos = 0
        for k, (grp, idx) in enumerate(ordem.items()):
            G = geoms[idx]
            x0, y0, x1, y1 = shapely.total_bounds(G)
            if np.isfinite([bx0, by0, bx1, by1]).all() and (x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1):
                continue
            mascara = uniao_robusta(list(G))
            vs = pyogrio.read_dataframe(str(caminho), layer=camada, columns=["id", "ano"], mask=mascara)
            n_leituras += 1
            if not len(vs):
                continue
            vg, _ = reparar(vs.geometry.values)
            tree = STRtree(G)
            ii, jj = tree.query(vg, predicate="intersects")        # ii: VS, jj: polígono do grupo
            if not len(ii):
                continue
            inter = intersecao_robusta(vg[ii], G[jj])
            a = area_ha([so_poligonos(x) for x in inter])
            for q in np.where(a > MIN_PEDACO_HA)[0]:
                linhas.append((ids[idx[jj[q]]], str(vs["id"].iloc[ii[q]]), ano, bioma, camada, so_poligonos(inter[q])))
                n_pedacos += 1
        if log:
            log(f"  VS {camada}: {n_leituras} leituras, {n_pedacos} peças")
    return pd.DataFrame(linhas, columns=["id_proj", "vs_id", "vs_ano", "vs_bioma", "vs_camada", "geometry"])


def atributos_vs(pedacos, ids, area_geo, biomas):
    """Atributos de VS por polígono a partir das peças (mesmos nomes da incorporação nos projetos do IBAMA).

    Devolve DataFrame indexado como ``ids``: tem (0/1), area_ha, pct, n_pol e ha_<bioma>.
    A área é a da UNIÃO das peças do polígono (peças de camadas diferentes não se somam duas vezes).
    """
    import pandas as pd

    ids = list(ids)
    saida = {c: [0.0] * len(ids) for c in ["area_ha", "n_pol"] + [f"ha_{b.lower()}" for b in biomas]}
    por_id = {k: v for k, v in pedacos.groupby("id_proj")} if len(pedacos) else {}
    for n, pid in enumerate(ids):
        sub = por_id.get(pid)
        if sub is None:
            continue
        u = uniao_robusta(list(sub["geometry"].values))
        saida["area_ha"][n] = float(area_ha([u])[0]) if u is not None else 0.0
        saida["n_pol"][n] = sub.groupby(["vs_camada", "vs_id"]).ngroups
        for b in biomas:
            sb = sub[sub["vs_bioma"] == b]
            if len(sb):
                ub = uniao_robusta(list(sb["geometry"].values))
                saida[f"ha_{b.lower()}"][n] = float(area_ha([ub])[0]) if ub is not None else 0.0
    df = pd.DataFrame(saida, index=range(len(ids)))
    df.insert(0, "tem", (df["area_ha"] > 0).astype(int))
    df["pct"] = np.where(np.asarray(area_geo, float) > 0, df["area_ha"] / np.asarray(area_geo, float) * 100.0, 0.0)
    df["n_pol"] = df["n_pol"].astype(int)
    return df[["tem", "area_ha", "pct", "n_pol"] + [f"ha_{b.lower()}" for b in biomas]]
