# Classe 4: Outros projetos (ICMBio e FUNBIO)

Quarta classe da hierarquia do Anexo 1, Camada 2 (projetos). A classe reúne projetos do MMA e de outros órgãos. Desde a v1.2.0
(23/10/2026) tem duas fontes, ambas pela **área total dos polígonos**, sem cruzamento com a VS (por isso a classe é igual nas duas
versões da VS):

- **Projetos do ICMBio** (GEF Terrestre e Restauração Ecológica), desde 14/10/2026. Seção [ICMBio](#icmbio-incluído-em-14102026).
- **Áreas de restauração da FUNBIO** (5 camadas), desde 23/10/2026. Seção [FUNBIO](#funbio-incluída-em-23102026).

A classe subtrai as classes 1 (Recooperar), 2 (MonitoRAD) e 3 (SICAR-regularização). Na sobreposição entre as fontes, o ICMBio fica
com a área (decisão de 23/10/2026). É calculada por `2_camada2_projetos.py OUTROS_PROJETOS` (função `classe_outros_projetos_icmbio`),
com as fontes e a ordem de precedência em `config_computo.FONTES_OUTROS_PROJETOS`.

Os **embargos PANGIA** (áreas embargadas do IBAMA, só a VS dentro do embargo) foram a fonte da classe 4 da v0.4.0 à v1.0.0 e **saíram da
hierarquia em 21/10/2026** (v1.1.0); a documentação está no [histórico](#histórico-embargos-pangia-v040-a-v100) abaixo.

## Classe 4 atual (v1.2.0)

Saída: `Tier4_Outros_Projetos/P2_Outros_Projetos_2026.gpkg` (até a v1.0.0, `P2_Outros_Projetos_PANGIA_20260920.gpkg`):
`P2_OUTROS_PROJETOS_poligonos` (polígonos inteiros do ICMBio e da FUNBIO com as sobreposições e a área líquida) e
`P2_OUTROS_PROJETOS_vs22q` / `_vs2224q` (polígonos líquidos, iguais nas duas versões; `id_proj` `ICMBIO-nnnnn` ou `FUNBIO-nnnnn`,
`fonte`, `projeto`, UF e bioma principais). Tabelas `T4_resumo.csv` (por fonte), `T4_resumo_uf_bioma.csv`, `T4_areas_uf_bioma.csv`,
`T4_conferencias.csv` e `T4_acumulado_classes_1_3_4.csv` (o nome segue o da v0.4.0; desde a v1.1.0 inclui a classe 2).

| Fonte | Polígonos | Área inteira (ha) | Sobreposta às classes 1 a 3 (ha) | Sobreposta ao ICMBio (ha) | **Área líquida (ha)** |
|---|---:|---:|---:|---:|---:|
| ICMBio GEF Terrestre | 602 | 4.588,5 | 0,0 | - | **4.588,5** |
| ICMBio Restauração Ecológica | 3.053 | 33.430,6 | 723,5 | - | **32.707,1** |
| FUNBIO (5 camadas) | 2.417 | 14.866,6 | 9,6 | 4.721,3 | **10.135,8** |
| **Classe 4** | **6.072** | **52.885,7** | **733,1** | **4.721,3** | **47.431,4** |

Conferências (`T4_conferencias.csv`): identidade de área por polígono; líquida = união da classe 4 - união das classes 1, 2 e 3
(cálculo independente); sobreposição zero entre os líquidos e com as classes 1 a 3; células UF x bioma somam a área de cada polígono;
nenhum polígono com área líquida sem UF; geometrias válidas. Todas ok.

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

### Inclusão incremental (`incluir_icmbio_classe4.py`, v0.9.0; registro histórico)

Desde a v1.1.0 a classe 4 é calculada diretamente a partir de `IN_ICMBio_2026` (e da FUNBIO); os números abaixo são os da inclusão
incremental sobre a classe 4 com PANGIA.

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

## FUNBIO (incluída em 23/10/2026)

### Entrada e decisões (23/10/2026)

`FUNBIO_Areas_Restauracao_20261023.gpkg` (EPSG:4674, geometrias 3D com medida, 2.449 polígonos, 15.054,7 ha):

| Camada | Programa | Polígonos | Área (ha) | Término |
|---|---|---:|---:|---|
| RockRio | RIR - Amazonas Live (MT) | 83 | 302,5 | 2022 |
| MataAtlantica | Projeto Mata Atlântica III (BA, PR, RJ, SP) | 344 | 2.567,7 | 2023 |
| GEF_Terrestre | GEF Terrestre (Caatinga, Pampa, Pantanal) | 582 | 4.488,1 | 2023-2025 |
| FlorestaViva | Floresta Viva (19 UFs) | 1.434 | 7.661,8 | 2026-2028 |
| AMLD | ExxonMobil-AMLD (RJ) | 6 | 34,7 | 2027 |

| Item | Regra |
|---|---|
| Área | total do polígono, sem cruzamento com a VS (como o ICMBio) |
| Projetos em execução | entram todos, inclusive os com término previsto depois de 2026 (1.036 do Floresta Viva e os 6 do AMLD) |
| Sobreposição dentro da FUNBIO | fica o polígono maior (188,1 ha em 65 pares; 32 polígonos saem inteiros) |
| Sobreposição com o ICMBio | fica o ICMBio (4.730,8 ha; quase todo o GEF Terrestre da FUNBIO repete as camadas "_Funbio" e "_ORR" do GEF Terrestre do ICMBio) |
| Área de referência | a geodésica da geometria; o campo `ÁREA_HA` difere em alguns polígonos (RockRio +3%) |

`consolidar_funbio.py` grava `Insumos/IN_FUNBIO_2026.gpkg` (camada `IN_FUNBIO`, 2.417 polígonos, 14.866,6 ha, sem sobreposição interna;
atributos padronizados, porque os nomes de campo variam entre as camadas). A análise de sobreposições com as classes 1 a 5
(`FUNBIO_Validacao_Sobreposicoes.xlsx`) está em `Computo_Planaveg_2026\Validacao_FUNBIO`.

### Inclusão incremental (`incluir_funbio_classe4.py`)

A classe 4 é refeita com ICMBio e FUNBIO (o ICMBio sai igual, porque precede a FUNBIO) e a FUNBIO livre (Δ, 10.135,8 ha) é subtraída das
classes 5 a 11, camadas nacionais e `_por_uf`, com a mesma rotina de subtração e conferência da inclusão do ICMBio:

| Versão da VS | vs22q | vs2224q |
|---|---:|---:|
| **Δ acrescentado à classe 4 (ha)** | **10.135,8** | **10.135,8** |
| Retirado da classe 5, OR (ha) | 1.378,8 | 1.378,8 |
| Retirado da classe 7, UC (ha) | 202,9 | 177,5 |
| Retirado da classe 9, APP (ha) | 25,1 | 39,3 |
| Retirado da classe 11, RL (ha) | 23,8 | 29,6 |
| Retirado das classes 6, 8 e 10 (ha) | 0,7 | 0,8 |
| **Efeito no total do cômputo (ha)** | **+8.504,5** | **+8.509,8** |

Interseção residual depois da gravação: 0 nas 174 camadas alteradas. O reporte final foi regerado depois da inclusão.

## Retirada dos embargos PANGIA (21/10/2026, v1.1.0)

Decisão do usuário: os embargos PANGIA não entram mais na hierarquia. As classes 4 a 11 foram recalculadas pelos scripts normais
(classe 4 só com o ICMBio, depois classes 5, 6 a 8 e 9 a 11), sem incremental: a área que era do PANGIA passa às classes seguintes onde é
também OR, TI, UC ou APP/AUR/RL. Classe 4: de 336.981,3 / 316.819,9 ha para 37.295,6 ha (vs22q / vs2224q); classes 5 a 11:
+77.136,7 / +78.914,2 ha; total do cômputo: -222.549,0 / -200.610,1 ha (de 8.824.118,4 / 9.026.415,6 para 8.601.569,5 / 8.825.805,5 ha).
A classe 4 antiga ficou em `D:\PLANAVEG_TEMP\_anterior_v1.0\` e no backup (zip da v1.0). O insumo `IN_Embargos_PANGIA_20260920*` continua
sendo gerado pelo passo 1, mas não é lido pela hierarquia.

# Histórico: embargos PANGIA (v0.4.0 a v1.0.0)

As seções abaixo descrevem a classe 4 enquanto ela teve os embargos PANGIA (retirados em 21/10/2026).

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

## Resultados (dados de 20/09/2026, só PANGIA)

| | vs22q | vs2224q |
|---|---|---|
| Embargos com VS | 23.084 | 21.574 |
| VS nos embargos, soma (ha) | 405.829,6 | 396.074,3 |
| Sobreposta ao Recooperar (ha) | 3.229,2 | 3.573,1 |
| Sobreposta ao SICAR-regularização (ha) | 8,5 | 4,4 |
| Sobreposta entre embargos (ha) | 45.758,2 | 43.924,9 |
| **Área líquida da classe 4 (ha)** | **356.833,7** | **348.571,8** |
| Acumulado das classes 1, 3 e 4 (ha) | 497.446,2 | 489.184,4 |

## Efeito do MonitoRAD na classe 4 com PANGIA (20/10/2026, v1.0.0)

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
