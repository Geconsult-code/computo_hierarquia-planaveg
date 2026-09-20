"""Passo 2 - Camada 2 (projetos)  (ESQUELETO - a implementar)

Objetivo: Aplica a hierarquia entre projetos: Recooperar > SICAR-regularização > Outros projetos > OR (MonitoRAD desativado). Conta a área inteira do projeto.

Entradas: Camadas IN_ das classes RECOOPERAR, SICAR_REGULARIZACAO, OUTROS_PROJETOS e OR.

Saídas: Camadas P2_<CLASSE> por UF, sem sobreposição entre si.

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 2 - Camada 2 (projetos): esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
