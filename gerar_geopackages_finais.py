"""Gera os GeoPackages finais de reporte do cômputo 2026, no padrão do cômputo 2025
(``Computo_Planaveg_2025``), acrescentando o atributo de UF/estado pedido em 28/09/2026.

Cada classe ativa da hierarquia (1 Recooperar, 3 SICAR-Regularização, 4 Outros Projetos, 5 OR, 6 TI, 7 UC,
8 Manguezal, 9 APP, 10 AUR, 11 RL) é dissolvida por UF x bioma (uma peça por combinação, juntando todas as
categorias - exceto no CAR, ver abaixo). As classes de governança/CAR (6 a 11) já têm peças líquidas com
``uf``/``bioma`` prontos (saída dos passos 3 e 3b); as classes de projeto (1, 3, 4, 5) só têm o polígono
inteiro (líquido, já sem sobreposição com classes anteriores - conferido: geometria bate com
``area_liquida_ha`` peça a peça), então são fragmentadas nas células UF x bioma com
``computo.territorio.CelulasUFBioma`` antes de dissolver.

A pedido do usuário (28/09/2026), as classes do CAR (9 APP, 10 AUR, 11 RL) saem em 3 camadas cada -
Habilitados, Analisados e Não analisados - em vez de uma única camada por classe.

Sem a etapa de Florestas Públicas Não Destinadas (CNFP) - pendente (ver ``PENDENCIAS`` em
``config_computo.py``): ``area_wit_fpnd = 0`` e ``computo = area_tnc`` (área líquida da hierarquia, sem
desconto de FPND). ``Area_ha`` é a área geodésica recalculada da geometria final (pode diferir ligeiramente
de ``computo`` por arredondamento, como no padrão 2025).

Gera as duas versões da VS (vs22q e vs2224q) - decisão do usuário em 28/09/2026.

Saída: ``GEODATABASE\\GEOPACKAGE\\Computo_Planaveg_2026\\Reporte_Final\\``
    - ``Planaveg_2026_Total.gpkg`` (camadas ``Reporte_Planaveg_Total_vs22q`` / ``_vs2224q``)
    - ``Planaveg_2026_Projetos_Recooperar.gpkg``, ``..._SICAR_Regularizacao.gpkg``,
      ``..._Projetos_Outros.gpkg``, ``..._Projetos_ORR.gpkg``
    - ``Planaveg_2026_Terras_Indigenas.gpkg``, ``..._Unidade_Conservacao.gpkg``, ``..._Manguezal.gpkg``
    - ``Planaveg_2026_Imoveis_APP.gpkg``, ``..._AUR.gpkg``, ``..._RL.gpkg`` (cada um com 3 camadas -
      ``_Habilitados``, ``_Analisados``, ``_Nao_Analisados`` - x 2 versões da VS)

Execução:  python gerar_geopackages_finais.py [CODIGO ...]
    sem argumento: todas as classes ativas (monta o Total ao final). Com um ou mais códigos (RECOOPERAR,
    SICAR_REGULARIZACAO, OUTROS_PROJETOS, OR, TI, UC, MANGUEZAL, APP, AUR, RL): só essas (para testar/retomar uma
    classe por vez - recomendado, já que APP e RL sozinhas levam horas). Depois que todas as classes ativas
    tiverem sido geradas (em quantas execuções separadas for preciso): ``python gerar_geopackages_finais.py
    --so-total`` monta o Total relendo as camadas já gravadas, sem reprocessar nenhuma geometria (rápido).
    Log: Reporte_Final/_log_geopackages_finais.txt.
"""
from __future__ import annotations

import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

import config_computo as cfg
from computo import anteriores, geometria, io_dados as io
from computo.territorio import CelulasUFBioma, Limites

SAIDA = cfg.SAIDA / "Reporte_Final"
ARQ_LOG = SAIDA / "_log_geopackages_finais.txt"

# classes do CAR: saem em 3 camadas (categoria), as demais em 1
CAR = ["APP", "AUR", "RL"]
CATEGORIAS_CAR = ["Habilitados", "Analisados", "Nao_Analisados"]
SUFIXO_CATEGORIA = {"Habilitados": "Habilitados", "Analisados": "Analisados", "Nao_Analisados": "Nao_Analisados"}

# classes de projeto (camada 2): só têm o polígono inteiro, precisam ser fragmentadas em células UF x bioma
PROJETO = ["RECOOPERAR", "SICAR_REGULARIZACAO", "OUTROS_PROJETOS", "OR"]
# RECOOPERAR e SICAR_REGULARIZACAO: mesma geometria nas duas versões da VS (não dependem da VS - ver computo/anteriores.py)
PROJETO_INDEPENDENTE_DE_VS = ["RECOOPERAR", "SICAR_REGULARIZACAO"]

