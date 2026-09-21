# Classe 3: SICAR - regularização ambiental (área a recompor de APP e RL)

Terceira classe da hierarquia do Anexo 1 (a classe 2, MonitoRAD, está desativada em 2026). Camada 2 (projetos):
conta a **área inteira** do polígono elegível, com ou sem VS. A classe **subtrai a classe 1** (Recooperar) e resolve
a sobreposição dentro da própria classe. A VS que cai nas áreas fica como atributo do polígono.

## Entradas

`CAR_Junho26_Regularizacao_Ambiental.gpkg` (camadas nomeadas "Julho26"), EPSG:4674:

| Camada | Feições | Uso |
|---|---|---|
| `CAR_Area_Recompor_APP_...` | 1.242 (tema `APP_ESCADINHA`, art. 61-A) | **entra** |
| `CAR_Area_Recompor_RL_...` | 1.238 (`ARL_PROPOSTA` 941, `ARL_APROVADA_NAO_AVERBADA` 178, `ARL_AVERBADA` 119) | **entra** |
| `CAR_Limite_Imovel_...` | 2.398 (2.391 códigos de imóvel) | só atributos (município, módulos fiscais, área do imóvel) |
| APPs, RL, AUR, Vegetação Nativa | - | não entram: são da Camada 1 (VS legalmente protegida) |

Todos os polígonos vêm de imóveis com a condição "Analisado, em regularização ambiental (Lei 12.651/2012)". O arquivo
cobre **AC, MT, PB, RJ e SP**, que é o conjunto nacional completo de imóveis nessa condição (confirmado em 21/09/2026; o prefixo do `cod_imovel` e o campo `cod_estado` coincidem em todos os imóveis).

## Elegibilidade (`config_computo.ELEGIBILIDADE_CAR_REG`)

| Regra | Valor | Situação |
|---|---|---|
| Condição do imóvel | igual à do relatório (comparação sem acento e sem símbolos: o arquivo traz "regularizacao" e "n") | do relatório |
| Status do cadastro (`ind_status`) | AT (ativo), PE (pendente) e SU (suspenso): entram todos (PE + SU = 1,2 mil ha de 33,6 mil) | Confirmado (D5, 21/09/2026) |
| Área mínima | polígonos com área geodésica <= 0,01 m2 saem (5 fragmentos nulos de RL no MT) | técnico |

## Hierarquia

1. **Subtração da classe 1:** de cada polígono retira-se a união dos polígonos líquidos do Recooperar que o cobrem
   (`P2_RECOOPERAR`; recorte peça a peça com índice espacial). Coluna `area_sobreposta_classes_anteriores_ha`.
2. **Sobreposição dentro da classe:** o CAR tem polígonos sobrepostos (APP entre imóveis vizinhos e dentro do mesmo
   imóvel, APP x RL). A área sobreposta conta uma vez, no polígono de maior precedência: **APP > RL averbada > RL
   aprovada e não averbada > RL proposta**, depois `fid_orig` (`PRECEDENCIA_CAR_REG`; Confirmado (D6, 21/09/2026), a ordem APP > RL vem
   da seção 4.3 do relatório). Coluna `area_sobreposta_na_classe_ha`.
3. `area_liquida_ha` = inteira - sobreposta nas classes anteriores - sobreposta na classe. Os polígonos líquidos são
   disjuntos entre si e da classe 1 (camada `P2_CAR_REGULARIZACAO`); é o que as classes seguintes vão subtrair.

## VS nos polígonos

Não havia cruzamento pronto para o SICAR-regularização; o passo 1 cruza os polígonos elegíveis com as camadas brutas
de VS qualificada (`config_computo.VS_CAMADAS`), por imóvel, usando o índice espacial dos GeoPackages:

- `vs22q`: as seis camadas de bioma da VS 2022 qualificada;
- `vs2224q`: as mesmas, com Amazônia e Cerrado trocados pela VS 2024 qualificada (Caatinga, Mata Atlântica, Pampa e Pantanal seguem 2022);
- a camada da Mata Atlântica 2022 vem sem CRS declarado e é lida como EPSG:4674 (como nos cruzamentos anteriores).

Saída: atributos `vs22q_*` e `vs2224q_*` na tabela (`_tem`, `_area_ha`, `_pct`, `_n_pol`, `_ha_<bioma>`, mesmos nomes do Recooperar) e as
peças "VS x polígono" em `IN_CAR_Regularizacao_Junho26_VS.gpkg` (camadas `vs22q_pedacos`, `vs2224q_pedacos`). No passo 2 a VS é recalculada
por peças (união) por polígono inteiro, por polígono líquido e por célula UF x bioma, e conferida contra o atributo.

## UF e bioma

Como no Tier-1: cada polígono é dividido em células UF x bioma (IBGE) e o que fica fora dos limites vira "FORA"
(`area_fora_ibge_ha` na tabela). **D7 (confirmado):** a área fora dos limites do IBGE fica rotulada "FORA", sem UF (14,6 ha, 87% do polígono `CARREG-RL-000924`, no AC, perto da fronteira); aparece separada nas tabelas por UF e bioma. `uf_diverge_car` marca quando a UF calculada difere do prefixo do `cod_imovel`.

## Campos e cuidados com os dados

- `area_decl_ha` (`num_area` da camada) **não é confiável nas camadas de RL** (soma 675 mil ha contra 30,8 mil ha de área geodésica: o campo repete a
  área da RL do imóvel em cada feição); todas as áreas do cômputo são geodésicas (GRS80).
- `id_proj` = `CARREG-<APP|RL>-<fid>`; rastreio por `camada_orig` e `fid_orig`.
- Não há dados pessoais nas camadas (só código do imóvel, tema, status e condição); há uma verificação automática no passo 1.
- O mesmo `cod_imovel` pode ter várias feições (o imóvel de PB aparece 8 vezes) e vários polígonos de APP do imóvel de PB se sobrepõem quase todos
  (54,9 dos 80,5 ha): a precedência resolve.

## Conferências (`T3_conferencias.csv`)

Identidade de área por polígono (inteira = sobreposta nas classes anteriores + sobreposta na classe + líquida); líquida = união dos
polígonos - união do Recooperar (cálculo independente); sobreposição zero entre líquidos e com a classe 1; células UF x bioma somam o polígono;
VS do atributo = VS recalculada; VS líquida <= VS inteira; nenhum polígono sem UF; geometrias válidas.
