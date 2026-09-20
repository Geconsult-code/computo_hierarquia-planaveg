# Hierarquia para o tratamento de sobreposições (Anexo 1)

Regra geral: cada classe entra no cômputo **subtraindo** a sobreposição com todas as classes de
ordem menor (maior prioridade). Uma área é contada uma única vez, na classe de maior prioridade.
Fonte: Relatório Técnico MMA/Conaveg (set/2026), Anexo 1 e seção 4.3.

| Ordem | Classe | Camada | Critério-chave | Subtrai sobreposição com |
|---|---|---|---|---|
| 1 | Recooperar (IBAMA) | 2 | Intencionalidade | - |
| 2 | MonitoRAD (IBAMA) | 2 | Intencionalidade | Recooperar (**desativado em 2026**) |
| 3 | SICAR - regularização ambiental (área a recuperar) | 2 | Intencionalidade | Recooperar, MonitoRAD |
| 4 | Outros projetos (MMA e demais órgãos) | 2 | Intencionalidade | Recooperar, MonitoRAD, SICAR-regularização |
| 5 | Observatório da Restauração (público) | 2 | Intencionalidade | classes 1 a 4 |
| 6 | Terras Indígenas (VS) | 1 | Governança | classes 1 a 5 |
| 7 | Unidades de Conservação (VS; APAs = áreas públicas) | 1 | Governança | classes 1 a 6 |
| 8 | Manguezais - APP ProManguezal (VS) | 1 | Governança | classes 1 a 7 |
| 9 | APP - SICAR (VS) | 1 | Governança | classes 1 a 8 |
| 10 | AUR - SICAR (VS) | 1 | Governança | classes 1 a 9 |
| 11 | RL - SICAR (VS) | 1 | Governança | classes 1 a 10 |

Após a hierarquia, são removidas do cômputo as áreas sobrepostas a **Florestas Públicas Não
Destinadas** (Cadastro Nacional de Florestas Públicas).

## Elegibilidade por classe

| Classe | O que entra |
|---|---|
| Recooperar | Licenciamento (LAC): todas as áreas. Reparação por danos: a partir de "projeto protocolado". Embargos: "em recuperação" ou "recuperada". |
| MonitoRAD | Embargos e licenciamento com indícios de recuperação (NDVI, metodologia do IBAMA). Fora do cômputo 2026. |
| SICAR-regularização | Área a recuperar dos imóveis com CAR "Analisado, em regularização ambiental (Lei 12.651/2012)". |
| Outros projetos | Polígonos de projetos de restauração do MMA e de outros ministérios e órgãos, com atributos mínimos do Anexo 3. |
| OR | Polígonos registrados como "público" na plataforma. |
| TI | VS em TI nas fases delimitada, declarada, homologada ou regularizada. |
| UC | VS em UCs do CNUC (proteção integral e uso sustentável); em APAs, só as áreas públicas. |
| Manguezais | VS sobre o mapeamento oficial do ProManguezal (APP em toda a extensão). |
| APP / AUR / RL | VS em APP, AUR e RL do CAR analisado nas condições da seção 4.1.1; "Aguardando análise", "Em análise" e "Aguardando retificação" só com conformidade INCRA (Anexo 4). |

Dentro do CAR, a precedência é APP > AUR > RL (seção 4.3), coerente com a ordem acima.

## Regra de contagem

- Camada 2 (projetos): a **área inteira** do projeto conta, com ou sem VS detectável.
- Camada 1 (VS legalmente protegida): conta só a **VS qualificada** (polígonos >= 2 ha) dentro dos territórios elegíveis.
- Uma área que seja VS e projeto ao mesmo tempo conta uma vez, como projeto.
