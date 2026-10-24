# Metodologia do cômputo Planaveg 2026

Este documento resume, para fins de implementação, a metodologia do Relatório Técnico
*Metodologia de Monitoramento Geoespacial e Reporte de Áreas em Processo de Recuperação da Vegetação
Nativa do Planaveg* (MMA / Secretaria-Executiva da Conaveg, setembro de 2026). O relatório é a
referência normativa; em caso de dúvida, vale o texto dele.

## 1. Objetivo

Estimar as áreas em processo de recuperação da vegetação nativa no Brasil para o reporte da meta
nacional do Planaveg 2025-2028 (12 milhões de hectares até 2030), consolidando fontes diferentes,
sem dupla contagem, e com base para o reporte de metas internacionais (KMGBF Meta 2, UNCCD, UNFCCC).

## 2. Estrutura do Sinaveg

O Sinaveg (Sistema Nacional de Monitoramento Geoespacial e Reporte de Áreas em Processo de
Recuperação da Vegetação Nativa) tem dois componentes: entrada de dados (camadas geoespaciais e bases
complementares) e saída de dados (estimativas de área).

- **Camada 1 - vegetação secundária (VS):** áreas em regeneração identificadas por sensoriamento
  remoto (TerraClass/INPE), qualificadas por parâmetros de elegibilidade.
- **Camada 2 - projetos de recuperação:** áreas de projetos com intencionalidade de recuperação,
  compulsórios ou voluntários (Recooperar, MonitoRAD, SICAR, Observatório da Restauração, outros).
- **Bases complementares:** FUNAI, INCRA, IBGE, SICAR, ProManguezal.

**Saídas:** (I) Áreas com Vegetação Secundária Legalmente Protegida; (II) Áreas de Projetos de
Recuperação da Vegetação Nativa.

## 3. Critérios-chave

- **Governança** (Camada 1): a VS só conta se estiver em área legalmente protegida por instrumento de
  gestão territorial e de acompanhamento e responsabilização, público ou privado, que viabilize sua
  permanência.
- **Intencionalidade** (Camada 2): existe projeto que fundamenta uma intervenção humana planejada de
  recuperação.

## 4. Camada 1 - parâmetros de elegibilidade (seção 4.1.1)

- Unidades de Conservação do CNUC (Lei 9.985/2000). Nas APAs, só as áreas públicas; as áreas privadas
  seguem o regime dos imóveis rurais.
- Terras Indígenas do CNTI nas fases delimitada, declarada, homologada e regularizada.
- Manguezais (APP em toda a extensão, Lei 12.651/2012, art. 4º, VII), pelo mapeamento oficial do
  ProManguezal.
- APP, AUR e RL do SICAR nas condições: analisado aguardando regularização; analisado em conformidade
  (equivale a "analisado, sem pendência"); analisado em conformidade com ativos ambientais; analisado
  em regularização ambiental; e "Aguardando análise", "Em análise" e "Aguardando retificação", desde
  que em conformidade com a base fundiária do INCRA (Anexo 4).

## 5. Camada 2 - integração de projetos (seção 4.2)

- **Recooperar (IBAMA):** licenciamento (todas as áreas de LAC); reparação por danos (status a partir
  de "projeto protocolado"); embargos (status "em recuperação" ou "recuperada").
- **MonitoRAD (IBAMA):** apenas clusters com indícios de recuperação por NDVI. *No cômputo 2026:* polígonos
  "Com indício de recuperação" da camada `MonitoRAD_ANALISE` (2.578 embargos da Amazônia Legal), pela **área total
  do polígono**, sem cruzamento com a VS (decisões de 20/10/2026). Ver `docs/tier2_monitorad.md`.
- **SICAR:** área a recuperar dos imóveis "Analisado, em regularização ambiental", pois há instrumento
  jurídico de compromisso com a recuperação.
- **Observatório da Restauração:** polígonos no formato "público".
  *No cômputo 2026:* ORR 2026 em nível de projeto (86.281 polígonos, todos com privacidade "Público", os 6 biomas),
  adotado em 24/09/2026 no lugar do ORR 2025 (4 polígonos dissolvidos por bioma). Entra pela **área total dos polígonos**,
  com ou sem VS (decisão de 21/09/2026), sem filtro de status; a VS fica como atributo. Ver `docs/tier5_or.md`.
