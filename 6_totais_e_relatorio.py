"""Passo 6 - Totais e relatório  (ESQUELETO - a implementar)

Objetivo: Gera as planilhas de área e polígonos por classe, arranjo, UF e bioma, com comparação com a meta nacional (12 Mha).

Entradas: Camadas COMPUTO_ de todas as UFs.

Saídas: SAIDA/Computo_Planaveg_2026_Resumo.xlsx (abas Resumo, por UF, por bioma, por arranjo, por classe).

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 6 - Totais e relatório: esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