# nome do arquivo final por classe (padrão 2025, com os nomes novos para SICAR_REGULARIZACAO e MANGUEZAL)
ARQUIVO_FINAL = {
    "RECOOPERAR": "Planaveg_2026_Projetos_Recooperar.gpkg",
    "SICAR_REGULARIZACAO": "Planaveg_2026_SICAR_Regularizacao.gpkg",
    "OUTROS_PROJETOS": "Planaveg_2026_Projetos_Outros.gpkg",
    "OR": "Planaveg_2026_Projetos_ORR.gpkg",
    "TI": "Planaveg_2026_Terras_Indigenas.gpkg",
    "UC": "Planaveg_2026_Unidade_Conservacao.gpkg",
    "MANGUEZAL": "Planaveg_2026_Manguezal.gpkg",
    "APP": "Planaveg_2026_Imoveis_APP.gpkg",
    "AUR": "Planaveg_2026_Imoveis_AUR.gpkg",
    "RL": "Planaveg_2026_Imoveis_RL.gpkg",
}

_HIER = {c["codigo"]: c for c in cfg.HIERARQUIA}


def log(msg, arquivo=ARQ_LOG):
    io.log(msg, arquivo)


def _celulas() -> CelulasUFBioma:
    lim = anteriores.carregar_limites()
    return CelulasUFBioma(lim, log=log)


def _pecas_diretas(codigo: str, versao: str) -> gpd.GeoDataFrame:
    """Classes de governança sem CAR (TI, UC, Manguezal): peças líquidas já com uf/bioma/area_ha prontos.
    Volume tratável (até ~440 mil peças por versão) - lê o GeoPackage nacional de uma vez."""
    arq, camada = anteriores.arquivos_classes(versao)[codigo]
    g = io.ler_camada(arq, camada, colunas=["uf", "bioma", "area_ha", "geometry"])
    return g


def _pecas_car_por_uf(codigo: str, versao: str) -> gpd.GeoDataFrame:
    """Classes do CAR (APP, AUR, RL): até ~5,6 milhões de peças nacionalmente - ler tudo de uma vez arriscaria
    memória. Em vez disso, lê e dissolve bloco a bloco pelos GeoPackages por UF que o passo 3b já mantém
    (``_por_uf``, ver ``3b_camada1_car.py``: ``manter_por_uf=True``), a mesma estratégia de "um bloco por vez"
    que o resto do pipeline usa para essas classes. Dissolvir cada bloco por uf x bioma x categoria antes de
    concatenar já reduz cada UF a poucas dezenas de linhas; o dissolve final (em ``gerar_classe``) só re-une
    esses poucos resultados, então o resultado é idêntico a dissolver tudo de uma vez."""
    from computo import car
    pasta = car.PASTAS[codigo] / "_por_uf"
    camada = f"P1_{codigo}_{versao}"
    partes = []
    for uf in cfg.UFS:
        f = pasta / f"P1_{codigo}_{versao}_{uf}.gpkg"
        if not f.exists():
            continue
        g = io.ler_camada(f, camada, colunas=["uf", "bioma", "categoria", "area_ha", "geometry"])
        if not len(g):
            continue
        diss = g.dissolve(by=["uf", "bioma", "categoria"], aggfunc={"area_ha": "sum"}, as_index=False)
        partes.append(diss)
        del g
    if not partes:
        raise FileNotFoundError(f"nenhum GeoPackage por UF encontrado em {pasta} para {codigo} {versao}")
    return gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=partes[0].crs)


def _pecas_via_clip(codigo: str, versao: str | None, celulas: CelulasUFBioma) -> gpd.GeoDataFrame:
    """Classes de projeto (1, 3, 4, 5): só o polígono inteiro (líquido) - fragmenta nas células UF x bioma."""
    arquivos = anteriores.arquivos_classes(versao)
    if codigo not in arquivos:
        # RECOOPERAR/SICAR_REGULARIZACAO não dependem de versão (ver arquivos_classes): usa a entrada sem versão
        arquivos = anteriores.arquivos_classes(None)
    arq, camada = arquivos[codigo]
    # só a geometria importa aqui: a área de cada fragmento é recalculada depois do recorte (geometria.area_ha),
    # não a partir de um atributo de área do polígono inteiro (que tem nomes diferentes conforme a classe: por
    # exemplo "area_liquida_ha" em RECOOPERAR/SICAR_REGULARIZACAO/OUTROS_PROJETOS, "area_ha" em OR).
    g = io.ler_camada(arq, camada, colunas=["geometry"])
    t0 = time.time()
    frag = celulas.fragmentar(g.geometry.values)
    frag["area_ha"] = geometria.area_ha(frag["geometry"].values)
    frag = gpd.GeoDataFrame(frag, geometry="geometry", crs=g.crs)
    log(f"{codigo} {versao or ''}: {len(g):,} polígonos -> {len(frag):,} fragmentos UF x bioma ({time.time() - t0:.0f}s)")
    return frag


