# Cômputo Planaveg 2026 - hierarquia de sobreposições

Automação em Python do cômputo das **áreas em processo de recuperação da vegetação nativa** para o
reporte da meta nacional do Planaveg 2025-2028, seguindo o Relatório Técnico *Metodologia de
Monitoramento Geoespacial e Reporte de Áreas em Processo de Recuperação da Vegetação Nativa*
(MMA / Conaveg, setembro de 2026).

> **Status (v0.9.0, outubro/2026):** cômputo 2026 concluído para o Brasil nas duas versões da vegetação
> secundária (VS 2022 qualificada e VS 2022-2024 qualificada), com as 10 classes ativas da hierarquia e os
> projetos do ICMBio (GEF Terrestre e Restauração Ecológica) na classe 4, incluídos em 14/10/2026.
> Produto final em `Computo_Planaveg_2026/Reporte_Final/`. Pendentes: remoção das Florestas Públicas Não
> Destinadas (fonte do dado) e desagregação por arranjos de implementação (passos 4 a 7, ver
> [Pipeline](#pipeline)). Decisões abertas: `PENDENCIAS`, em `config_computo.py`.

## Onde este repositório se encaixa

| # | Repositório | Papel |
|---|---|---|
| 1 | [analise_conformidade_sicar-incra](https://github.com/Geconsult-code/analise_conformidade_sicar-incra) | Conformidade CAR x INCRA e seleção dos imóveis (Habilitados, Analisados, Não Analisados) |
| 2 | [cruzamento_vegetacao-secundaria](https://github.com/Geconsult-code/cruzamento_vegetacao-secundaria) | Cruzamento da VS com APP, RL e AUR dos imóveis selecionados |
| 3 | **computo_hierarquia-planaveg** (este) | Consolida tudo na hierarquia do Anexo 1 e produz o cômputo, sem dupla contagem |
| 4 | [visualizacao_categoria-fundiaria](https://github.com/Geconsult-code/visualizacao_categoria-fundiaria) | Fragmenta o cômputo e acrescenta atributos de filtro (categoria fundiária, instrumento, município, bacia) |

## Como o cômputo funciona

- **Camada 2 (projetos, critério de intencionalidade):** Recooperar, SICAR-regularização, outros projetos
  (embargos PANGIA e ICMBio) e Observatório da Restauração. Conta a área inteira do projeto (exceto os
  embargos PANGIA, que entram só pela interseção com a VS).
- **Camada 1 (VS legalmente protegida, critério de governança):** VS qualificada em TI, UC, manguezais e
  APP/AUR/RL do CAR.
- **Hierarquia:** cada classe subtrai as de maior prioridade ([docs/hierarquia_anexo1.md](docs/hierarquia_anexo1.md)).
  Uma área que é projeto e VS conta uma vez, como projeto.
- **MonitoRAD:** fora do cômputo 2026 (dados não recebidos); a classe existe na configuração, desativada.

| Ordem | Classe | Camada | Documentação |
|---|---|---|---|
| 1 | Recooperar (IBAMA) | 2 | [tier1_recooperar.md](docs/tier1_recooperar.md) |
| 2 | MonitoRAD (IBAMA) - *desativada* | 2 | - |
| 3 | SICAR - Analisado, em regularização ambiental (área a recuperar) | 2 | [tier3_car_regularizacao.md](docs/tier3_car_regularizacao.md) |
| 4 | Outros projetos (embargos PANGIA x VS; ICMBio GEF Terrestre e Restauração Ecológica, área total) | 2 | [tier4_outros_projetos.md](docs/tier4_outros_projetos.md) |
| 5 | Observatório da Restauração (ORR 2026) | 2 | [tier5_or.md](docs/tier5_or.md) |
| 6 | VS em Terras Indígenas | 1 | [tier6_8_governanca_publica.md](docs/tier6_8_governanca_publica.md) |
| 7 | VS em Unidades de Conservação (APAs: só área pública) | 1 | idem |
| 8 | VS em manguezais (ProManguezal) | 1 | idem |
| 9 | VS em APP (SICAR) | 1 | [tier9_11_car.md](docs/tier9_11_car.md) |
| 10 | VS em AUR (SICAR) | 1 | idem |
| 11 | VS em RL (SICAR) | 1 | idem |

## Resultados do cômputo 2026 (área geodésica, ha)

| Classe | VS 2022 qualificada | VS 2022-2024 qualificada |
|---|---:|---:|
| 1 Recooperar | 107.093,1 | 107.093,1 |
| 3 SICAR-regularização | 33.519,5 | 33.519,5 |
| 4 Outros projetos (PANGIA + ICMBio) | 394.091,2 | 385.834,9 |
| 5 Observatório da Restauração | 159.072,6 | 159.084,5 |
| 6 TI | 940.531,6 | 978.255,5 |
| 7 UC | 1.336.759,2 | 1.340.029,8 |
| 8 Manguezal | 16.436,7 | 16.564,2 |
| 9 APP (Habilitados / Analisados / Não Analisados) | 338.258,4 / 141.231,4 / 741.647,6 | 350.522,3 / 142.857,5 / 748.198,0 |
| 10 AUR (Habilitados / Analisados / Não Analisados) | 16.372,5 / 5.661,5 / 35.058,5 | 17.502,2 / 6.129,5 / 36.321,7 |
| 11 RL (Habilitados / Analisados / Não Analisados) | 1.164.049,7 / 639.230,1 / 2.527.914,8 | 1.203.693,0 / 658.855,4 / 2.626.900,7 |
| **Total** | **8.596.928,3** | **8.811.361,7** |

Campo `computo` do `Planaveg_2026_Total.gpkg` (= `area_tnc`, área líquida gravada por cada classe), sem o
desconto das Florestas Públicas Não Destinadas (`area_wit_fpnd = 0`). A soma de `Area_ha` (área geodésica
da geometria final dissolvida) fica cerca de 29 ha abaixo nas duas versões (8.596.899,0 e 8.811.333,9 ha),
quase toda na classe 9 APP - Não Analisados. A meta nacional é de 12 Mha até 2030.

Efeito da inclusão do ICMBio (v0.9.0) em relação à v0.8.0: classe 4 +37.257,5 ha (vs22q) e +37.263,1 ha
(vs2224q); a mesma área sai das classes seguintes, quase toda do Observatório da Restauração (-28.196,1 e
-28.202,3 ha), das UCs (-811,1 e -803,0 ha) e das TIs (-48,8 e -46,6 ha). Total: +8.201,2 e +8.210,9 ha.

## Pipeline

| Passo | Script | Função | Situação |
|---|---|---|---|
| 1 | `1_preparar_insumos.py` | Elegibilidade, padronização de CRS e campos, reparo de geometrias, VS dos projetos | Implementado (Recooperar, CAR-regularização, PANGIA, OR, TI, UC, Manguezal) |
| 2 | `2_camada2_projetos.py` | Classes 1, 3, 4 e 5: hierarquia entre projetos, UF e bioma | Implementado |
| 3 | `3_camada1_vs_governanca.py` | Classes 6, 7 e 8: VS dentro dos territórios | Implementado |
| 3b | `3b_camada1_car.py` | Classes 9, 10 e 11: VS em APP/AUR/RL, por UF, com retomada | Implementado |
| 2b | `incluir_icmbio_classe4.py` | ICMBio na classe 4 de forma incremental: Δ (ICMBio fora das classes 1, 3 e 4) entra na classe 4 e sai das classes 5 a 11 | Executado em 14/10/2026 |
| final | `gerar_geopackages_finais.py` | Dissolve por UF x bioma e grava o reporte (`Reporte_Final`) e o Total | Implementado |
| 4 | `4_aplicar_hierarquia.py` | Remoção das Florestas Públicas Não Destinadas | Esqueleto (fonte do dado pendente) |
| 5 | `5_desagregacao_arranjos.py` | Arranjos de implementação da Figura 4, por UF e bioma | Esqueleto |
| 6 | `6_totais_e_relatorio.py` | Tabelas de área e comparação com a meta | Esqueleto |
| 7 | `7_validacao_resultados.py` | Sobreposição zero entre classes, geometrias, conservação de área | Esqueleto (conferências feitas por classe nos passos 2, 3 e 3b) |

A hierarquia é aplicada **classe a classe** nos passos 2, 3 e 3b: cada classe já grava a sua área
líquida, sem as classes anteriores. Por isso o passo 4 ficou reduzido à remoção das Florestas Públicas
Não Destinadas.

Princípios: recorte **peça a peça** com índice espacial (nunca dissolução estadual, que levou o recorte
do MG a 21 h em outro projeto); um GeoPackage por UF nas classes grandes (limite de ~2 GB do ArcGIS);
retomada automática com marcadores; execução por UF (`SOMENTE_ESTES`, `PULAR`, `REFAZER`); área
geodésica GRS80 em EPSG:4674.

## Dados: restaurar o backup

Os dados de entrada e os intermediários que este repositório lê estão no backup do projeto
(`F:\BKP_PLANAVEG`, organizado e documentado no repositório
[`backup_planaveg_2026`](https://github.com/Geconsult-code/backup_planaveg_2026)). Para rodar
os scripts em outro computador ou em outra pasta, restaure só o que este repositório usa
(cerca de 136 GB descompactados) e aponte os scripts para a pasta restaurada:

```powershell
git clone https://github.com/Geconsult-code/backup_planaveg_2026
cd backup_planaveg_2026
# simulação: mostra o volume por pasta e o espaço necessário
python restaurar_backup.py --backup F:\BKP_PLANAVEG --destino D:\PLANAVEG_DADOS --repo computo
# restauração (pode ser interrompida e retomada)
python restaurar_backup.py --backup F:\BKP_PLANAVEG --destino D:\PLANAVEG_DADOS --repo computo --executar
# uma vez só; abra um terminal novo depois
setx PLANAVEG_RAIZ "D:\PLANAVEG_DADOS"
```

O `config_computo.py` lê `PLANAVEG_RAIZ`; nenhum script precisa ser editado. Não defina
`PLANAVEG_SAIDA` de forma permanente (ver o README do `backup_planaveg_2026`).

Sem a variável, os scripts usam a pasta original no Dropbox (`GEODATABASE\GEOPACKAGE`), que hoje
guarda só uma cópia reduzida dos dados. Detalhes, opções e o inventário completo do backup
(`_manifesto_backup.csv`) estão no README do `backup_planaveg_2026`.

## Instalação

Recomendado conda-forge (no Windows, `pip` costuma quebrar GDAL/fiona):

```
conda create -n geo python=3.11 geopandas pyogrio -c conda-forge
conda activate geo
pip install -e .
python exemplos/teste_nucleo.py        # testes sintéticos de integridade
```

## Execução completa

As classes devem ser processadas **na ordem**, porque cada uma subtrai as anteriores.

```
conda activate geo

# Classes 1, 3, 4 e 5 (projetos)
python 1_preparar_insumos.py           # -> Computo_Planaveg_2026\Insumos
python 2_camada2_projetos.py           # -> Tier1_Recooperar, Tier3_CAR_Regularizacao, Tier4_Outros_Projetos, Tier5_OR
#   ou por classe:  python 1_preparar_insumos.py or ;  python 2_camada2_projetos.py or

# Classes 6, 7 e 8 (TI, UC e Manguezal)
python 1_preparar_insumos.py ti uc manguezal
python 3_camada1_vs_governanca.py      # -> Tier6_TI, Tier7_UC, Tier8_Manguezal

# Classes 9, 10 e 11 (APP, AUR e RL do CAR)
python 3b_camada1_car.py AC DF SE      # validação em UFs pequenas (~5 min)
python 3b_camada1_car.py               # 27 UFs, duas versões da VS (horas; retoma de onde parou)
python 3b_camada1_car.py --consolidar  # consolidação (roda sozinha quando todas as UFs terminam)

# ICMBio na classe 4 (incremental; entrada Insumos\IN_ICMBio_2026.gpkg). Simulação, depois gravação.
# Retoma de onde parou e nunca subtrai duas vezes (ICMBio_incremental_estado.json).
python incluir_icmbio_classe4.py
python incluir_icmbio_classe4.py --executar

# Reporte final
python gerar_geopackages_finais.py RECOOPERAR SICAR_REGULARIZACAO OUTROS_PROJETOS OR
python gerar_geopackages_finais.py TI UC MANGUEZAL
python gerar_geopackages_finais.py AUR
python gerar_geopackages_finais.py APP      # ~2 h
python gerar_geopackages_finais.py RL       # ~3,5 h
python gerar_geopackages_finais.py --so-total
```

Tempos de referência e uso de memória:

| Etapa | Tempo | Observação |
|---|---|---|
| Classe 4 (PANGIA) | ~25 min | usa o cruzamento VS x embargos já feito |
| Classe 5 (OR) | ~15 min com o ORR 2025 | o ORR 2026 (86 mil projetos) é mais lento |
| Classes 6 / 7 / 8 | ~10 / ~20 / ~2 min | UC chega a ~5 GB de memória; o CAR total de MG tem 550 MB |
| Classes 9 a 11 | horas | PA, MT, GO e MG (400 a 600 mil peças) são as mais lentas; dá para abrir 2 ou 3 terminais com UFs diferentes |
| Reporte final | ~6 h no total | APP ~2 h e RL ~3,5 h; `--so-total` ~20 min |

Os caminhos vêm de `config_computo.py` (ou das variáveis `PLANAVEG_RAIZ` e `PLANAVEG_SAIDA`). Cada
classe grava o próprio log na sua pasta (`_log_passo2*.txt`, `_log_geopackages_finais.txt`).

## Saídas

Em `GEODATABASE\GEOPACKAGE\Computo_Planaveg_2026\`:

```
Insumos/                     # passo 1: IN_<CLASSE> (elegíveis, polígonos inteiros)
Tier1_Recooperar/ ... Tier11_RL/   # passos 2, 3 e 3b: P1_/P2_ por classe, conferências (T*_conferencias.csv), logs
Reporte_Final/
├── Planaveg_2026_Total.gpkg                 # Reporte_Planaveg_Total_vs22q / _vs2224q (605 feições cada)
├── Planaveg_2026_Projetos_Recooperar.gpkg, _SICAR_Regularizacao, _Projetos_Outros, _Projetos_ORR
├── Planaveg_2026_Terras_Indigenas.gpkg, _Unidade_Conservacao, _Manguezal
└── Planaveg_2026_Imoveis_APP.gpkg, _AUR, _RL   # 3 camadas cada (Habilitados, Analisados, Não analisados) x 2 versões
Visualizacao/                # produto do repositório visualizacao_categoria-fundiaria
```

Campos do Total, no padrão do cômputo 2025: `hierarquia`, `Bioma`, `uf`, `categoria` (classes do CAR),
`tier`, `area_tnc` (área líquida da hierarquia), `area_wit_fpnd` (desconto de FPND, hoje 0), `computo`
(= `area_tnc` − `area_wit_fpnd`) e `Area_ha` (geodésica da geometria final). O dicionário completo dos
insumos e saídas está em [docs/dicionario_dados.md](docs/dicionario_dados.md).

## Estrutura

```
computo_hierarquia-planaveg/
├── config_computo.py              # caminhos, fontes, hierarquia, elegibilidade, PENDENCIAS
├── computo/                       # núcleo: geometria, io_dados, elegibilidade, hierarquia, territorio,
│                                  #   governanca, car, embargos, vs, anteriores, arranjos, validacao
├── 1_preparar_insumos.py ... 7_validacao_resultados.py
├── gerar_geopackages_finais.py
├── docs/
│   ├── metodologia.md             # resumo do relatório técnico e decisões de 2026
│   ├── hierarquia_anexo1.md       # ordem das classes e regra de contagem
│   ├── dicionario_dados.md        # insumos e saídas
│   └── tier*.md                   # método, decisões e conferências de cada classe
├── exemplos/teste_nucleo.py       # testes sintéticos de integridade
├── CHANGELOG.md, CITATION.cff, LICENSE, pyproject.toml, requirements.txt
```

## Licença e citação

MIT (ver `LICENSE`). Para citar: Braga Meira, M. (2026). *Cômputo Planaveg 2026 - hierarquia de
sobreposições* (v0.9.0) [software]. Geoconsult Ltda. Ver `CITATION.cff`.
