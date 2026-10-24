# Dicionário de dados (insumos)

Inventário dos dados em `GEODATABASE\GEOPACKAGE`, conferido em 20/09/2026. Contagens de feições e
campos vêm da leitura direta dos arquivos.

## Camada 2 - projetos

| Arquivo | Camadas (feições) | Observações |
|---|---|---|
| `IBAMA_Projetos_Recooperar_2026_com_area.gpkg` (EPSG:4674); com a VS incorporada: `Projetos_com_VegSec\IBAMA_Projetos_Recooperar_2026_com_VegSec.gpkg` (entrada do Tier-1) | Licenciamento (76); Reparação por danos (1.181); Embargo (357); Outras áreas (76) | `status_are`: Em recuperação, Recuperada, Pendente de recuperação, ATUALIZAR (6 no licenciamento). Campo `area_ha` |
| `IBAMA_Projetos_Recooperar_2025_com_area.gpkg` (EPSG:4326) | Licenciamento (67); Reparação (2.553); Embargo (1.726); Outras (136) | Muitos `ATUALIZAR` e "Competência de outros órgãos". Versão anterior; relação com a 2026 a definir |
| `IBAMA_Areas_Embargadas_MonitoRAD2026.gpkg` (entrada da classe 2, via `Insumos\IN_MonitoRAD_2026.gpkg`) | `MonitoRAD_ANALISE` (clusters de NDVI; 2.392 peças "Com indício de recuperação"); `MonitoRAD_EMBARGOS` (polígonos dos embargos) | Campos `avaliacao`, `value`, `seq_tad` (= `NUM_TAD_1` dos embargos), `Area_ha`; `dat_embarg` nos embargos. Ver `docs/tier2_monitorad.md` |
| `CAR_Junho26_Regularizacao_Ambiental.gpkg` (EPSG:4674; só AC, MT, PB, RJ e SP; entrada da classe 3) | Limite do imóvel (2.398); APPs (44.631); RL (2.477); AUR (183); Vegetação nativa (2.323); **Área a recompor APP (1.242); Área a recompor RL (1.238)** | Camadas nomeadas "Julho26" dentro de arquivo "Junho26". Chave `cod_imovel`. Fonte da classe SICAR-regularização |
| `ICMBio_Projetos_Restauracao_2026_com_area.gpkg` | Restauracao_Ecologica (3.609); Areas_Degradadas (3.855); Embargos_maior5ha (3.685) | CRS não definido no arquivo. Só `Restauracao_Ecologica` entra na classe 4 (decisão de 14/10/2026) |
| `FUNBIO_Areas_Restauracao_20261023.gpkg` (EPSG:4674; entrada da classe 4 desde 23/10/2026, via `Insumos\IN_FUNBIO_2026.gpkg`) | RockRio (83); MataAtlantica (344); GEF_Terrestre (582); FlorestaViva (1.434); AMLD (6) | Geometrias 3D com medida (Z/M descartados). Campos com grafias diferentes entre camadas (ID/id/id_1, ANO_FINAL/ANO_FIM, BIOMA/Bioma), padronizados por `consolidar_funbio.py`. Ver `docs/tier4_outros_projetos.md` |
| `ICMBio_Projetos_GEF_Terrestre_2026_com_area.gpkg` | 7 camadas (Pantanal, Pampa, Caatinga; 4 a 326 feições) | CRS heterogêneos (sem CRS, 32722, 31981, 31984), geometrias 3D. As 7 camadas entram na classe 4 (decisão de 14/10/2026) |
| `ORR_Observatorio_Restauracao_2025_com_area.gpkg` | 1 camada, 4 feições (uma por bioma: Amazônia, Caatinga, Cerrado, Mata Atlântica; 48,7 mil ha) | Campo `hierarquia` = ORR. Já dissolvido; sem Pampa e Pantanal. CRS Albers customizado (WKT "Albers"; no QGIS/GDAL usar `+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs`), geometrias Z/M e 38.473 partes. Entrada da classe 5 (área total, com ou sem VS) |
| `IBAMA_Areas_Embargadas_PANGIA20260920_Poligonos.gpkg` (EPSG:4674) | 1 camada, 50.674 polígonos (5,88 Mha somados; 5,16 Mha sem sobreposição interna) | Versão limpa de `..._PANGIA20260920.gpkg` (91.327 registros). Chave `num_tad` + `serie_tad` (`seq_tad` = 0 em 1.563 registros). Sem campo de status de recuperação. Foi entrada da classe 4 (só a VS dentro do embargo) até a v1.0.0; **fora da hierarquia desde 21/10/2026**. Colunas com nome/CPF/CNPJ do embargado e textos livres (`nome_embar`, `cpf_cnpj_e`, `nome_imove`, `des_locali`, `des_tad`, `des_infrac`) **não** seguem para o cômputo (LGPD) |

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

