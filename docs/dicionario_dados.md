# Dicionário de dados (insumos)

Inventário dos dados em `GEODATABASE\GEOPACKAGE`, conferido em 20/09/2026. Contagens de feições e
campos vêm da leitura direta dos arquivos.

## Camada 2 - projetos

| Arquivo | Camadas (feições) | Observações |
|---|---|---|
| `IBAMA_Projetos_Recooperar_2026_com_area.gpkg` (EPSG:4674); com a VS incorporada: `Projetos_com_VegSec\IBAMA_Projetos_Recooperar_2026_com_VegSec.gpkg` (entrada do Tier-1) | Licenciamento (76); Reparação por danos (1.181); Embargo (357); Outras áreas (76) | `status_are`: Em recuperação, Recuperada, Pendente de recuperação, ATUALIZAR (6 no licenciamento). Campo `area_ha` |
| `IBAMA_Projetos_Recooperar_2025_com_area.gpkg` (EPSG:4326) | Licenciamento (67); Reparação (2.553); Embargo (1.726); Outras (136) | Muitos `ATUALIZAR` e "Competência de outros órgãos". Versão anterior; relação com a 2026 a definir |
| `CAR_Junho26_Regularizacao_Ambiental.gpkg` (EPSG:4674; só AC, MT, PB, RJ e SP; entrada da classe 3) | Limite do imóvel (2.398); APPs (44.631); RL (2.477); AUR (183); Vegetação nativa (2.323); **Área a recompor APP (1.242); Área a recompor RL (1.238)** | Camadas nomeadas "Julho26" dentro de arquivo "Junho26". Chave `cod_imovel`. Fonte da classe SICAR-regularização |
| `ICMBio_Projetos_Restauracao_2026_com_area.gpkg` | Restauracao_Ecologica (3.609); Areas_Degradadas (3.855); Embargos_maior5ha (3.685) | CRS não definido no arquivo. Definir quais camadas são projetos |
| `ICMBio_Projetos_GEF_Terrestre_2026_com_area.gpkg` | 7 camadas (Pantanal, Pampa, Caatinga; 4 a 326 feições) | CRS heterogêneos (sem CRS, 32722, 31981, 31984), geometrias 3D |
| `ORR_Observatorio_Restauracao_2025_com_area.gpkg` | 1 camada, 4 feições (uma por bioma: Amazônia, Caatinga, Cerrado, Mata Atlântica; 48,7 mil ha) | Campo `hierarquia` = ORR. Já dissolvido; sem Pampa e Pantanal. CRS Albers customizado (WKT "Albers"; no QGIS/GDAL usar `+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs`), geometrias Z/M e 38.473 partes. Entrada da classe 5 (área total, com ou sem VS) |
| `IBAMA_Areas_Embargadas_PANGIA20260920_Poligonos.gpkg` (EPSG:4674) | 1 camada, 50.674 polígonos (5,88 Mha somados; 5,16 Mha sem sobreposição interna) | Versão limpa de `..._PANGIA20260920.gpkg` (91.327 registros). Chave `num_tad` + `serie_tad` (`seq_tad` = 0 em 1.563 registros). Sem campo de status de recuperação. Entrada da classe 4 (só a VS dentro do embargo). Colunas com nome/CPF/CNPJ do embargado e textos livres (`nome_embar`, `cpf_cnpj_e`, `nome_imove`, `des_locali`, `des_tad`, `des_infrac`) **não** seguem para o cômputo (LGPD) |

## Camada 1 - governança

| Arquivo | Conteúdo |
|---|---|
| `Terras_Indigenas_FUNAI20260507.gpkg` | 657 feições; campos `terrai_nom`, `fase_ti`, `uf_sigla` |
| `Unidades_Conservacao_CNUC20260507.gpkg` | 3.323 feições; campos `nome_uc`, `esfera`, `grupo`, `categoria`, `uf` |
| `Pro-Manguezal_IBAMA20260508.gpkg` | 7.661 feições; campos `Id`, `area_ha` |
| `CAR_Maio2026_Imoveis_Selecionados/` | `<UF>_CAR_Imoveis_Selecionados_{Habilitados, Analisados, Nao_Analisados}.gpkg` (BA só Nao_Analisados; ES sem Analisados) |
| `Vegetacao_Secundaria_INPE/` | VS 2022 (Brasil, 6 biomas) e 2024 (Amazônia e Cerrado), bruta e qualificada (>= 2 ha) |

