# Classes 9, 10 e 11 - VS em APP, AUR e RL dos imóveis do CAR (Camada 1, governança)

Passo 3b (`3b_camada1_car.py`, v0.7.0). A área da classe é a **vegetação secundária qualificada dentro da APP, da AUR ou da RL dos imóveis selecionados
do CAR**, sem dupla contagem com as classes de maior prioridade (1, 3, 4, 5, 6, 7 e 8) e entre elas. Duas versões da VS: `vs22q` (2022 qualificada) e
`vs2224q` (2022 qualificada; Amazônia e Cerrado pela 2024 qualificada).

## Entradas

Os cruzamentos já calculados, em `Cruzamento_Espacial_Vegetacao_Secundaria\VS-Cadastro_Ambiental_Rural`: um arquivo por categoria do imóvel (Habilitados,
Analisados, Não analisados) e por versão (`VS_2022_Imoveis_Selecionados_<categoria>_Qualificado.gpkg`, `VS_2024_Imoveis_Selecionados_<categoria>.gpkg`), com as camadas
`VS_APP_<categoria>`, `VS_AUR_<categoria>` e `VS_RL_<categoria>` (`uf`, `cod_imovel`, `tipo`, `bioma`, `ano`, `des_condic`, `area_ha`). São ~2,7 milhões de peças de APP,
10 mil de AUR e 760 mil de RL na 2022 qualificada (2,3 milhões, 7,5 mil e 645 mil na 2024). Cada UF ocupa um bloco contínuo de FIDs; o script lê só o bloco da UF.

`vs2224q` = peças da 2022 qualificada nos biomas que a 2024 não cobre (Caatinga, Mata Atlântica, Pampa, Pantanal) + todas as peças da 2024 (Amazônia e Cerrado). Em toda UF que
tem Amazônia ou Cerrado na 2022 há a 2024 correspondente (verificado).

## Regras

1. **A classe manda; a categoria desempata.** APP (9) > AUR (10) > RL (11), qualquer que seja a categoria do imóvel. Dentro da classe, a sobreposição entre imóveis fica com
   Habilitados > Analisados > Não analisados e, na mesma categoria, com o menor `cod_imovel` (o cruzamento não traz a data de cadastro). *Adotado a confirmar (C1 e C2).*
2. **União por imóvel.** As peças do cruzamento se sobrepõem dentro do mesmo imóvel (temas de APP sobrepostos e duplicatas exatas): no AC, a soma de `area_ha` das peças de APP é
   3,3 vezes a área da união (43.416 ha contra 13.038 ha); na RL e na AUR quase não há sobreposição. Antes de qualquer precedência, as peças de cada imóvel
   (categoria, `cod_imovel`, bioma da VS, ano) são unidas. **Somar `area_ha` do cruzamento superestima a APP.**
3. Cada classe subtrai as classes 1, 3, 4, 5, 6, 7 e 8 (líquidas, na versão da VS; lidas pela caixa da UF) e, na AUR e na RL, as classes do CAR de maior prioridade da mesma UF.
   As APAs entram nas UCs só pela área pública (APA menos o CAR total), de modo que a parte privada delas segue aqui, no regime do imóvel.
4. UF e bioma do IBGE por fragmento (as células UF x bioma do passo 3); o que sair dos limites do IBGE fica como "FORA". `uf_car` guarda a UF do imóvel; `bioma_vs`, o bioma da VS.

## Achado: a união do GEOS descarta área sem avisar

Com peças duplicadas e sobrepostas do mesmo imóvel, `shapely.union_all` (GEOS) devolveu uniões sem 3 ha no AC (4 imóveis; um trecho de 1,4 ha estava dentro de uma peça de 33 ha), **sem lançar erro**.
A conferência independente (união de todas as peças menos as classes anteriores, sem usar a união por imóvel) acusou -3,00 ha e levou ao diagnóstico. A união passou a usar precisão fixa
(grade de 1e-9 grau, ~0,1 mm; `car.uniao_grade`) e é conferida: cada peça deve estar dentro da união do imóvel, e o que faltar é reincorporado (`car.uniao_verificada`; o log informa
"cobertura corrigida em N peças" se isso ocorrer). Com a grade, a cobertura falhou em 0 dos 1.691 imóveis do AC. `geometria.clip_seguro` trata o outro erro
do GEOS que apareceu (anel degenerado no recorte).