## Saídas da classe 2 (MonitoRAD)

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_MonitoRAD_2026.gpkg` (`IN_MONITORAD`) | 2.361 polígonos "Com indício de recuperação" recortados pelo próprio embargo, sem sobreposição interna (`consolidar_monitorad.py`) |
| `Tier2_MonitoRAD\P2_MonitoRAD_2026.gpkg` | `P2_MONITORAD` (Δ líquido da classe 1, `id_proj` MRAD-nnnnn, UF e bioma principais, `area_liquida_ha`); `P2_MONITORAD_poligonos` (polígonos inteiros, `elegivel_computo = 1`) |
| `Tier2_MonitoRAD\MonitoRAD_incremental_resumo.csv` / `_alteracoes.csv` / `_estado.json`, `_log_monitorad_incremental.txt` | Área retirada por classe e versão, feições alteradas, retomada e log da inclusão |

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

## Saídas da classe 4 (Outros projetos: ICMBio e FUNBIO, desde a v1.2.0)

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_ICMBio_2026.gpkg` (`IN_ICMBIO`) | ver abaixo, "ICMBio na classe 4" |
| `Insumos\IN_FUNBIO_2026.gpkg` (`IN_FUNBIO`) | 2.417 polígonos sem sobreposição interna (fica o maior), 14.866,6 ha. Campos `id_funbio`, `camada_orig`, `id_orig`, `programa`, `projeto`, `subprojeto`, `fonte_financ`, `instrumento`, `edital`, `executor`, `estrategia`, `tecnica`, `ano_inicio`, `ano_fim`, `municipio_fonte`, `uf_fonte`, `bioma_fonte`, `area_attr_ha` (campo ÁREA_HA), `area_orig_ha`, `area_ha_geo`, `sobreposta_funbio_maior_ha`, `recortado_por_maior`, `fonte` (`FUNBIO_2026`) |
| `Tier4_Outros_Projetos\P2_Outros_Projetos_2026.gpkg` | `P2_OUTROS_PROJETOS_poligonos` (polígonos inteiros do ICMBio e da FUNBIO, `id_proj` `ICMBIO-nnnnn` / `FUNBIO-nnnnn`, sobreposições com as classes 1 a 3 e dentro da classe, área líquida, UF e bioma principais, `elegivel_computo`); `P2_OUTROS_PROJETOS_vs22q` e `_vs2224q` (polígonos líquidos, iguais nas duas versões: `id_proj`, `fonte`, `projeto`, `uf_principal`, `bioma_principal`, `area_liquida_ha`) |
| `T4_resumo.csv` (por fonte), `T4_resumo_uf_bioma.csv`, `T4_areas_uf_bioma.csv`, `T4_conferencias.csv`, `T4_acumulado_classes_1_3_4.csv` (classes 1 a 4, incluindo a 2) | Resumos, tabela longa polígono x UF x bioma, conferências e acumulado |
| `Tier4_Outros_Projetos\FUNBIO_incremental_resumo.csv` / `_alteracoes.csv` / `_estado.json`, `_log_funbio_incremental.txt` | Inclusão incremental da FUNBIO: área retirada por camada das classes 5 a 11, feições alteradas, retomada e log |

