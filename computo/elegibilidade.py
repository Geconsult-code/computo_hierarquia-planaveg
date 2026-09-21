"""Filtros de elegibilidade por fonte.

Traduz os campos das bases para o vocabulário do relatório (config_computo.ELEGIBILIDADE_*).
Implementado: Recooperar (IBAMA). TI, UC e APA: a implementar com a Camada 1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _txt(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip()


def limpar_placeholders(s: pd.Series, placeholders) -> pd.Series:
    """Vazios e valores-placeholder (ATUALIZAR, Não se aplica...) viram nulo."""
    t = _txt(s)
    t = t.where(t != "", pd.NA)
    ph = {p.lower() for p in placeholders}
    return t.where(~t.str.lower().isin(ph), pd.NA)


def filtrar_recooperar(gdf, categoria: str, regras: dict, campo_status: str, campo_etapa: str):
    """Elegibilidade de uma camada do Recooperar.

    Devolve DataFrame (mesmo índice) com ``elegivel`` (0/1) e ``motivo``.
    ``categoria``: licenciamento | reparacao | embargo | outras.
    """
    n = len(gdf)
    status = _txt(gdf[campo_status]) if campo_status in gdf else pd.Series([pd.NA] * n, index=gdf.index, dtype="string")
    etapa = _txt(gdf[campo_etapa]) if campo_etapa in gdf else pd.Series([pd.NA] * n, index=gdf.index, dtype="string")
    r = regras[categoria]
    ok = np.ones(n, dtype=bool)
    motivo = np.array(["premissa: 100% da camada"] * n, dtype=object)

    # 1) status permitido (quando a categoria restringe)
    lista = r.get("status")
    if lista is not None:
        permitido = status.isin(lista).fillna(False).to_numpy(bool)
        ok &= permitido
        motivo = np.where(permitido, f"status na lista {lista}", f"status fora da lista (status_are)")

    # 2) reparação: etapa sem projeto protocolado
    if categoria == "reparacao":
        et = etapa.str.lower().fillna("")
        fora = np.zeros(n, dtype=bool)
        for trecho in r.get("etapas_fora", []):
            fora |= et.str.contains(trecho.lower(), regex=False).to_numpy(bool)
        atualizar = (et == "atualizar").to_numpy(bool)
        regra_atu = r.get("etapa_atualizar", {})
        atu_ok = status.map(lambda v: bool(regra_atu.get(v, False))).to_numpy(bool)
        motivo = np.where(ok, "etapa igual ou posterior a 'projeto protocolado'", motivo)
        motivo = np.where(fora, "etapa sem projeto protocolado (sem projeto/indícios)", motivo)
        motivo = np.where(atualizar & atu_ok, "etapa ATUALIZAR com status Recuperada (projeto concluído)", motivo)
        motivo = np.where(atualizar & ~atu_ok, "etapa ATUALIZAR sem evidência de projeto protocolado", motivo)
        ok &= ~fora
        ok &= ~(atualizar & ~atu_ok)
    return pd.DataFrame({"elegivel": ok.astype(int), "motivo": motivo}, index=gdf.index)


def _ano(serie: pd.Series, sentinelas, ano_min: int, ano_max: int) -> pd.Series:
    d = pd.to_datetime(serie.astype("string").str[:19], format="ISO8601", errors="coerce")
    sent = d.dt.strftime("%Y-%m-%d").isin(sentinelas)
    y = d.where(~sent).dt.year.astype("Float64")
    return y.where((y >= ano_min) & (y <= ano_max))


def ano_inicio(gdf, cadeia, sentinelas, ano_min: int, ano_max: int):
    """Primeiro ano válido da cadeia [(campo, rótulo), ...]. Devolve (ano, fonte) como Series."""
    ano = pd.Series(pd.array([pd.NA] * len(gdf), dtype="Float64"), index=gdf.index)
    fonte = pd.Series(pd.array([pd.NA] * len(gdf), dtype="string"), index=gdf.index)
    for campo, rotulo in cadeia:
        if campo not in gdf:
            continue
        y = _ano(gdf[campo], sentinelas, ano_min, ano_max)
        usar = ano.isna() & y.notna()
        ano = ano.where(~usar, y)
        fonte = fonte.where(~usar, rotulo)
    return ano.astype("Int64"), fonte


def ano_de_campo(gdf, campo, sentinelas, ano_min: int, ano_max: int) -> pd.Series:
    if campo not in gdf:
        return pd.Series(pd.array([pd.NA] * len(gdf), dtype="Int64"), index=gdf.index)
    return _ano(gdf[campo], sentinelas, ano_min, ano_max).astype("Int64")


def filtrar_ti(gdf):
    raise NotImplementedError


def filtrar_uc(gdf):
    raise NotImplementedError


def area_publica_apa(gdf_apa, gdf_imoveis_privados):
    raise NotImplementedError
