"""Consolida as áreas de restauração da FUNBIO (FUNBIO_Areas_Restauracao_20261023.gpkg) para a classe 4 (decisões de 23/10/2026).

1. As 5 camadas (RockRio, MataAtlantica, GEF_Terrestre, FlorestaViva, AMLD) entram inteiras: todos os polígonos, inclusive os
   projetos com término previsto depois de 2026; pela ÁREA TOTAL do polígono, sem cruzamento com a VS.
2. Geometrias em 2D (o arquivo traz Z e M), reparadas; só a parte poligonal.
3. Sobreposição entre polígonos da FUNBIO: fica o polígono MAIOR (mesma regra do ICMBio); os menores ficam com a parte de fora.
4. Atributos padronizados (os nomes de campo variam entre as camadas).
Na hierarquia, o ICMBio precede a FUNBIO dentro da classe 4 (decisão de 23/10/2026): isso é aplicado na inclusão
(incluir_funbio_classe4.py / 2_camada2_projetos.py), não aqui.
Uso: python consolidar_funbio.py <FUNBIO_Areas_Restauracao_20261023.gpkg> <saida IN_FUNBIO_2026.gpkg>
"""
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio
import shapely
from pyproj import Geod

ORIG, SAIDA = sys.argv[1], sys.argv[2]
geod = Geod(ellps="GRS80")


def ha(g):
    return 0.0 if g is None or shapely.is_empty(g) else abs(geod.geometry_area_perimeter(g)[0]) / 1e4


def poli(g):
    if g is None or shapely.is_empty(g):
        return None
    partes = [p for p in shapely.get_parts(g) if shapely.get_type_id(p) == 3]
    if not partes:
        return None
    u = shapely.union_all(partes)
    return None if shapely.is_empty(u) else u


def campo(g, *nomes):
    for n in nomes:
        for c in g.columns:
            if c.lower() == n.lower():
                return g[c]
    return pd.Series([None] * len(g), index=g.index)


partes = []
for camada, _ in pyogrio.list_layers(ORIG):
    g = pyogrio.read_dataframe(ORIG, layer=camada)
    geoms = shapely.force_2d(np.asarray(g.geometry.values, dtype=object))
    geoms = [poli(shapely.make_valid(x)) for x in geoms]
    d = pd.DataFrame({
        "camada_orig": camada.replace("FUNBIO_Areas_Restauração_", ""),
        "id_orig": campo(g, "ID", "id_1").astype(str).values,
        "programa": campo(g, "PROGRAMA").fillna("").astype(str).str.strip().values,
        "projeto": campo(g, "PROJETO").values, "subprojeto": campo(g, "SUBPROJETO").values,
        "fonte_financ": campo(g, "FONTE_FINA").values, "instrumento": campo(g, "INSTRUMENT").values,
        "edital": campo(g, "edital").values, "executor": campo(g, "EXECUTOR", "Exec").values,
        "estrategia": campo(g, "ESTRATÉGI").values, "tecnica": campo(g, "TÉCNICA").values,
        "ano_inicio": pd.to_numeric(campo(g, "ANO_INÍCI"), errors="coerce").values,
        "ano_fim": pd.to_numeric(campo(g, "ANO_FINAL", "ANO_FIM"), errors="coerce").values,
        "municipio_fonte": campo(g, "nom_mun").values, "uf_fonte": campo(g, "uf").values, "bioma_fonte": campo(g, "BIOMA").values,
        "area_attr_ha": pd.to_numeric(campo(g, "ÁREA_HA"), errors="coerce").values,
    })
    d["geometry"] = geoms
    partes.append(d)
f = pd.concat(partes, ignore_index=True)
f = f[f["geometry"].notna()].reset_index(drop=True)
f["area_orig_ha"] = [ha(x) for x in f.geometry]

# sobreposição interna: o maior fica com a área (empate: ordem do arquivo)
ordem = np.argsort(-f["area_orig_ha"].to_numpy(), kind="stable")
geoms = list(f.geometry)
aceitas, saida = [], [None] * len(f)
for i in ordem:
    g = geoms[i]
    if aceitas:
        t = shapely.STRtree(aceitas)
        idx = t.query(g, predicate="intersects")
        if len(idx):
            g = poli(shapely.difference(g, shapely.union_all([aceitas[k] for k in idx])))
    saida[i] = g
    if g is not None:
        aceitas.append(g)
f["geometry"] = saida
f["area_ha_geo"] = [ha(x) for x in f.geometry]
f["sobreposta_funbio_maior_ha"] = f["area_orig_ha"] - f["area_ha_geo"]
f["recortado_por_maior"] = (f["sobreposta_funbio_maior_ha"] > 1e-6).astype(int)
desc = f[f.geometry.isna() | (f["area_ha_geo"] < 1e-6)]
f = f[f.geometry.notna() & (f["area_ha_geo"] >= 1e-6)].reset_index(drop=True)
f.insert(0, "id_funbio", np.arange(1, len(f) + 1))
f["fonte"] = "FUNBIO_2026"
out = gpd.GeoDataFrame(f, geometry="geometry", crs="EPSG:4674")
pyogrio.write_dataframe(out, SAIDA, layer="IN_FUNBIO", promote_to_multi=True)
u = shapely.union_all(np.asarray(out.geometry.values, dtype=object))
print(f"polígonos: {len(f) + len(desc)} lidos, {len(desc)} saem inteiros (cobertos por maiores), {len(f)} no insumo")
print(f"área: {f['area_orig_ha'].sum() + desc['area_orig_ha'].sum():,.1f} ha original; sobreposição interna removida "
      f"{f['sobreposta_funbio_maior_ha'].sum() + desc['area_orig_ha'].sum():,.1f} ha; insumo {f['area_ha_geo'].sum():,.1f} ha (união {ha(u):,.1f})")
print(f.groupby("camada_orig")[["area_orig_ha", "area_ha_geo"]].sum().round(1).to_string())
