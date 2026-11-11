"""Verificações estáticas do notebook de análise: executado, sem erro e sem dados reais."""
import json

from src import config

ARQ = config.RAIZ / "notebooks" / "01_analise_exploratoria.ipynb"
NB = json.loads(ARQ.read_text(encoding="utf-8"))
CODIGO = [c for c in NB["cells"] if c["cell_type"] == "code"]


def test_notebook_executado_sem_erros():
    assert CODIGO and all(c["execution_count"] for c in CODIGO)
    erros = [o for c in CODIGO for o in c["outputs"] if o["output_type"] == "error"]
    assert not erros


def test_notebook_declara_dados_simulados():
    abertura = "".join(NB["cells"][0]["source"]).lower()
    assert "simulad" in abertura and "nenhum incidente exibido aqui é real" in abertura


def test_notebook_nao_le_dados_privados():
    fonte = "\n".join("".join(c["source"]) for c in CODIGO)
    assert "DATA_PRIVATE" not in fonte and "incidentes_tratados_real" not in fonte
    assert "assert all(checagens.values())" in fonte  # trava de reprodutibilidade
