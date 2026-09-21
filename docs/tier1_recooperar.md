# Tier-1: classe Recooperar 2026

Primeiro nível da hierarquia do Anexo 1 (classe 1). Não subtrai nenhuma outra classe. Segue a
regra da Camada 2: **conta a área inteira do polígono de projeto elegível**. A vegetação secundária (VS)
que cai dentro do projeto **não é subtraída nem somada à parte**: fica como atributo do polígono, para
ser tratada nos passos seguintes (Camada 1 subtrai os projetos).

## Entradas

`Projetos_com_VegSec\IBAMA_Projetos_Recooperar_2026_com_VegSec.gpkg` (4 camadas: Licenciamento,
Reparação por danos, Embargo, Outras áreas) e, para recalcular a VS, os cruzamentos em
`Cruzamento_Espacial_Vegetacao_Secundaria\VS-Projetos_Restauracao` (VS 2022 qualificada = `vs22q`;
VS 2022-2024 qualificada = `vs2224q`). Limites IBGE de UF e bioma.

## Elegibilidade (`config_computo.ELEGIBILIDADE_RECOOPERAR`)

| Categoria | Regra | Situação da decisão |
|---|---|---|
| Licenciamento | 100% da camada (inclui 6 polígonos `ATUALIZAR`) | **PENDENTE D3** |
| Reparação por danos | Por etapa (`descricao_`): fora "sem projeto" e "indícios"; `ATUALIZAR` só se status = Recuperada; inclui "Projeto reprovado" (leitura literal) | **PENDENTE D2** |
| Embargo | Status Em recuperação ou Recuperada | adotado |
| Outras áreas | 100% da camada | **PENDENTE D4** |

Esses parâmetros são editáveis no config; basta reexecutar os passos 1 e 2.

## Sobreposição dentro da classe

Polígonos de categorias diferentes se sobrepõem em cerca de 1% da área. Para não contar duas vezes, a
área **líquida** de cada polígono é: polígono menos a união dos polígonos de maior precedência que o
cobrem. Precedência: Licenciamento > Reparação > Embargo > Outras; empate por `ano_inicio` (mais antigo
primeiro, nulo por último) e `fid_orig`. Os polígonos líquidos são disjuntos e somam a união (conferido).
A tabela traz as duas leituras: `area_ha_geo` (inteira) e `area_liquida_ha`.

## VS nos polígonos

Os atributos `vs22q_*` e `vs2224q_*` vêm do passo anterior (`incorporar_vegsec_projetos.py`). O
Tier-1 recalcula a VS por peças (união das peças VS x projeto interceptada com a geometria) e confere
com o atributo (diferença < 0,01 ha por polígono). `vs*_liq_ha` é a VS dentro da geometria líquida. Onde
projetos se sobrepõem, a soma dos atributos por polígono conta a VS duas vezes; a VS líquida não.

## UF e bioma

Cada polígono é dividido em células UF x bioma (IBGE). O que fica fora dos limites (faixa costeira/mar)
recebe "FORA" e é conferido (tolerância 0,05% da área). `uf_principal` é a UF de maior área;
`uf_diverge_fonte` marca quando ela não consta no campo de UF da fonte.

## Campos e dados pessoais

Campos harmonizados em `CAMPOS_RECOOPERAR`. Colunas com dados pessoais (`administra`, `cpf_cnpj_a`,
`cpf_cnpj_e`, `editor_alt`, `editor_cad`, `numeropess`) **não** entram nas saídas (teste automático).
`possui_pro` e `area_proje` são descartados por não serem confiáveis. `ano_inicio` = `dt_projeto` >
`dt_assinat` > `dt_documen` (proxy, sinalizado em `ano_inicio_fonte`); datas sentinela (2000-12-31,
2001-01-01) e anos fora de 1990-2026 viram nulo.

## Desvio em relação ao desenho do repositório

O desenho prevê um GeoPackage por UF. Para o Recooperar (1.363 polígonos, ~100 mil ha) um único
GeoPackage basta; a divisão por UF fica na tabela longa (`T1_areas_uf_bioma.csv`) e em `uf_principal`.
Classes grandes (CAR, VS) seguirão o desenho por UF.

## Conferências (`T1_conferencias.csv`)

Área líquida = área da união; sobreposição entre líquidos ~ 0; área inteira = soma das células
UF x bioma; VS do atributo = VS recalculada; VS líquida <= VS soma; sem UF principal ausente; sem
geometria líquida inválida.
