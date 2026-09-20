"""Passo 7 - Validação  (ESQUELETO - a implementar)

Objetivo: Verifica sobreposição zero entre classes, geometrias válidas e não vazias, conservação de área e conferência geodésica x equal-area.

Entradas: Camadas COMPUTO_ e IN_/P1_/P2_ de todas as UFs.

Saídas: SAIDA/_logs/validacao_computo.json e relatório de inconsistências.

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 7 - Validação: esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
