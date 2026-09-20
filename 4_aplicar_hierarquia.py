"""Passo 4 - Aplicar a hierarquia completa  (ESQUELETO - a implementar)

Objetivo: Subtrai, peça a peça, as classes precedentes (Anexo 1) das peças de VS da Camada 1 e remove as áreas de Florestas Públicas Não Destinadas.

Entradas: Camadas P2_ e P1_ do passo anterior; Florestas Públicas Não Destinadas (fonte pendente).

Saídas: Camadas COMPUTO_<CLASSE> por UF, sem sobreposição entre classes; campo 'saida' (VS legalmente protegida | projetos).

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 4 - Aplicar a hierarquia completa: esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
