# Cômputo Planaveg 2026 - hierarquia de sobreposições

Automação em Python do cômputo das **áreas em processo de recuperação da vegetação nativa** para o
reporte da meta nacional do Planaveg 2025-2028, seguindo o Relatório Técnico *Metodologia de
Monitoramento Geoespacial e Reporte de Áreas em Processo de Recuperação da Vegetação Nativa*
(MMA / Conaveg, setembro de 2026).

> **Status: v0.6.0 - classes 1 (Recooperar 2026), 3 (SICAR-regularização), 4 (Outros projetos: embargos PANGIA), 5 (OR),
> 6 (TI), 7 (UC) e 8 (Manguezal) implementadas.** Passos 1 e 2 funcionam para as classes de projetos (1, 3 e 5: área completa dos
> polígonos, com os atributos de VS na tabela; classe 4: só a VS dentro do embargo) e o passo 3 para as classes de governança 6 a 8
> (a área da classe é a VS qualificada dentro do território; APAs só na área pública). Cada classe subtrai as anteriores. Pendentes: o ICMBio
> (parte da classe 4), as classes 9 a 11 (APP, AUR e RL do CAR, por UF, com a precedência Habilitados > Analisados > Não analisados)
> e os passos 4 a 7. Regras do Recooperar, da classe 3 e da classe 4 (E1 a E4) confirmadas em 21/09/2026. Decisões abertas: `PENDENCIAS`,
> em `config_computo.py`. Método e saídas: `docs/tier1_recooperar.md`, `docs/tier3_car_regularizacao.md`, `docs/tier4_outros_projetos.md`,
> `docs/tier5_or.md` e `docs/tier6_8_governanca_publica.md`.

## Onde este repositório se encaixa

