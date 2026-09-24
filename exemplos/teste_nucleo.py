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


def teste_config_embargos_pangia():
    import config_computo as c
    f = c.FONTES["embargos_pangia"]
    assert set(f["cruzamento"]) == set(c.VS_VERSOES)
    assert c.precedentes("OUTROS_PROJETOS") == ["RECOOPERAR", "SICAR_REGULARIZACAO"]      # MonitoRAD (inativo) não entra
    assert c.SAIDA_TIER4.name == "Tier4_Outros_Projetos"
    # nenhum campo pessoal segue para o cômputo
    assert not set(c.CAMPOS_EMBARGO_PANGIA.values()) & set(c.COLUNAS_PESSOAIS_PANGIA)
    for campo in ("nome_embar", "cpf_cnpj_e", "nome_imove"):
        assert campo in c.COLUNAS_PESSOAIS_PANGIA


def teste_embargos_harmonizar():
    import pandas as pd
    import config_computo as c
    from computo.embargos import harmonizar
    g = pd.DataFrame({"num_tad": ["A1", "A2", "A3"], "serie_tad": [" ", "B", "C"], "seq_tad": [0, 5, 7], "uf": ["PA", "AM", "MT"],
                      "cod_munici": [1, 2, 3], "municipio": ["X", " ", "Z"], "sit_desmat": ["D", "N", "D"],
                      "tipo_area": ["Desmatamento", " ", "Não se aplica"], "des_tipo_b": ["Amazonia", " ", "Cerrado"],
                      "operacao": [" ", "ONDA VERDE", " "],
                      "dat_embarg": pd.to_datetime(["2015-03-02", "2001-01-01", "1980-05-05"], utc=True)})
    h = harmonizar(g, c.CAMPOS_EMBARGO_PANGIA, c.PLACEHOLDERS_PANGIA, c.DATAS_SENTINELA, c.ANO_MIN, c.ANO_MAX)
    assert h["serie_tad"].isna().tolist() == [True, False, False] and h["municipio_fonte"].isna().tolist() == [False, True, False]
    assert h["tipo_area"].isna().tolist() == [False, True, True]                 # vazio e "Não se aplica" viram nulo
    assert h["ano_embargo"].tolist()[0] == 2015 and pd.isna(h["ano_embargo"].iloc[1]) and pd.isna(h["ano_embargo"].iloc[2])
    assert h["data_embargo"].iloc[0] == "2015-03-02" and pd.isna(h["data_embargo"].iloc[1])   # 2001-01-01 = data nula do sistema
    assert not [x for x in h.columns if x in c.COLUNAS_PESSOAIS_PANGIA]


def teste_pedacos_cruzamento_embargos():
    """Peças VS x embargo: ligação por idx_embargo (FID - 1), conferência da chave e união por embargo."""
    import tempfile
    import warnings
    from pathlib import Path
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    import shapely
    from computo.embargos import ler_pedacos_cruzamento, uniao_por_id
    from computo.geometria import area_ha
    d = Path(tempfile.mkdtemp())
    box = lambda x0, y0, x1, y1: shapely.segmentize(shapely.box(x0, y0, x1, y1), 0.005)
    chaves = pd.DataFrame({"id_proj": ["EMB-000001", "EMB-000002"], "num_tad": ["T1", "T2"], "serie_tad": ["", "S"], "seq_tad": ["0", "9"]},
                          index=pd.Index([1, 2], name="fid_orig"))
    pecas = gpd.GeoDataFrame({"idx_embargo": [0, 0, 1, 1], "num_tad": ["T1", "T1", "T2", "T2"], "serie_tad": [" ", " ", "S", "S"],
                              "seq_tad": [0, 0, 9, 9], "vs_id": [10, 11, 12, 13], "vs_ano": ["2022"] * 4,
                              "vs_bioma": ["Cerrado", "Cerrado", "Amazonia", "Amazonia"], "vs_fonte": ["2022_qualificada"] * 4},
                             geometry=[box(-50, -10, -49.99, -9.99), box(-49.995, -10, -49.985, -9.99),       # 1 e 2 se sobrepõem
                                       box(-40, -5, -39.99, -4.99), box(-39.9, -5, -39.9 + 1e-7, -5 + 1e-7)],  # 4 é desprezível
                             crs=4674)
    f = d / "cruz.gpkg"
    pecas.to_file(f, layer="L", driver="GPKG")
    ped = ler_pedacos_cruzamento(f, "L", chaves)
    assert len(ped) == 3 and set(ped["id_proj"]) == {"EMB-000001", "EMB-000002"}              # a peça desprezível saiu
    u = uniao_por_id(ped, ["EMB-000001", "EMB-000002", "EMB-000003"])
    assert u[2] is None
    esperado = area_ha([shapely.union_all([pecas.geometry[0], pecas.geometry[1]])])[0]
    assert abs(area_ha([u[0]])[0] - esperado) < 1e-6 * esperado < area_ha([pecas.geometry[0]])[0] + area_ha([pecas.geometry[1]])[0]
    # arquivo de embargos trocado: a chave não confere -> erro claro
    ruim = chaves.copy()
    ruim["num_tad"] = ["X1", "X2"]
    try:
        ler_pedacos_cruzamento(f, "L", ruim)
    except ValueError as e:
        assert "num_tad" in str(e)
    else:
        raise AssertionError("deveria recusar chave diferente")