## Conferências (por UF, versão e classe; `T9_conferencias.csv`, `T10_...`, `T11_...`)

Identidade de área por imóvel (peças = sobreposição no imóvel + classes anteriores + na classe + líquida); soma dos fragmentos UF x bioma = líquida; área fora dos limites do IBGE;
fragmentos sem UF ou bioma; geometrias inválidas; líquida <= união do imóvel; `area_ha` do arquivo = área geodésica recalculada; sobreposição dos líquidos com as classes anteriores
(cada par recortado pela caixa da parte); sobreposição entre fragmentos líquidos; e a conferência independente (área líquida = união das peças - união das classes anteriores, por
componente conexo). As duas últimas são as pesadas: rodam por padrão com até 200 mil peças na classe (`--conferencia auto`); `--conferencia completa` força e `leve` omite.

## Validação (nuvem, 4 UFs: AC, DF, SE e PR; 220 conferências, todas dentro do limite)

Área (ha) na versão vs22q (peças do arquivo = soma de `area_ha`; união = por imóvel; líquida = depois de subtrair as classes anteriores e a sobreposição entre imóveis):

| Classe | UF | Peças | Soma de `area_ha` | União por imóvel | Líquida |
|---|---|---:|---:|---:|---:|
| 9 APP | AC | 34.258 | 43.416,4 | 13.037,9 | 12.790,2 |
| 9 APP | DF | 4.128 | 2.108,3 | 643,0 | 579,3 |
| 9 APP | PR | 111.063 | 87.411,3 | 27.560,4 | 27.107,8 |
| 9 APP | SE | 1.710 | 1.565,1 | 462,6 | 458,4 |
| 10 AUR | DF, PR, SE | 225 | 599,0 | 599,0 | 523,3 |
| 11 RL | AC | 8.643 | 49.029,4 | 49.023,1 | 41.567,4 |
| 11 RL | DF | 727 | 1.372,6 | 1.372,5 | 1.071,6 |
| 11 RL | PR | 18.448 | 65.050,6 | 65.050,2 | 47.600,5 |
| 11 RL | SE | 895 | 3.963,6 | 3.963,6 | 3.690,5 |

A consolidação foi testada nas quatro UFs (GeoPackages, resumos, conferências e acumulados). Tempo de execução na nuvem (2 núcleos): AC ~4 min por versão, PR (129 mil peças) ~14 min por versão.
Estimativa para o Brasil (3,5 milhões de peças por versão): algumas horas por versão, de preferência em dois ou três terminais com UFs diferentes; PA, MT, GO e MG (400 a 600 mil peças) são as mais pesadas.
A memória não foi medida nas UFs grandes (no PR, o processo chegou a ~2,3 GB; espere bem mais em PA, MT, GO e MG).

## Saídas (ver `docs/dicionario_dados.md`)

`Tier9_APP\P1_APP_CAR_Maio2026.gpkg`, `Tier10_AUR\P1_AUR_CAR_Maio2026.gpkg` e `Tier11_RL\P1_RL_CAR_Maio2026.gpkg` (camadas `P1_<classe>_vs22q` e `_vs2224q`), `T9`, `T10` e `T11`
(`_resumo`, `_resumo_uf`, `_resumo_uf_bioma`, `_conferencias`) e os acumulados `T9_acumulado_classes_1_3_4_5_6_7_8_9.csv`, `T10_...10.csv` e `T11_...11.csv`.

## Limitações e pendências

- C1 e C2 (acima) a confirmar. A ordem de imóveis da mesma categoria por `cod_imovel` só muda em qual imóvel fica a área sobreposta, não o total.
- O cruzamento traz só a VS já intersectada com APP/AUR/RL dos imóveis selecionados: imóveis fora da seleção (cancelados, não elegíveis) não entram, como definido nas etapas anteriores.
- O cômputo dos totais nacionais (soma das classes, Florestas Públicas Não Destinadas e arranjos) fica para os passos 4 a 7.
