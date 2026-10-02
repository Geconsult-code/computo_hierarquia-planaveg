# Changelog

Histórico reconstituído a partir do README e dos registros de trabalho. Datas de 2026.

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