def teste_tabela_celulas_sem_vs():
    import geopandas as gpd
    import shapely
    from computo.territorio import Limites, tabela_celulas
    uf = gpd.GeoDataFrame({"SIGLA_UF": ["AA", "BB"]}, geometry=[shapely.box(-51, -11, -50, -9), shapely.box(-50, -11, -49, -9)], crs=4674)
    bio = gpd.GeoDataFrame({"Bioma": ["Cerrado"]}, geometry=[shapely.box(-51, -11, -49, -9)], crs=4674)
    lim = Limites(uf, "SIGLA_UF", bio, "Bioma")
    g = shapely.segmentize(shapely.box(-50.2, -10.5, -49.8, -10.0), 0.005)
    liq = shapely.segmentize(shapely.box(-50.2, -10.5, -50.0, -10.0), 0.005)
    cel = tabela_celulas([g, None, g], [liq, None, None], lim)                  # None = embargo sem VS na versão
    assert set(cel["i"]) == {0, 2} and set(cel["uf"]) == {"AA", "BB"}
    assert list(cel.columns) == ["i", "uf", "bioma", "area_completa_ha", "area_liquida_ha"]
    assert cel[cel["i"] == 2]["area_liquida_ha"].sum() == 0 and cel[cel["i"] == 0]["area_liquida_ha"].sum() > 0


def teste_config_or():
    import config_computo as c
    f = c.FONTES["or"]
    assert f["arquivo"].startswith("ORR_") and f["camada"]
    assert c.precedentes("OR") == ["RECOOPERAR", "SICAR_REGULARIZACAO", "OUTROS_PROJETOS"]      # MonitoRAD (inativo) não entra
    assert c.SAIDA_TIER5.name == "Tier5_OR" and c.CELULA_VS_OR_GRAUS > 0
    assert set(c.BIOMA_IBGE_PARA_VS) >= {"Amazônia", "Caatinga", "Cerrado", "Mata Atlântica"}   # os 4 biomas do ORR


def teste_classes_anteriores_por_versao():
    """A classe 4 tem geometria por versão da VS: a classe 5 precisa saber qual subtrair."""
    import importlib
    m = importlib.import_module("2_camada2_projetos")
    sem = m._arquivos_classes()
    assert set(sem) == {"RECOOPERAR", "SICAR_REGULARIZACAO"}
    com = m._arquivos_classes("vs2224q")
    assert com["OUTROS_PROJETOS"][1] == "P2_OUTROS_PROJETOS_vs2224q"
    try:
        m._geoms_por_classe("OR")        # sem versão, a classe 4 não pode ser resolvida
    except (NotImplementedError, FileNotFoundError):
        pass
    else:
        raise AssertionError("deveria exigir a versão da VS")


def teste_pedacos_vs_poligono_multiparte():
    """Polígono de várias partes (como o ORR): as peças das partes, sob o mesmo id, somam a VS do polígono."""
    import tempfile
    from pathlib import Path
    import geopandas as gpd
    import numpy as np
    import shapely
    from computo.embargos import uniao_por_id
    from computo.geometria import area_ha
    from computo.vs import atributos_vs, pedacos_em_poligonos
    d = Path(tempfile.mkdtemp())
    box = lambda x0, y0, x1, y1: shapely.segmentize(shapely.box(x0, y0, x1, y1), 0.005)
    vs = gpd.GeoDataFrame({"id": [1, 2], "ano": ["2022", "2022"]}, geometry=[box(-50.00, -10.00, -49.98, -9.98), box(-40.10, -5.00, -40.05, -4.95)], crs=4674)
    vs.to_file(d / "vs.gpkg", layer="L", driver="GPKG")
    p1, p2, p3 = box(-50.01, -10.01, -49.99, -9.99), box(-40.08, -5.02, -40.02, -4.97), box(-30, -1, -29.99, -0.99)   # 3 partes do mesmo polígono
    partes = np.array([p1, p2, p3], dtype=object)
    ped = pedacos_em_poligonos(partes, np.array(["ORR-X"] * 3), np.array(["a", "b", "c"]), [("vs.gpkg", "L", "Cerrado", "2022")], d)
    assert set(ped["id_proj"]) == {"ORR-X"} and len(ped) == 2
    multi = shapely.MultiPolygon([p1, p2, p3])
    esperado = area_ha([shapely.intersection(multi, shapely.union_all(list(vs.geometry)))])[0]
    at = atributos_vs(ped, ["ORR-X"], [area_ha([multi])[0]], ["Cerrado"])
    assert abs(at["area_ha"].iloc[0] - esperado) < 1e-6 * esperado and at["tem"].iloc[0] == 1
    assert abs(area_ha([uniao_por_id(ped, ["ORR-X"])[0]])[0] - esperado) < 1e-6 * esperado


