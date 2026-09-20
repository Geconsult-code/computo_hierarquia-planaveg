"""Filtros de elegibilidade por fonte (esqueleto).

Traduz os campos das bases para o vocabulário do relatório (config_computo.ELEGIBILIDADE_*):
Recooperar (status_are por camada), TI (fase_ti), UC (CNUC; APA = só áreas públicas), CAR
(condições da seção 4.1.1) e SICAR-regularização (áreas a recompor APP e RL).
"""
from __future__ import annotations


def filtrar_recooperar(gdf, camada: str):
    raise NotImplementedError


def filtrar_ti(gdf):
    raise NotImplementedError


def filtrar_uc(gdf):
    raise NotImplementedError


def area_publica_apa(gdf_apa, gdf_imoveis_privados):
    raise NotImplementedError
