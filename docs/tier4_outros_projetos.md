# Classe 4: Outros projetos (embargos PANGIA e ICMBio)

Quarta classe da hierarquia do Anexo 1, Camada 2 (projetos). A classe reúne projetos do MMA e de outros órgãos. Em 2026 tem duas
fontes:

- **Áreas embargadas do IBAMA (PANGIA, 20/09/2026)**: diferente das classes 1 e 3, **só entra a vegetação secundária (VS) dentro do
  embargo**, nunca a extensão total do polígono (decisão de 20/09/2026). Seções "Entradas" a "Dados pessoais" abaixo.
- **Projetos do ICMBio (GEF Terrestre e Restauração Ecológica)**, incluídos em 14/10/2026 pela **área total dos polígonos**, sem
  cruzamento com a VS. Seção [ICMBio](#icmbio-incluído-em-14102026).

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

## Resultados (dados de 20/09/2026, só PANGIA; com o ICMBio ver a seção seguinte)

| | vs22q | vs2224q |
|---|---|---|
| Embargos com VS | 23.084 | 21.574 |
| VS nos embargos, soma (ha) | 405.829,6 | 396.074,3 |
| Sobreposta ao Recooperar (ha) | 3.229,2 | 3.573,1 |
| Sobreposta ao SICAR-regularização (ha) | 8,5 | 4,4 |
| Sobreposta entre embargos (ha) | 45.758,2 | 43.924,9 |
| **Área líquida da classe 4 (ha)** | **356.833,7** | **348.571,8** |
| Acumulado das classes 1, 3 e 4 (ha) | 497.446,2 | 489.184,4 |

## ICMBio (incluído em 14/10/2026)

### Seleção dos polígonos (decisões de 14/10/2026)

| Item | Regra |
|---|---|
| Arquivos e camadas | `ICMBio_Projetos_GEF_Terrestre_2026` (as 7 camadas) e, de `ICMBio_Projetos_Restauracao_2026`, só a camada **Restauração Ecológica** (Áreas Degradadas e Embargos > 5 ha ficam fora) |
| Área | total do polígono, sem cruzamento com a VS: a mesma geometria nas duas versões da VS |
| Sobreposição dentro do GEF | em cada grupo de polígonos sobrepostos fica um só, o maior; entre cópias idênticas, o da camada `_ORR` |
| Sobreposição dentro da Restauração Ecológica | mesma regra (fica o maior; sobreposição > 0,01 ha) |
| Entre os dois arquivos | fica o GEF; a Restauração Ecológica é recortada por ele |

| | Polígonos | Área (ha) |
|---|---:|---:|
| GEF Terrestre, após a seleção | 602 | 4.588,5 |
| Restauração Ecológica, após a seleção interna | 3.190 | perda de 496,8 ha nas sobreposições |
| Restauração Ecológica, após o recorte pelo GEF (137 removidos, 40 recortados) | 3.053 | 33.430,6 |
| **Total do insumo `Insumos/IN_ICMBio_2026.gpkg`** | **3.655** | **38.019,1** |

As planilhas de validação da seleção (`ICMBio_Validacao_Sobreposicoes.gpkg` e `.xlsx`) estão em `Computo_Planaveg_2026\Validacao_ICMBio`.

### Inclusão incremental (`incluir_icmbio_classe4.py`)

O cômputo não foi refeito. Cada classe k > 4 já é a sua fonte menos as classes 1 a k-1; sendo Δ a parte do ICMBio ainda fora das
classes 1, 3 e 4, a nova classe k é a classe k atual menos Δ, o mesmo resultado de recalcular tudo. O script, por versão da VS:

1. calcula Δ = ICMBio - (classes 1, 3 e 4);
2. acrescenta Δ à classe 4 (`P2_OUTROS_PROJETOS_<versão>`, peças `ICMBIO-nnnnn`) e grava `P2_OUTROS_PROJETOS_ICMBIO_poligonos`;
3. subtrai Δ das classes 5 a 11 (camadas nacionais e `_por_uf`), alterando só as feições que tocam Δ;
4. relê as feições alteradas e confere que a interseção restante com Δ é zero.

| Versão da VS | vs22q | vs2224q |
|---|---:|---:|
| ICMBio já coberto pelas classes 1, 3 e 4 (ha) | 761,6 | 756,0 |
| **Δ acrescentado à classe 4 (ha)** | **37.257,5** | **37.263,1** |
| Retirado da classe 5, OR (ha) | 28.196,1 | 28.202,3 |
| Retirado da classe 7, UC (ha) | 811,1 | 803,0 |
| Retirado da classe 6, TI (ha) | 48,8 | 46,6 |
| Retirado das classes 8 a 11 (ha) | 0,3 | 0,3 |
| **Efeito no total do cômputo (ha)** | **+8.201,2** | **+8.210,9** |
| **Classe 4, PANGIA + ICMBio, na v0.9.0 (ha, campo `computo`)** | **394.091,2** | **385.834,9** |

A sobreposição com o OR vem das camadas do GEF com "ORR" no nome, que são os mesmos projetos do Observatório: como a classe 4
precede a 5, essa área passou a contar como ICMBio. Interseção residual depois da gravação: 0 em todas as camadas. O reporte final
(`Reporte_Final/`) foi regerado depois da inclusão.

## Efeito do MonitoRAD (classe 2, incluído em 20/10/2026)

O MonitoRAD precede a classe 4 e 1.170 dos seus 1.793 embargos também estão no cadastro PANGIA. Na inclusão incremental
(`docs/tier2_monitorad.md`) saíram da classe 4 57.109,8 ha (vs22q) e 69.015,0 ha (vs2224q), todos da parte PANGIA; o ICMBio
não muda. Classe 4 final (v1.0.0, campo `computo`): **336.981,3 ha** (vs22q) e **316.819,9 ha** (vs2224q), dos quais PANGIA
299.723,9 / 279.556,8 ha, GEF Terrestre 4.588,5 ha e Restauração Ecológica 32.669,0 / 32.674,5 ha.

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