def teste_config_vs_camadas():
    import config_computo as c
    assert set(c.VS_CAMADAS) == set(c.VS_VERSOES)
    assert [b for _, _, b, _ in c.VS_CAMADAS["vs22q"]] == c.BIOMAS_VS and all(a == "2022" for *_, a in c.VS_CAMADAS["vs22q"])
    v24 = {b: a for _, _, b, a in c.VS_CAMADAS["vs2224q"]}
    assert v24["Amazonia"] == "2024" and v24["Cerrado"] == "2024"
    assert all(v24[b] == "2022" for b in ("Caatinga", "Mata_Atlantica", "Pampa", "Pantanal")) and len(v24) == 6


def _box(x0, y0, x1, y1, seg=0.01):
    import shapely
    return shapely.segmentize(shapely.box(x0, y0, x1, y1), seg)


def teste_subtrair_grandes():
    """Polígono grande (como o CAR dissolvido de uma UF): peça dentro sai inteira, na borda perde só a parte coberta, no buraco e fora fica."""
    import numpy as np
    import shapely
    from computo.geometria import area_ha
    from computo.hierarquia import subtrair_grandes
    grande = shapely.difference(_box(0, 0, 2, 2, 0.01), _box(1.0, 1.0, 1.4, 1.4, 0.01))          # quadrado 2x2 com buraco (>200 vértices)
    dentro, borda, no_buraco, fora = _box(0.2, 0.2, 0.3, 0.3), _box(1.9, 0.5, 2.1, 0.6), _box(1.1, 1.1, 1.2, 1.2), _box(3, 3, 3.1, 3.1)
    pecas = np.array([dentro, borda, no_buraco, fora], dtype=object)
    rest, ret = subtrair_grandes(pecas, [grande])
    a = area_ha(pecas)
    assert rest[0] is None and abs(ret[0] - a[0]) < 1e-6 * a[0]
    esperado = area_ha([shapely.intersection(borda, grande)])[0]
    assert abs(ret[1] - esperado) < 1e-6 * esperado and abs(area_ha([rest[1]])[0] - (a[1] - esperado)) < 1e-6 * a[1]
    assert ret[2] == 0 and ret[3] == 0 and rest[2] is not None and rest[3] is not None
    # sem partes ou sem peças: devolve o que recebeu
    r2, t2 = subtrair_grandes(pecas, [])
    assert t2.sum() == 0 and all(x is y for x, y in zip(r2, pecas))
    # peças None são ignoradas
    r3, t3 = subtrair_grandes(np.array([None, dentro], dtype=object), [grande])
    assert r3[0] is None and t3[0] == 0 and r3[1] is None and t3[1] > 0


def teste_celulas_uf_bioma():
    """Peça inteira numa célula (caminho rápido), peça que cruza a divisa de UF, e peça parcialmente fora dos limites ("FORA")."""
    import geopandas as gpd
    import numpy as np
    from computo.geometria import area_ha
    from computo.territorio import CelulasUFBioma, Limites
    uf = gpd.GeoDataFrame({"sigla": ["AA", "BB"]}, geometry=[_box(0, 0, 1, 2), _box(1, 0, 2, 2)], crs=4674)
    bio = gpd.GeoDataFrame({"nome": ["Norte", "Sul"]}, geometry=[_box(0, 1, 2, 2), _box(0, 0, 2, 1)], crs=4674)
    cel = CelulasUFBioma(Limites(uf, "sigla", bio, "nome"))
    assert len(cel.geoms) == 4
    pecas = np.array([_box(0.2, 0.2, 0.3, 0.3), _box(0.9, 1.4, 1.1, 1.6), _box(1.9, 0.5, 2.1, 0.6), None], dtype=object)
    fr = cel.fragmentar(pecas)
    a = area_ha([p for p in pecas[:3]])
    for i in range(3):
        assert abs(fr[fr["i"] == i]["geometry"].pipe(lambda s: area_ha(list(s))).sum() - a[i]) < 1e-6 * a[i]      # a soma dos fragmentos é a peça
    assert list(fr[fr["i"] == 0][["uf", "bioma"]].itertuples(index=False, name=None)) == [("AA", "Sul")]
    assert sorted(fr[fr["i"] == 1]["uf"]) == ["AA", "BB"] and set(fr[fr["i"] == 1]["bioma"]) == {"Norte"}
    fora = fr[(fr["i"] == 2) & (fr["uf"] == "FORA")]
    assert len(fora) == 1 and abs(area_ha(list(fora["geometry"])).sum() - a[2] / 2) < 1e-3 * a[2]                  # metade da peça está fora
    assert 3 not in set(fr["i"])                                                                                    # None não gera linha