- **Outros projetos:** MMA e demais órgãos, com polígono, extensão e ano de implantação (Anexo 3).
  *No cômputo 2026:* projetos do ICMBio (GEF Terrestre e Restauração Ecológica) e áreas de restauração da FUNBIO
  (5 camadas, desde 23/10/2026), pela área total dos polígonos. Os embargos PANGIA entraram até a v1.0.0 (só a VS
  dentro do embargo) e saíram da hierarquia em 21/10/2026. Ver `docs/tier4_outros_projetos.md`.

Os projetos entram no cômputo mesmo sem VS detectável.

## 6. Tratamento de sobreposições (seção 4.3 e Anexo 1)

Aplica-se a hierarquia descrita em [hierarquia_anexo1.md](hierarquia_anexo1.md): projetos primeiro
(Recooperar, MonitoRAD, SICAR-regularização, outros projetos, OR), depois VS legalmente protegida
(TI, UC, manguezais, APP, AUR, RL). Uma área que é VS e projeto conta uma vez, como projeto. Ao final,
removem-se as áreas sobrepostas a Florestas Públicas Não Destinadas, por insegurança de reporte
enquanto não tiverem destinação definida.

## 7. Desagregação pelos arranjos de implementação (Anexo 2, Figura 4)

| Arranjo | Meta até 2030 | Critério espacial |
|---|---|---|
| Áreas públicas (UCs, TIs e outros territórios coletivos) | 2 Mha | UCs, TIs, manguezais em áreas públicas |
| APP, RL e AUR | 9 Mha | CAR (APP, RL, AUR) |
| Áreas rurais de baixa produtividade | 1 Mha | Fora de áreas públicas e de APP/RL/AUR; projetos não classificados como embargo, LAC ou reparação |
| Recuperação não incluída nos anteriores | - | Projetos em imóveis rurais fora de APP/RL/AUR e das áreas de baixa produtividade |

Os totais devem também poder ser desagregados por UF, bioma, categoria fundiária (assentamentos,
territórios quilombolas, TI, UC, CAR) e limites administrativos.

## 8. Conformidade CAR x INCRA (Anexo 4)

