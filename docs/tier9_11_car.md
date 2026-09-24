# Classes 9, 10 e 11 - VS em APP, AUR e RL dos imóveis do CAR (Camada 1, governança)

Passo 3b (`3b_camada1_car.py`, v0.7.2). A área da classe é a **vegetação secundária qualificada dentro da APP, da AUR ou da RL dos imóveis selecionados
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

1. **Habilitados primeiro; depois, a classe manda e a categoria desempata.** Os imóveis Habilitados precedem os Analisados e os Não analisados em qualquer classe (a RL de um
   Habilitado vence a APP de um Não analisado). Dentro de cada grupo, APP (9) > AUR (10) > RL (11). Entre Analisados e Não analisados a categoria desempata dentro da classe
   (Analisados > Não analisados) e, na mesma categoria, a sobreposição entre imóveis fica com o menor `cod_imovel` (o cruzamento não traz a data de cadastro).
   *Confirmado em 21/09/2026 (C1 e C2).* O cálculo segue seis "blocos", nesta ordem: APP, AUR e RL dos Habilitados (`APP_H`, `AUR_H`, `RL_H`); APP, AUR e RL dos Analisados +
   Não analisados (`APP_AN`, `AUR_AN`, `RL_AN`). Os resultados são reunidos por classe (9, 10 e 11) e a categoria do imóvel continua em cada parte.
2. **União por imóvel.** As peças do cruzamento se sobrepõem dentro do mesmo imóvel (temas de APP sobrepostos e duplicatas exatas): no AC, a soma de `area_ha` das peças de APP é
   3,3 vezes a área da união (43.416 ha contra 13.038 ha); na RL e na AUR quase não há sobreposição. Antes de qualquer precedência, as peças de cada imóvel
   (categoria, `cod_imovel`, bioma da VS, ano) são unidas. **Somar `area_ha` do cruzamento superestima a APP.**
3. Cada bloco subtrai as classes 1, 3, 4, 5, 6, 7 e 8 (líquidas, na versão da VS; lidas pela caixa da UF) e os blocos do CAR anteriores da mesma UF (colunas
   `sobreposta_app_h_ha`, `sobreposta_aur_h_ha`, `sobreposta_rl_h_ha`, `sobreposta_app_an_ha`, `sobreposta_aur_an_ha`); `sobreposta_na_classe_ha` é a sobreposição entre imóveis do mesmo bloco.
   As APAs entram nas UCs só pela área pública (APA menos o CAR total), de modo que a parte privada delas segue aqui, no regime do imóvel.
4. UF e bioma do IBGE por fragmento (as células UF x bioma do passo 3); o que sair dos limites do IBGE fica como "FORA". `uf_car` guarda a UF do imóvel; `bioma_vs`, o bioma da VS.

## Achado: a união do GEOS descarta área sem avisar

Com peças duplicadas e sobrepostas do mesmo imóvel, `shapely.union_all` (GEOS) devolveu uniões sem 3 ha no AC (4 imóveis; um trecho de 1,4 ha estava dentro de uma peça de 33 ha), **sem lançar erro**.
A conferência independente (união de todas as peças menos as classes anteriores, sem usar a união por imóvel) acusou -3,00 ha e levou ao diagnóstico. A união passou a usar precisão fixa
(grade de 1e-9 grau, ~0,1 mm; `car.uniao_grade`) e é conferida: cada peça deve estar dentro da união do imóvel, e o que faltar é reincorporado (`car.uniao_verificada`; o log informa
"cobertura corrigida em N peças" se isso ocorrer). Com a grade, a cobertura falhou em 0 dos 1.691 imóveis do AC. `geometria.clip_seguro` trata o outro erro
do GEOS que apareceu (anel degenerado no recorte).

## Achado: em imóveis com muitas peças sobrepostas, a própria união com grade pode falhar

