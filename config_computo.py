"""Configuração central do cômputo Planaveg 2026.

Todos os scripts (1 a 7) e o pacote ``computo`` leem daqui: caminhos, fontes de
dados, ordem da hierarquia (Anexo 1 do Relatório Técnico MMA/Conaveg, set/2026),
regras de elegibilidade e parâmetros de execução.

Itens marcados com ``PENDENTE`` dependem de decisão do usuário e NÃO devem ser
tratados como definitivos até serem confirmados (ver ``PENDENCIAS`` no final).
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
# PLANAVEG_RAIZ / PLANAVEG_SAIDA permitem apontar para outra cópia dos dados (testes) sem editar o arquivo.
RAIZ = Path(os.environ.get("PLANAVEG_RAIZ", r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE"))
SAIDA = Path(os.environ.get("PLANAVEG_SAIDA", RAIZ / "Computo_Planaveg_2026"))   # classes grandes: 1 GeoPackage por UF (~2 GB no ArcGIS)
LOGS = SAIDA / "_logs"
PROGRESSO = SAIDA / "_progresso"                # checkpoints JSON (retomada automática)
SAIDA_INSUMOS = SAIDA / "Insumos"               # passo 1: IN_<CLASSE> (elegíveis, polígonos inteiros)
SAIDA_TIER1 = SAIDA / "Tier1_Recooperar"        # passo 2 (classe 1): P2_RECOOPERAR + tabelas
SAIDA_TIER3 = SAIDA / "Tier3_CAR_Regularizacao" # passo 2 (classe 3, SICAR-regularização); a classe 2 (MonitoRAD) está desativada
SAIDA_TIER4 = SAIDA / "Tier4_Outros_Projetos"   # passo 2 (classe 4, Outros projetos: por ora só embargos PANGIA x VS)
SAIDA_TIER5 = SAIDA / "Tier5_OR"                # passo 2 (classe 5, Observatório da Restauração)
SAIDA_TIER6 = SAIDA / "Tier6_TI"                # passo 3 (classe 6, VS em Terras Indígenas)
SAIDA_TIER7 = SAIDA / "Tier7_UC"                # passo 3 (classe 7, VS em Unidades de Conservação; APAs: área pública)
SAIDA_TIER8 = SAIDA / "Tier8_Manguezal"         # passo 3 (classe 8, VS em manguezais do ProManguezal)
SAIDA_TIER9 = SAIDA / "Tier9_APP"               # passo 3b (classe 9, VS em APP dos imóveis do CAR)
SAIDA_TIER10 = SAIDA / "Tier10_AUR"             # passo 3b (classe 10, VS em AUR dos imóveis do CAR)
SAIDA_TIER11 = SAIDA / "Tier11_RL"              # passo 3b (classe 11, VS em RL dos imóveis do CAR)

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
        # Recooperar 2026 (decidido) com a VS qualificada incorporada aos polígonos originais
        # (saída de incorporar_vegsec_projetos.py; polígonos inteiros, atributos vs22q_* e vs2224q_*).
        "arquivo": "Projetos_com_VegSec/IBAMA_Projetos_Recooperar_2026_com_VegSec.gpkg",
        # Peças VS x projeto usadas para recalcular a VS na área líquida e por UF/bioma:
        "cruzamento": {
            "vs22q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Projetos_Restauracao/IBAMA_Projetos_Recooperar_2026_x_VegSec_2022_qualificada.gpkg",
            "vs2224q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Projetos_Restauracao/IBAMA_Projetos_Recooperar_2026_x_VegSec_2022-2024_qualificada.gpkg",
        },
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
    "outros_projetos": {   # ICMBio ADIADO (decisão de 21/09/2026): não entra no Tier-1; retomar depois
        "icmbio_restauracao": "Projetos_com_VegSec/ICMBio_Projetos_Restauracao_2026_com_VegSec.gpkg",   # PENDENTE: quais camadas
        "icmbio_gef_terrestre": "Projetos_com_VegSec/ICMBio_Projetos_GEF_Terrestre_2026_com_VegSec.gpkg",
    },
    "or": {"arquivo": "ORR_Observatorio_Restauracao_2026.gpkg", "camada": "20260917_ORdados_base_publico",
           "campo_bioma": "Bioma", "campo_area": "AreaCalc_h"},   # trocado para o ORR 2026 em 24/09/2026 (decisão abaixo)
    "monitorad": None,   # NÃO ENTRA no cômputo 2026 (dados ainda não recebidos)
    # --- Camada 1 (Governança) ---
    # Classes 6 a 8: entram as peças "VS qualificada x território" dos cruzamentos já calculados (uma peça por território x feição de VS).
    "ti": {
        "arquivo": "Terras_Indigenas_FUNAI20260507.gpkg",
        "cruzamento": {
            "vs22q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Terras_Indigenas/Terras_Indigenas_FUNAI20260507_x_VegSec_qualificado.gpkg",
            "vs2224q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Terras_Indigenas/Terras_Indigenas_FUNAI20260507_x_VegSec_2022-2024_qualificado.gpkg",
        },
        "camada_cruzamento": "Terras_Indigenas_FUNAI20260507_vegsec",
    },
    "uc": {
        "arquivo": "Unidades_Conservacao_CNUC20260507.gpkg",
        "cruzamento": {
            "vs22q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Unidades_Conservacao/Unidades_Conservacao_CNUC20260507_x_VegSec_qualificado.gpkg",
            "vs2224q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Unidades_Conservacao/Unidades_Conservacao_CNUC20260507_x_VegSec_2022-2024_qualificado.gpkg",
        },
        "camada_cruzamento": "Unidades_Conservacao_CNUC20260507_vegsec",
    },
    "manguezal": {
        "arquivo": "Pro-Manguezal_IBAMA20260508.gpkg",
        "cruzamento": {
            "vs22q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Pro_Manguezal/Pro-Manguezal_IBAMA20260508_x_VegSec_qualificado.gpkg",
            "vs2224q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Pro_Manguezal/Pro-Manguezal_IBAMA20260508_x_VegSec_2022-2024_qualificado.gpkg",
        },
        "camada_cruzamento": "Pro_Manguezal_IBAMA20260508_vegsec",
    },
    # CAR total (todos os imóveis cadastrados, sem cancelados) dissolvido por UF: 1 feição por UF. Serve para tirar a parte privada das APAs.
    "car_total": {
        "arquivo": "Analise_Territorial_CAR-INCRA_dissolvido/CAR_Brasil_Maio2026_Imovel_Area_Total_dissolvido_UF.gpkg",
        "camada": "CAR_BRASIL_Area_Total_dissolvido_UF", "campo_uf": "uf",
    },
    # SIGEF: imóveis públicos dentro de APAs (2.760 parcelas nacionais) - recupera como pública a parte do CAR total que, dentro
    # da APA, é na verdade um imóvel público (decisão de 24/09/2026, ver APA_AREA_PUBLICA). Todas as parcelas entram, qualquer
    # que seja o status (`status`: CERTIFICADA/REGISTRADA; `situacao_i`: REGISTRADA/TITULADANAOREGISTRADA/NAOTITULADA).
    "sigef_publico_apa": {"arquivo": "SIGEF_Publico_em_APA.gpkg", "camada": "sigefpublico_em_apa"},
    "car_selecionados_dir": "CAR_Maio2026_Imoveis_Selecionados",   # <UF>_CAR_Imoveis_Selecionados_<categoria>.gpkg
    # Cruzamento VS x APP/AUR/RL dos imóveis selecionados (um arquivo por categoria; camadas VS_<APP|AUR|RL>_<categoria>; campos
    # uf, cod_imovel, tipo, bioma, ano, des_condic, area_ha). Cada UF ocupa um bloco contínuo de FIDs.
    "car_cruzamentos": {
        "pasta": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Cadastro_Ambiental_Rural",
        "2022q": "VS_2022_Imoveis_Selecionados_{categoria}_Qualificado.gpkg",
        "2024": "VS_2024_Imoveis_Selecionados_{categoria}.gpkg",          # só Amazônia e Cerrado (VS 2024 qualificada)
        "camada": "VS_{classe}_{categoria}",
        "biomas_2024": ["Amazonia", "Cerrado"],   # vs2224q = 2022q nos demais biomas + 2024 nestes dois
    },
    # --- Apoio ---
    "assentamentos": {"arquivo": "Assentamentos_Rurais_INCRA20260610.gpkg"},
    "quilombolas": {"arquivo": "Territorios_Quilombolas_INCRA20260610.gpkg"},
    "estados": {"arquivo": "IBGE_Limite_Estados.gpkg", "camada": "Limite_Estados_IBGE_2025", "campo_uf": "SIGLA_UF"},
    "biomas": {"arquivo": "IBGE_Limite_Biomas.gpkg", "camada": "Limite_Biomas_IBGE_1_250_000", "campo": "Bioma"},
    "embargos_pangia": {   # já limpo: sem registros sem geometria e sem pontos (50.674 polígonos)
        "arquivo": "IBAMA_Areas_Embargadas_PANGIA20260920_Poligonos.gpkg",
        "camada": "IBAMA_Area_Embargada_PANGIA20260920",
        # Cruzamento VS qualificada x embargos (uma peça por embargo x feição de VS; ``idx_embargo`` = posição 0-based
        # do embargo no arquivo acima, isto é, FID - 1). Classe 4: só a VS dentro do embargo entra no cômputo.
        "cruzamento": {
            "vs22q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Areas_Embargadas/IBAMA_Areas_Embargadas_PANGIA20260920_x_VegSec_2022_qualificada.gpkg",
            "vs2224q": "Cruzamento_Espacial_Vegetacao_Secundaria/VS-Areas_Embargadas/IBAMA_Areas_Embargadas_PANGIA20260920_x_VegSec_2022-2024_qualificada.gpkg",
        },
        "camada_cruzamento": "IBAMA_Area_Embargada_PANGIA20260920_vegsec",
    },
    "florestas_publicas_nao_destinadas": None,                      # PENDENTE: fonte do dado (CNFP)
}

# Vegetação secundária qualificada (>= 2 ha). DECIDIDO: o cômputo roda em DUAS versões, sempre com VS qualificada.
# Prefixo = prefixo dos atributos de VS nos arquivos de projetos (vs22q_*, vs2224q_*).
VS_VERSOES = {
    "vs22q": "2022_qualificada",
    "vs2224q": "2022-2024_qualificada",   # Amazônia e Cerrado substituídos pela VS 2024 qualificada
}
BIOMAS_VS = ["Amazonia", "Caatinga", "Cerrado", "Mata_Atlantica", "Pampa", "Pantanal"]
VS_ARQUIVOS = {
    "2022_qualificada": ["Vegetacao_Secundaria_INPE/VS_2022_TerraBrasilis_Vegetacao_Secundaria_Qualificada_Brasil.gpkg"],
    "2022-2024_qualificada": [
        "Vegetacao_Secundaria_INPE/VS_2024_Terraclass_Vegetacao_Secundaria_Qualificada_Bioma_Amazonia.gpkg",
        "Vegetacao_Secundaria_INPE/VS_2024_Terraclass_Vegetacao_Secundaria_Qualificada_Bioma_Cerrado.gpkg",  # conferido: abr/2025
        "Vegetacao_Secundaria_INPE/VS_2022_TerraBrasilis_Vegetacao_Secundaria_Qualificada_Brasil.gpkg",       # demais 4 biomas
    ],
}

# ---------------------------------------------------------------------------
# Elegibilidade (valores de campo -> vocabulário do relatório)  [D2, D3, D4 CONFIRMADAS em 21/09/2026]
# ---------------------------------------------------------------------------
ELEGIBILIDADE_RECOOPERAR = {
    "campo_status": "status_are",
    "campo_etapa": "descricao_",
    # Licenciamento (LAC): premissa do usuário = 100% da camada. Nenhum registro traz "LAC" literal
    # (tipo_licen = LO, LI, ...). Inclui 6 polígonos com status ATUALIZAR (8,3 mil ha).      [D3 CONFIRMADA 21/09/2026]
    "licenciamento": {"status": None},
    # Reparação: "a partir de projeto protocolado", lido pela ETAPA (descricao_).             [D2 CONFIRMADA 21/09/2026]
    #  - fora: etapas sem projeto (regeneração/indício);
    #  - etapa ATUALIZAR: entra só se status = Recuperada (projeto concluído); em recuperação, fica fora;
    #  - "Projeto reprovado" ENTRA pela leitura literal (etapa >= protocolado): 2,4 mil ha; para retirar, ver etapas_fora.
    #  - o filtro é pela etapa, não pelo status: entram também os "Pendente de recuperação" (219 polígonos, 10,8 mil ha).
    "reparacao": {
        "status": ["Em recuperação", "Pendente de recuperação", "Recuperada"],
        "etapas_fora": ["sem projeto", "indícios", "índicios"],          # correspondência por trecho, sem caixa
        "etapa_atualizar": {"Recuperada": True, "Em recuperação": False, "Pendente de recuperação": False},
    },
    # Embargo: status "Em recuperação" ou "Recuperada" (a camada 2026 só traz esses dois).
    "embargo": {"status": ["Em recuperação", "Recuperada"]},
    # Outras áreas: categoria do dashboard do relatório; fora da lista de premissas.         [D4 CONFIRMADA 21/09/2026: 100%, inclui 4 'Pendente de recuperação']
    "outras": {"status": None},
}
# Ordem de precedência DENTRO do Recooperar quando polígonos de camadas diferentes se sobrepõem
# (a área sobreposta é contada uma vez, na categoria de maior precedência). Ajustável.
PRECEDENCIA_RECOOPERAR = ["licenciamento", "reparacao", "embargo", "outras"]
SIGLA_CATEGORIA = {"licenciamento": "LIC", "reparacao": "REP", "embargo": "EMB", "outras": "OUT"}
NOME_CATEGORIA = {"licenciamento": "Licenciamento", "reparacao": "Reparação por danos",
                  "embargo": "Áreas embargadas", "outras": "Outras áreas de projetos"}
# Valores-placeholder do IBAMA/ICMBio que viram nulo nos campos harmonizados:
PLACEHOLDERS = ["ATUALIZAR", "ATUALIZAR - ATUALIZAR", "Não se aplica", "Nao se aplica", "Não informado", "Não identificado"]
# Cadeia do ano de início (Recooperar): primeiro campo válido; o último é proxy (data da informação).
ANO_INICIO_CADEIA = [("dt_projeto", "dt_projeto"), ("dt_assinat", "dt_assinat"), ("dt_documen", "dt_documen (proxy)")]
ANO_MIN, ANO_MAX = 1990, 2026                      # anos fora deste intervalo viram nulo
DATAS_SENTINELA = ["2000-12-31", "2001-01-01"]     # data "nula" do sistema do IBAMA
# Campos harmonizados do Recooperar: nome novo -> campo de origem (placeholders viram nulo).
# Todos os demais campos originais ficam só em Projetos_com_VegSec/*_com_VegSec.gpkg (rastreabilidade
# pelos campos arquivo_orig, camada_orig e fid_orig).
CAMPOS_RECOOPERAR = {
    "processo_sei": "processo", "documento_sei": "documento_", "embargo_num": "embargo", "auto_infracao": "auto_infra",
    "termo_compromisso": "termo_comp", "licenca_num": "licenca_au",
    "status_recuperacao": "status_are", "etapa_processo": "descricao_",
    "tipo_licenca": "tipo_licen", "tipologia": "tipologia_", "nome_projeto": "empreendim",
    "estrategia": "tecnica_re", "local_recuperacao": "local_repa", "encaminhamento": "enc_admini",
    "classe_uso": "classe_uso", "categoria_fundiaria": "dominialid",
    "uf_fonte": "sg_uf", "municipio_fonte": "municipio", "bioma_fonte": "bioma",
}
# Campos do Recooperar que NÃO seguem para o cômputo (dados pessoais, LGPD) nem para o dashboard:
COLUNAS_PESSOAIS_RECOOPERAR = ["administra", "cpf_cnpj_a", "cpf_cnpj_e", "editor_alt", "editor_cad", "numeropess"]
CAR_CONDICOES_SICAR_REGULARIZACAO = ["Analisado, em regularização ambiental (Lei nº 12.651/2012)"]

# ---------------------------------------------------------------------------
# Classe 3 - SICAR-regularização (área a recompor de APP e RL dos imóveis "Analisado, em regularização ambiental")
# ---------------------------------------------------------------------------
# Elegibilidade [D0, D5, D6 e D7 CONFIRMADAS em 21/09/2026]:
#  - condição do imóvel: a do relatório (comparação sem acento e sem símbolos: "regularizacao" == "regularização");
#  - status do cadastro (ind_status): AT ativo, PE pendente, SU suspenso. O relatório não filtra pelo status do
#    cadastro e a camada já vem filtrada pela condição; por isso entram todos (PE+SU = 1,2 mil ha de 33,6 mil).
ELEGIBILIDADE_CAR_REG = {
    "condicao": CAR_CONDICOES_SICAR_REGULARIZACAO[0],
    "status_car": ["AT", "PE", "SU"],           # [D5 CONFIRMADA: manter todos] retirar PE/SU deixaria só cadastros ativos (-1,2 mil ha)
    "area_min_ha": 1e-6,                        # polígonos com área geodésica <= 0,01 m2 saem (5 fragmentos nulos no CAR)
}
# Ordem de precedência DENTRO da classe (área sobreposta conta uma vez): APP > RL (seção 4.3 do relatório);
# entre os temas de RL: averbada > aprovada e não averbada > proposta; depois fid.  [D6 CONFIRMADA em 21/09/2026]
PRECEDENCIA_CAR_REG = ["APP_ESCADINHA", "ARL_AVERBADA", "ARL_APROVADA_NAO_AVERBADA", "ARL_PROPOSTA"]   # por cod_tema
NOME_CAR_REG = {"app": "Área a recompor - APP (art. 61-A)", "rl": "Área a recompor - Reserva Legal"}
# Campos que seguem do CAR (sem dados pessoais: a camada só traz códigos de imóvel, tema e situação).
CAMPOS_CAR_REG = {"cod_tema": "cod_tema", "nom_tema": "nom_tema", "cod_imovel": "cod_imovel",
                  "status_car": "ind_status", "condicao_car": "des_condic"}

# ---------------------------------------------------------------------------
# Classe 4 - Outros projetos (por ora: embargos PANGIA; ICMBio adiado). A área da classe é a VS DENTRO do embargo.
# ---------------------------------------------------------------------------
# Decidido pelo usuário: embargos PANGIA entram como "Outros projetos" só pela interseção com a VS qualificada
# (duas versões), nunca pela extensão total. E1 a E4 confirmadas pelo usuário em 21/09/2026 (ver docs/tier4_outros_projetos.md):
#  E1 o arquivo de embargos não tem campo de situação/status: entram todos os 50.674 polígonos; o filtro é ter VS;
#  E2 sobreposição entre embargos: a área fica com o embargo MAIS ANTIGO (dat_embarg), depois o de menor FID;
#  E3 a geometria da classe difere entre as versões da VS (a VS 2022-2024 substitui Amazônia e Cerrado);
#  E4 nenhum filtro pela data do embargo: a VS entra mesmo em embargos posteriores ao ano da VS (~20% da área líquida da vs22q
#     está em embargos de 2023 em diante). Decisão do usuário (21/09/2026): NÃO filtrar por data.
PRECEDENCIA_EMBARGO_PANGIA = "data do embargo (mais antigo primeiro), depois FID"
NOME_EMBARGO_PANGIA = "Embargo PANGIA (IBAMA) - VS dentro do embargo"
# Campos do embargo que seguem para o cômputo: nome novo -> campo de origem.
CAMPOS_EMBARGO_PANGIA = {
    "num_tad": "num_tad", "serie_tad": "serie_tad", "seq_tad": "seq_tad",
    "uf_fonte": "uf", "cod_municipio": "cod_munici", "municipio_fonte": "municipio",
    "situacao_desmat": "sit_desmat", "tipo_area": "tipo_area", "bioma_fonte": "des_tipo_b", "operacao": "operacao",
}
# NÃO seguem (nomes/CPF/CNPJ de embargados e textos livres com nomes de pessoas, imóveis e lugares): LGPD.
COLUNAS_PESSOAIS_PANGIA = ["nome_embar", "cpf_cnpj_e", "nome_imove", "des_locali", "des_tad", "des_infrac"]
PLACEHOLDERS_PANGIA = ["", "Não se aplica", "Nao se aplica", "Não Se Aplica"]
ELEGIBILIDADE_EMBARGO_PANGIA = {"area_min_ha": 1e-6}   # peça de VS com área <= 0,01 m2 sai

# ---------------------------------------------------------------------------
# Classe 5 - OR (Observatório da Restauração, formato público) [uso confirmado em 21/09/2026; fonte trocada para o ORR 2026 em 24/09/2026]
# ---------------------------------------------------------------------------
# Até 23/09/2026 o arquivo (ORR 2025) trazia 4 feições, uma por bioma (Amazônia, Caatinga, Cerrado, Mata Atlântica), já dissolvidas,
# sem atributos por projeto, e filtradas por 'hierarquia' == 'ORR'. O ORR 2026 (`ORR_Observatorio_Restauracao_2026.gpkg`, camada
# `20260917_ORdados_base_publico`) veio no nível de projeto (86.281 polígonos, todos com `Privacidad` = "Público"), sem o campo
# 'hierarquia' e sem 'id_proj' - por isso ELEGIBILIDADE_OR não filtra mais por hierarquia. Decisão de 24/09/2026: usar TODOS os
# polígonos do ORR 2026, independente de status (`ProjAtivo`: Sim/Não/Não identificado/vazio) - sem filtro de status.
# Entra pela ÁREA TOTAL dos polígonos, com ou sem VS (como as classes 1 e 3); a VS fica como atributo. A classe subtrai as
# classes 1, 3 e 4 (a 4 na versão da VS em cálculo). Ao contrário do ORR 2025 (dissolvido, sem sobreposição entre si por
# construção), o ORR 2026 tem projetos que se sobrepõem entre si (submissões distintas na mesma área); a sobreposição interna
# deixou de ser um erro esperado e passou a ser tratada como nas outras classes com múltiplos polígonos (embargos, TI, UC):
# quem tem menor `fid_orig` fica com a área (não há outro critério de prioridade nos dados; `1_preparar_insumos.py` documenta).
ELEGIBILIDADE_OR = {"area_min_ha": 1e-6}
NOME_OR = "Observatório da Restauração (ORR 2026, formato público, nível de projeto)"
CELULA_VS_OR_GRAUS = 0.25    # agrupa as partes em células de 0,25 grau para ler a VS (uma leitura por célula)

# ---------------------------------------------------------------------------
# Classes 6 a 8 - Governança (TI, UC, Manguezal): a área da classe é a VS qualificada DENTRO do território
# ---------------------------------------------------------------------------
# TI: só as fases do relatório (seção 4.1.1): delimitada, declarada, homologada e regularizada. Ficam de fora "Em Estudo" e
#     "Encaminhada RI". Sobreposição entre TIs: a fase mais avançada fica com a área (regularizada > homologada > declarada > delimitada),
#     depois o menor código da TI. [T1 adotada, a confirmar]
ELEGIBILIDADE_TI = {
    "fases": ["Regularizada", "Homologada", "Declarada", "Delimitada"],   # ordem = precedência entre TIs sobrepostas
    "area_min_ha": 1e-6,
}
# UC: todas as categorias do CNUC (proteção integral e uso sustentável). O cruzamento traz também a ZONA DE AMORTECIMENTO
#     (limite = "za"), que não é UC e fica de fora; só entra limite = "uc". APAs: só a área pública, que é a APA menos os imóveis
#     do CAR (decisão de 21/09/2026), recuperando como pública a parte disso que é imóvel público do SIGEF (decisão de 24/09/2026,
#     ver APA_AREA_PUBLICA); a parte que continua privada segue o regime dos imóveis (classes APP, AUR e RL).
#     Sobreposição entre UCs: proteção integral > uso sustentável; fora da APA > APA; esfera federal > estadual > municipal; a mais
#     antiga (ano de criação); depois o código CNUC. [U1 adotada, a confirmar]
ELEGIBILIDADE_UC = {
    "limite": "uc",
    "categoria_apa": "Área de Proteção Ambiental",
    "grupos": ["Proteção Integral", "Uso Sustentável"],                    # ordem = precedência
    "esferas": ["Federal", "Estadual", "Municipal"],                       # ordem = precedência
    "area_min_ha": 1e-6,
}
ELEGIBILIDADE_MANGUEZAL = {"area_min_ha": 1e-6}   # APP em toda a extensão (Art. 4º, VII): toda a VS do ProManguezal entra

# VS por camada (arquivo, camada, bioma em BIOMAS_VS). Todas em SIRGAS 2000 (a VS 2022 da Mata Atlântica vem
# sem CRS definido no arquivo; é tratada como EPSG:4674, como nos cruzamentos anteriores).
_VS22 = "Vegetacao_Secundaria_INPE/VS_2022_TerraBrasilis_Vegetacao_Secundaria_Qualificada_Brasil.gpkg"
_VS24A = "Vegetacao_Secundaria_INPE/VS_2024_Terraclass_Vegetacao_Secundaria_Qualificada_Bioma_Amazonia.gpkg"
_VS24C = "Vegetacao_Secundaria_INPE/VS_2024_Terraclass_Vegetacao_Secundaria_Qualificada_Bioma_Cerrado.gpkg"
_L22 = {"Amazonia": "Vegetacao_Secundaria_Amazonia_2022_qualificada", "Caatinga": "Vegetacao_Secundaria_Caatinga_2022_qualificada",
        "Cerrado": "Vegetacao_Secundaria_Cerrado_2022_qualificada", "Mata_Atlantica": "Vegetacao_Secundaria_Mata_Atlantica_2022_qualificada",
        "Pampa": "Vegetacao_Secundaria_Pampa_2022_qualificada", "Pantanal": "Vegetacao_Secundaria_Pantanal_2022_qualificada"}
VS_CAMADAS = {
    "vs22q": [(_VS22, _L22[b], b, "2022") for b in BIOMAS_VS],
    "vs2224q": [(_VS22, _L22[b], b, "2022") for b in ("Caatinga", "Mata_Atlantica", "Pampa", "Pantanal")]
               + [(_VS24A, "VS_Amazônia_2024_2ha_2casas", "Amazonia", "2024"),
                  (_VS24C, "vs_qualificacao_cerrado_2024_v01", "Cerrado", "2024")],
}

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


# Decisões confirmadas pelo usuário em 21/09/2026 (Recooperar 2026, Tier-1):
#   D2 Reparação por etapa (fora "sem projeto", "indícios" e ATUALIZAR não Recuperada; entram "Projeto reprovado" e
#      "Pendente de recuperação"); D3 Licenciamento 100% (inclui 6 ATUALIZAR); D4 Outras áreas 100%;
#   precedência Licenciamento > Reparação > Embargo > Outras.
# Decisões confirmadas em 21/09/2026 (SICAR-regularização, classe 3): D0 o arquivo (AC, MT, PB, RJ e SP; 2.391 imóveis) é o conjunto
#   nacional completo; D5 entram todos os status do cadastro (AT, PE, SU); D6 precedência APP > RL averbada > RL aprovada não
#   averbada > RL proposta; D7 a área fora dos limites do IBGE fica rotulada 'FORA' (14,6 ha, polígono CARREG-RL-000924), sem UF.
#   Classe 4 (21/09/2026): embargos PANGIA20260920 entram só pela interseção com a VS qualificada (decisão de 20/09/2026); E1 a E4 CONFIRMADAS em 21/09/2026 (todos os embargos com VS; embargo mais antigo fica com a área sobreposta; polígonos por versão; sem filtro pela data do embargo).
#   Classe 5 (21/09/2026): usar o ORR 2025 (4 polígonos dissolvidos por bioma), pela ÁREA TOTAL dos polígonos, independente do cruzamento com a VS.
# Classes 9 a 11 (CAR: APP, AUR, RL). Precedência confirmada pelo usuário em 21/09/2026 (C1 e C2):
#   1) os imóveis HABILITADOS precedem os Analisados e os Não analisados, em qualquer classe: a RL de um Habilitado vence a APP de um Analisado;
#   2) dentro de cada grupo, a classe manda: APP > AUR > RL (dentro do imóvel também);
#   3) entre Analisados e Não analisados, a classe manda e a categoria desempata (a APP de um Não analisado vence a RL de um Analisado;
#      na mesma classe, Analisados > Não analisados);
#   4) na mesma categoria, a sobreposição entre imóveis fica com o menor cod_imovel (o cruzamento não traz a data de cadastro).
# Ordem de processamento (cada bloco subtrai as classes 1 a 8 e todos os blocos anteriores):
#   APP-Habilitados, AUR-Habilitados, RL-Habilitados, APP-(Analisados e Não analisados), AUR-(idem), RL-(idem).
CAR_GRUPOS_PRECEDENCIA = [["Habilitados"], ["Analisados", "Nao_Analisados"]]
CAR_ROTULOS_GRUPOS = ["H", "AN"]      # sufixo do bloco nas colunas sobreposta_<classe>_<sufixo>_ha
CAR_CATEGORIAS_PRECEDENCIA = [c for g in CAR_GRUPOS_PRECEDENCIA for c in g]     # Habilitados, Analisados, Nao_Analisados
# As peças de um mesmo imóvel se sobrepõem no cruzamento (temas de APP sobrepostos, duplicatas): antes da precedência as peças de cada
# imóvel (categoria, cod_imovel, bioma da VS) são unidas.
# APAs (decisão de 21/09/2026, refinada em 24/09/2026): área pública = APA menos os imóveis cadastrados no CAR (CAR total
# dissolvido por UF, sem cancelados), RECUPERANDO como pública a parte disso que é um imóvel público do SIGEF (todas as
# parcelas do SIGEF entram, qualquer que seja o status). Implementado em computo.governanca.apa_area_publica.
APA_AREA_PUBLICA = "(APA menos CAR total) união (SIGEF_Publico_em_APA ∩ APA) - CAR_Brasil_Maio2026_Imovel_Area_Total_dissolvido_UF e SIGEF_Publico_em_APA.gpkg"
PENDENCIAS = [
    "ICMBio (adiado em 21/09/2026): quais camadas são projetos; ver análise de atributos e sobreposição (Analise_Atributos_e_Sobreposicao_Projetos_IBAMA_ICMBio.xlsx).",
    "OR: trocado para o ORR 2026 em 24/09/2026 (nível de projeto, 86.281 polígonos, todos os status - ver comentário de ELEGIBILIDADE_OR); "
    "se sair versão mais nova, trocar FONTES['or'].",
    "APA/UC: SIGEF_Publico_em_APA.gpkg incorporado em 24/09/2026 para recuperar como pública a parte do CAR total que é imóvel "
    "público dentro da APA (ver APA_AREA_PUBLICA e computo.governanca.apa_area_publica) - ainda sem rodada nacional com essa mudança.",
    "Florestas Públicas Não Destinadas (CNFP): fonte do dado.",
    "CAR Regularização: arquivo 'Junho26' com camadas 'Julho26' (2.398 imóveis) - confirmar.",
    # T1 e U1 confirmadas pelo usuário em 21/09/2026:
    #   T1 sobreposição entre TIs: fase mais avançada (regularizada > homologada > declarada > delimitada), depois o menor código da TI;
    #   U1 sobreposição entre UCs: proteção integral > uso sustentável; fora da APA > APA; federal > estadual > municipal; a mais antiga; menor código CNUC.
    "Classes 9 a 11 (CAR), achado: as peças de APP do cruzamento se sobrepõem dentro do mesmo imóvel (temas de APP sobrepostos e duplicatas): a soma de area_ha das peças de APP do cruzamento é várias vezes a área da união (3,3 vezes no AC); RL e AUR quase não se sobrepõem.",
]