def teste_elegibilidade_e_prioridades_governanca():
    import pandas as pd
    import config_computo as c
    from computo import governanca as gov
    ti = pd.DataFrame({"fase_ti": ["Regularizada", "Em Estudo", "Delimitada", "Homologada", "Encaminhada RI", "Declarada"],
                       "terrai_cod": [5, 1, 2, 3, 4, 6], "vs_id": [1, 2, 3, 4, 5, 6]})
    m, motivo = gov.elegiveis_ti(ti, c.ELEGIBILIDADE_TI)
    assert m.tolist() == [True, False, True, True, False, True] and motivo[1] != "" and motivo[0] == ""
    r = gov.prioridade_ti(ti, c.ELEGIBILIDADE_TI)
    assert len(set(r)) == len(ti) and r[0] < r[3] < r[5] < r[2]                         # regularizada > homologada > declarada > delimitada
    uc = pd.DataFrame({"limite": ["uc", "za", "UC ", "uc", "uc", "uc"],
                       "grupo": ["Uso Sustentável", "Proteção Integral", "Proteção Integral", "Uso Sustentável", "Uso Sustentável", "Uso Sustentável"],
                       "categoria": ["Floresta Nacional", "Parque Nacional", "Parque Nacional", "Área de Proteção Ambiental", "Reserva Extrativista", "Floresta Nacional"],
                       "esfera": ["Federal", "Federal", "Estadual", "Federal", "Estadual", "Estadual"],
                       "cria_ano": ["1990", "1990", "2000", "1980", "1985", "1970"], "cd_cnuc": list("abcdef"), "vs_id": range(6)})
    m, _ = gov.elegiveis_uc(uc, c.ELEGIBILIDADE_UC)
    assert m.tolist() == [True, False, True, True, True, True]                            # 'za' fora; espaço e maiúscula toleradas
    assert gov.eh_apa(uc, c.ELEGIBILIDADE_UC).tolist() == [False, False, False, True, False, False]
    r = gov.prioridade_uc(uc, c.ELEGIBILIDADE_UC)
    assert len(set(r)) == len(uc)
    assert r[2] < r[0] < r[3]          # proteção integral primeiro; dentro do uso sustentável, fora da APA antes da APA
    assert r[0] < r[4] and r[5] > r[0] and r[3] > r[4]    # federal antes de estadual; a APA (mesmo federal) depois das demais
    mg = pd.DataFrame({"Id": [9, 3, 3], "vs_id": [1, 5, 2]})
    r = gov.prioridade_manguezal(mg)
    assert len(set(r)) == 3 and r[2] < r[1] < r[0]


def teste_config_camada1():
    import config_computo as c
    from computo import anteriores
    assert c.precedentes("TI") == ["RECOOPERAR", "SICAR_REGULARIZACAO", "OUTROS_PROJETOS", "OR"]
    assert c.precedentes("UC")[-1] == "TI" and c.precedentes("MANGUEZAL")[-2:] == ["TI", "UC"]
    assert c.CAR_CATEGORIAS_PRECEDENCIA == ["Habilitados", "Analisados", "Nao_Analisados"]
    for k in ("ti", "uc", "manguezal"):
        assert set(c.FONTES[k]["cruzamento"]) == set(c.VS_VERSOES) and c.FONTES[k]["camada_cruzamento"]
    assert c.FONTES["car_total"]["campo_uf"] == "uf"
    assert c.ELEGIBILIDADE_TI["fases"][0] == "Regularizada" and "Em Estudo" not in c.ELEGIBILIDADE_TI["fases"]
    assert c.ELEGIBILIDADE_UC["limite"] == "uc"
    arq = anteriores.arquivos_classes("vs22q")
    assert arq["TI"][1] == "P1_TI_vs22q" and arq["UC"][1] == "P1_UC_vs22q" and arq["MANGUEZAL"][1] == "P1_MANGUEZAL_vs22q"
    assert arq["TI"][0].parent.name == "Tier6_TI" and arq["UC"][0].parent.name == "Tier7_UC" and arq["MANGUEZAL"][0].parent.name == "Tier8_Manguezal"
    assert "TI" not in anteriores.arquivos_classes()          # as classes 4 a 8 dependem da versão da VS


