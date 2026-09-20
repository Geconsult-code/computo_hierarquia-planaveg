"""Passo 1 - Preparar insumos  (ESQUELETO - a implementar)

Objetivo: Aplica a elegibilidade de cada fonte, padroniza CRS (EPSG:4674) e campos, repara geometrias e atribui UF e bioma pelos limites do IBGE.

Entradas: Fontes de config_computo.FONTES (Recooperar, CAR Regularização, ICMBio, OR, TI, UC, ProManguezal, PANGIA, Assentamentos, Quilombolas); IBGE_Limite_Estados e IBGE_Limite_Biomas.

Saídas: SAIDA/<UF>_Computo_Planaveg_2026.gpkg, camadas de insumo elegível por classe (prefixo IN_); relatório de contagens e áreas antes/depois de cada filtro.

Configuração: config_computo.py (SOMENTE_ESTES, PULAR, REFAZER, HIERARQUIA, FONTES).
Execução prevista: por UF, com retomada automática e log; validar primeiro em uma UF pequena (AC).
"""
from __future__ import annotations

import sys

import config_computo as cfg


def main() -> int:
    ufs = [u for u in (cfg.SOMENTE_ESTES or cfg.UFS) if u not in cfg.PULAR]
    print("Passo 1 - Preparar insumos: esqueleto ainda não implementado.")
    print("UFs previstas:", ", ".join(ufs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
