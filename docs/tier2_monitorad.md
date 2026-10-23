# Classe 2: MonitoRAD (IBAMA)

Segunda classe da hierarquia do Anexo 1, camada 2 (projetos, intencionalidade), depois do Recooperar. Incluída no
cômputo 2026 em 20/10/2026 (v1.0.0), de forma incremental, sem refazer as demais classes.

## Entrada

`GEODATABASE\GEOPACKAGE\IBAMA_Areas_Embargadas_MonitoRAD2026.gpkg`, entregue pelo IBAMA em outubro/2026:

| Camada | Conteúdo |
|---|---|
| `MonitoRAD_ANALISE` | Clusters de NDVI dentro de áreas embargadas, com `avaliacao` ("Com indício de recuperação" / "Sem indício de recuperação"), `value` (0, 1, 2), `seq_tad` (termo do embargo) e `Area_ha` |
| `MonitoRAD_EMBARGOS` | Polígonos dos embargos analisados (`NUM_TAD_1`, `dat_embarg`, `year`, `SIGLA_UF`, `municipio`, `AVALIA_`) |

## Decisões (20/10/2026)

1. Entram os polígonos com `avaliacao = 'Com indício de recuperação'`, qualquer que seja o `value`. O filtro é
   por igualdade exata (um filtro por substring pegaria também "Sem indício").
2. Cada peça é recortada pelo polígono do próprio embargo (`seq_tad` = `NUM_TAD_1`); o que fica fora dele não é usado.
3. Não pode haver sobreposição: onde embargos se sobrepõem fica o mais antigo (`dat_embarg`; empate: ordem no
   arquivo) e os mais novos ficam só com a parte fora dos mais antigos.
4. Casos conferidos: 6DPDXMZE (peças "Sem indício" duplicadas) e 634469-E (só "Sem indício") não entram; as duas
   peças "Com indício" do 757723-E (Lábrea/AM, 124,8 ha) estão a cerca de 50 km do polígono do embargo e são descartadas.
5. O MonitoRAD entra pela **área total do polígono**, sem cruzamento com a VS; por isso a classe 2 é igual nas duas
   versões da VS.

## Consolidação (`consolidar_monitorad.py`)

```
python consolidar_monitorad.py <...>\IBAMA_Areas_Embargadas_MonitoRAD2026.gpkg <...>\Insumos\IN_MonitoRAD_2026.gpkg
```

| Etapa | Peças | Embargos | Área (ha) |
|---|---:|---:|---:|
| Peças "Com indício de recuperação" | 2.392 | 1.814 | 303.626,1 |
| (-) parte fora do polígono do próprio embargo | | | -1.662,3 |
| (-) parte sobreposta a embargo mais antigo | | | -14.574,4 |
| **Insumo `IN_MONITORAD` (sem sobreposição interna)** | **2.361** | **1.793** | **287.389,4** |

Áreas geodésicas (GRS80). 29 peças saem inteiras (totalmente fora do próprio embargo ou totalmente sobrepostas). Campos
de `IN_MONITORAD`: `id_monitorad` (MRAD-nnnnn), `fonte`, `seq_tad`, `value`, `avaliacao`, `dat_embarg`, `year`,
`SIGLA_UF`, `municipio`, `AVALIA_`, `prec_ordem`, `area_monitorad_ha` (o `Area_ha` original, renomeado porque o
GeoPackage não aceita dois campos que só diferem na caixa), `area_orig_ha`, `fora_do_embargo_ha`, `area_no_embargo_ha`,
`sobreposta_embargo_anterior_ha` e `area_ha`. Embargos de 1999 a 2024, em 9 UFs da Amazônia Legal (PA, MT, AM, RO, RR,
TO, MA, AC, AP).

## Sobreposição com as outras camadas de projeto (antes da hierarquia)

Análise em `Validacao_MonitoRAD/` (`sobreposicao_projetos.py`, Albers IBGE): o MonitoRAD sobrepõe 1.139,3 ha ao
Recooperar (970,8 ha em embargos, 163,8 em reparação, 4,6 em licenciamento), 57.223,3 / 69.202,7 ha à VS dentro dos
embargos PANGIA da classe 4 (vs22q / vs2224q), 112,2 ha ao ORR e nada ao SICAR-regularização ou ao ICMBio. 1.170 dos
1.793 embargos também estão no cadastro PANGIA (mesmo termo); como a classe 2 precede a 4, essa área passa a contar
como MonitoRAD.

## Inclusão incremental (`incluir_monitorad_classe2.py`)

Cada classe k > 2 já era a sua fonte menos as classes 1..k-1, e a classe 2 estava vazia. Com Δ = MonitoRAD menos a
classe 1, a nova classe k é a classe k anterior menos Δ, o mesmo resultado de recalcular tudo. O script:

1. calcula Δ e grava `Tier2_MonitoRAD/P2_MonitoRAD_2026.gpkg` (camadas `P2_MONITORAD`, polígonos líquidos com UF e
   bioma principais, e `P2_MONITORAD_poligonos`, polígonos inteiros com `elegivel_computo = 1`);
2. subtrai Δ das classes 3 a 11 (SICAR-regularização uma vez; por versão, Outros projetos, OR, TI, UC, Manguezal e
   APP/AUR/RL nacionais e por UF), alterando só as feições que tocam Δ;
3. relê as feições alteradas e confere que a interseção restante com Δ é zero;
4. grava `MonitoRAD_incremental_resumo.csv`, `_alteracoes.csv`, `_estado.json` (retomada: rodar de novo não subtrai
   duas vezes) e `_log_monitorad_incremental.txt`.

| Versão da VS | vs22q | vs2224q |
|---|---:|---:|
| MonitoRAD já coberto pela classe 1, Recooperar (ha) | 1.139,3 | 1.139,3 |
| **Δ, classe 2 (ha)** | **286.250,1** | **286.250,1** |
| Retirado da classe 4, Outros projetos (PANGIA) (ha) | 57.109,8 | 69.015,0 |
| Retirado da classe 11, RL (ha) | 1.752,3 | 1.984,5 |
| Retirado da classe 9, APP (ha) | 150,0 | 149,3 |
| Retirado das classes 7 UC / 6 TI / 5 OR (ha) | 27,8 / 14,4 / 5,8 | 27,2 / 14,3 / 5,9 |
| Retirado das classes 3, 8 e 10 (ha) | 0 | 0 |
| **Efeito no total do cômputo (ha)** | **+227.190,1** | **+215.053,9** |

Interseção residual depois da gravação: 0 em todas as camadas. Depois, o reporte final foi regerado
(`gerar_geopackages_finais.py MONITORAD ... RL` e `--so-total`), com o GeoPackage
`Reporte_Final/Planaveg_2026_Projetos_MonitoRAD.gpkg`. Classe 2 por bioma: Amazônia 271.016,9 ha, Cerrado 15.214,2 ha,
Pantanal 19,0 ha.
