"""Teste de integridade da configuração e do pacote (não depende dos dados).

Executar da raiz do repositório:  python exemplos/teste_nucleo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config_computo as cfg
import computo


def teste_ordem_unica_e_contigua():
    ordens = [c["ordem"] for c in cfg.HIERARQUIA]
    assert ordens == sorted(ordens), "HIERARQUIA deve estar em ordem crescente"
    assert len(set(ordens)) == len(ordens), "ordens repetidas"
    assert ordens == list(range(1, len(ordens) + 1)), "ordens devem ser 1..N sem lacunas"


def teste_codigos_unicos():
    codigos = [c["codigo"] for c in cfg.HIERARQUIA]
    assert len(set(codigos)) == len(codigos)


def teste_camadas_coerentes_com_relatorio():
    # Camada 2 (projetos) antes da Camada 1 (VS legalmente protegida)
    camadas = [c["camada"] for c in cfg.HIERARQUIA]
    assert camadas == sorted(camadas, reverse=True), "projetos (camada 2) devem preceder a VS (camada 1)"
    cod = {c["codigo"]: c for c in cfg.HIERARQUIA}
    assert cod["RECOOPERAR"]["ordem"] == 1
    assert cod["APP"]["ordem"] < cod["AUR"]["ordem"] < cod["RL"]["ordem"], "CAR: APP > AUR > RL"


def teste_monitorad_desativado():
    cod = {c["codigo"]: c for c in cfg.HIERARQUIA}
    assert cod["MONITORAD"]["ativo"] is False
    assert "MONITORAD" not in [c["codigo"] for c in cfg.classes_ativas()]
    assert cfg.FONTES["monitorad"] is None


def teste_precedentes():
    assert cfg.precedentes("RECOOPERAR") == []
    assert cfg.precedentes("SICAR_REGULARIZACAO") == ["RECOOPERAR"]          # MonitoRAD inativo
    assert cfg.precedentes("RL") == [c["codigo"] for c in cfg.classes_ativas() if c["codigo"] != "RL"]


def teste_arranjos_somam_meta():
    total = sum(a["meta_mha"] or 0 for a in cfg.ARRANJOS.values())
    assert total == cfg.META_NACIONAL_MHA, f"metas dos arranjos ({total}) != meta nacional"


def teste_ufs():
    assert len(cfg.UFS) == 27 and len(set(cfg.UFS)) == 27


def teste_pacote():
    assert computo.__version__


# ---------------------------------------------------------------------------
# Tier-1 (Recooperar): testes sintéticos, sem depender dos dados
# ---------------------------------------------------------------------------
def teste_config_recooperar():
    assert set(cfg.PRECEDENCIA_RECOOPERAR) == set(cfg.ELEGIBILIDADE_RECOOPERAR) - {"campo_status", "campo_etapa"}
    assert set(cfg.VS_VERSOES) == {"vs22q", "vs2224q"}
    assert not set(cfg.CAMPOS_RECOOPERAR.values()) & set(cfg.COLUNAS_PESSOAIS_RECOOPERAR), "dado pessoal no mapa de campos"


def teste_elegibilidade_recooperar():
    import pandas as pd
    from computo.elegibilidade import filtrar_recooperar
    E = cfg.ELEGIBILIDADE_RECOOPERAR
    rep = pd.DataFrame({
        "status_are": ["Em recuperação", "Em recuperação", "Em recuperação", "Pendente de recuperação", "Pendente de recuperação",
                       "Recuperada", "Em recuperação"],
        "descricao_": ["Projeto aprovado - em execução", "Em recuperação - sem projeto", "Indícios de que a área está em trajetória de recuperação",
                       "Projeto protocolado - não analisado", "Projeto reprovado", "ATUALIZAR", "ATUALIZAR"]})
    r = filtrar_recooperar(rep, "reparacao", E, "status_are", "descricao_")
    assert r["elegivel"].tolist() == [1, 0, 0, 1, 1, 1, 0], r["elegivel"].tolist()
    emb = pd.DataFrame({"status_are": ["Em recuperação", "Recuperada", "Pendente de recuperação"], "descricao_": ["x", "y", "z"]})
    assert filtrar_recooperar(emb, "embargo", E, "status_are", "descricao_")["elegivel"].tolist() == [1, 1, 0]
    lic = pd.DataFrame({"status_are": ["ATUALIZAR", None], "descricao_": ["ATUALIZAR", None]})
    assert filtrar_recooperar(lic, "licenciamento", E, "status_are", "descricao_")["elegivel"].tolist() == [1, 1]


def teste_ano_inicio():
    import pandas as pd
    from computo.elegibilidade import ano_inicio
    g = pd.DataFrame({
        "dt_projeto": ["2015-03-01T00:00:00", None, None, None, "1901-01-01T00:00:00"],
        "dt_assinat": ["2019-01-01T00:00:00", "2001-01-01T00:00:00", "2018-05-05T03:00:00", None, None],
        "dt_documen": ["2024-01-01T00:00:00", "2022-02-02T00:00:00", None, None, "2023-01-01T00:00:00"]})
    ano, fonte = ano_inicio(g, cfg.ANO_INICIO_CADEIA, cfg.DATAS_SENTINELA, cfg.ANO_MIN, cfg.ANO_MAX)
    assert ano.tolist() == [2015, 2022, 2018, pd.NA, 2023]
    assert fonte.tolist() == ["dt_projeto", "dt_documen (proxy)", "dt_assinat", pd.NA, "dt_documen (proxy)"]


def teste_liquido_por_precedencia():
    import numpy as np
    import shapely
    from computo.geometria import area_ha
    from computo.hierarquia import liquido_por_precedencia
    seg = lambda g: shapely.segmentize(g, 0.005)       # arestas curtas: área geodésica aditiva, como nos dados reais
    a = seg(shapely.box(-50.00, -10.00, -49.90, -9.90))
    b = seg(shapely.box(-49.95, -10.00, -49.85, -9.90))     # metade sobreposta a a
    c = seg(shapely.box(-50.00, -10.00, -49.90, -9.90))     # idêntico a a
    d = seg(shapely.box(-40.00, -10.00, -39.95, -9.95))     # isolado
    geoms = np.array([a, b, c, d], dtype=object)
    liq, sobre, n_prec = liquido_por_precedencia(geoms, np.array([0, 1, 2, 3]))
    aa = area_ha(geoms)
    assert abs(sobre[0]) < 1e-9 and n_prec[0] == 0                      # a: maior precedência, nada retirado
    assert abs(sobre[1] - aa[0] / 2) < 1e-3 * aa[0] / 2                 # b perde a metade que é de a
    assert liq[2] is None and abs(sobre[2] - aa[2]) < 1e-6              # c idêntico: some
    assert abs(sobre[3]) < 1e-9
    uniao = area_ha([shapely.union_all(geoms)])[0]
    assert abs(sum(area_ha([g])[0] for g in liq if g is not None) - uniao) < 1e-6 * uniao   # líquidos somam a união
    # a ordem de precedência muda quem fica com a área sobreposta
    liq2, _, _ = liquido_por_precedencia(geoms, np.array([1, 0, 2, 3]))
    assert area_ha([liq2[0]])[0] < aa[0] and abs(area_ha([liq2[1]])[0] - aa[1]) < 1e-6


def teste_celulas_uf_bioma():
    import geopandas as gpd
    import shapely
    from computo.geometria import area_ha
    from computo.territorio import Limites
    uf = gpd.GeoDataFrame({"SIGLA_UF": ["AA", "BB"]}, geometry=[shapely.box(-51, -11, -50, -9), shapely.box(-50, -11, -49, -9)], crs=4674)
    bio = gpd.GeoDataFrame({"Bioma": ["Cerrado"]}, geometry=[shapely.box(-51, -11, -49.5, -9)], crs=4674)   # não cobre a borda leste
    lim = Limites(uf, "SIGLA_UF", bio, "Bioma")
    # segmentize: a área geodésica só é aditiva quando as arestas são curtas (como nos dados reais);
    # numa caixa com arestas de 100 km, dividir a caixa muda o traçado geodésico e a soma difere ~2e-5.
    g = shapely.segmentize(shapely.box(-50.2, -10.5, -49.2, -10.0), 0.005)      # cruza a divisa AA/BB e sai do bioma
    cel = lim.celulas(g)
    rotulos = {(u, b) for u, b, _ in cel}
    assert rotulos == {("AA", "Cerrado"), ("BB", "Cerrado"), ("BB", "FORA")}, rotulos
    assert abs(sum(area_ha([c])[0] for _, _, c in cel) - area_ha([g])[0]) < 1e-6 * area_ha([g])[0]   # nada se perde


def teste_sem_dado_pessoal_no_insumo():
    import config_computo as c
    for campo in ("administra", "cpf_cnpj_a", "cpf_cnpj_e", "editor_alt", "editor_cad", "numeropess"):
        assert campo in c.COLUNAS_PESSOAIS_RECOOPERAR


def teste_elegibilidade_car_regularizacao():
    import pandas as pd
    import config_computo as c
    from computo.elegibilidade import filtrar_car_regularizacao
    E = c.ELEGIBILIDADE_CAR_REG
    g = pd.DataFrame({
        "des_condic": ["Analisado, em regularizacao ambiental (Lei n 12.651/2012)",       # como vem no arquivo (sem acento e sem "º")
                       "Analisado, em regularização ambiental (Lei nº 12.651/2012)",       # como está no config
                       "Analisado, sem pendência", "Analisado, em regularizacao ambiental (Lei n 12.651/2012)",
                       "Analisado, em regularizacao ambiental (Lei n 12.651/2012)"],
        "ind_status": ["AT", "PE", "AT", "CA", "SU"]})
    r = filtrar_car_regularizacao(g, E, area_ha=[1.0, 2.0, 3.0, 4.0, 0.0])
    assert r["elegivel"].tolist() == [1, 1, 0, 0, 0], r
    assert "condição" in r["motivo"].iloc[2] and "status" in r["motivo"].iloc[3] and "desprez" in r["motivo"].iloc[4]
    assert all(t in c.PRECEDENCIA_CAR_REG for t in ("APP_ESCADINHA", "ARL_AVERBADA", "ARL_APROVADA_NAO_AVERBADA", "ARL_PROPOSTA"))
    assert c.PRECEDENCIA_CAR_REG[0] == "APP_ESCADINHA"                                     # APP > RL (seção 4.3)


def teste_subtrair_precedentes():
    import numpy as np
    import shapely
    from computo.geometria import area_ha
    from computo.hierarquia import subtrair_precedentes
    seg = lambda g: shapely.segmentize(g, 0.005)
    pecas = np.array([seg(shapely.box(-50.00, -10.00, -49.90, -9.90)),        # metade coberta
                      seg(shapely.box(-50.00, -10.00, -49.95, -9.95)),        # totalmente coberta
                      seg(shapely.box(-40.00, -10.00, -39.95, -9.95))], dtype=object)   # isolada
    prec = np.array([seg(shapely.box(-49.95, -10.05, -49.80, -9.80)), seg(shapely.box(-50.10, -10.10, -49.94, -9.94))], dtype=object)
    rest, ret = subtrair_precedentes(pecas, prec)
    a = area_ha(pecas)
    assert rest[1] is None and abs(ret[1] - a[1]) < 1e-3 * a[1]
    assert abs(ret[2]) < 1e-9 and abs(area_ha([rest[2]])[0] - a[2]) < 1e-6
    assert abs(ret[0] + area_ha([rest[0]])[0] - a[0]) < 1e-6 * a[0]                  # retirada + restante = inteira
    assert shapely.intersection(rest[0], shapely.union_all(prec)).area < 1e-12          # o restante não toca os precedentes
    r2, ret2 = subtrair_precedentes(pecas, np.array([], dtype=object))                  # sem classes anteriores: nada muda
    assert (ret2 == 0).all() and all(x is not None for x in r2)


def teste_pedacos_vs_em_poligonos(tmp=None):
    """Cruzamento com camadas de VS brutas: peças, atributos e camada sem CRS declarado."""
    import tempfile
    from pathlib import Path
    import geopandas as gpd
    import numpy as np
    import shapely
    from computo.geometria import area_ha
    from computo.vs import atributos_vs, pedacos_em_poligonos
    d = Path(tempfile.mkdtemp())
    box = lambda x0, y0, x1, y1: shapely.segmentize(shapely.box(x0, y0, x1, y1), 0.005)
    # VS "2022": dois polígonos; VS "2024": um, sobre o mesmo local do segundo (não deve ser somado se for outra camada/bioma)
    vs22 = gpd.GeoDataFrame({"id": [1, 2], "ano": ["2022", "2022"]}, geometry=[box(-50.00, -10.00, -49.98, -9.98), box(-49.90, -10.00, -49.85, -9.95)], crs=4674)
    vs24 = gpd.GeoDataFrame({"id": [7], "ano": ["2024"]}, geometry=[box(-49.90, -10.00, -49.88, -9.98)], crs=4674)
    f22, f24 = d / "vs22.gpkg", d / "vs24.gpkg"
    vs22.to_file(f22, layer="L22", driver="GPKG")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        vs24.set_crs(None, allow_override=True).to_file(f24, layer="L24", driver="GPKG")   # camada sem CRS declarado
    # polígonos: A (cobre o VS 1 e metade do 2), B no mesmo imóvel (sobrepõe A no VS 2), C longe de tudo
    A = box(-50.02, -10.02, -49.88, -9.97); B = box(-49.92, -10.02, -49.86, -9.96); C = box(-30, -10, -29.9, -9.9)
    geoms = np.array([A, B, C], dtype=object)
    ids = np.array(["A", "B", "C"]); grupos = np.array(["im1", "im1", "im2"])
    camadas = [("vs22.gpkg", "L22", "Cerrado", "2022"), ("vs24.gpkg", "L24", "Amazonia", "2024")]
    ped = pedacos_em_poligonos(geoms, ids, grupos, camadas, d)
    assert set(ped["id_proj"]) == {"A", "B"} and "C" not in set(ped["id_proj"])
    at = atributos_vs(ped, ids, area_ha(geoms), ["Amazonia", "Cerrado"])
    esperado_A = area_ha([shapely.intersection(A, shapely.union_all([vs22.geometry[0], vs22.geometry[1], vs24.geometry[0]]))])[0]
    assert abs(at["area_ha"].iloc[0] - esperado_A) < 1e-6 * esperado_A
    assert at["tem"].tolist() == [1, 1, 0] and at["n_pol"].iloc[0] == 3 and at["pct"].iloc[2] == 0
    assert at["ha_amazonia"].iloc[0] > 0 and at["ha_cerrado"].iloc[0] > at["ha_amazonia"].iloc[0]
    # união: a VS 2024 está dentro do VS 2022 nº 2; a área da VS de A não pode ultrapassar a área do polígono
    assert at["area_ha"].iloc[0] <= area_ha([A])[0]


def teste_config_vs_camadas():
    import config_computo as c
    assert set(c.VS_CAMADAS) == set(c.VS_VERSOES)
    assert [b for _, _, b, _ in c.VS_CAMADAS["vs22q"]] == c.BIOMAS_VS and all(a == "2022" for *_, a in c.VS_CAMADAS["vs22q"])
    v24 = {b: a for _, _, b, a in c.VS_CAMADAS["vs2224q"]}
    assert v24["Amazonia"] == "2024" and v24["Cerrado"] == "2024"
    assert all(v24[b] == "2022" for b in ("Caatinga", "Mata_Atlantica", "Pampa", "Pantanal")) and len(v24) == 6


if __name__ == "__main__":
    testes = [v for k, v in sorted(globals().items()) if k.startswith("teste_")]
    for t in testes:
        t()
        print("OK ", t.__name__)
    print(f"{len(testes)} testes passaram.")
