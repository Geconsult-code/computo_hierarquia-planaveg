"""Leitura e gravação de dados (esqueleto).

A implementar: leitura por bbox/UF (pyogrio), resolução de CRS ausente (ex.: camadas do ICMBio),
padronização para EPSG:4674, gravação incremental por UF em GeoPackage (transação, VACUUM,
journal_mode=DELETE, < 2 GB), checkpoints JSON em config_computo.PROGRESSO.
"""
from __future__ import annotations


def ler_camada(caminho, camada=None, bbox=None):
    raise NotImplementedError


def gravar_uf(gdf, uf: str, camada: str) -> None:
    raise NotImplementedError


def concluida(uf: str, etapa: str) -> bool:
    raise NotImplementedError
