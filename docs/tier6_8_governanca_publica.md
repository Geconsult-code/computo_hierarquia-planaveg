# Classes 6 a 8: TI, UC e Manguezal (Camada 1, governança pública)

Sexta a oitava classes da hierarquia do Anexo 1, Camada 1 (VS legalmente protegida). Diferente dos projetos (classes 1, 3 e 5, que contam a área
total do polígono), aqui **a área da classe é a VS qualificada (>= 2 ha) dentro do território**. Cada classe subtrai as de maior prioridade,
uma de cada vez, e a sobreposição entre territórios da própria classe conta uma vez. Como a geometria da classe é a própria VS, há um conjunto
líquido **por versão da VS** (`vs22q`: VS 2022 qualificada; `vs2224q`: Amazônia e Cerrado trocados pela VS 2024 qualificada).

## Entrada

| Arquivo | Uso |
|---|---|
| `Cruzamento_Espacial_Vegetacao_Secundaria\VS-Terras_Indigenas\Terras_Indigenas_FUNAI20260507_x_VegSec_[2022-2024_]qualificado.gpkg` | Peças "VS x TI" (uma por TI x feição de VS), camada `Terras_Indigenas_FUNAI20260507_vegsec`; 42.931 (vs22q) e 44.279 (vs2224q) peças |
| `...\VS-Unidades_Conservacao\Unidades_Conservacao_CNUC20260507_x_VegSec_[2022-2024_]qualificado.gpkg` | Peças "VS x UC", camada `Unidades_Conservacao_CNUC20260507_vegsec`; 157.985 e 163.065 peças |
| `...\VS-Pro_Manguezal\Pro-Manguezal_IBAMA20260508_x_VegSec_[2022-2024_]qualificado.gpkg` | Peças "VS x manguezal", camada `Pro_Manguezal_IBAMA20260508_vegsec`; 3.712 e 3.738 peças |
| `Analise_Territorial_CAR-INCRA_dissolvido\CAR_Brasil_Maio2026_Imovel_Area_Total_dissolvido_UF.gpkg` | CAR total dissolvido por UF (imóveis sem cancelados), só para tirar a área privada das APAs |
| `SIGEF_Publico_em_APA.gpkg`, camada `sigefpublico_em_apa` | 2.760 parcelas de imóveis públicos dentro de APAs (todos os status); recupera como pública a parte do CAR total acima que é, na verdade, pública (desde 24/09/2026) |
| Classes 1, 3, 4 e 5 (passo 2) e, na UC e no Manguezal, as classes 6 e 7 | Camadas líquidas por versão, subtraídas |
| `IBGE_Limite_Estados`, `IBGE_Limite_Biomas` | UF e bioma |

As peças dos cruzamentos já trazem a VS recortada pelo território; o script confere a área gravada (`area_ha`) contra o recálculo geodésico (diferença máxima 0,0000 ha
nas três classes) e repara geometrias (nenhuma inválida nas peças).

## Decisões

| Item | Regra | Situação |
|---|---|---|
| Área da classe | VS qualificada dentro do território; uma versão por VS | Regra do relatório |
| TI: fases | Delimitada, declarada, homologada e regularizada (seção 4.1.1). Ficam de fora "Em estudo" (699 peças, 16,5 mil ha de VS) e "Encaminhada RI" (420 peças, 12,3 mil ha) | Regra do relatório |
| TI: sobreposição entre TIs | A fase mais avançada fica com a área (regularizada > homologada > declarada > delimitada), depois o menor código da TI | **Adotado (T1), a confirmar.** Só muda a fase à qual a área sobreposta é atribuída, não o total |
| UC: elegibilidade | Só o limite da UC (`limite = uc`). O cruzamento traz também a zona de amortecimento (`limite = za`), que não é UC e fica de fora (2.305 peças, 15,8 mil ha de VS em vs22q) | Adotado |
| UC: APAs | Só a área pública: **(APA menos o CAR total) união (SIGEF ∩ APA)**, por UF. A parte em imóvel do CAR fica registrada (`area_privada_ha`), exceto a que o SIGEF marca como imóvel público (recuperada como pública); a VS que continuar privada segue para APP, AUR ou RL (classes 9 a 11) | Decidido (21/09/2026); SIGEF acrescentado em 24/09/2026 |
| UC: sobreposição entre UCs | Proteção integral > uso sustentável; fora da APA > APA; federal > estadual > municipal; a mais antiga (`cria_ano`); menor código CNUC | **Adotado (U1), a confirmar.** Só muda a categoria que fica com a área sobreposta, não o total |
| Manguezal | Toda a VS do ProManguezal (APP em toda a extensão, Art. 4º, VII); sem filtro | Regra do relatório |
| Precedência dentro da classe | Peça a peça, rank único por peça (`_rank` em `computo/governanca.py`) | - |

## Hierarquia (passo 3, `3_camada1_vs_governanca.py`)

