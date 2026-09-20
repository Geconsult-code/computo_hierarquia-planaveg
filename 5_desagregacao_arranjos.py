"""Passo 5 - Desagregação por arranjos  (ESQUELETO - a implementar)

Objetivo: Classifica cada área do cômputo em um único arranjo de implementação (Figura 4) e desagrega por UF, bioma e categoria fundiária.

Entradas: Camadas COMPUTO_<CLASSE>; UC, TI, assentamentos, quilombolas, CAR, limites IBGE.

Saídas: Campo 'arranjo' nas camadas COMPUTO_; tabelas de área por arranjo x UF x bioma.

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 5 - Desagregação por arranjos: esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