## Cruzamentos já calculados (entradas do passo 3)

Em `Cruzamento_Espacial_Vegetacao_Secundaria/`: `VS-Cadastro_Ambiental_Rural` (VS x imóveis selecionados,
APP/RL/AUR, versões 2022, 2022 qualificada e 2024), `VS-Terras_Indigenas`, `VS-Unidades_Conservacao`,
`VS-Pro_Manguezal` e `VS-Projetos_Restauracao`, com planilhas-resumo de área por bioma.

## Apoio

| Arquivo | Conteúdo |
|---|---|
| `IBGE_Limite_Estados.gpkg` | 27 UFs (`SIGLA_UF`, `NM_UF`), EPSG:4674, total 8.509.361 km2 |
| `IBGE_Limite_Biomas.gpkg` | 6 biomas (`Bioma`, `CD_Bioma`), EPSG:4674, nomes acentuados; soma 0,06% maior que a dos Estados |
| `Assentamentos_Rurais_INCRA20260610.gpkg` | 8.212 feições; campos `uf`, `nome_proje`, `fase` |
| `Territorios_Quilombolas_INCRA20260610.gpkg` | 434 feições; campos `nm_comunid`, `cd_uf`, `fase` |
| `Analise_Territorial_CAR-INCRA_dissolvido/` | CAR e INCRA dissolvidos por UF, com planilha de áreas |

## Não disponíveis

- MonitoRAD: dados não recebidos (fora do cômputo 2026).
- Florestas Públicas Não Destinadas (CNFP): fonte a definir.

## Saídas do Tier-1 (Recooperar 2026)

Em `Computo_Planaveg_2026\Insumos` e `Computo_Planaveg_2026\Tier1_Recooperar` (ver `docs/tier1_recooperar.md`).

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_Recooperar_2026.gpkg` (`IN_RECOOPERAR`) | Polígonos elegíveis inteiros, campos harmonizados, sem dados pessoais, com atributos de VS |
| `Insumos\IN_Recooperar_2026_excluidos.csv` / `_resumo.csv` | Polígonos fora do cômputo e o motivo; total x elegível por categoria |
| `Tier1_Recooperar\P2_Recooperar_2026.gpkg` | `P2_RECOOPERAR_poligonos` (polígonos inteiros, 1 por projeto, 67 campos) e `P2_RECOOPERAR` (polígonos líquidos, disjuntos) |
| `T1_areas_uf_bioma.csv` | Tabela longa: 1 linha por projeto x UF x bioma (área completa e líquida, VS completa e líquida nas 2 versões) |
| `T1_resumo_categoria_uf_bioma.csv`, `T1_resumo.csv`, `T1_conferencias.csv` | Totais, conferências de conservação de área |

Colunas próprias do Tier-1 na tabela de polígonos: `id_proj` (`REC26-<LIC|REP|EMB|OUT>-<fid>`), `categoria`,
`elegivel_computo`, `motivo_elegibilidade`, `ano_inicio` e `ano_inicio_fonte`, `ano_infracao`,
`prec_ordem`, `n_precedentes_sobrepostos`, `area_sobreposta_ha`, `area_liquida_ha`, `uf_principal`, `ufs`,
`bioma_principal`, `biomas`, `uf_diverge_fonte`, `vs22q_*` e `vs2224q_*` (`_tem`, `_area_ha`, `_pct`, `_n_pol`,
`_ha_<bioma>`, `_completa_recalc_ha`, `_liq_ha`).

## Saídas da classe 3 (SICAR-regularização)

Em `Computo_Planaveg_2026\Insumos` e `Computo_Planaveg_2026\Tier3_CAR_Regularizacao` (ver `docs/tier3_car_regularizacao.md`).

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_CAR_Regularizacao_Junho26.gpkg` (`IN_CAR_REG`) | Polígonos elegíveis inteiros (APP e RL a recompor) com atributos do CAR e de VS (`vs22q_*`, `vs2224q_*`) |
| `Insumos\IN_CAR_Regularizacao_Junho26_VS.gpkg` | Peças VS x polígono (`vs22q_pedacos`, `vs2224q_pedacos`), com `id_proj`, `vs_id`, `vs_ano`, `vs_bioma`, `area_ha` |
| `Insumos\IN_CAR_Regularizacao_Junho26_resumo.csv` / `_excluidos.csv` | Total x elegível; polígonos fora do cômputo e o motivo |
| `Tier3_CAR_Regularizacao\P2_CAR_Regularizacao_Junho26.gpkg` | `P2_CAR_REGULARIZACAO_poligonos` (inteiros, com sobreposições, área líquida, UF/bioma e VS) e `P2_CAR_REGULARIZACAO` (líquidos, disjuntos) |
| `T3_areas_uf_bioma.csv`, `T3_resumo_categoria_tema_uf_bioma.csv`, `T3_resumo.csv`, `T3_conferencias.csv` | Tabelas longas, resumos e conferências |
| `T3_acumulado_classes_1_e_3.csv` | Área líquida acumulada das classes 1 e 3 por classe, categoria, UF e bioma |

