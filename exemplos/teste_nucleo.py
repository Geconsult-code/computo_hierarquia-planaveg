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


if __name__ == "__main__":
    testes = [v for k, v in sorted(globals().items()) if k.startswith("teste_")]
    for t in testes:
        t()
        print("OK ", t.__name__)
    print(f"{len(testes)} testes passaram.")