## Saídas da classe 4 até a v1.0.0 (embargos PANGIA; histórico)

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

### ICMBio na classe 4 (desde 14/10/2026; inclusão incremental da v0.9.0)

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_ICMBio_2026.gpkg` (`IN_ICMBIO`) | 3.655 polígonos sem sobreposição interna, área total (38.019,1 ha): 602 do GEF Terrestre (4.588,5 ha) e 3.053 da Restauração Ecológica (33.430,6 ha, já recortada pelo GEF). Campos `fonte` (`ICMBio_GEF_Terrestre_2026` / `ICMBio_Restauracao_2026`), `camada_orig`, `fid_orig`, `projeto`, `instituicao`, `uc`, `data_inicio`, `data_conclusao`, `recortado_por_gef`, `area_orig_ha` |
| `Tier4_Outros_Projetos\P2_Outros_Projetos_PANGIA_20260920.gpkg` | `P2_OUTROS_PROJETOS_vs22q` / `_vs2224q` passam a ter também as peças `ICMBIO-nnnnn` (Δ, a parte do ICMBio fora das classes 1, 3 e 4); nova camada `P2_OUTROS_PROJETOS_ICMBIO_poligonos` (polígonos inteiros com a área líquida por versão) |
| `Tier4_Outros_Projetos\ICMBio_incremental_resumo.csv` / `_alteracoes.csv` | Por versão x camada: feições alteradas e apagadas, área antes, removida e depois, interseção medida e residual; uma linha por feição alterada |
| `Tier4_Outros_Projetos\ICMBio_incremental_delta.gpkg` | Δ por versão (`delta_vs22q`, `delta_vs2224q`): o que entrou na classe 4 e saiu das classes 5 a 11 |
| `Tier4_Outros_Projetos\ICMBio_incremental_estado.json`, `_log_icmbio_incremental.txt` | Etapas concluídas (retomada) e log |

## Saídas da classe 5 (OR: Observatório da Restauração)

Em `Computo_Planaveg_2026\Insumos` e `Computo_Planaveg_2026\Tier5_OR` (ver `docs/tier5_or.md`). Entrada desde 24/09/2026:
`ORR_Observatorio_Restauracao_2026.gpkg` (camada `20260917_ORdados_base_publico`; 86.281 polígonos, um por projeto, todos com
`Privacidad` = "Público"; até 23/09/2026 a entrada era `ORR_Observatorio_Restauracao_2025_com_area.gpkg`, 4 polígonos dissolvidos
por bioma). Todos os polígonos entram, sem filtro de status (nem o antigo `hierarquia`, que não existe mais no arquivo, nem o
`ProjAtivo` do arquivo novo - decisão do usuário em 24/09/2026).

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_OR_2026.gpkg` (`IN_OR`) | Os polígonos inteiros (2D, reparados), com `id_proj` (`ORR-<bioma>-<fid_orig>`, único por projeto), `fid_orig` (FID do GeoPackage de origem), `bioma_fonte`, `area_decl_ha` (campo `AreaCalc_h` do ORR 2026), `area_ha_geo`, `n_partes`, elegibilidade e os atributos `vs22q_*` e `vs2224q_*` |
| `Insumos\IN_OR_2026_VS.gpkg` | Peças VS x ORR (`vs22q_pedacos`, `vs2224q_pedacos`) |
| `Insumos\IN_OR_2026_resumo.csv` / `_excluidos.csv` | Área e VS por polígono e versão; polígonos fora do cômputo (geometria vazia ou área desprezível) |
| `Tier5_OR\P2_OR_2026.gpkg` | `P2_OR_poligonos` (os polígonos inteiros com sobreposições e área líquida por versão), `P2_OR_vs22q` e `P2_OR_vs2224q` (polígonos líquidos, uma parte por linha, disjuntos entre si e das classes 1, 3 e 4) |
| `T5_areas_uf_bioma.csv`, `T5_resumo_uf_bioma.csv`, `T5_resumo.csv`, `T5_conferencias.csv` | Tabela longa polígono x versão x UF x bioma, resumos e conferências |
| `T5_acumulado_classes_1_3_4_5.csv` | Área líquida acumulada das classes 1, 3, 4 e 5, por versão da VS, classe, categoria, UF e bioma |

