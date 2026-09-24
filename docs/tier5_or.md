# Classe 5: OR (Observatório da Restauração)

Quinta classe da hierarquia do Anexo 1, Camada 2 (projetos). Fonte: o arquivo do Observatório da Restauração em formato "público".
Como nas classes 1 e 3, **entra a área total dos polígonos, independente do cruzamento com a VS** (decisão de 21/09/2026); a VS
fica como atributo. A classe subtrai as classes 1 (Recooperar), 3 (SICAR-regularização) e 4 (Outros projetos).

**Atualizado em 24/09/2026: a fonte trocou do ORR 2025 (4 polígonos dissolvidos por bioma) para o ORR 2026 (86.281 polígonos em
nível de projeto).** Por decisão do usuário, entram TODOS os polígonos, qualquer que seja o status (o arquivo novo não tem mais o
campo `hierarquia` usado antes para filtrar; o campo `ProjAtivo` que ele traz também não filtra nada). As seções "Resultados",
"Conferências" e "Desempenho" abaixo descrevem a rodada com o ORR 2025 e estão desatualizadas até a próxima rodada nacional
rodar com o ORR 2026 - mantidas só como referência histórica.

## Entrada

| Arquivo | Uso |
|---|---|
| `ORR_Observatorio_Restauracao_2026.gpkg`, camada `20260917_ORdados_base_publico` | 86.281 polígonos, um por projeto de restauração, todos com `Privacidad` = "Público"; cobre os 6 biomas (inclui Pampa e Pantanal, que faltavam no ORR 2025) |
| `P2_RECOOPERAR`, `P2_CAR_REGULARIZACAO`, `P2_OUTROS_PROJETOS_<versão>` | classes 1, 3 e 4 (líquidas), subtraídas |
| VS bruta (as 3 camadas de VS 2022 qualificada e as 2 de VS 2024 qualificada) | atributo de VS por polígono (passo 1) |

Características do arquivo novo: CRS EPSG:4674 (já no padrão do pipeline, sem reprojeção), geometrias `MultiPolygon` 2D, sem Z/M, e
um atributo por projeto (`NmProjeto`, `InstExecu`, `TecnRest`, `EstratRest`, `Bioma`, `AreaCalc_h`, `ProjAtivo`, `DataInici`,
`DataConcl`, `Coletivo` etc. - nenhum é dado pessoal). Não existe mais um `id_proj` natural (o ORR 2025 usava só o bioma, porque
tinha 1 polígono por bioma); o passo 1 grava `id_proj` = `ORR-<bioma>-<fid_orig>`, onde `fid_orig` vem do FID do próprio
GeoPackage (único por definição). Geometrias válidas, sem nulas/vazias (checado em 24/09/2026, ver conversa com o usuário).

*(O arquivo antigo, `ORR_Observatorio_Restauracao_2025_com_area.gpkg`, camada `Observatorio_da_Restauracao_2025`, trazia 4 polígonos,
um por bioma - Amazônia, Caatinga, Cerrado, Mata Atlântica -, já dissolvidos, 38.473 partes, sem Pampa e Pantanal, em CRS Albers
customizado: `+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs`.)*

## Decisões

| Item | Regra | Situação |
|---|---|---|
| Papel do OR | área **total** dos polígonos, com ou sem VS; VS como atributo | Decidido (21/09/2026) |
| Versões da VS | `vs22q` e `vs2224q`; a área da classe é a mesma nas duas versões, muda o atributo de VS e a subtração da classe 4 | Decidido |
| Versão do arquivo | ORR 2026 (nível de projeto); se sair versão nova, trocar `FONTES['or']` em `config_computo.py` | Adotado (24/09/2026) |
| Filtro de status | nenhum: todos os polígonos entram, qualquer que seja `ProjAtivo` | Decidido (24/09/2026) |
| Precedência entre projetos sobrepostos | menor `fid_orig` (não há outro critério nos dados de origem) | Adotado (24/09/2026), consistente com o critério de desempate já usado em outras classes com múltiplos polígonos |
| ICMBio | as camadas do ICMBio GEF com "ORR" no nome podem se sobrepor a este arquivo quando o ICMBio voltar; a hierarquia resolve (o OR conta uma vez) | Registro |

## Hierarquia

