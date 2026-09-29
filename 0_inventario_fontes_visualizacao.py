"""
0_inventario_fontes_visualizacao.py
Cômputo Planaveg 2026 - atributos de visualização (etapa 0: diagnóstico)

Só LÊ metadados: camadas, CRS, tipo de geometria, nº de feições, campos e,
para campos categóricos "interessantes", até 40 valores distintos.
NÃO processa, NÃO grava nada além do relatório .txt.

Uso (env geo):  python 0_inventario_fontes_visualizacao.py
Saída: inventario_fontes_visualizacao.txt (mesma pasta do script)
"""
from pathlib import Path
import warnings
import pyogrio

warnings.filterwarnings("ignore")

# Pastas varridas recursivamente (*.gpkg). Acrescente aqui as pastas de
# CNUC, FUNAI e INCRA (assentamentos/quilombolas) se estiverem fora delas.
RAIZES = [
    Path(r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE"),
    Path(r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\INCRA-CAR\Analise_Conformidade"),
]
IGNORAR_PASTAS = ("Vegetacao_Secundaria",)  # VS é pesada e não é fonte de flag
SAIDA = Path(__file__).with_name("inventario_fontes_visualizacao.txt")

MAX_VALORES = 40
MAX_FEICOES_DISTINCT = 500_000  # acima disso não faz SELECT DISTINCT
CAMPOS_ALVO = ("esfera", "categ", "grupo", "nivel", "nm_", "nome", "hierarq",
               "tier", "classe", "status", "fase", "tipo", "uf", "sigla",
               "bacia", "regiao", "modulo", "etapa", "fonte", "origem", "camada",
               "projeto", "programa")


def valores_distintos(caminho, camada, campo):
    sql = (f'SELECT DISTINCT "{campo}" AS v FROM "{camada}" '
           f'LIMIT {MAX_VALORES + 1}')
    df = pyogrio.read_dataframe(caminho, sql=sql, read_geometry=False)
    vals = df["v"].tolist()
    extra = " ..." if len(vals) > MAX_VALORES else ""
    return f"{vals[:MAX_VALORES]}{extra}"


def main():
    linhas = []
    arquivos = sorted(
        p for r in RAIZES if r.exists() for p in r.rglob("*.gpkg")
        if not any(ig.lower() in parte.lower()
                   for parte in p.parts[:-1] for ig in IGNORAR_PASTAS)
    )
    for r in RAIZES:
        if not r.exists():
            linhas.append(f"!! pasta não encontrada: {r}")
    print(f"{len(arquivos)} arquivos a inventariar", flush=True)
    for i, arq in enumerate(arquivos, 1):
        print(f"[{i}/{len(arquivos)}] {arq.name}", flush=True)
        linhas.append(f"\n##### {arq}  ({arq.stat().st_size/1e6:,.1f} MB)")
        try:
            camadas = pyogrio.list_layers(arq)
        except Exception as e:
            linhas.append(f"   !! erro ao listar camadas: {e}")
            continue
        for nome, _ in camadas:
            try:
                info = pyogrio.read_info(arq, layer=nome)
            except Exception as e:
                linhas.append(f"  == {nome}: !! {e}")
                continue
            crs = (info.get("crs") or "")[:60]
            linhas.append(f"  == {nome} | {info['geometry_type']} | "
                          f"{info['features']:,} feições | {crs}")
            for campo, tipo in zip(info["fields"], info["dtypes"]):
                linha = f"     - {campo} ({tipo})"
                if (tipo == "object"
                        and any(k in campo.lower() for k in CAMPOS_ALVO)
                        and info["features"] <= MAX_FEICOES_DISTINCT):
                    try:
                        linha += f" -> {valores_distintos(arq, nome, campo)}"
                    except Exception as e:
                        linha += f" -> !! {e}"
                linhas.append(linha)
    SAIDA.write_text("\n".join(linhas), encoding="utf-8")
    print(f"{len(arquivos)} arquivos inventariados -> {SAIDA}")


if __name__ == "__main__":
    main()