Colunas próprias de `P2_OR_poligonos`, para cada versão `<p>` (`vs22q`, `vs2224q`): `<p>_sobreposta_recooperar_ha`, `<p>_sobreposta_sicar_regularizacao_ha`,
`<p>_sobreposta_outros_projetos_ha`, `<p>_sobreposta_classes_anteriores_ha`, `<p>_n_precedentes_sobrepostos`, `<p>_sobreposta_na_classe_ha`,
`<p>_area_liquida_ha`, `<p>_uf_principal`, `<p>_ufs`, `<p>_bioma_principal`, `<p>_biomas`, `<p>_area_fora_ibge_ha`.

## Saídas das classes 6 a 8 (TI, UC e Manguezal: governança)

Em `Computo_Planaveg_2026\Insumos`, `Tier6_TI`, `Tier7_UC` e `Tier8_Manguezal` (ver `docs/tier6_8_governanca_publica.md`). Entradas: os cruzamentos
VS x território já calculados, um por versão da VS (`Cruzamento_Espacial_Vegetacao_Secundaria\VS-Terras_Indigenas`, `VS-Unidades_Conservacao` e `VS-Pro_Manguezal`;
uma peça por território x feição de VS qualificada, com `vs_id`, `vs_ano`, `vs_bioma`, `area_ha`) e, para as APAs, o CAR total dissolvido por UF
(`Analise_Territorial_CAR-INCRA_dissolvido\CAR_Brasil_Maio2026_Imovel_Area_Total_dissolvido_UF.gpkg`).

| Arquivo | Conteúdo |
|---|---|
| `Insumos\IN_TI_FUNAI20260507.gpkg`, `IN_UC_CNUC20260507.gpkg`, `IN_Manguezal_ProManguezal20260508.gpkg` | Peças elegíveis, uma camada por versão da VS (`vs22q_pedacos`, `vs2224q_pedacos`), com `id_peca` (`TI-<versão>-<n>`, `UC-...`, `MG-...`), os atributos do território, `area_ha_arq` (área gravada no cruzamento), `area_original_ha` (VS no território antes de tirar a área privada das APAs) e `area_ha_geo` (VS no território, área geodésica). UC: `apa` (verdadeiro nas APAs) e `area_privada_ha` (VS da APA que está em imóvel do CAR) |
| `Insumos\IN_<...>_resumo.csv` / `_excluidos.csv` | Nº de peças, de territórios e VS, por versão e grupo; o que ficou fora e por quê (TI em estudo ou encaminhada RI; zona de amortecimento; APA inteira em imóvel do CAR) |
| `Tier6_TI\P1_TI_FUNAI20260507.gpkg` (idem `Tier7_UC\P1_UC_CNUC20260507.gpkg`, `Tier8_Manguezal\P1_Manguezal_ProManguezal20260508.gpkg`) | `P1_<classe>_vs22q` e `P1_<classe>_vs2224q`: partes líquidas (polígonos simples), uma por peça x UF x bioma, disjuntas entre si e das classes de maior prioridade, com os atributos do território, `categoria`, `uf`, `bioma` (IBGE) e `area_ha`; `P1_<classe>_pecas_vs22q` e `_vs2224q`: tabela sem geometria com uma linha por peça |
| `T6_resumo.csv`, `T6_resumo_uf_bioma.csv`, `T6_conferencias.csv`, `T6_acumulado_classes_1_3_4_5_6.csv` (e `T7_...`, `T8_...`) | Resumo por versão e categoria; área líquida por versão, UF, bioma e categoria; conferências; área líquida acumulada das classes já processadas |