def teste_apa_area_publica():
    """APA menos o CAR total por UF: o que está em imóvel é privado; a UF sem feição é ignorada.

    ``apa[4]`` cobre também a recuperação SIGEF (decisão 24/09/2026): cai inteira num imóvel do CAR (sairia toda), mas
    metade dela é um imóvel público segundo o SIGEF e volta a ser pública."""
    import tempfile
    from pathlib import Path
    import geopandas as gpd
    import numpy as np
    import shapely
    import config_computo as c
    from computo import governanca as gov
    from computo.geometria import area_ha
    d = Path(tempfile.mkdtemp())
    car = gpd.GeoDataFrame({"uf": ["AC", "AM"]}, geometry=[shapely.MultiPolygon([_box(0, 0, 1, 1), _box(5, 5, 6, 6)]), _box(10, 10, 11, 11)], crs=4674)
    car.to_file(d / "car.gpkg", layer="CAR", driver="GPKG")
    sigef = gpd.GeoDataFrame({"id": [1]}, geometry=[_box(0, 0, 0.5, 0.5)], crs=4674)
    sigef.to_file(d / "sigef.gpkg", layer="sigefpublico_em_apa", driver="GPKG")
    ant = (c.RAIZ, dict(c.FONTES["car_total"]), dict(c.FONTES.get("sigef_publico_apa") or {}), list(c.UFS))
    try:
        c.RAIZ = d
        c.FONTES["car_total"] = {"arquivo": "car.gpkg", "camada": "CAR", "campo_uf": "uf"}
        c.FONTES["sigef_publico_apa"] = {"arquivo": "sigef.gpkg", "camada": "sigefpublico_em_apa"}
        c.UFS[:] = ["AC", "AM", "RO"]
        # apa[4]: inteira no imóvel AC (0,0,1,1) - sairia toda; metade dela (0,0,0.5,0.5) é imóvel público do SIGEF e volta
        apa = np.array([_box(0.5, 0.5, 1.5, 0.9), _box(5.2, 5.2, 5.4, 5.4), _box(20, 20, 20.1, 20.1), _box(10.5, 10.5, 11.5, 10.6),
                        _box(0, 0, 1, 0.5)], dtype=object)
        pub, ret = gov.apa_area_publica(apa)
    finally:
        c.RAIZ, c.FONTES["car_total"] = ant[0], ant[1]
        if ant[2]:
            c.FONTES["sigef_publico_apa"] = ant[2]
        else:
            c.FONTES.pop("sigef_publico_apa", None)
        c.UFS[:] = ant[3]
    a = area_ha(apa)
    assert abs(ret[0] - a[0] / 2) < 1e-3 * a[0] and abs(area_ha([pub[0]])[0] - a[0] / 2) < 1e-3 * a[0]      # metade da APA está no imóvel
    assert pub[1] is None and abs(ret[1] - a[1]) < 1e-6 * a[1]                                                # inteira no imóvel: sai
    assert ret[2] == 0 and pub[2] is not None                                                                 # fora do CAR: pública
    assert abs(ret[3] - a[3] / 2) < 1e-3 * a[3]
    assert pub[4] is not None and abs(area_ha([pub[4]])[0] - a[4] / 2) < 1e-3 * a[4]                          # SIGEF recupera metade
    assert abs(ret[4] - a[4] / 2) < 1e-3 * a[4]                                                                # ... e só a outra metade fica privada


def teste_sobrepoe_interiores():
    """O passo 3 só conta sobreposição de interiores: peças que se tocam na divisa (fragmentos de UF x bioma) não contam."""
    import importlib
    import numpy as np
    m = importlib.import_module("3_camada1_vs_governanca")
    a = np.array([_box(0, 0, 1, 1), _box(1, 0, 2, 1), _box(0.5, 0, 1.5, 1)], dtype=object)
    ii, jj, ar = m._sobrepoe(a, a)
    pares = {(int(i), int(j)) for i, j in zip(ii, jj) if i < j}
    assert pares == {(0, 2), (1, 2)} and (ar[[(i, j) in {(0, 2), (2, 0), (1, 2), (2, 1)} for i, j in zip(ii, jj)]] > 0).all()
    assert m.CLASSES_IMPLEMENTADAS == ["TI", "UC", "MANGUEZAL"] and set(m._CLASSES) == set(m.CLASSES_IMPLEMENTADAS)


def teste_liquido_independente():
    """Conferência por componente conexo = (união das peças - união das classes anteriores), sem dupla contagem entre peças."""
    import importlib
    import numpy as np
    import shapely
    from computo.geometria import area_ha
    m = importlib.import_module("3_camada1_vs_governanca")
    pecas = np.array([_box(0, 0, 2, 2), _box(1, 0, 3, 2), _box(10, 10, 11, 11), None], dtype=object)      # as duas primeiras se sobrepõem
    prec = np.array([_box(1.5, 0, 2.5, 2), _box(10, 10, 10.5, 11), _box(50, 50, 51, 51)], dtype=object)
    a_U, a_liq = m.liquido_independente(pecas, prec)
    U = shapely.union_all(list(pecas[:3])); P = shapely.union_all(list(prec))
    assert abs(a_U - area_ha([U])[0]) < 1e-6 * a_U
    esperado = area_ha([shapely.difference(U, P)])[0]
    assert abs(a_liq - esperado) < 1e-6 * esperado and a_liq < a_U
    assert m.liquido_independente(pecas, np.array([], dtype=object))[1] == a_U               # sem classes anteriores: a união inteira
    assert m.liquido_independente(np.array([None], dtype=object), prec) == (0.0, 0.0)


