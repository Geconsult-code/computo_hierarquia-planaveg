# Cômputo Planaveg 2026 - hierarquia de sobreposições

Automação em Python do cômputo das **áreas em processo de recuperação da vegetação nativa** para o
reporte da meta nacional do Planaveg 2025-2028, seguindo o Relatório Técnico *Metodologia de
Monitoramento Geoespacial e Reporte de Áreas em Processo de Recuperação da Vegetação Nativa*
(MMA / Conaveg, setembro de 2026).

> **Status: esqueleto (v0.1.0).** A estrutura, a configuração e a documentação estão prontas. Os
> módulos e scripts serão implementados passo a passo. Decisões ainda abertas estão em `PENDENCIAS`,
> no arquivo `config_computo.py`.

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
| 1 | `1_preparar_insumos.py` | Aplica elegibilidade, padroniza CRS e campos, atribui UF e bioma (limites IBGE) |
| 2 | `2_camada2_projetos.py` | Hierarquia entre os projetos: Recooperar > SICAR-regularização > Outros projetos > OR |
| 3 | `3_camada1_vs_governanca.py` | Consolida os cruzamentos VS x TI, UC, manguezais e APP/AUR/RL |
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
├── computo/                 # núcleo reutilizável (geometria, io_dados, elegibilidade, hierarquia, arranjos, validacao)
├── 1_preparar_insumos.py ... 7_validacao_resultados.py
├── docs/                    # metodologia, hierarquia (Anexo 1), dicionário de dados
└── exemplos/teste_nucleo.py # teste de integridade da configuração
```

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
sobreposições* (v0.1.0) [software]. Geoconsult Ltda. Ver `CITATION.cff`.
