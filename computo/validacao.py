"""Verificações de consistência (esqueleto).

A implementar: sobreposição par-a-par entre classes ~ 0; geometrias válidas e não vazias;
conservação de área (entrada = saída + removido por classe); conferência geodésica x equal-area.
"""
from __future__ import annotations


def sobreposicao_entre_classes(uf: str) -> dict:
    raise NotImplementedError


def conservacao_de_area(uf: str) -> dict:
    raise NotImplementedError