A verificação de coerência dos imóveis do CAR com a base fundiária do INCRA (SIGEF e SNCI) é feita pelo
repositório [analise_conformidade_sicar-incra](https://github.com/Geconsult-code/analise_conformidade_sicar-incra).
O cruzamento da VS com APP/RL/AUR dos imóveis selecionados vem do repositório
`cruzamento_vegetacao-secundaria`. Este repositório **consome** esses resultados.

## 9. Decisões específicas do cômputo 2026

- MonitoRAD (decisões de 20/10/2026): entram os polígonos "Com indício de recuperação", qualquer que seja o `value`, recortados
  pelo polígono do próprio embargo (o que fica fora não é usado); onde embargos se sobrepõem fica o mais antigo (`dat_embarg`).
  Incluído de forma incremental (`incluir_monitorad_classe2.py`): a parte livre da classe 1 entra na classe 2 e sai das classes 3 a 11.
- Embargos PANGIA: entraram na classe 4 da v0.4.0 à v1.0.0 só pela interseção com a VS qualificada (50.674 polígonos
  reais, sem registros sem geometria e sem pontos). **Retirados da hierarquia em 21/10/2026** (v1.1.0): as classes 4 a 11
  foram recalculadas e a área passou às classes seguintes onde também é OR, TI, UC ou CAR.
- ICMBio (decisões de 14/10/2026): entram na classe 4 pela área total, sem cruzamento com a VS, o GEF Terrestre (7 camadas) e a
  camada Restauração Ecológica. Em cada grupo de polígonos sobrepostos fica o maior (nas cópias, o da camada `_ORR`); entre os dois
  arquivos fica o GEF. Incluído de forma incremental em 14/10/2026; desde a v1.1.0 a classe 4 é calculada direto do insumo.
- FUNBIO (decisões de 23/10/2026): entram na classe 4 pela área total as 5 camadas de `FUNBIO_Areas_Restauracao_20261023`, inclusive
  os projetos com término após 2026; na sobreposição interna fica o polígono maior; na sobreposição com o ICMBio, fica o ICMBio.
  Incluída de forma incremental (`incluir_funbio_classe4.py`): a parte livre das classes 1 a 4 entra na classe 4 e sai das 5 a 11.
- Classes de governança (6 TI, 7 UC, 8 Manguezal; `docs/tier6_8_governanca_publica.md`): a área da classe é a VS qualificada dentro do território, por versão da VS.
  TI: fases delimitada, declarada, homologada e regularizada. UC: só o limite da UC (a zona de amortecimento não é UC); nas APAs entra só a área pública
  (APA menos os imóveis do CAR). Manguezal: toda a VS do ProManguezal.
- Classes do CAR (9 APP, 10 AUR, 11 RL; `docs/tier9_11_car.md`): a área da classe é a VS qualificada dentro da APP, da AUR ou da RL dos imóveis selecionados.
  Os imóveis Habilitados precedem os Analisados e os Não analisados em qualquer classe; dentro de cada grupo a classe manda (APP > AUR > RL). Entre Analisados e Não analisados a
  categoria desempata dentro da classe (Analisados > Não analisados) e, na mesma categoria, vence o menor `cod_imovel` (o cruzamento não traz a data de cadastro).
  As peças do cruzamento se sobrepõem dentro do mesmo imóvel (temas de APP sobrepostos e duplicatas): antes da precedência elas são unidas por imóvel.
- Áreas calculadas de forma geodésica (elipsoide GRS80), em EPSG:4674, como no restante do projeto.
- Itens ainda pendentes de decisão estão em `PENDENCIAS` no arquivo `config_computo.py`.

## 10. Produto final do cômputo 2026

A hierarquia é aplicada classe a classe (passos 2, 3 e 3b): cada classe já é gravada com a área líquida,
sem as classes de maior prioridade. O script `gerar_geopackages_finais.py` dissolve cada classe por UF x
bioma (classes de projeto são antes fragmentadas nas células UF x bioma) e grava o reporte em
`Computo_Planaveg_2026/Reporte_Final/`, no padrão do cômputo 2025, com o atributo de UF e as classes do
CAR separadas em Habilitados, Analisados e Não analisados (decisões de 28/09/2026). São geradas as duas
versões da VS (2022 qualificada e 2022-2024 qualificada).

Totais (campo `computo`, área geodésica líquida de cada classe): **8.610.074,0 ha** com a VS 2022 qualificada e
**8.834.315,2 ha** com a VS 2022-2024 qualificada (v1.2.0: classe 4 com ICMBio e FUNBIO, sem os embargos PANGIA). Versões
anteriores: 8.601.569,5 / 8.825.805,5 ha (v1.1.0, sem PANGIA), 8.824.118,4 / 9.026.415,6 ha (v1.0.0, com MonitoRAD e PANGIA),
8.596.928,3 / 8.811.361,7 ha (v0.9.0) e 8.588.727,1 / 8.803.150,8 ha (v0.8.0). Desde a v1.1.0 as classes 1 a 5 não dependem
da VS e são iguais nas duas versões; a diferença entre as versões vem só das classes de VS (6 a 11).

## 11. Pendências do cômputo 2026

- **Florestas Públicas Não Destinadas (CNFP):** fonte do dado não definida; no reporte, `area_wit_fpnd = 0`
  e `computo = area_tnc`.
- **Arranjos de implementação (seção 7):** passos 5 e 6 ainda não implementados.
- Demais itens em `PENDENCIAS`, no `config_computo.py`.

## 12. Uso posterior

O Total do reporte é a entrada do repositório
[visualizacao_categoria-fundiaria](https://github.com/Geconsult-code/visualizacao_categoria-fundiaria),
que fragmenta o cômputo por município e bacia e acrescenta atributos de filtro (categorias de CAR,
APP/RL/AUR por categoria, componentes de projeto, UC/APA/RPPN e esferas, TI, assentamentos e
quilombolas); desde a v1.2.0 o MonitoRAD é um componente próprio de PROJ. Na versão de 16/10/2026 (com o ICMBio) a área de cada classe foi conservada com diferença
máxima de 0,002 ha, todas as classes têm 100% da área com a flag própria e a matriz de preenchimento dos
atributos não tem nenhuma violação.
