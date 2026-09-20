"""Aplicação da hierarquia do Anexo 1 (esqueleto).

Princípio: cada classe subtrai as classes de ordem menor (config_computo.precedentes). O recorte
é feito PEÇA A PEÇA com índice espacial (STRtree): para cada peça, subtrai-se apenas a união das
geometrias precedentes que a intersectam. Nunca dissolver o estado inteiro (custo proibitivo).
"""
from __future__ import annotations


def subtrair_precedentes(pecas, precedentes):
    raise NotImplementedError


def aplicar_hierarquia(uf: str) -> None:
    raise NotImplementedError
