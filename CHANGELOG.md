# Changelog

Histórico reconstituído a partir do README e dos registros de trabalho. Datas de 2026.

## [1.0.0] - 21/10
### Adicionado
- MonitoRAD (IBAMA) como classe 2 (decisões de 20/10/2026): polígonos "Com indício de recuperação" de
  `MonitoRAD_ANALISE`, qualquer `value`, recortados pelo polígono do próprio embargo, sem sobreposição (fica o embargo
  mais antigo) e pela área total, sem cruzamento com a VS. Com isso as 11 classes da hierarquia estão ativas.
- `consolidar_monitorad.py`: gera `Insumos/IN_MonitoRAD_2026.gpkg` (2.361 polígonos, 1.793 embargos, 287.389,4 ha).
- `incluir_monitorad_classe2.py`: inclusão incremental; Δ = MonitoRAD menos a classe 1 (286.250,1 ha) entra na classe 2
  (`Tier2_MonitoRAD/P2_MonitoRAD_2026.gpkg`) e é subtraído das classes 3 a 11, com conferência de interseção residual zero.
- `docs/tier2_monitorad.md`; `gerar_geopackages_finais.py` gera `Planaveg_2026_Projetos_MonitoRAD.gpkg`; teste
  `teste_monitorad_ativo`.
### Alterado
- `config_computo.py`: MONITORAD ativo, fonte `FONTES["monitorad"]` e `SAIDA_TIER2`.
- Reporte final regerado: Total 8.824.118,4 ha (vs22q) e 9.026.415,6 ha (vs2224q), +227.190,1 e +215.053,9 ha em
  relação à v0.9.0. Classe 4 -57.109,8 / -69.015,0 ha (PANGIA); RL -1.752,3 / -1.984,5 ha; APP -150,0 / -149,3 ha;
  UC, TI e OR menos de 30 ha cada.
- Documentação: README, metodologia, Anexo 1, dicionário de dados, classes 3 e 4. `metodologia.md` da raiz e de
  `docs/` voltam a ser iguais; a de `docs/` estava desatualizada (ORR 2025, sem ICMBio e sem as seções 10 a 12).

## [0.9.0] - 16/10
### Adicionado
- Projetos do ICMBio na classe 4 (Outros projetos), pela área total dos polígonos, sem cruzamento com a VS
  (decisões de 14/10/2026): GEF Terrestre (7 camadas) e Restauração Ecológica (só essa camada do arquivo de
  Restauração); em cada grupo de polígonos sobrepostos fica o maior (nas cópias, o da camada `_ORR`); entre os
  dois arquivos fica o GEF. Insumo consolidado: `Insumos/IN_ICMBio_2026.gpkg` (3.655 polígonos, 38.019,1 ha).
- `incluir_icmbio_classe4.py`: inclusão incremental, sem refazer o cômputo. Δ = ICMBio menos as classes 1, 3 e 4
  entra na classe 4 e é subtraído das classes 5 a 11 (camadas nacionais e por UF), com conferência de interseção
  residual zero, retomada e resumos `ICMBio_incremental_*`.
### Alterado
- Reporte final (`Reporte_Final/`) regerado: Total 8.596.928,3 ha (vs22q) e 8.811.361,7 ha (vs2224q),
  +8.201,2 e +8.210,9 ha em relação à v0.8.0. Classe 4 +37.257,5 / +37.263,1 ha; OR -28.196,1 / -28.202,3 ha;
  UC -811,1 / -803,0 ha; TI -48,8 / -46,6 ha; demais classes < 0,2 ha.
- `config_computo.py`: ICMBio deixa de constar como adiado em `FONTES` e `PENDENCIAS`.

## [0.8.0] - outubro
### Adicionado
- `gerar_geopackages_finais.py`: reporte final em `Reporte_Final/` (Total + um GeoPackage por classe,
  duas versões da VS, atributo de UF; classes do CAR em Habilitados, Analisados e Não analisados) e
  modo `--so-total`.
- Documentação reorganizada: README com status, resultados, pipeline e tempos; metodologia com
  produto final, pendências e uso posterior; este CHANGELOG.
### Removido
- Cópias antigas de `metodologia.md` e `hierarquia_anexo1.md` na raiz (as versões válidas estão em `docs/`).
- Logs de execução (`_run_*_stdout.txt`) do repositório; passaram a ser ignorados pelo `.gitignore`.

## [0.7.x] - 24 a 26/09
- Classes 9 (APP), 10 (AUR) e 11 (RL): `3b_camada1_car.py`, por UF e versão da VS, com retomada,
  Habilitados à frente de Analisados e Não analisados.
- Classe 5 trocada para o ORR 2026 (86.281 projetos).
- APAs (classe 7): parte do CAR que é imóvel público pelo SIGEF volta a contar como área pública
  (`SIGEF_Publico_em_APA.gpkg`).
- 0.7.4: `3b_camada1_car.py --consolidar` aceita UF sem nenhuma peça de AUR ou RL (ex.: AC e BA em AUR).

## [0.4.0 - 0.6.x] - 21 a 24/09
- Classe 4 (Outros projetos): embargos PANGIA pela interseção com a VS (regras E1 a E4).
- Classe 5 (OR) com o ORR 2025, pela área total dos polígonos.
- Classes 6 (TI), 7 (UC) e 8 (Manguezal): `3_camada1_vs_governanca.py`; regras T1 e U1.

## [0.3.x] - 21/09
- Classe 3 (SICAR - em regularização ambiental): área a recompor de APP e RL do CAR Junho26;
  precedência APP > RL averbada > RL aprovada não averbada > RL proposta; área fora do IBGE como "FORA".

## [0.2.x] - 21/09
- Classe 1 (Recooperar 2026) com a área completa dos polígonos elegíveis (regras D2 a D4) e precedência
  Licenciamento > Reparação > Embargo > Outras.

## [0.1.0] - 20/09
- Esqueleto do repositório: configuração, núcleo `computo/`, scripts numerados e documentação da hierarquia.
