# Classe 4: Outros projetos (por ora, embargos PANGIA)

Quarta classe da hierarquia do Anexo 1, Camada 2 (projetos). A classe reúne projetos do MMA e de outros órgãos; em 2026 o
ICMBio ficou fora (adiado) e a única fonte é o cadastro de **áreas embargadas do IBAMA (PANGIA, 20/09/2026)**. Diferente das
classes 1 e 3, **só entra a vegetação secundária (VS) dentro do embargo**, nunca a extensão total do polígono (decisão de 20/09/2026).
A classe subtrai as classes 1 (Recooperar) e 3 (SICAR-regularização) e resolve a sobreposição entre embargos.

## Entradas

| Arquivo | Uso |
|---|---|
| `IBAMA_Areas_Embargadas_PANGIA20260920_Poligonos.gpkg` (50.674 polígonos, EPSG:4674) | embargos; sem campo de situação/status |
| `Cruzamento_Espacial_Vegetacao_Secundaria\VS-Areas_Embargadas\..._PANGIA20260920_x_VegSec_2022_qualificada.gpkg` e `..._2022-2024_qualificada.gpkg` | peças "VS x embargo" (uma por embargo x feição de VS), já calculadas; `idx_embargo` = FID do embargo - 1 |
| `P2_RECOOPERAR` e `P2_CAR_REGULARIZACAO` | classes 1 e 3 (líquidas, disjuntas), subtraídas |

O passo 1 **confere** o cruzamento contra o arquivo de embargos: a chave `num_tad` + `serie_tad` + `seq_tad` de cada peça tem de ser a do embargo
apontado por `idx_embargo`, e cada peça tem de estar dentro do polígono desse embargo (tolerância 0,001 ha no total). Se o arquivo de
embargos for trocado ou reordenado sem refazer o cruzamento, o script para com uma mensagem. As peças com área <= 0,01 m2 saem (19 na
versão 2022, 4 embargos ficam sem VS).

## Decisões

| Item | Regra | Situação |
|---|---|---|
| Papel dos embargos | entram como "Outros projetos" só pela interseção com a VS qualificada | Decidido (20/09/2026) |
| Versões da VS | duas: `vs22q` e `vs2224q` (Amazônia e Cerrado pela VS 2024). **A geometria da classe muda com a versão**, porque a área da classe é a própria VS | Decidido |
| E1 - elegibilidade | o arquivo não tem campo de status: entram todos os 50.674 embargos; o filtro é ter VS dentro | Decidido (21/09/2026) |
| E2 - sobreposição entre embargos | a área fica com o embargo mais antigo (`dat_embarg`), depois o de menor FID; muda só a atribuição, não o total | Decidido (21/09/2026) |
| E3 - saídas por versão | um conjunto de polígonos líquidos por versão (as classes seguintes vão subtrair o da versão que estiverem calculando) | Decidido (21/09/2026) |
| E4 - data do embargo | nenhum filtro pela data do embargo x ano da VS | Decidido (21/09/2026): não filtrar |

## Hierarquia

1. **VS no embargo:** união das peças de cada embargo (`<p>_area_vs_embargo_ha`).
2. **Subtração das classes 1 e 3**, uma de cada vez (`<p>_sobreposta_recooperar_ha`, `<p>_sobreposta_sicar_regularizacao_ha`).
3. **Sobreposição entre embargos:** conta uma vez, no embargo de maior precedência (`<p>_sobreposta_na_classe_ha`).
4. `<p>_area_liquida_ha` = VS no embargo - sobreposta às classes anteriores - sobreposta entre embargos. Os polígonos líquidos são disjuntos
   entre si e das classes 1 e 3 (camadas `P2_OUTROS_PROJETOS_vs22q` e `P2_OUTROS_PROJETOS_vs2224q`). Como a área da classe é VS, área líquida e VS líquida são a mesma coisa.

## Resultados (dados de 20/09/2026)

| | vs22q | vs2224q |
|---|---|---|
| Embargos com VS | 23.084 | 21.574 |
| VS nos embargos, soma (ha) | 405.829,6 | 396.074,3 |
| Sobreposta ao Recooperar (ha) | 3.229,2 | 3.573,1 |
| Sobreposta ao SICAR-regularização (ha) | 8,5 | 4,4 |
| Sobreposta entre embargos (ha) | 45.758,2 | 43.924,9 |
| **Área líquida da classe 4 (ha)** | **356.833,7** | **348.571,8** |
| Acumulado das classes 1, 3 e 4 (ha) | 497.446,2 | 489.184,4 |

## E4 (decidido em 21/09/2026: não filtrar): data do embargo x ano da VS

A VS de 2022 (ou de 2024) existia antes de embargos posteriores; a regeneração não é consequência desses embargos. Na versão vs22q,
73,2 mil ha (20,5%) da área líquida estão em embargos de 2023 em diante (35,6 mil ha em 2023-2024 e 37,7 mil ha em 2025-2026); na vs2224q,
61,6 mil ha (17,7%) em embargos de 2023 em diante (31,1 mil ha de 2025 em diante, posteriores à VS 2024 da Amazônia e do Cerrado). O cômputo
não filtra por data (decisão do usuário em 21/09/2026): todos os polígonos com VS ficam. A coluna `ano_embargo` permanece nas saídas, caso um filtro seja pedido depois.

## Conferências (`T4_conferencias.csv`, por versão)

Identidade de área por embargo; líquida = união da VS nos embargos - união das classes 1 e 3 (cálculo independente); sobreposição zero entre
líquidos e com as classes 1 e 3; células UF x bioma somam a VS do embargo; VS fora do IBGE desprezível; atributo de VS do passo 1 = VS
recalculada; VS toda dentro do polígono do embargo; nenhum embargo sem UF; UF calculada x campo `uf` do embargo (informativo, 0,6% divergem);
geometrias válidas; nenhuma coluna com dado pessoal.

Verificação externa (fora dos scripts, no QGIS, sobre as camadas brutas de VS): em 38 embargos (30 com VS, estratificados por bioma, e 8 sem VS)
a VS dentro do embargo coincide com o cruzamento usado, nas duas versões, com diferença máxima de 1e-6 ha.

## Dados pessoais (LGPD)

O arquivo do PANGIA traz nome e CPF/CNPJ do embargado, nome do imóvel e textos livres. O passo 1 só lê os campos de `CAMPOS_EMBARGO_PANGIA`; as colunas
`nome_embar`, `cpf_cnpj_e`, `nome_imove`, `des_locali`, `des_tad` e `des_infrac` nem chegam a ser carregadas, e há uma verificação automática nas saídas.
Ficam o número do termo (`num_tad`, `serie_tad`, `seq_tad`), a data, o município, a UF e a operação.
