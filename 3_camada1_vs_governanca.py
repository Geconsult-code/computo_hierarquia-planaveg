"""Passo 3 - Camada 1 (VS legalmente protegida)  (ESQUELETO - a implementar)

Objetivo: Consolida em esquema padrão os cruzamentos já calculados da VS qualificada com TI, UC, manguezais e APP/AUR/RL dos imóveis selecionados. Não refaz os cruzamentos.

Entradas: Cruzamento_Espacial_Vegetacao_Secundaria/* (VS-Terras_Indigenas, VS-Unidades_Conservacao, VS-Pro_Manguezal, VS-Cadastro_Ambiental_Rural) na versão de VS definida em config_computo.VS_VERSAO.

Saídas: Camadas P1_<CLASSE> por UF (peças de VS por classe, ainda com sobreposição entre classes).

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 3 - Camada 1 (VS legalmente protegida): esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