1. **Peças elegíveis** (passo 1): VS x território, por versão, com `id_peca`.
2. **Subtração das classes de maior prioridade**, uma de cada vez e na versão da VS (`sobreposta_<classe>_ha`): 1 Recooperar, 3 SICAR-regularização, 4 Outros projetos e 5 OR na TI;
   mais a 6 (TI) na UC; mais a 6 e a 7 no Manguezal. Como só a VS entra, subtrair as camadas líquidas equivale a subtrair os territórios.
3. **Sobreposição entre territórios da classe** (`sobreposta_na_classe_ha`): a área sobreposta fica com o de maior precedência (`liquido_por_precedencia`).
4. `area_liquida_ha` = VS no território - sobreposta às classes anteriores - sobreposta na classe. As partes líquidas são disjuntas entre si e das classes anteriores.
5. **UF e bioma** pelas células UF x bioma do IBGE (`CelulasUFBioma`, calculadas uma vez): a peça inteira numa célula não é recortada; só as que cruzam divisas.
   O que sobra fora dos limites do IBGE vira `FORA` (nenhuma área se perde em silêncio).

Na UC, as **APAs** são tratadas no passo 1 (`computo.governanca.apa_area_publica`): cada peça de APA perde a parte coberta pelo CAR total da UF (`subtrair_grandes`); em seguida, o que foi retirado é
cruzado com a união nacional do `SIGEF_Publico_em_APA.gpkg` (`sigef_publico_uniao`, calculada uma vez) e a parte que cai dentro de um imóvel público do SIGEF volta a ser pública (`uniao_par_robusta`) -
decisão de 24/09/2026, porque uma parcela registrada no CAR dentro de uma APA pode ser, na prática, um imóvel público. O CAR de cada UF é um polígono dissolvido com dezenas ou
centenas de milhares de partes (BA: 565 mil; MG: 60 mil partes e 34 milhões de vértices). Partes com mais de 100 mil vértices (uma parte do CAR do CE tem 3 milhões) são divididas em células de
0,25 grau antes de reparar (`make_valid` numa parte dessas levou mais de 4 minutos; em células, segundos). A área do CAR total reconstituída confere com a gravada no arquivo (`area_ha`) nas UFs conferidas (AC, AP, CE, DF, ES, MG, RR e SE): diferença de 0 a 0,26% (a área do arquivo vem de outro método de cálculo; no MG, 49.861.635 x 49.861.655 ha).
A UC lê o CAR de cada UF uma vez para as duas versões da VS. O SIGEF (2.760 parcelas, todos os status, união nacional 1.776.487,6 ha) é lido e unido uma única vez, não por UF.

## Saídas

Ver `docs/dicionario_dados.md` (seção "Saídas das classes 6 a 8"). Em resumo: `Insumos\IN_<TI|UC|Manguezal>_....gpkg` (peças elegíveis), e em `Tier6_TI`, `Tier7_UC` e `Tier8_Manguezal`
os GeoPackages `P1_...gpkg` com as partes líquidas por versão (`P1_TI_vs22q`, ...) e a tabela de peças, mais `T6_*.csv`, `T7_*.csv` e `T8_*.csv` (resumos, conferências e acumulado das classes já processadas).

## Resultados (validação na nuvem, dados de 21/09/2026 - histórico, anterior ao SIGEF e ao ORR 2026)

**Desatualizado**: os números abaixo são de antes da recuperação SIGEF (item "UC: APAs" em Decisões) e da troca do OR para o ORR 2026 (ver `docs/tier5_or.md`), ambas de 24/09/2026. A recuperação SIGEF
reduz `area_privada_ha` das APAs e aumenta a VS elegível na classe 7; a mudança do OR também desloca `sobreposta_5_ha`. Ainda sem rodada nacional com essas mudanças - os valores abaixo servem só
de referência de magnitude/ordem de grandeza até a próxima rodada completa.

Áreas em hectares (geodésicas, GRS80). "VS elegível" é a VS qualificada dentro do território, depois das regras de elegibilidade (e, nas APAs, da retirada da área privada).

| | TI vs22q | TI vs2224q | UC vs22q | UC vs2224q | Manguezal vs22q | Manguezal vs2224q |
|---|---|---|---|---|---|---|
| Peças elegíveis | 41.812 | 43.143 | 105.822 | 108.087 | 3.711 | 3.737 |
| Territórios | 562 | 558 | 1.734 | 1.735 | n/d (o `Id` do ProManguezal vem zerado) | n/d |
| VS elegível (ha) | 962.890,2 | 1.003.299,1 | 1.433.544,8 | 1.436.374,0 | 38.624,0 | 39.305,3 |
| (-) Sobreposta à classe 1, Recooperar | 188,2 | 218,8 | 4.694,8 | 2.516,3 | 0,0 | 0,0 |
| (-) Sobreposta à classe 3, SICAR-regularização | 2,4 | 0,9 | 8,7 | 8,7 | 0,0 | 0,0 |
| (-) Sobreposta à classe 4, Outros projetos | 15.707,0 | 16.948,7 | 37.502,6 | 38.622,8 | 0,9 | 0,9 |
| (-) Sobreposta à classe 5, OR | 87,9 | 80,4 | 486,8 | 486,8 | 2,6 | 2,6 |
| (-) Sobreposta à classe 6, TI | | | 34.063,6 | 34.821,6 | 9,5 | 9,5 |
| (-) Sobreposta à classe 7, UC | | | | | 22.174,1 | 22.728,0 |
| (-) Sobreposta entre territórios da classe | 6.236,0 | 7.652,9 | 16.933,2 | 17.234,5 | 0,0 | 0,0 |
| **Área líquida da classe (ha)** | **940.668,6** | **978.397,4** | **1.339.855,1** | **1.342.683,4** | **16.436,7** | **16.564,2** |

