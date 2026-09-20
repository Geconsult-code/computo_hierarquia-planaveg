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
- **MonitoRAD (IBAMA):** apenas clusters com indícios de recuperação por NDVI. *Não entra no cômputo
  2026 (dados ainda não recebidos).*
- **SICAR:** área a recuperar dos imóveis "Analisado, em regularização ambiental", pois há instrumento
  jurídico de compromisso com a recuperação.
- **Observatório da Restauração:** polígonos no formato "público".
- **Outros projetos:** MMA e demais órgãos, com polígono, extensão e ano de implantação (Anexo 3).

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

- MonitoRAD fora do cômputo.
- Embargos PANGIA (20/09/2026): mantidos só os 50.674 polígonos reais; removidos 13.810 registros sem
  geometria e 26.843 pontos (microcírculos), com extensão corrigida.
- Áreas calculadas de forma geodésica (elipsoide GRS80), em EPSG:4674, como no restante do projeto.
- Itens ainda pendentes de decisão estão em `PENDENCIAS` no arquivo `config_computo.py`.