Na rodada nacional (v0.7.1), GO, MG e PA pararam com `GEOSException` dentro de `car.uniao_grade` ("side location conflict" em GO e MG, "unable
to assign free hole to a shell" em PA) — nos três casos na APP (Habilitados ou Analisados+Não analisados), classes com centenas de milhares de
peças. A união com grade (e a mesma união repetida com `make_valid`) não deu conta de algum imóvel com peças muito sobrepostas nessas UFs; sem um
recurso a mais, o script parava a UF inteira. `car.uniao_grade` agora tenta, em ordem, até funcionar: grade (1e-9°); grade com as peças corrigidas
por `make_valid` (como antes); grade mais grossa (1e-6°, funde vértices quase coincidentes); sem grade (precisão flutuante do GEOS, outro caminho
de código no GEOS); e, como último recurso, união par a par por divisão binária (sempre funciona, pois nunca envolve mais de duas geometrias por
vez). Cada nível além do primeiro é contado e aparece no log ("união robusta em N imóveis"); a conferência de cobertura de `uniao_verificada`
roda do mesmo jeito depois, então um resultado desse caminho é conferido como qualquer outro. Testado com uma falha simulada de `union_all` (todas
as tentativas com grade e sem grade falhando): a união par a par produziu a área correta. Não foi possível reproduzir a peça exata que travava em
GO, MG ou PA na nuvem (arquivos grandes demais para o teste); recomendo rodar essas três UFs de novo e conferir no log se "união robusta" aparece
e se as conferências fecham.

## Achado: um `--refazer` parcial apagava o GeoPackage nacional das outras UFs, sem avisar

A consolidação (`consolidar()`) sempre reconstrói `P1_<classe>_Maio2026.gpkg` a partir dos GeoPackages por UF em `_por_uf` (dentro de
cada pasta Tier9/10/11), e por padrão apagava esses arquivos por UF ao final, para economizar espaço. O marcador de "UF x versão
concluída", porém, não é apagado. Resultado: depois da primeira consolidação nacional (as 27 UFs), um `--refazer` de só algumas UFs
(o conserto de GO, MG e PA para o `GEOSException`, depois RO/SP/TO e BA/MA/MG/MT/PA/RO/SC/SP para a saída inválida do `difference`)
dispara uma nova consolidação automática assim que as UFs recém-refeitas voltam a "prontas" - e essa consolidação tenta reler o
GeoPackage por UF de **todas** as 27 UFs, mas a maioria já tinha sido apagada na consolidação anterior. O código pulava
silenciosamente as UFs sem arquivo, e o `P1_<classe>_Maio2026.gpkg` final ficava só com as UFs da última rodada parcial - visível no
log da rodada de 23-24/09/2026: cada uma das quatro consolidações produziu uma contagem de partes completamente diferente (ex.: RL
vs22q foi de 5.558.650 para 54.382, depois 1.739.729, depois 4.422.144 partes - nem de longe um total nacional estável). As tabelas
(`T9/T10/T11_resumo*.csv`, `_conferencias.csv`, `_acumulado*.csv`, e portanto a planilha de comparação) **não são afetadas**: vêm de
`Tier9_APP/_por_uf`, um diretório único e comum às três classes que nunca é limpo automaticamente, e sempre agrega as 27 UFs a partir
dos CSVs por UF, que persistem entre rodadas.

Corrigido na v0.7.2: `consolidar()` passou a manter os GeoPackages por UF por padrão (`manter_por_uf=True`); apagá-los exige o novo
flag explícito `--limpar-por-uf`. Além disso, se uma UF está marcada como "concluída" mas seu GeoPackage por UF não existe mais, a
consolidação agora lança um erro explícito em vez de pular a UF em silêncio. **Pendência:** os `P1_APP_CAR_Maio2026.gpkg`,
`P1_AUR_CAR_Maio2026.gpkg` e `P1_RL_CAR_Maio2026.gpkg` atuais (gravados na consolidação das 09:14 de 24/09/2026) refletem só as UFs
BA, MA, MG, MT, PA, RO, SC e SP (a última rodada parcial) - não o Brasil inteiro. Reconstruir o GeoPackage nacional completo exige
reprocessar as 27 UFs (os arquivos por UF das demais já foram apagados) e só então consolidar; ficou pendente, a critério do usuário,
dado o custo (a rodada de 23-24/09/2026 já levou quase 24h para bem menos UFs).

## Conferências (por UF, versão, classe e bloco; `T9_conferencias.csv`, `T10_...`, `T11_...`)

Identidade de área por imóvel (peças = sobreposição no imóvel + classes anteriores + na classe + líquida); soma dos fragmentos UF x bioma = líquida; área fora dos limites do IBGE;
fragmentos sem UF ou bioma; geometrias inválidas; líquida <= união do imóvel; `area_ha` do arquivo = área geodésica recalculada; sobreposição dos líquidos com as classes anteriores
(cada par recortado pela caixa da parte); sobreposição entre fragmentos líquidos; e a conferência independente (área líquida = união das peças - união das classes anteriores, por
componente conexo). As duas últimas são as pesadas: rodam por padrão com até 200 mil peças na classe (`--conferencia auto`); `--conferencia completa` força e `leve` omite.

## Validação (nuvem, 4 UFs: AC, DF, SE e PR; 440 conferências nas três classes, todas dentro do limite)

Área (ha) na versão vs22q (peças do arquivo = soma de `area_ha`; união = por imóvel; líquida = depois de subtrair as classes anteriores, os blocos anteriores e a sobreposição entre imóveis):

| Classe | UF | Peças | Soma de `area_ha` | União por imóvel | Líquida |
|---|---|---:|---:|---:|---:|
| 9 APP | AC | 34.258 | 43.416,4 | 13.037,9 | 12.788,8 |
| 9 APP | DF | 4.128 | 2.108,3 | 643,0 | 578,1 |
| 9 APP | PR | 111.063 | 87.411,3 | 27.560,4 | 27.106,9 |
| 9 APP | SE | 1.710 | 1.565,1 | 462,6 | 458,4 |
| 10 AUR | DF, PR, SE | 225 | 599,0 | 599,0 | 523,3 |
| 11 RL | AC | 8.643 | 49.029,4 | 49.023,1 | 41.568,8 |
| 11 RL | DF | 727 | 1.372,6 | 1.372,5 | 1.072,7 |
| 11 RL | PR | 18.448 | 65.050,6 | 65.050,2 | 47.601,5 |
| 11 RL | SE | 895 | 3.963,6 | 3.963,6 | 3.690,6 |

A regra dos Habilitados primeiro só desloca área entre classes e categorias, sem mudar o total de forma relevante (AC, vs22q: APP de 12.790,2 para 12.788,8 ha e RL de 41.567,4 para 41.568,8 ha em relação à regra anterior, em que a classe mandava em todas as categorias). Área líquida por categoria nas quatro UFs (vs22q): APP 5.672,7 (Habilitados), 3.874,8 (Analisados) e 31.384,5 ha
(Não analisados); AUR 6,2, 84,8 e 432,3 ha; RL 12.677,7, 9.193,0 e 72.062,9 ha.

A consolidação foi testada nas quatro UFs (GeoPackages, resumos, conferências e acumulados). Tempo de execução na nuvem (2 núcleos): AC ~4 min por versão, PR (129 mil peças) ~14 min por versão.
Estimativa para o Brasil (3,5 milhões de peças por versão): algumas horas por versão, de preferência em dois ou três terminais com UFs diferentes; PA, MT, GO e MG (400 a 600 mil peças) são as mais pesadas.
A memória não foi medida nas UFs grandes (no PR, o processo chegou a ~2,3 GB; espere bem mais em PA, MT, GO e MG).

## Saídas (ver `docs/dicionario_dados.md`)

`Tier9_APP\P1_APP_CAR_Maio2026.gpkg`, `Tier10_AUR\P1_AUR_CAR_Maio2026.gpkg` e `Tier11_RL\P1_RL_CAR_Maio2026.gpkg` (camadas `P1_<classe>_vs22q` e `_vs2224q`), `T9`, `T10` e `T11`
(`_resumo`, `_resumo_uf`, `_resumo_uf_bioma`, `_conferencias`) e os acumulados `T9_acumulado_classes_1_3_4_5_6_7_8_9.csv`, `T10_...10.csv` e `T11_...11.csv`.

## Limitações e pendências

- A ordem por `cod_imovel` (mesma categoria) só muda em qual imóvel fica a área sobreposta, não o total.
- O cruzamento traz só a VS já intersectada com APP/AUR/RL dos imóveis selecionados: imóveis fora da seleção (cancelados, não elegíveis) não entram, como definido nas etapas anteriores.
- O cômputo dos totais nacionais (soma das classes, Florestas Públicas Não Destinadas e arranjos) fica para os passos 4 a 7.
