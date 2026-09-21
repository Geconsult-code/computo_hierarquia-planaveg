"""Leitura e gravação de dados.

- ``ler_camada``: lê uma camada do GeoPackage com o CRS declarado no próprio arquivo (resolve o
  srs_id customizado 300001 do GDAL), força 2D e padroniza para EPSG:4674.
- ``gravar_camada``: grava em GeoPackage (MultiPolígono).
- ``ler_pedacos_vs``: lê as peças "VS x projeto" do cruzamento espacial.
- ``gravar_uf`` / ``concluida``: por UF, com checkpoints (a implementar nas classes grandes).
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path

import numpy as np
import pyogrio
import shapely
from pyproj import CRS

CRS_ALVO = "EPSG:4674"


def log(msg: str, arquivo=None) -> None:
    linha = f"{time.strftime('%H:%M:%S')} {msg}"
    print(linha, flush=True)
    if arquivo is not None:
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(linha + "\n")


def crs_da_camada(arquivo, camada) -> CRS:
    con = sqlite3.connect(str(arquivo))
    try:
        r = con.execute(
            "select s.definition, s.organization, s.organization_coordsys_id "
            "from gpkg_geometry_columns c join gpkg_spatial_ref_sys s on s.srs_id = c.srs_id "
            "where c.table_name = ?", (camada,)).fetchone()
    finally:
        con.close()
    if r is None:
        raise RuntimeError(f"sem CRS registrado para a camada {camada}")
    definicao, org, cod = r
    if org and org.upper() == "EPSG" and cod and cod > 0:
        return CRS.from_epsg(int(cod))
    return CRS.from_wkt(definicao)


def ler_camada(caminho, camada=None, colunas=None, com_fid=False, where=None, bbox=None):
    """GeoDataFrame em EPSG:4674, 2D. ``fid_as_index=False``: o FID original não é reaproveitado.

    ``com_fid=True`` grava o FID da camada de origem na coluna ``fid_orig`` (rastreabilidade quando o arquivo
    não traz um campo próprio, como nas camadas do SICAR). ``bbox`` = (xmin, ymin, xmax, ymax) no CRS da camada
    (as camadas gravadas por este projeto estão em EPSG:4674): lê só as feições que tocam a caixa."""
    caminho = Path(caminho)
    if camada is None:
        camada = pyogrio.list_layers(str(caminho))[0][0]
    g = pyogrio.read_dataframe(str(caminho), layer=camada, columns=colunas, fid_as_index=com_fid, where=where, bbox=bbox)
    if com_fid:
        g["fid_orig"] = g.index.astype("int64")
        g = g.reset_index(drop=True)
    g = g.set_crs(crs_da_camada(caminho, camada), allow_override=True)
    g["geometry"] = shapely.force_2d(g.geometry.values)
    return g.to_crs(CRS_ALVO)


def _norm(s: str) -> str:
    """Compara nomes ignorando qualquer caractere não alfanumérico ASCII (Reparação -> Repara__o)."""
    return re.sub(r"[^0-9A-Za-z]+", "", s).lower()


def camada_do_cruzamento(arquivo, nome_orig):
    nomes = [n for n, _ in pyogrio.list_layers(str(arquivo))]
    if nome_orig + "_vegsec" in nomes:
        return nome_orig + "_vegsec"
    alvo = _norm(nome_orig + "_vegsec")
    achadas = [n for n in nomes if _norm(n) == alvo]
    if len(achadas) > 1:
        raise RuntimeError(f"mais de uma camada de cruzamento corresponde a {nome_orig}: {achadas}")
    return achadas[0] if achadas else None


def ler_pedacos_vs(arquivo, camadas_orig):
    """Geometrias (EPSG:4674, 2D) de todas as peças VS x projeto das camadas indicadas (vetor de objetos)."""
    partes = []
    for nome in camadas_orig:
        c = camada_do_cruzamento(arquivo, nome)
        if c is None:
            raise RuntimeError(f"camada de cruzamento de '{nome}' não encontrada em {arquivo}")
        g = pyogrio.read_dataframe(str(arquivo), layer=c, columns=["vs_bioma"])
        if g.crs is None or g.crs.to_epsg() != 4674:
            g = g.to_crs(CRS_ALVO)
        partes.append(np.array(shapely.force_2d(g.geometry.values), dtype=object))
    return np.concatenate(partes) if partes else np.array([], dtype=object)


def gravar_camada(gdf, arquivo, camada, primeira=False):
    """Grava/atualiza uma camada. ``primeira=True`` recria o arquivo."""
    arquivo = Path(arquivo)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    if primeira and arquivo.exists():
        arquivo.unlink()
    pyogrio.write_dataframe(gdf, str(arquivo), layer=camada, driver="GPKG", promote_to_multi=True,
                            append=arquivo.exists())


def gravar_uf(gdf, uf: str, camada: str) -> None:
    raise NotImplementedError("gravação por UF será implementada com as classes grandes (SICAR, TI, UC...)")


def concluida(uf: str, etapa: str) -> bool:
    raise NotImplementedError
