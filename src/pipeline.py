"""Pipeline completo: catálogo -> incidentes -> análise -> grafo -> banco.

Uso:
  python -m src.pipeline                 # usa FONTE_INCIDENTES do .env
  python -m src.pipeline --fonte simulado
  python -m src.pipeline --fonte real_anonimizado

Fonte "real_anonimizado" lê data/raw/servicenow/incidentes_sanitizados.csv
(gerado por src.sanitizar_servicenow no ambiente do trabalho).
Os CSVs publicáveis (só agregados + incidentes sem texto livre quando reais)
são gravados em data/processed/.
"""
from __future__ import annotations

import argparse

import pandas as pd

from src import analise, catalogo, config, db, extracao, grafo, perfis
from src.simular_incidentes import simular


def carregar_incidentes(fonte: str) -> pd.DataFrame:
    if fonte == "simulado":
        inc, gab = simular()
        inc.to_csv(config.ARQ_INCIDENTES_SIM, index=False)
        gab.to_csv(config.DATA_PROCESSED / "incidentes_simulados_gabarito.csv", index=False)
    else:
        arq = config.DATA_RAW / "servicenow" / "incidentes_sanitizados.csv"
        inc = pd.read_csv(arq)
        # pseudônimo vindo do "caller" é o atendente, não o participante: cada INC conta como 1 pessoa
        if "pseud_origem" in inc:
            sem_cpf = inc["pseud_origem"] != "cpf"
            inc.loc[sem_cpf, "participante_pseud"] = "inc:" + inc.loc[sem_cpf, "inc_id"]
    inc["opened_at"] = pd.to_datetime(inc["opened_at"])
    inc["origem"] = fonte
    return inc


def funil(inc: pd.DataFrame, tec: pd.DataFrame) -> pd.DataFrame:
    total = len(inc)
    so = inc["so"] if "so" in inc else pd.Series("android", index=inc.index)
    login = inc[inc["classe_erro"] != "fora_escopo"]
    android = login[so.loc[login.index] == "android"]
    sdk_txt = int((tec.get("sdk_origem") == "texto").sum()) if "sdk_origem" in tec else int(tec["sdk"].notna().sum())
    etapas = [
        ("Incidentes exportados", total),
        ("Falhas de login (exclui outros serviços)", len(login)),
        ("... em Android (exclui iOS e sem plataforma)", len(android)),
        ("... classificadas como técnicas", len(tec)),
        ("... com marca identificada", int(tec["marca"].notna().sum())),
        ("... com modelo casado ao catálogo Play Console (R2)", int(tec["model_id"].notna().sum())),
        ("... com versão do Android citada no texto", sdk_txt),
        ("Participantes distintos (técnicas em Android)", tec["participante_pseud"].nunique()),
        ("Cruzados com Instana (R1) - pendente", 0),
    ]
    return pd.DataFrame([{"ordem": i + 1, "etapa": e, "n": n, "pct_total": 100 * n / total}
                         for i, (e, n) in enumerate(etapas)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", default=config.FONTE_INCIDENTES, choices=["simulado", "real_anonimizado"])
    ap.add_argument("--sem-banco", action="store_true", help="só gera os CSVs")
    ap.add_argument("--gravar-banco-real", action="store_true",
                    help="com fonte real, grava também no MariaDB local (por padrão, não grava)")
    a = ap.parse_args()
    real = a.fonte != "simulado"
    # Resultados reais NUNCA vão para data/processed (versionado); ficam em data/private/real
    destino = config.DATA_PRIVATE / "real" if real else config.DATA_PROCESSED
    destino.mkdir(parents=True, exist_ok=True)

    print("1/6 Catálogo Play Console")
    cat = catalogo.ler_catalogo()
    dsdk = catalogo.explodir_sdk(cat)
    print(f"    {len(cat):,} modelos | base = {cat['install_n'].sum():,} aparelhos")

    print(f"2/6 Incidentes ({a.fonte})")
    inc = carregar_incidentes(a.fonte)
    inc, mapping = extracao.enriquecer(inc, cat)

    print("3/6 Taxas por grupo")
    pop = analise.populacao(cat, dsdk)
    tec = analise.preparar_incidentes(inc, pop)
    tx = analise.taxas(tec, pop)
    print(f"    taxa geral (técnicos em Android): {analise.taxa_geral(tec, cat):.2f} por mil aparelhos")

    print("4/6 Modelo de Poisson")
    poi = analise.modelo_poisson(tec, pop)

    print("5/6 Grafo")
    G = grafo.construir(tec, pop)
    nos, arestas = grafo.para_tabelas(G)
    print(f"    {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")

    fun = funil(inc, tec)
    perf = perfis.construir(inc, cat, pop, tec)
    print(f"    {int(perf['tem_taxa'].sum())} perfis com taxa, {int((perf['status'] == 'critico').sum())} críticos")

    inc.to_csv(destino / f"incidentes_tratados_{a.fonte}.csv", index=False)
    for nome, df in [("resultados_taxas", tx), ("modelo_poisson", poi), ("grafo_nos", nos),
                     ("grafo_arestas", arestas), ("lineage", fun), ("perfis", perf)]:
        df.to_csv(destino / f"{nome}.csv", index=False)
    print(f"    CSVs em {destino}")

    if a.sem_banco or (real and not a.gravar_banco_real):
        return
    print("6/6 Gravando no banco")
    eng = db.get_engine()
    catalogo_db = cat.drop(columns=[c for c in cat.columns if c not in db.devices_catalog.c])
    for df, nome in [(catalogo_db, "devices_catalog"), (dsdk, "device_sdk"), (mapping, "model_mapping"),
                     (inc, "incidents"), (extracao.tabela_regras(), "error_class"), (fun, "lineage"),
                     (tx, "resultados_taxas"), (poi, "modelo_poisson"), (nos, "grafo_nos"),
                     (arestas, "grafo_arestas"), (perf, "perfis")]:
        db.gravar(df, nome, eng)
    db.recriar_tabelas(eng, ["instana_requests"])
    print("    OK:", eng.url.render_as_string(hide_password=True))


if __name__ == "__main__":
    main()