Colunas próprias da tabela de polígonos: `id_proj`, `categoria` (app/rl), `cod_tema`, `cod_imovel`, `status_car`, `condicao_car`, `uf_car`,
`municipio_car`, `mod_fiscal`, `area_imovel_ha`, `area_decl_ha`, `area_ha_geo`, `elegivel_computo`, `motivo_elegibilidade`, `prec_ordem`,
`area_sobreposta_classes_anteriores_ha`, `n_precedentes_sobrepostos`, `area_sobreposta_na_classe_ha`, `area_liquida_ha`, `uf_principal`, `ufs`,
`bioma_principal`, `biomas`, `area_fora_ibge_ha`, `uf_diverge_car`, `vs*_completa_recalc_ha`, `vs*_liq_ha`.

## Saídas da classe 4 (Outros projetos: embargos PANGIA)

Em `Computo_Planaveg_2026\Insumos` e `Computo_Planaveg_2026\Tier4_Outros_Projetos` (ver `docs/tier4_outros_projetos.md`).
Entrada: `IBAMA_Areas_Embargadas_PANGIA20260920_Poligonos.gpkg` e o cruzamento com a VS qualificada em
`Cruzamento_Espacial_Vegetacao_Secundaria\VS-Areas_Embargadas` (`idx_embargo` = FID do embargo - 1).

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_Embargos_PANGIA_20260920.gpkg` (`IN_EMBARGOS_PANGIA`) | Embargos inteiros que têm VS em alguma versão (referência), campos sem dados pessoais e atributos `vs22q_*` e `vs2224q_*` |
| `Insumos\IN_Embargos_PANGIA_20260920_VS.gpkg` | Peças VS x embargo (`vs22q_pedacos`, `vs2224q_pedacos`), com `id_proj`, `vs_id`, `vs_ano`, `vs_bioma`, `vs_camada`, `area_ha` |
| `Insumos\IN_Embargos_PANGIA_20260920_resumo.csv` / `_excluidos.csv` | Total x com VS, por UF; embargos sem VS (fora do cômputo) |
| `Tier4_Outros_Projetos\P2_Outros_Projetos_PANGIA_20260920.gpkg` | `P2_OUTROS_PROJETOS_poligonos` (embargos inteiros com a VS, as sobreposições e a área líquida de cada versão), `P2_OUTROS_PROJETOS_vs22q` e `P2_OUTROS_PROJETOS_vs2224q` (polígonos líquidos da classe, disjuntos entre si e das classes 1 e 3) |
| `T4_areas_uf_bioma.csv`, `T4_resumo_uf_bioma.csv`, `T4_resumo.csv`, `T4_conferencias.csv` | Tabela longa embargo x versão x UF x bioma, resumos e conferências |
| `T4_acumulado_classes_1_3_4.csv` | Área líquida acumulada das classes 1, 3 e 4, por versão da VS, classe, categoria, UF e bioma |

Colunas próprias da tabela de polígonos: `id_proj` (`EMB-<fid>`), `num_tad`, `serie_tad`, `seq_tad`, `data_embargo`, `ano_embargo`,
`uf_fonte`, `cod_municipio`, `municipio_fonte`, `situacao_desmat`, `tipo_area`, `bioma_fonte`, `operacao`, `area_ha_geo` (embargo inteiro),
`prec_ordem`, e, para cada versão `<p>` (`vs22q`, `vs2224q`): `<p>_tem`, `<p>_area_ha`, `<p>_pct`, `<p>_n_pol`, `<p>_ha_<bioma>`
(passo 1), `<p>_area_vs_embargo_ha`, `<p>_sobreposta_recooperar_ha`, `<p>_sobreposta_sicar_regularizacao_ha`,
`<p>_sobreposta_classes_anteriores_ha`, `<p>_n_precedentes_sobrepostos`, `<p>_sobreposta_na_classe_ha`, `<p>_area_liquida_ha`,
`<p>_uf_principal`, `<p>_ufs`, `<p>_bioma_principal`, `<p>_biomas`, `<p>_uf_diverge_fonte`, `<p>_area_fora_ibge_ha`.

## Saídas da classe 5 (OR: Observatório da Restauração)

Em `Computo_Planaveg_2026\Insumos` e `Computo_Planaveg_2026\Tier5_OR` (ver `docs/tier5_or.md`). Entrada:
`ORR_Observatorio_Restauracao_2025_com_area.gpkg` (camada `Observatorio_da_Restauracao_2025`; 4 polígonos, um por bioma).

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_OR_2025.gpkg` (`IN_OR`) | Os 4 polígonos inteiros (2D, reparados), com `id_proj` (`ORR-Amazonia`, `ORR-Caatinga`, `ORR-Cerrado`, `ORR-Mata_Atlantica`), `bioma_fonte`, `hierarquia_fonte`, `area_decl_ha`, `area_ha_geo`, `n_partes`, elegibilidade e os atributos `vs22q_*` e `vs2224q_*` |
| `Insumos\IN_OR_2025_VS.gpkg` | Peças VS x ORR (`vs22q_pedacos`, `vs2224q_pedacos`) |
| `Insumos\IN_OR_2025_resumo.csv` / `_excluidos.csv` | Área e VS por polígono e versão; polígonos fora do cômputo (nenhum) |
| `Tier5_OR\P2_OR_2025.gpkg` | `P2_OR_poligonos` (os 4 polígonos inteiros com sobreposições e área líquida por versão), `P2_OR_vs22q` e `P2_OR_vs2224q` (polígonos líquidos, uma parte por linha, disjuntos entre si e das classes 1, 3 e 4) |
| `T5_areas_uf_bioma.csv`, `T5_resumo_uf_bioma.csv`, `T5_resumo.csv`, `T5_conferencias.csv` | Tabela longa polígono x versão x UF x bioma, resumos e conferências |
| `T5_acumulado_classes_1_3_4_5.csv` | Área líquida acumulada das classes 1, 3, 4 e 5, por versão da VS, classe, categoria, UF e bioma |

Colunas próprias de `P2_OR_poligonos`, para cada versão `<p>` (`vs22q`, `vs2224q`): `<p>_sobreposta_recooperar_ha`, `<p>_sobreposta_sicar_regularizacao_ha`,
`<p>_sobreposta_outros_projetos_ha`, `<p>_sobreposta_classes_anteriores_ha`, `<p>_n_precedentes_sobrepostos`, `<p>_sobreposta_na_classe_ha`,
`<p>_area_liquida_ha`, `<p>_uf_principal`, `<p>_ufs`, `<p>_bioma_principal`, `<p>_biomas`, `<p>_area_fora_ibge_ha`.