def teste_config_car():
    """Classes 9 a 11: fontes dos cruzamentos, pastas de saída e ordem das categorias."""
    c = cfg.FONTES["car_cruzamentos"]
    assert c["2022q"].format(categoria="Habilitados") == "VS_2022_Imoveis_Selecionados_Habilitados_Qualificado.gpkg"
    assert c["2024"].format(categoria="Analisados") == "VS_2024_Imoveis_Selecionados_Analisados.gpkg"
    assert c["camada"].format(classe="APP", categoria="Nao_Analisados") == "VS_APP_Nao_Analisados"
    assert c["biomas_2024"] == ["Amazonia", "Cerrado"]
    assert cfg.CAR_CATEGORIAS_PRECEDENCIA == ["Habilitados", "Analisados", "Nao_Analisados"]
    assert cfg.CAR_GRUPOS_PRECEDENCIA == [["Habilitados"], ["Analisados", "Nao_Analisados"]] and cfg.CAR_ROTULOS_GRUPOS == ["H", "AN"]
    from computo import car as _car
    assert [b[2] for b in _car.blocos()] == ["APP_H", "AUR_H", "RL_H", "APP_AN", "AUR_AN", "RL_AN"]
    assert cfg.precedentes("APP") == ["RECOOPERAR", "SICAR_REGULARIZACAO", "OUTROS_PROJETOS", "OR", "TI", "UC", "MANGUEZAL"]
    assert cfg.precedentes("RL")[-2:] == ["APP", "AUR"]
    from computo import anteriores, car
    assert car.CLASSES == ["APP", "AUR", "RL"] and set(anteriores.arquivos_classes("vs22q")) >= {"APP", "AUR", "RL"}


def teste_clip_seguro():
    """Sem falha do GEOS o resultado é o de clip_by_rect; com um anel degenerado devolve algo em vez de lançar erro."""
    import shapely
    from computo.geometria import clip_seguro
    g = _box(0, 0, 2, 2)
    r = clip_seguro(g, 1, 1, 3, 3)
    assert r.bounds == (1.0, 1.0, 2.0, 2.0) and abs(r.area - 1.0) < 1e-12          # área planar do recorte 1 x 1


def teste_reparar_saida_difference_invalida():
    """shapely.difference/intersection às vezes devolvem uma geometria tecnicamente inválida SEM lançar erro (achado na rodada nacional
    das classes 9 a 11: líquidos inválidos em SP, RO e TO). diferenca_robusta deve corrigir isso antes de devolver."""
    import numpy as np
    import shapely
    from computo.geometria import diferenca_robusta
    bowtie = shapely.Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])           # auto-interseção clássica: inválida
    assert not shapely.is_valid(bowtie)
    original = shapely.difference
    shapely.difference = lambda a, b, **kw: np.array([bowtie] * len(a), dtype=object)
    try:
        r = diferenca_robusta(np.array([_box(0, 0, 1, 1)], dtype=object), np.array([_box(5, 5, 6, 6)], dtype=object))
    finally:
        shapely.difference = original
    assert r[0] is not None and shapely.is_valid(r[0])


def teste_uniao_por_imovel():
    """Peças duplicadas e sobrepostas do mesmo imóvel viram uma só; imóveis, categorias e biomas diferentes ficam separados."""
    import numpy as np
    import pandas as pd
    import shapely
    from computo import car
    from computo.geometria import area_ha
    pecas = [_box(0, 0, 1, 1), _box(0, 0, 1, 1), _box(0.5, 0, 1.5, 1), _box(5, 5, 6, 6), _box(0.2, 0.2, 0.4, 0.4)]
    d = pd.DataFrame({"categoria": ["Habilitados"] * 3 + ["Analisados", "Habilitados"], "cod_imovel": ["A", "A", "A", "B", "C"],
                      "bioma_vs": ["Cerrado"] * 5, "ano": [2022] * 5, "uf_car": ["GO"] * 5, "des_condic": ["x"] * 5,
                      "geometry": pecas})
    d["area_ha_geo"] = area_ha(np.array(pecas, dtype=object))
    d["area_ha_arq"] = d["area_ha_geo"]
    u, n_vazias, n_corr, n_robusta = car.unir_por_imovel(d)
    assert len(u) == 3 and n_vazias == 0 and n_corr == 0 and n_robusta == 0
    a = u[u["cod_imovel"] == "A"].iloc[0]
    esperado = area_ha([_box(0, 0, 1.5, 1)])[0]
    assert a["n_pecas"] == 3 and abs(area_ha([a["geometry"]])[0] - esperado) < 1e-6 * esperado
    assert a["area_pecas_geo_ha"] > area_ha([a["geometry"]])[0] * 1.5           # a soma das peças é maior que a união
    pos = car.ordem_precedencia(u)
    ordem = list(u["cod_imovel"].iloc[np.argsort(pos)])
    assert ordem == ["A", "C", "B"]          # Habilitados (A antes de C), depois Analisados (B)


def teste_uniao_verificada_cobre_as_pecas():
    """A união de peças sobrepostas cobre cada peça; uma peça só devolve a própria peça."""
    import numpy as np
    import shapely
    from computo import car
    from computo.geometria import area_ha
    P = np.array([_box(0, 0, 1, 1), _box(0.5, 0.5, 1.5, 1.5), _box(0.5, 0.5, 1.5, 1.5), _box(3, 3, 4, 4)], dtype=object)
    u, n = car.uniao_verificada(P)
    assert n == 0 and abs(u.area - 2.75) < 1e-9            # 1 + 1 + 1 - 0,25 (planar, em graus2)
    assert all(shapely.area(shapely.difference(x, u)) < 1e-12 for x in P)
    u1, n1 = car.uniao_verificada(P[:1])
    assert u1 is P[0] and n1 == 0
    assert car.uniao_verificada(np.array([None], dtype=object)) == (None, 0)


