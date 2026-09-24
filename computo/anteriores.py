"""Classes já processadas (passo 2 e classes 6 a 8 do passo 3): onde estão e como lê-las.

Cada classe subtrai as de maior prioridade. As de projetos (1, 3) têm a mesma geometria nas duas versões da VS; as classes
cuja área é a própria VS (4 e 6 a 8) e o OR (que subtrai a 4) têm um conjunto líquido POR VERSÃO. Por isso ``arquivos_classes``
recebe a versão da VS (vs22q | vs2224q).
"""
from __future__ import annotations

import numpy as np

import config_computo as cfg
from . import io_dados as io
from .territorio import Limites

# nomes de arquivo (iguais aos usados pelos scripts 2 e 3)
ARQ_OUT_RECOOPERAR = "P2_Recooperar_2026.gpkg"
ARQ_OUT_CAR_REG = "P2_CAR_Regularizacao_Junho26.gpkg"
ARQ_OUT_EMB = "P2_Outros_Projetos_PANGIA_20260920.gpkg"
ARQ_OUT_OR = "P2_OR_2026.gpkg"
ARQ_OUT_TI = "P1_TI_FUNAI20260507.gpkg"
ARQ_OUT_UC = "P1_UC_CNUC20260507.gpkg"
ARQ_OUT_MANGUEZAL = "P1_Manguezal_ProManguezal20260508.gpkg"
ARQ_OUT_APP = "P1_APP_CAR_Maio2026.gpkg"
ARQ_OUT_AUR = "P1_AUR_CAR_Maio2026.gpkg"
ARQ_OUT_RL = "P1_RL_CAR_Maio2026.gpkg"


def carregar_limites() -> Limites:
    e, b = cfg.FONTES["estados"], cfg.FONTES["biomas"]
    uf = io.ler_camada(cfg.RAIZ / e["arquivo"], e["camada"])
    bio = io.ler_camada(cfg.RAIZ / b["arquivo"], b["camada"])
    return Limites(uf, e["campo_uf"], bio, b["campo"])


def arquivos_classes(versao=None) -> dict:
    """{classe: (arquivo, camada)} das classes já processadas. As que dependem da versão da VS só entram se ``versao`` for dada."""
    arq = {"RECOOPERAR": (cfg.SAIDA_TIER1 / ARQ_OUT_RECOOPERAR, "P2_RECOOPERAR"),
           "SICAR_REGULARIZACAO": (cfg.SAIDA_TIER3 / ARQ_OUT_CAR_REG, "P2_CAR_REGULARIZACAO")}
    if versao:
        arq["OUTROS_PROJETOS"] = (cfg.SAIDA_TIER4 / ARQ_OUT_EMB, f"P2_OUTROS_PROJETOS_{versao}")
        arq["OR"] = (cfg.SAIDA_TIER5 / ARQ_OUT_OR, f"P2_OR_{versao}")
        arq["TI"] = (cfg.SAIDA_TIER6 / ARQ_OUT_TI, f"P1_TI_{versao}")
        arq["UC"] = (cfg.SAIDA_TIER7 / ARQ_OUT_UC, f"P1_UC_{versao}")
        arq["MANGUEZAL"] = (cfg.SAIDA_TIER8 / ARQ_OUT_MANGUEZAL, f"P1_MANGUEZAL_{versao}")
        arq["APP"] = (cfg.SAIDA_TIER9 / ARQ_OUT_APP, f"P1_APP_{versao}")
        arq["AUR"] = (cfg.SAIDA_TIER10 / ARQ_OUT_AUR, f"P1_AUR_{versao}")
        arq["RL"] = (cfg.SAIDA_TIER11 / ARQ_OUT_RL, f"P1_RL_{versao}")
    return arq


def geoms_por_classe(codigo, versao=None, bbox=None, somente=None):
    """Lista de (classe, geometrias líquidas disjuntas) das classes ativas de maior prioridade já processadas.

    ``bbox`` restringe a leitura às feições que tocam a caixa (classes 9 a 11, processadas por UF); ``somente`` limita as classes
    lidas dos arquivos (as classes do CAR já processadas na mesma UF ficam em memória)."""
    arquivos = arquivos_classes(versao)
    saida = []
    for c in cfg.precedentes(codigo):
        if somente is not None and c not in somente:
            continue
        if c not in arquivos:
            raise NotImplementedError(f"classe anterior {c} ainda não processada (ou falta a versão da VS) - necessária para subtrair")
        arq, camada = arquivos[c]
        if not arq.exists():
            raise FileNotFoundError(f"Não encontrei {arq}. Rode a classe {c} antes.")
        saida.append((c, np.array(io.ler_camada(arq, camada, bbox=bbox).geometry.values, dtype=object)))
    return saida
