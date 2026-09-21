"""Embargos PANGIA (IBAMA) para a classe 4 (Outros projetos).

- ``harmonizar``: campos do embargo sem dados pessoais (config_computo.CAMPOS_EMBARGO_PANGIA), data e ano do embargo.
- ``ler_pedacos_cruzamento``: peças "VS x embargo" do cruzamento espacial já feito (uma peça por embargo x feição de VS),
  ligadas ao embargo pela posição (``idx_embargo`` = FID - 1) e CONFERIDAS pela chave num_tad + serie_tad + seq_tad.
- ``uniao_por_id``: a área da classe 4 de cada embargo = união das suas peças (a VS dentro do embargo).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import io_dados as io
from .geometria import area_ha, reparar, so_poligonos, uniao_robusta

COLUNAS_PECA = ["idx_embargo", "num_tad", "serie_tad", "seq_tad", "vs_id", "vs_ano", "vs_bioma", "vs_fonte"]


def _txt(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip()


def harmonizar(g, campos: dict, placeholders, sentinelas, ano_min: int, ano_max: int) -> pd.DataFrame:
    """Campos harmonizados do embargo (vazios e placeholders viram nulo) + ``data_embargo`` e ``ano_embargo``.

    ``g`` deve ter sido lido só com as colunas necessárias (as colunas pessoais nem chegam a ser carregadas).
    """
    ph = {p.lower() for p in placeholders}
    out = pd.DataFrame(index=g.index)
    for novo, origem in campos.items():
        t = _txt(g[origem])
        t = t.where(t != "", pd.NA)
        out[novo] = t.where(~t.str.lower().isin(ph), pd.NA)
    dt = pd.to_datetime(g["dat_embarg"], utc=True, errors="coerce")
    dia = dt.dt.strftime("%Y-%m-%d")
    dt = dt.where(~dia.isin(sentinelas))                       # data "nula" do sistema do IBAMA
    ano = dt.dt.year
    ano = ano.where((ano >= ano_min) & (ano <= ano_max))
    out["data_embargo"] = dt.dt.strftime("%Y-%m-%d")
    out["ano_embargo"] = ano.astype("Int64")
    return out


def ler_pedacos_cruzamento(caminho, camada, chaves: pd.DataFrame, area_min_ha: float = 1e-6):
    """Peças VS x embargo do cruzamento ``caminho`` (EPSG:4674), ligadas a ``chaves``.

    chaves : DataFrame indexado por ``fid_orig`` (FID do arquivo de embargos, a partir de 1) com as colunas
             ``id_proj``, ``num_tad``, ``serie_tad`` e ``seq_tad`` (iguais às do arquivo de embargos).
    Devolve DataFrame (id_proj, vs_id, vs_ano, vs_bioma, vs_camada, geometry). Levanta ValueError se alguma peça
    apontar para um embargo com chave diferente (arquivo de embargos trocado ou reordenado).
    """
    p = io.ler_camada(caminho, camada, colunas=COLUNAS_PECA)
    fid = p["idx_embargo"].astype("int64").to_numpy() + 1
    if not np.isin(fid, chaves.index.to_numpy()).all():
        raise ValueError(f"{caminho}: idx_embargo fora do arquivo de embargos")
    alvo = chaves.loc[fid]
    for c in ("num_tad", "serie_tad", "seq_tad"):
        a = _txt(p[c]).fillna("").to_numpy()
        b = _txt(alvo[c]).fillna("").to_numpy()
        if not (a == b).all():
            raise ValueError(f"{caminho}: a chave '{c}' das peças não confere com o embargo apontado por idx_embargo "
                             f"({int((a != b).sum())} peças). O arquivo de embargos mudou desde o cruzamento? Refaça o cruzamento.")
    geoms, _ = reparar(p.geometry.values)
    d = pd.DataFrame({"id_proj": alvo["id_proj"].to_numpy(), "vs_id": p["vs_id"].astype(str).to_numpy(),
                      "vs_ano": p["vs_ano"].astype(str).to_numpy(), "vs_bioma": p["vs_bioma"].astype(str).to_numpy(),
                      "vs_camada": (p["vs_fonte"].astype(str) + "|" + p["vs_bioma"].astype(str)).to_numpy(),
                      "geometry": list(geoms)})
    ok = np.array([x is not None and not x.is_empty for x in geoms])
    d = d[ok].reset_index(drop=True)
    a = area_ha(d["geometry"].values)
    return d[a > area_min_ha].reset_index(drop=True)


def uniao_por_id(pedacos: pd.DataFrame, ids) -> np.ndarray:
    """União das peças de cada id (None se não houver), alinhada a ``ids``."""
    ids = list(ids)
    por_id = {k: v["geometry"].values for k, v in pedacos.groupby("id_proj")} if len(pedacos) else {}
    saida = np.empty(len(ids), dtype=object)
    for n, pid in enumerate(ids):
        g = por_id.get(pid)
        saida[n] = so_poligonos(uniao_robusta(list(g))) if g is not None else None
    return saida