1. **Área total** dos polígonos (`area_ha_geo`, geodésica GRS80).
2. **Subtração das classes 1, 3 e 4**, uma de cada vez (`<p>_sobreposta_recooperar_ha`, `<p>_sobreposta_sicar_regularizacao_ha`,
   `<p>_sobreposta_outros_projetos_ha`). A geometria da classe 4 depende da versão da VS, por isso a classe 5 usa `P2_OUTROS_PROJETOS_<versão>`.
3. **Sobreposição entre os polígonos do ORR** (`<p>_sobreposta_na_classe_ha`): com o ORR 2025 (4 polígonos dissolvidos por bioma) essa
   sobreposição era zero por construção; desde o ORR 2026 (86.281 projetos, submissões distintas podendo cobrir a mesma área) ela deixou
   de ser zero e passou a ser resolvida como nas outras classes com múltiplos polígonos: menor `fid_orig` fica com a área.
4. `<p>_area_liquida_ha` = área total - sobreposta às classes anteriores - sobreposta na classe. Os polígonos líquidos são disjuntos
   entre si e das classes 1, 3 e 4 (camadas `P2_OR_vs22q` e `P2_OR_vs2224q`, com uma parte por linha).
5. UF e bioma pelas células dos limites do IBGE (a soma das células é a área do polígono).

## Resultados (ORR 2025 - histórico, ver nota no topo)

| | vs22q | vs2224q |
|---|---|---|
| Polígonos / partes | 4 / 38.473 | 4 / 38.473 |
| Área total dos polígonos (ha) | 48.705,8 | 48.705,8 |
| Sobreposta ao Recooperar (ha) | 278,8 | 278,8 |
| Sobreposta ao SICAR-regularização (ha) | 1.182,7 | 1.182,7 |
| Sobreposta à classe 4 (ha) | 0,007 | 0,008 |
| **Área líquida da classe 5 (ha)** | **47.244,2** | **47.244,2** |
| VS dentro dos polígonos, atributo (ha) | 4.287,5 (8,8%) | 4.351,9 (8,9%) |
| VS líquida (ha) | 4.264,7 | 4.329,3 |
| Acumulado das classes 1, 3, 4 e 5 (ha) | 544.690,5 | 536.428,6 |

Por bioma (área total / líquida, ha): Amazônia 3.500,2 / 3.500,2; Caatinga 22,2 / 15,0; Cerrado 1.684,6 / 1.625,9; Mata Atlântica 43.498,8 / 42.103,2.
A sobreposição com as classes 1 e 3 está quase toda na Mata Atlântica (1.395,6 ha).

## Conferências (`T5_conferencias.csv`, 22 verificações, ORR 2025)

Área geodésica x área declarada no arquivo (dentro de 0,1%); polígonos do ORR disjuntos; identidade de área por polígono (inteira =
sobreposta às anteriores + na classe + líquida); líquida = união do ORR - união das classes 1, 3 e 4 (cálculo independente);
sobreposição zero entre líquidos e com as classes 1, 3 e 4; células UF x bioma somam a área do polígono; área fora dos limites do IBGE
desprezível (0,018 ha, rotulados "FORA"); atributo de VS do passo 1 = VS recalculada por peças; VS líquida <= VS inteira; nenhum polígono sem UF;
geometrias válidas. Tudo dentro da tolerância, nas duas versões.

Verificação externa (fora dos scripts, no QGIS, sobre as camadas brutas de VS): a VS dentro de cada um dos 4 polígonos, nas duas versões, coincide com
o atributo do passo 1, com diferença máxima de 1,2e-4 ha (Mata Atlântica, 3.331,96 ha).

Com o ORR 2026, a verificação "polígonos do ORR disjuntos" deixou de exigir zero (virou informativa - ver `chk` em `classe_or`,
`2_camada2_projetos.py`): projetos podem se sobrepor entre si, e a área líquida trata essa sobreposição pela precedência de `fid_orig`.

## Desempenho (ORR 2025, histórico)

Passo 1 (`python 1_preparar_insumos.py or`): ~2 min; as 38 mil partes são agrupadas em células de 0,25 grau (`CELULA_VS_OR_GRAUS`) e a VS bruta é lida
uma vez por célula. Passo 2 (`python 2_camada2_projetos.py or`): ~15 min; a maior parte é o recorte por UF x bioma do polígono da Mata Atlântica
(~3,5 min por versão). Exige as classes 1, 3 e 4 já processadas. Com o ORR 2026 (86.281 polígonos, ~4x a área bruta do ORR 2025), o tempo dos
dois passos deve crescer bastante - sem medição ainda; a suspeita maior é o passo 2, que hoje processa polígono por polígono.
