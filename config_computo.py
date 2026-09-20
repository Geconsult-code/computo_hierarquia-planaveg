"""Configuração central do cômputo Planaveg 2026.

Todos os scripts (1 a 7) e o pacote ``computo`` leem daqui: caminhos, fontes de
dados, ordem da hierarquia (Anexo 1 do Relatório Técnico MMA/Conaveg, set/2026),
regras de elegibilidade e parâmetros de execução.

Itens marcados com ``PENDENTE`` dependem de decisão do usuário e NÃO devem ser
tratados como definitivos até serem confirmados (ver ``PENDENCIAS`` no final).
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
RAIZ = Path(r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE")
SAIDA = RAIZ / "Computo_Planaveg_2026"          # 1 GeoPackage por UF (limite ~2 GB do ArcGIS)
LOGS = SAIDA / "_logs"
PROGRESSO = SAIDA / "_progresso"                # checkpoints JSON (retomada automática)

# ---------------------------------------------------------------------------
# Parâmetros gerais
# ---------------------------------------------------------------------------
CRS_TRABALHO = 4674          # SIRGAS 2000 geográfico (padrão de todo o projeto)
ELIPSOIDE = "GRS80"          # área geodésica (pyproj.Geod), mesmo padrão dos outros repositórios
CRS_EQUAL_AREA_CONFERENCIA = 6933   # apenas conferência cruzada de áreas
AREA_MIN_VS_HA = 2.0         # filtro de VS qualificada; já aplicado externamente (arquivos *_Qualificada)

UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]
SOMENTE_ESTES: list[str] = []   # ex.: ["AC"] para validar em uma UF pequena antes do lote
PULAR: list[str] = []           # UFs a ignorar
REFAZER: list[str] = []         # UFs a reprocessar mesmo já concluídas

# Nomes de bioma: o limite do IBGE é acentuado; as camadas de VS usam nomes sem acento.
BIOMA_IBGE_PARA_VS = {
    "Amazônia": "Amazonia",
    "Caatinga": "Caatinga",
    "Cerrado": "Cerrado",
    "Mata Atlântica": "Mata_Atlantica",
    "Pampa": "Pampa",
    "Pantanal": "Pantanal",
}

# ---------------------------------------------------------------------------
# Fontes de dados (caminhos relativos a RAIZ)
# ---------------------------------------------------------------------------
FONTES = {
    # --- Camada 2 (Intencionalidade) ---
    "recooperar": {
        "arquivo": "IBAMA_Projetos_Recooperar_2026_com_area.gpkg",     # PENDENTE: 2025 x 2026
        "camadas": {
            "licenciamento": "Processo_de_Licenciamento_Ambiental",
            "reparacao": "Processo_de_Reparação_por_danos",
            "embargo": "Processo_de_Embargo",
            "outras": "Outras_Áreas",
        },
    },
    "sicar_regularizacao": {
        "arquivo": "CAR_Junho26_Regularizacao_Ambiental.gpkg",
        "camadas": {
            "recompor_app": "CAR_Area_Recompor_APP_Julho26_Regularizacao_Ambiental",
            "recompor_rl": "CAR_Area_Recompor_RL_Julho26_Regularizacao_Ambiental",
            "imoveis": "CAR_Limite_Imovel_Julho26_Regularizacao_Ambiental",
        },
    },
    "outros_projetos": {
        "icmbio_restauracao": "ICMBio_Projetos_Restauracao_2026_com_area.gpkg",   # PENDENTE: quais camadas
        "icmbio_gef_terrestre": "ICMBio_Projetos_GEF_Terrestre_2026_com_area.gpkg",
    },
    "or": {"arquivo": "ORR_Observatorio_Restauracao_2025_com_area.gpkg"},          # PENDENTE: confirmar conteúdo
    "monitorad": None,   # NÃO ENTRA no cômputo 2026 (dados ainda não recebidos)
    # --- Camada 1 (Governança) ---
    "ti": {"arquivo": "Terras_Indigenas_FUNAI20260507.gpkg"},
    "uc": {"arquivo": "Unidades_Conservacao_CNUC20260507.gpkg"},
    "manguezal": {"arquivo": "Pro-Manguezal_IBAMA20260508.gpkg"},
    "car_selecionados_dir": "CAR_Maio2026_Imoveis_Selecionados",   # <UF>_CAR_Imoveis_Selecionados_<categoria>.gpkg
    # --- Apoio ---
    "assentamentos": {"arquivo": "Assentamentos_Rurais_INCRA20260610.gpkg"},
    "quilombolas": {"arquivo": "Territorios_Quilombolas_INCRA20260610.gpkg"},
    "estados": {"arquivo": "IBGE_Limite_Estados.gpkg", "camada": "Limite_Estados_IBGE_2025", "campo_uf": "SIGLA_UF"},
    "biomas": {"arquivo": "IBGE_Limite_Biomas.gpkg", "camada": "Limite_Biomas_IBGE_1_250_000", "campo": "Bioma"},
    "embargos_pangia": {   # já limpo: sem registros sem geometria e sem pontos (50.674 polígonos)
        "arquivo": "IBAMA_Areas_Embargadas_PANGIA20260920_Poligonos.gpkg",
        "camada": "IBAMA_Area_Embargada_PANGIA20260920",
    },                                                              # PENDENTE: papel no cômputo
    "florestas_publicas_nao_destinadas": None,                      # PENDENTE: fonte do dado (CNFP)
}

# Vegetação secundária qualificada (>= 2 ha). PENDENTE: definir a versão de referência.
VS_VERSAO = "PENDENTE"   # "2022_qualificada" | "2022-2024_qualificada"
VS_ARQUIVOS = {
    "2022_qualificada": ["Vegetacao_Secundaria_INPE/VS_2022_TerraBrasilis_Vegetacao_Secundaria_Qualificada_Brasil.gpkg"],
    "2022-2024_qualificada": [
        "Vegetacao_Secundaria_INPE/VS_2024_Terraclass_Vegetacao_Secundaria_Qualificada_Bioma_Amazonia.gpkg",
        "Vegetacao_Secundaria_INPE/VS_2024_Terraclass_Vegetacao_Secundaria_Qualificada_Bioma_Cerrado.gpkg",  # suspeita de filtro
        "Vegetacao_Secundaria_INPE/VS_2022_TerraBrasilis_Vegetacao_Secundaria_Qualificada_Brasil.gpkg",       # demais 4 biomas
    ],
}

# ---------------------------------------------------------------------------
# Elegibilidade (valores de campo -> vocabulário do relatório)  [PENDENTE: confirmar]
# ---------------------------------------------------------------------------
ELEGIBILIDADE_RECOOPERAR = {
    "campo_status": "status_are",
    "licenciamento": None,                                # todas as áreas de LAC (100% têm projeto)
    "reparacao": ["Em recuperação", "Recuperada"],        # relatório: "a partir de projeto protocolado"
    "embargo": ["Em recuperação", "Recuperada"],          # relatório: "em recuperação" ou "recuperada"
}
ELEGIBILIDADE_TI_FASES = ["Delimitada", "Declarada", "Homologada", "Regularizada"]  # conferir valores reais de fase_ti
CAR_CONDICOES_SICAR_REGULARIZACAO = ["Analisado, em regularização ambiental (Lei nº 12.651/2012)"]

# ---------------------------------------------------------------------------
# Hierarquia (Anexo 1): cada classe subtrai TODAS as classes ativas de ordem menor.
# ---------------------------------------------------------------------------
HIERARQUIA = [
    dict(ordem=1, codigo="RECOOPERAR", nome="Recooperar (IBAMA)", camada=2, criterio="Intencionalidade", ativo=True),
    dict(ordem=2, codigo="MONITORAD", nome="MonitoRAD (IBAMA)", camada=2, criterio="Intencionalidade", ativo=False),
    dict(ordem=3, codigo="SICAR_REGULARIZACAO", nome="SICAR - Analisado, em regularização ambiental (área a recuperar)", camada=2, criterio="Intencionalidade", ativo=True),
    dict(ordem=4, codigo="OUTROS_PROJETOS", nome="Outros projetos (MMA, ICMBio e demais órgãos)", camada=2, criterio="Intencionalidade", ativo=True),
    dict(ordem=5, codigo="OR", nome="Observatório da Restauração (formato público)", camada=2, criterio="Intencionalidade", ativo=True),
    dict(ordem=6, codigo="TI", nome="VS em Terras Indígenas", camada=1, criterio="Governança", ativo=True),
    dict(ordem=7, codigo="UC", nome="VS em Unidades de Conservação (APAs: só áreas públicas)", camada=1, criterio="Governança", ativo=True),
    dict(ordem=8, codigo="MANGUEZAL", nome="VS em manguezais (APP - ProManguezal)", camada=1, criterio="Governança", ativo=True),
    dict(ordem=9, codigo="APP", nome="VS em APP (SICAR)", camada=1, criterio="Governança", ativo=True),
    dict(ordem=10, codigo="AUR", nome="VS em AUR (SICAR)", camada=1, criterio="Governança", ativo=True),
    dict(ordem=11, codigo="RL", nome="VS em RL (SICAR)", camada=1, criterio="Governança", ativo=True),
]
# Após a hierarquia: remover áreas sobrepostas a Florestas Públicas Não Destinadas (CNFP).
REMOVER_FLORESTAS_PUBLICAS_NAO_DESTINADAS = True

# Classes de saída do Sinaveg (seção 3.1.2 do relatório)
SAIDAS = {
    1: "Áreas com Vegetação Secundária Legalmente Protegida",
    2: "Áreas de Projetos de Recuperação da Vegetação Nativa",
}

# Arranjos de implementação do Planaveg 2025-2028 (Figura 4) e metas até 2030 (Mha)
ARRANJOS = {
    "PUBLICAS": dict(nome="Áreas públicas (UCs, TIs e outros territórios coletivos)", meta_mha=2.0),
    "APP_RL_AUR": dict(nome="APP, RL e AUR de imóveis rurais", meta_mha=9.0),
    "BAIXA_PRODUTIVIDADE": dict(nome="Áreas rurais de baixa produtividade", meta_mha=1.0),
    "NAO_INCLUIDA": dict(nome="Recuperação não incluída nos arranjos anteriores", meta_mha=None),
}
META_NACIONAL_MHA = 12.0


def classes_ativas() -> list[dict]:
    """Classes da hierarquia que participam do cômputo, em ordem de prioridade."""
    return sorted((c for c in HIERARQUIA if c["ativo"]), key=lambda c: c["ordem"])


def precedentes(codigo: str) -> list[str]:
    """Códigos das classes ativas que têm prioridade sobre ``codigo`` (as que ele subtrai)."""
    alvo = next(c for c in HIERARQUIA if c["codigo"] == codigo)
    return [c["codigo"] for c in classes_ativas() if c["ordem"] < alvo["ordem"]]


PENDENCIAS = [
    "Versão da VS de referência (VS_VERSAO): 2022 qualificada x 2022-2024; Cerrado 2024 qualificado com filtro suspeito.",
    "Recooperar: 2025 x 2026 e mapeamento de status_are para o vocabulário do relatório.",
    "Papel dos embargos PANGIA no cômputo (só 45% dos embargos do Recooperar 2026 casam por número/série).",
    "ICMBio: quais camadas são projetos (Restauracao_Ecologica; Areas_Degradadas; Embargos_maior5ha).",
    "OR: arquivo com 4 feições (uma por bioma, dissolvido) - confirmar que é o conjunto público final.",
    "Florestas Públicas Não Destinadas (CNFP): fonte do dado.",
    "CAR Regularização: arquivo 'Junho26' com camadas 'Julho26' (2.398 imóveis) - confirmar.",
    "APAs: definição da área pública (sugestão: APA menos imóveis privados do CAR).",
]
