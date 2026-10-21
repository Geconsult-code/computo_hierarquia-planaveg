"""Consolida os polígonos do MonitoRAD 2026 "Com indício de recuperação" (decisões de 20/10/2026).

1. MonitoRAD_ANALISE, avaliacao = 'Com indício de recuperação' (qualquer `value`).
2. Cada peça é recortada pelo polígono do próprio embargo (MonitoRAD_EMBARGOS, NUM_TAD_1 = seq_tad):
   o que fica fora do embargo não é usado.
3. Sobreposição entre embargos: fica o embargo mais antigo (dat_embarg; empate: ordem do arquivo);
   os mais novos ficam só com a parte fora dos mais antigos.
Saída: IN_MonitoRAD_2026.gpkg, camada IN_MONITORAD (sem sobreposição interna), mais um resumo.
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
    """Só a parte poligonal (descarta linhas/pontos de interseções)."""
    if g is None or shapely.is_empty(g):
        return None
    partes = [p for p in shapely.get_parts(g) if shapely.get_type_id(p) in (3, 6)]
    if not partes:
        return None
    u = shapely.union_all(partes)
    return u if not shapely.is_empty(u) else None


a = pyogrio.read_dataframe(ORIG, layer="MonitoRAD_ANALISE")
e = pyogrio.read_dataframe(ORIG, layer="MonitoRAD_EMBARGOS").reset_index(names="ordem_arquivo")
c = a[a["avaliacao"] == "Com indício de recuperação"].copy()
emb = e.set_index("NUM_TAD_1")
c = c.join(emb[["ordem_arquivo", "dat_embarg", "year", "SIGLA_UF", "municipio", "AVALIA_", "geometry"]]
           .rename(columns={"geometry": "geom_embargo"}), on="seq_tad")
assert c["geom_embargo"].notna().all()

c["area_orig_ha"] = [ha(g) for g in c.geometry]
c["geometry"] = [poli(shapely.intersection(shapely.make_valid(g), shapely.make_valid(ge)))
                 for g, ge in zip(c.geometry, c.geom_embargo)]
c["area_no_embargo_ha"] = [ha(g) for g in c.geometry]
c["fora_do_embargo_ha"] = c.area_orig_ha - c.area_no_embargo_ha
c = c[c.geometry.notna()].drop(columns="geom_embargo")

# precedência: embargo mais antigo primeiro
c = c.sort_values(["dat_embarg", "ordem_arquivo", "value"], na_position="last").reset_index(drop=True)
c["prec_ordem"] = np.arange(1, len(c) + 1)
liquidas, aceitas = [], []
arvore_geoms = []
for g in c.geometry:
    resto = g
    if arvore_geoms:
        t = shapely.STRtree(arvore_geoms)
        idx = t.query(resto, predicate="intersects")
        if len(idx):
            resto = poli(shapely.difference(resto, shapely.union_all([arvore_geoms[i] for i in idx])))
    liquidas.append(resto)
    if resto is not None:
        arvore_geoms.append(resto)
c["geometry"] = liquidas
c["area_ha"] = [ha(g) for g in c.geometry]
c["sobreposta_embargo_anterior_ha"] = c.area_no_embargo_ha - c.area_ha
removidas = c[c.geometry.isna() | (c.area_ha < 1e-6)]
c = c[c.geometry.notna() & (c.area_ha >= 1e-6)].copy()
c["id_monitorad"] = [f"MRAD-{i:05d}" for i in range(1, len(c) + 1)]
c["fonte"] = "IBAMA_MonitoRAD_2026"
cols = ["id_monitorad", "fonte", "seq_tad", "value", "avaliacao", "dat_embarg", "year", "SIGLA_UF", "municipio",
        "AVALIA_", "prec_ordem", "area_monitorad_ha", "area_orig_ha", "fora_do_embargo_ha", "area_no_embargo_ha",
        "sobreposta_embargo_anterior_ha", "area_ha", "geometry"]
c = c.rename(columns={"Area_ha": "area_monitorad_ha"})
out = gpd.GeoDataFrame(c[cols], geometry="geometry", crs=e.crs)
out["dat_embarg"] = out["dat_embarg"].astype(str)
pyogrio.write_dataframe(out, SAIDA, layer="IN_MONITORAD", promote_to_multi=True)

# conferência: sem sobreposição interna
u = shapely.union_all(np.asarray(out.geometry.values, dtype=object))
print(f"pecas Com: {len(a[a.avaliacao == 'Com indício de recuperação'])}, area {a.loc[a.avaliacao == 'Com indício de recuperação', 'Area_ha'].sum():,.1f} ha")
print(f"fora do proprio embargo (removido): {c.fora_do_embargo_ha.sum() + removidas.fora_do_embargo_ha.sum():,.1f} ha")
print(f"sobreposta a embargo mais antigo (removido): {c.sobreposta_embargo_anterior_ha.sum() + removidas.sobreposta_embargo_anterior_ha.sum():,.1f} ha")
print(f"pecas descartadas inteiras: {len(removidas)}")
print(f"final: {len(out)} pecas, {out.seq_tad.nunique()} embargos, {out.area_ha.sum():,.1f} ha; uniao {ha(u):,.1f} ha")
for t in ("634469-E", "757723-E"):
    s = c[c.seq_tad == t]
    print(t, s[["value", "area_monitorad_ha", "area_no_embargo_ha", "area_ha"]].round(2).to_dict("records"))
