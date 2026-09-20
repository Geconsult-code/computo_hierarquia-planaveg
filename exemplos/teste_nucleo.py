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


if __name__ == "__main__":
    testes = [v for k, v in sorted(globals().items()) if k.startswith("teste_")]
    for t in testes:
        t()
        print("OK ", t.__name__)
    print(f"{len(testes)} testes passaram.")