| Repositório | Papel |
|---|---|
| [analise_conformidade_sicar-incra](https://github.com/Geconsult-code/analise_conformidade_sicar-incra) | Conformidade CAR x INCRA e seleção dos imóveis (Habilitados, Analisados, Não Analisados) |
| `cruzamento_vegetacao-secundaria` | Cruzamento da vegetação secundária com APP, RL e AUR dos imóveis selecionados |
| **computo_hierarquia-planaveg** (este) | Consolida tudo na hierarquia do Anexo 1 e produz o cômputo, sem dupla contagem |

## Como o cômputo funciona

- **Camada 2 (projetos):** Recooperar, SICAR-regularização, outros projetos e Observatório da
  Restauração. Conta a área inteira do projeto.
- **Camada 1 (VS legalmente protegida):** vegetação secundária qualificada (>= 2 ha) em TI, UC,
  manguezais e APP/AUR/RL do CAR.
- **Hierarquia:** cada classe subtrai as de maior prioridade (ver `docs/hierarquia_anexo1.md`).
  Depois removem-se as Florestas Públicas Não Destinadas.
- **Saída:** duas classes (VS legalmente protegida; projetos), desagregadas por arranjo de
  implementação, UF e bioma.
- **MonitoRAD:** fora do cômputo 2026 (dados não recebidos); a classe existe na configuração, desativada.

## Pipeline

| Passo | Script | Função |
|---|---|---|
| 1 | `1_preparar_insumos.py` | Aplica elegibilidade, padroniza CRS e campos, repara geometrias (**implementado: Recooperar, CAR-regularização, embargos PANGIA, OR, TI, UC e Manguezal**) |
| 2 | `2_camada2_projetos.py` | Hierarquia entre os projetos e atribuição de UF e bioma (**implementado: classes 1 Recooperar, 3 CAR-regularização, 4 Outros projetos/PANGIA e 5 OR**; demais pendentes) |
| 3 | `3_camada1_vs_governanca.py` | Hierarquia da Camada 1 (**implementado: classes 6 TI, 7 UC e 8 Manguezal**; APP, AUR e RL pendentes) |
| 4 | `4_aplicar_hierarquia.py` | Aplica a ordem completa do Anexo 1 e remove Florestas Públicas Não Destinadas |
| 5 | `5_desagregacao_arranjos.py` | Classifica nos arranjos da Figura 4, por UF e bioma |
| 6 | `6_totais_e_relatorio.py` | Tabelas de área e comparação com a meta (12 Mha) |
| 7 | `7_validacao_resultados.py` | Sobreposição zero entre classes, geometrias, conservação de área |

Princípios: recorte **peça a peça** com índice espacial (nunca dissolução estadual, que levou o recorte
do MG a 21 h em outro projeto); um GeoPackage por UF (limite de ~2 GB do ArcGIS); retomada automática
com checkpoints; execução por UF (`SOMENTE_ESTES`, `PULAR`, `REFAZER`); área geodésica GRS80 em EPSG:4674.

## Estrutura

```
computo_hierarquia-planaveg/
├── config_computo.py        # caminhos, fontes, hierarquia, elegibilidade, pendências
├── computo/                 # núcleo reutilizável (geometria, io_dados, elegibilidade, hierarquia, territorio, governanca, anteriores...)
├── 1_preparar_insumos.py ... 7_validacao_resultados.py
├── docs/                    # metodologia, hierarquia (Anexo 1), dicionário de dados
└── exemplos/teste_nucleo.py # teste de integridade da configuração
```

## Executar as classes 1, 3, 4 e 5 (Recooperar 2026, SICAR-regularização, embargos PANGIA e OR)

```
conda activate geo
python exemplos/teste_nucleo.py        # 31 testes sintéticos
python 1_preparar_insumos.py           # -> Computo_Planaveg_2026\Insumos (Recooperar, CAR-regularização, embargos PANGIA e OR, com a VS)
python 2_camada2_projetos.py           # -> ...\Tier1_Recooperar, ...\Tier3_CAR_Regularizacao, ...\Tier4_Outros_Projetos e ...\Tier5_OR
# ou por classe:  python 1_preparar_insumos.py or ;  python 2_camada2_projetos.py or
```

Os caminhos vêm de `config_computo.py` (ou das variáveis `PLANAVEG_RAIZ` e `PLANAVEG_SAIDA`). Cada classe subtrai as anteriores
(a 3 subtrai `P2_RECOOPERAR`; a 4 subtrai as classes 1 e 3; a 5 subtrai as classes 1, 3 e 4), por isso devem ser processadas na ordem. Cada classe grava o
próprio log na sua pasta (`_log_passo2.txt`, `_log_passo2_car.txt`, `_log_passo2_outros.txt`, `_log_passo2_or.txt`). O passo 1 do PANGIA usa o cruzamento
VS x embargos já feito (`Cruzamento_Espacial_Vegetacao_Secundaria\VS-Areas_Embargadas`); a classe 4 leva ~25 min e a classe 5 ~15 min (UF x bioma). O passo 1 do OR lê a VS bruta por células de 0,25 grau (~2 min).

## Executar as classes 6, 7 e 8 (TI, UC e Manguezal)

```
python 1_preparar_insumos.py ti uc manguezal   # peças VS x território por versão da VS; UC: APA menos o CAR total (~45 min; a etapa das APAs lê o CAR de cada UF)
python 3_camada1_vs_governanca.py              # -> ...\Tier6_TI, ...\Tier7_UC e ...\Tier8_Manguezal (TI ~10 min, UC ~20 min, Manguezal ~2 min)
```

Exigem as classes 1, 3, 4 e 5 já processadas (`2_camada2_projetos.py`); a classe 7 subtrai também a 6, e a 8 subtrai a 6 e a 7. O CAR total dissolvido por UF
(`Analise_Territorial_CAR-INCRA_dissolvido`) só é usado para tirar a área privada das APAs; o de MG chega a 550 MB (34 milhões de vértices) e pede uns 5 GB de memória; o passo 3 da UC chega a ~5 GB. Ver `docs/tier6_8_governanca_publica.md`.

## Instalação

Recomendado conda-forge (no Windows, `pip` costuma quebrar GDAL/fiona):

```
conda create -n geo python=3.11 geopandas pyogrio -c conda-forge
conda activate geo
pip install -e .
python exemplos/teste_nucleo.py
```

## Dados de entrada

Ficam em `GEODATABASE\GEOPACKAGE` (caminho em `config_computo.py`). O inventário está em
`docs/dicionario_dados.md`.

## Licença e citação

MIT (ver `LICENSE`). Para citar: Braga Meira, M. (2026). *Cômputo Planaveg 2026 - hierarquia de
sobreposições* (v0.6.0) [software]. Geoconsult Ltda. Ver `CITATION.cff`.