Colunas da tabela de peças, além dos atributos do território: `categoria` (TI: fase; UC: grupo, com "- APA (área pública)" nas APAs; Manguezal: "Manguezal"), `area_vs_original_ha`,
`area_vs_no_territorio_ha`, `sobreposta_<classe>_ha` para cada classe anterior (`recooperar`, `sicar_regularizacao`, `outros_projetos`, `or` e, na UC e no Manguezal, `ti` e `uc`),
`sobreposta_classes_anteriores_ha`, `n_precedentes_na_classe`, `sobreposta_na_classe_ha` e `area_liquida_ha`. Na camada de partes, o campo `uf` da UC vira `uf_cnuc`
(os nomes dos estados, como no CNUC) porque `uf` fica reservado à UF do IBGE.

## Saídas das classes 9 a 11 (APP, AUR e RL do CAR: governança)

Em `Computo_Planaveg_2026\Tier9_APP`, `Tier10_AUR` e `Tier11_RL` (ver `docs/tier9_11_car.md`). Entradas: os cruzamentos VS x APP/AUR/RL dos imóveis selecionados
(`Cruzamento_Espacial_Vegetacao_Secundaria\VS-Cadastro_Ambiental_Rural`), um arquivo por categoria (Habilitados, Analisados, Não analisados) e versão da VS
(`VS_2022_Imoveis_Selecionados_<categoria>_Qualificado.gpkg` e `VS_2024_Imoveis_Selecionados_<categoria>.gpkg`, a 2024 só com Amazônia e Cerrado), camadas
`VS_<APP|AUR|RL>_<categoria>` com `uf`, `cod_imovel`, `tipo`, `bioma`, `ano`, `des_condic`, `selecao_final` e `area_ha`. Cada UF ocupa um bloco contínuo de FIDs.

| Arquivo | Conteúdo |
|---|---|
| `Tier9_APP\P1_APP_CAR_Maio2026.gpkg` (idem `Tier10_AUR\P1_AUR_CAR_Maio2026.gpkg`, `Tier11_RL\P1_RL_CAR_Maio2026.gpkg`) | `P1_<classe>_vs22q` e `P1_<classe>_vs2224q`: partes líquidas (polígonos simples) por imóvel x UF x bioma, disjuntas entre si e das classes de maior prioridade. Atributos: `classe`, `categoria` (Habilitados, Analisados, Nao_Analisados), `cod_imovel`, `bioma_vs` (bioma da feição de VS, sem acento), `ano` (da VS), `uf_car` (UF do imóvel), `uf` e `bioma` (limites IBGE; "FORA" se sair deles), `area_ha` |
| `T9_resumo.csv`, `T9_resumo_uf.csv` (idem T10, T11) | Por versão e categoria (e por UF): `n_pecas`, `n_imoveis`, `area_pecas_arquivo_ha` (soma de `area_ha` do cruzamento), `sobreposta_no_imovel_ha` (sobreposição das peças do mesmo imóvel), `area_uniao_imovel_ha`, `sobreposta_<classe>_ha` para cada classe anterior (`recooperar`, `sicar_regularizacao`, `outros_projetos`, `or`, `ti`, `uc`, `manguezal`) e para cada bloco do CAR anterior (`sobreposta_app_h_ha`, `sobreposta_aur_h_ha`, `sobreposta_rl_h_ha`, `sobreposta_app_an_ha`, `sobreposta_aur_an_ha`; `h` = Habilitados, `an` = Analisados + Não analisados), `sobreposta_na_classe_ha` (entre imóveis do mesmo bloco) e `area_liquida_ha` |
| `T9_resumo_uf_bioma.csv`, `T9_conferencias.csv`, `T9_acumulado_classes_1_3_4_5_6_7_8_9.csv` (idem T10, T11) | Área líquida por versão, UF, bioma e categoria; conferências de cada UF; área líquida acumulada das classes já processadas |
| `Tier9_APP\_por_uf\` | Marcadores de retomada (`ok_<versão>_<UF>.txt`) e tabelas por UF; os GeoPackages por UF são apagados depois da consolidação |