def teste_uniao_grade_fallback_par_a_par():
    """GO, MG e PA pararam a UF inteira quando shapely.union_all lançou GEOSException mesmo com grade e make_valid (achado da rodada
    nacional v0.7.1). Com union_all sempre falhando (simulado), uniao_grade deve cair até a união par a par e ainda acertar a área."""
    import numpy as np
    import shapely
    from shapely.errors import GEOSException
    from computo import car
    from computo.geometria import area_ha
    pecas = np.array([_box(0, 0, 1, 1), _box(0.5, 0.5, 1.5, 1.5), _box(1, 1, 2, 2), _box(0.2, 0.2, 0.3, 0.3)], dtype=object)
    esperado = area_ha([car.uniao_grade(pecas)])[0]
    original = shapely.union_all

    def falha(*a, **kw):
        raise GEOSException("simulado: side location conflict")

    shapely.union_all = falha
    try:
        contador = []
        u = car.uniao_grade(pecas, contador)
    finally:
        shapely.union_all = original
    assert contador == [4]           # todos os níveis com union_all falharam (0 a 3); só a união par a par (nível 4) funcionou
    assert abs(area_ha([u])[0] - esperado) < 1e-9


def teste_sobreposicao_com_grandes():
    """Sobreposição das partes com polígonos grandes: só interseção real conta; toque na divisa não conta."""
    import numpy as np
    from computo import car
    from computo.geometria import area_ha
    grande = _box(0, 0, 2, 2, 0.01)
    partes = np.array([_box(1.5, 0.5, 2.5, 0.6), _box(2, 0, 3, 1), _box(5, 5, 6, 6)], dtype=object)
    esperado = area_ha([_box(1.5, 0.5, 2.0, 0.6)])[0]
    assert abs(car.sobreposicao_com_grandes(partes, [grande]) - esperado) < 1e-4 * esperado
    assert car.sobreposicao_com_grandes(partes, []) == 0.0
    assert car.sobreposicao_com_grandes(np.array([], dtype=object), [grande]) == 0.0


def teste_indice_fids_e_leitura_por_uf(tmp=None):
    """Índice de FIDs por UF (bloco contínuo) e leitura só do bloco da UF."""
    import tempfile
    import geopandas as gpd
    from pathlib import Path
    from computo import car
    tmp = Path(tempfile.mkdtemp())
    g = gpd.GeoDataFrame({"uf": ["AC"] * 3 + ["GO"] * 2, "cod_imovel": list("abcde")},
                         geometry=[_box(i, 0, i + 0.5, 0.5) for i in range(5)], crs=4674)
    arq = tmp / "x.gpkg"
    g.to_file(arq, layer="VS_APP_Habilitados", driver="GPKG")
    antigo = cfg.SAIDA_TIER9
    cfg.SAIDA_TIER9 = tmp / "t9"
    try:
        idx = car.indice_fids(arq, "VS_APP_Habilitados")
        assert idx == {"AC": (1, 3, 3), "GO": (4, 5, 2)}
        assert car.indice_fids(arq, "VS_APP_Habilitados") == idx           # segunda chamada: do cache em disco
        assert (cfg.SAIDA_TIER9 / "_indice_fids_car.json").exists()
    finally:
        cfg.SAIDA_TIER9 = antigo