Por categoria (área líquida, vs22q / vs2224q): TI regularizada 832.892,0 / 861.469,3; declarada 56.965,2 / 62.839,9; delimitada 36.897,3 / 38.587,0; homologada 13.914,1 / 15.501,2.
UC proteção integral 295.603,9 / 293.327,2; uso sustentável fora das APAs 498.758,8 / 491.497,0; APAs (só área pública) 545.492,4 / 557.859,1.

APAs: a VS nas peças de APA é 2.075.580,1 ha (vs22q) e 2.128.849,9 ha (vs2224q); 1.505.374,8 e 1.546.467,5 ha (72,5%) estão em imóveis do CAR e saem da classe 7 (49.854 e 52.693 peças ficam inteiras dentro de imóveis).
Ficam 570.205,3 e 582.382,5 ha na área pública, antes de subtrair as classes 1 a 6.

Por bioma (vs22q; a Amazônia e o Cerrado mudam na vs2224q): TI Amazônia 795.243,3, Cerrado 107.990,3, Caatinga 18.896,5, Mata Atlântica 16.200,8, Pantanal 2.275,3, Pampa 61,8;
UC Amazônia 1.044.912,9, Cerrado 109.859,6, Caatinga 106.961,8, Mata Atlântica 63.970,5, Pantanal 13.550,9, Pampa 555,4; Manguezal Amazônia 15.671,0, Mata Atlântica 554,9, Caatinga 191,5, Cerrado 18,5.
Uns 0,5 (TI), 44 (UC) e 0,8 ha (Manguezal) ficam fora dos limites do IBGE de UF ou bioma (rotulados `FORA`).

Acumulado das classes 1, 3, 4, 5, 6, 7 e 8 (áreas líquidas, sem dupla contagem): 2.841.650,9 ha (vs22q) e 2.874.073,6 ha (vs2224q). As classes 9 a 11 (APP, AUR e RL) e o desconto das Florestas Públicas Não Destinadas ainda não entram.

## Conferências (`T6_conferencias.csv`, `T7_conferencias.csv`, `T8_conferencias.csv`)

Por classe e versão: identidade de área por peça (VS = sobreposta às classes anteriores + na classe + líquida); a soma dos fragmentos UF x bioma é a área líquida; área fora dos limites do IBGE
desprezível; nenhum fragmento sem UF ou bioma; geometrias válidas; **sobreposição zero** entre fragmentos e com as classes anteriores; líquida = (união das peças - união das classes anteriores),
cálculo independente por componente conexo; líquida <= VS no território; APAs: área pública <= VS original. Tolerância por peça: 1e-3 ha ou 1e-6 da área (a diferença entre polígonos de
dezenas de milhares de hectares tem ruído de ~1e-8 da área). Tudo dentro da tolerância, nas duas versões e nas três classes.

Verificação externa (fora dos scripts, no QGIS, sobre as camadas brutas de VS 2022 qualificada): a VS dentro do ProManguezal soma 38.623,994 ha em 3.712 peças e 38.623,994 ha na união
(sem sobreposição entre os polígonos do ProManguezal), igual à soma do passo 1 (38.624,0 ha em 3.711 peças; uma peça micro fica fora).

## Desempenho

Passo 1 (`python 1_preparar_insumos.py ti uc manguezal`): TI e Manguezal, segundos; UC ~40 min, quase todo na etapa das APAs (lê o CAR de cada UF; MG sozinho ~13 min e ~4 GB de memória).
Passo 3 (`python 3_camada1_vs_governanca.py`): TI ~10 min, UC ~23 min, Manguezal ~1 min; a maior parte é a divisão por UF x bioma e as conferências.
A UC pede ~5 GB de memória; o cálculo independente (por componente conexo) foi escrito assim porque uma diferença única entre as uniões do país inteiro estourava a memória.

## Limitações e pendências

- Adotados a confirmar: T1 (sobreposição entre TIs) e U1 (sobreposição entre UCs); só mudam a categoria que fica com a área sobreposta, não o total.
- O `Id` do ProManguezal vem zerado (não identifica polígono); a precedência dentro da classe usa só o identificador da peça de VS (a sobreposição entre os polígonos do ProManguezal é nula).
- As APAs usam o CAR total da versão de maio de 2026 e o SIGEF de setembro de 2026 (todos os status); a área privada retirada e a recuperação SIGEF são as mesmas para as duas versões da VS.
- Os "Resultados" acima são anteriores ao SIGEF e ao ORR 2026 (24/09/2026); pendente uma rodada nacional com as duas mudanças (ver nota na seção Resultados).
- Classes 9 a 11 (APP, AUR, RL do CAR) e ICMBio: próximas etapas.