def _dissolver(g: gpd.GeoDataFrame, chave: list[str]) -> gpd.GeoDataFrame:
    """Uma peça por combinação de ``chave`` (uf, bioma); soma area_ha, união da geometria. Só mantém as colunas
    necessárias antes de dissolver (evita que colunas extras - ex.: categoria, já filtrada para um único valor -
    quebrem o aggfunc)."""
    g = g.loc[g.geometry.notna() & ~g.geometry.is_empty, chave + ["area_ha", "geometry"]].copy()
    diss = g.dissolve(by=chave, aggfunc={"area_ha": "sum"}, as_index=False)
    return diss


def _linhas_finais(diss: gpd.GeoDataFrame, codigo: str, categoria: str | None) -> gpd.GeoDataFrame:
    """Monta as colunas do padrão 2025 (+ uf): hierarquia, Bioma, area_tnc, area_wit_fpnd, computo, tier, Area_ha, uf."""
    h = _HIER[codigo]
    nome = h["nome"] if categoria is None else f"{h['nome']} - {categoria.replace('_', ' ')}"
    out = gpd.GeoDataFrame({
        "hierarquia": nome,
        "Bioma": diss["bioma"].values,
        "uf": diss["uf"].values,
        "area_tnc": diss["area_ha"].values,
        "area_wit_fpnd": 0.0,
        "computo": diss["area_ha"].values,
        "tier": h["ordem"],
        "Area_ha": geometria.area_ha(diss.geometry.values),
    }, geometry=diss.geometry.values, crs=diss.crs)
    if categoria is not None:
        out["categoria"] = categoria
    return out


def gerar_classe(codigo: str, celulas: CelulasUFBioma | None, resultado: dict) -> None:
    """Gera o(s) GeoPackage(s) de uma classe (as duas versões da VS) e guarda as linhas em ``resultado`` (para o Total)."""
    versoes = [None] if codigo in PROJETO_INDEPENDENTE_DE_VS else list(cfg.VS_VERSOES)
    out_arq = SAIDA / ARQUIVO_FINAL[codigo]
    # ``primeira=True`` recria o ARQUIVO INTEIRO (ver io.gravar_camada), não só a camada - por isso o controle é
    # por arquivo de saída (uma vez por execução desta classe), nunca por nome de camada: cada camada (classe x
    # categoria x versão) só é escrita uma vez aqui, então uma flag por nome de camada nunca "já visto" e recriaria
    # o arquivo a cada nova camada, apagando as anteriores (bug encontrado na 1a execução real: só a última camada
    # sobrevivia no .gpkg).
    arquivo_iniciado = False
    for versao in versoes:
        if codigo in PROJETO:
            pecas = _pecas_via_clip(codigo, versao, celulas)
        elif codigo in CAR:
            pecas = _pecas_car_por_uf(codigo, versao)
        else:
            pecas = _pecas_diretas(codigo, versao)
        rotulos_versao = list(cfg.VS_VERSOES) if versao is None else [versao]
        categorias = CATEGORIAS_CAR if codigo in CAR else [None]
        for categoria in categorias:
            sub = pecas if categoria is None else pecas[pecas["categoria"] == categoria]
            diss = _dissolver(sub, chave=["uf", "bioma"])
            finais = _linhas_finais(diss, codigo, categoria)
            for v in rotulos_versao:
                camada = codigo if categoria is None else f"{codigo}_{SUFIXO_CATEGORIA[categoria]}"
                camada = f"{camada}_{v}"
                io.gravar_camada(finais, out_arq, camada, primeira=not arquivo_iniciado)
                arquivo_iniciado = True
                resultado.setdefault(v, []).append(finais.assign(_classe=codigo, _categoria=categoria or ""))
                log(f"{codigo}{' ' + categoria if categoria else ''} {v}: {len(finais)} peças, "
                    f"{finais['computo'].sum():,.1f} ha -> {out_arq.name} [{camada}]")