def teste_processar_classe_car():
    """Uma classe do CAR: dedupe por imóvel, classe anterior subtraída, precedência entre categorias e conferências todas OK."""
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    from computo import car
    from computo.geometria import area_ha
    from computo.territorio import CelulasUFBioma, Limites
    uf = gpd.GeoDataFrame({"sigla": ["AA"]}, geometry=[_box(0, 0, 10, 10)], crs=4674)
    bio = gpd.GeoDataFrame({"nome": ["Norte"]}, geometry=[_box(0, 0, 10, 10)], crs=4674)
    cel = CelulasUFBioma(Limites(uf, "sigla", bio, "nome"))
    # imóvel H (Habilitados) com duas peças sobrepostas; imóvel N (Não analisados) sobrepõe H em 1 x 1 e a classe anterior em 1 x 1
    pecas = [_box(1, 1, 3, 3), _box(2, 1, 4, 3), _box(3, 1, 5, 3)]
    cats = ["Habilitados", "Habilitados", "Nao_Analisados"]
    cods = ["H", "H", "N"]
    d = pd.DataFrame({"categoria": cats, "cod_imovel": cods, "bioma_vs": ["Cerrado"] * 3, "ano": [2022] * 3, "uf_car": ["AA"] * 3,
                      "des_condic": ["x"] * 3, "classe": ["APP"] * 3, "geometry": pecas})
    d["area_ha_geo"] = area_ha(np.array(pecas, dtype=object))
    d["area_ha_arq"] = d["area_ha_geo"]
    anterior = np.array([_box(4.5, 1, 6, 3)], dtype=object)              # cobre 0,5 x 2 do imóvel N
    r = car.processar_classe("APP", d, [("TI", anterior)], cel, "teste", conferencia="completa")
    assert all(c["ok"] for c in r["conferencias"]), [c for c in r["conferencias"] if not c["ok"]]
    t = r["unidades"].set_index("cod_imovel")
    a1 = area_ha([_box(1, 1, 3, 3)])[0]
    assert abs(t.loc["H", "area_liquida_ha"] - area_ha([_box(1, 1, 4, 3)])[0]) < 1e-3 * a1       # H fica com a união das suas duas peças
    assert abs(t.loc["N", "sobreposta_na_classe_ha"] - area_ha([_box(3, 1, 4, 3)])[0]) < 1e-3 * a1     # a sobreposição fica com Habilitados
    assert abs(t.loc["N", "sobreposta_ti_ha"] - area_ha([_box(4.5, 1, 5, 3)])[0]) < 1e-3 * a1
    esperado_n = area_ha([_box(4, 1, 4.5, 3)])[0]
    assert abs(t.loc["N", "area_liquida_ha"] - esperado_n) < 1e-3 * a1
    p = r["partes"]
    assert set(p["uf"]) == {"AA"} and set(p["bioma"]) == {"Norte"} and abs(p["area_ha"].sum() - (t["area_liquida_ha"].sum())) < 1e-3 * a1


def teste_blocos_habilitados_primeiro():
    """Habilitados precedem Analisados/Nao_Analisados em qualquer classe: a RL de um Habilitado vence a APP de um Nao_Analisado;
    entre Analisados e Nao_Analisados a classe manda (APP de N vence a RL de A)."""
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    from computo import anteriores, car
    from computo.geometria import area_ha
    from computo.territorio import CelulasUFBioma, Limites
    uf = gpd.GeoDataFrame({"sigla": ["AA"]}, geometry=[_box(0, 0, 10, 10)], crs=4674)
    bio = gpd.GeoDataFrame({"nome": ["Norte"]}, geometry=[_box(0, 0, 10, 10)], crs=4674)
    cel = CelulasUFBioma(Limites(uf, "sigla", bio, "nome"))
    # RL de H, APP de N e RL de A, todas sobre o mesmo retângulo 1 x 1 a 3 x 3 (2 x 2 graus)
    ret = _box(1, 1, 3, 3)
    linhas = [("RL", "Habilitados", "H1", ret), ("APP", "Nao_Analisados", "N1", ret), ("RL", "Analisados", "A1", ret),
              ("RL", "Analisados", "A2", _box(6, 1, 7, 2)), ("APP", "Nao_Analisados", "N2", _box(6, 1, 7, 2))]
    d = pd.DataFrame({"classe": [x[0] for x in linhas], "categoria": [x[1] for x in linhas], "cod_imovel": [x[2] for x in linhas],
                      "bioma_vs": "Cerrado", "ano": 2022, "uf_car": "AA", "des_condic": "x", "geometry": [x[3] for x in linhas]})
    d["area_ha_geo"] = area_ha(np.array(d["geometry"].values, dtype=object))
    d["area_ha_arq"] = d["area_ha_geo"]
    fixas = anteriores.geoms_por_classe
    anteriores.geoms_por_classe = lambda *a, **k: []          # sem classes 1 a 8: só a precedência do CAR
    try:
        res = car.processar_uf_versao("AA", "vs22q", d, cel, conferencia="completa")
    finally:
        anteriores.geoms_por_classe = fixas
    for r in res.values():
        assert all(c["ok"] for c in r["conferencias"]), [c for c in r["conferencias"] if not c["ok"]]
    liq = {cl: r["unidades"].set_index("cod_imovel")["area_liquida_ha"] for cl, r in res.items()}
    a = area_ha([ret])[0]
    assert abs(liq["RL"]["H1"] - a) < 1e-3 * a                      # o Habilitado fica com a área inteira
    assert liq["RL"]["A1"] < 1e-6 and liq["APP"]["N1"] < 1e-6      # os outros dois perdem tudo para o Habilitado
    b = area_ha([_box(6, 1, 7, 2)])[0]
    assert abs(liq["APP"]["N2"] - b) < 1e-3 * b and liq["RL"]["A2"] < 1e-6     # dentro de A + N a classe manda (APP > RL)
    u = res["RL"]["unidades"].set_index("cod_imovel")
    assert abs(u.loc["A1", "sobreposta_rl_h_ha"] - a) < 1e-3 * a
    assert abs(u.loc["A2", "sobreposta_app_an_ha"] - b) < 1e-3 * b


if __name__ == "__main__":
    testes = [v for k, v in sorted(globals().items()) if k.startswith("teste_")]
    for t in testes:
        t()
        print("OK ", t.__name__)
    print(f"{len(testes)} testes passaram.")