def gerar_total(resultado: dict) -> None:
    out_arq = SAIDA / "Planaveg_2026_Total.gpkg"
    for i, versao in enumerate(cfg.VS_VERSOES):
        partes = resultado.get(versao, [])
        if not partes:
            continue
        total = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=partes[0].crs)
        total = total.drop(columns=["_classe", "_categoria"])
        camada = f"Reporte_Planaveg_Total_{versao}"
        # mesmo cuidado de gerar_classe: primeira=True recria o arquivo inteiro - só na 1a versão desta execução,
        # senão a 2a versão apagaria a camada da 1a.
        io.gravar_camada(total, out_arq, camada, primeira=(i == 0))
        log(f"TOTAL {versao}: {len(total)} peças, {total['computo'].sum():,.1f} ha -> {out_arq.name} [{camada}]")


def montar_total_de_arquivos() -> None:
    """Monta o Total lendo de volta as camadas finais já gravadas em cada arquivo .gpkg de classe, sem reprocessar
    nenhuma geometria. Existe porque, na prática, as classes foram geradas uma de cada vez (execuções separadas,
    por segurança de memória e para poder conferir cada uma contra os resumos do pipeline antes de seguir para a
    próxima - RL sozinha levou ~3h30) - nesse caso o dict ``resultado`` de ``gerar_classe`` (só em memória) não
    sobrevive entre processos, então ``gerar_total`` (que depende dele) nunca é chamada por ``main``. Esta função
    é o caminho alternativo: relê as 8+18=26 camadas já gravadas (7 classes simples x 2 versões, RECOOPERAR e
    SICAR_REGULARIZACAO x 2 rótulos de versão mesmo sendo a mesma geometria - ver ``PROJETO_INDEPENDENTE_DE_VS`` -,
    e APP/AUR/RL x 3 categorias x 2 versões) e concatena por versão. Uso: ``python gerar_geopackages_finais.py
    --so-total``, depois que todas as classes ativas já tiverem sido geradas (com ``gerar_classe``/``main``)."""
    out_arq = SAIDA / "Planaveg_2026_Total.gpkg"
    codigos = [c["codigo"] for c in cfg.classes_ativas()]
    faltando = [c for c in codigos if not (SAIDA / ARQUIVO_FINAL[c]).exists()]
    if faltando:
        raise FileNotFoundError(f"faltam classes ainda não geradas em {SAIDA}: {', '.join(faltando)}")
    for i, versao in enumerate(cfg.VS_VERSOES):
        partes = []
        for codigo in codigos:
            arq = SAIDA / ARQUIVO_FINAL[codigo]
            categorias = CATEGORIAS_CAR if codigo in CAR else [None]
            for categoria in categorias:
                camada = codigo if categoria is None else f"{codigo}_{SUFIXO_CATEGORIA[categoria]}"
                camada = f"{camada}_{versao}"
                g = io.ler_camada(arq, camada)
                if "categoria" not in g.columns:
                    g["categoria"] = pd.NA
                partes.append(g)
        total = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=partes[0].crs)
        camada = f"Reporte_Planaveg_Total_{versao}"
        # mesmo cuidado de gerar_classe/gerar_total: primeira=True recria o arquivo inteiro - só na 1a versão.
        io.gravar_camada(total, out_arq, camada, primeira=(i == 0))
        log(f"TOTAL (de arquivos) {versao}: {len(total)} peças, {total['computo'].sum():,.1f} ha -> "
            f"{out_arq.name} [{camada}]")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--so-total"]:
        SAIDA.mkdir(parents=True, exist_ok=True)
        log("=== gerar_geopackages_finais: --so-total (montagem a partir dos arquivos já gerados) ===")
        montar_total_de_arquivos()
        log("fim")
        return 0
    codigos = [a.upper() for a in argv] or [c["codigo"] for c in cfg.classes_ativas()]
    SAIDA.mkdir(parents=True, exist_ok=True)
    log(f"=== gerar_geopackages_finais: {', '.join(codigos)} ===")
    celulas = _celulas() if any(c in PROJETO for c in codigos) else None
    resultado: dict[str, list] = {}
    for codigo in codigos:
        t0 = time.time()
        gerar_classe(codigo, celulas, resultado)
        log(f"{codigo}: concluído em {time.time() - t0:.0f}s")
    if set(codigos) == {c["codigo"] for c in cfg.classes_ativas()}:
        gerar_total(resultado)
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
