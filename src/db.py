"""Conexão com o banco e definição das tabelas.

O esquema é definido uma única vez aqui (SQLAlchemy Core) e funciona tanto no
MariaDB (uso principal) quanto em SQLite (para reprodução rápida). O arquivo
sql/schema.sql é gerado a partir deste módulo: `python -m src.db --ddl`.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String,
                        Table, Text, create_engine)
from sqlalchemy.engine import URL, Engine
from sqlalchemy.schema import CreateTable

from src import config  # noqa: F401  (carrega o .env)

metadata = MetaData()

devices_catalog = Table(
    "devices_catalog", metadata,
    Column("model_id", Integer, primary_key=True, autoincrement=False,
           comment="ID sequencial atribuído na carga"),
    Column("brand", String(60), index=True),
    Column("device", String(80), comment="codinome do aparelho"),
    Column("manufacturer", String(80)),
    Column("model_name", String(160), index=True),
    Column("ram_min_mb", Integer),
    Column("ram_max_mb", Integer),
    Column("ram_faixa", String(20)),
    Column("form_factor", String(30)),
    Column("soc", String(80)),
    Column("gpu", String(120)),
    Column("abis", String(120)),
    Column("sdk_list", String(80), comment="versões de SDK separadas por ;"),
    Column("sdk_max", Integer),
    Column("install_n", Integer, comment="aparelhos ativos com o app"),
    Column("anr_rate", Float),
    Column("crash_rate", Float),
    comment="Catálogo do Google Play Console (uma linha por modelo)",
)

device_sdk = Table(
    "device_sdk", metadata,
    Column("model_id", Integer, primary_key=True, autoincrement=False),
    Column("sdk", Integer, primary_key=True, autoincrement=False),
    Column("android", String(10)),
    Column("peso", Float, comment="fração da base do modelo atribuída à versão"),
    Column("install_est", Float, comment="instalações estimadas (premissa REGRA_SDK)"),
    comment="Modelo x versão do Android (base estimada)",
)

model_mapping = Table(
    "model_mapping", metadata,
    Column("texto_normalizado", String(160), primary_key=True),
    Column("model_id", Integer),
    Column("metodo", String(20), comment="exato | alias | fuzzy | manual | sem_match"),
    Column("score", Float),
    comment="Nome escrito no chamado -> modelo do catálogo",
)

incidents = Table(
    "incidents", metadata,
    Column("inc_id", String(20), primary_key=True, comment="ID fictício"),
    Column("origem", String(20), comment="simulado | real_anonimizado"),
    Column("opened_at", DateTime),
    Column("participante_pseud", String(16), comment="pseudônimo (hash com sal)"),
    Column("descricao", Text, comment="texto sem dados pessoais"),
    Column("modelo_informado", String(160)),
    Column("model_id", Integer, index=True),
    Column("sdk", Integer),
    Column("android", String(10)),
    Column("app_version", String(20)),
    Column("rede", String(20)),
    Column("so", String(15), comment="android | ios | ambos | desconhecido"),
    Column("marca", String(40), comment="marca citada no texto"),
    Column("sdk_origem", String(20), comment="texto | sdk_max_do_modelo"),
    Column("classe_erro", String(20), comment="tecnico | conta_cadastro | fora_escopo | indefinido"),
    Column("subtipo_erro", String(40)),
    comment="Incidentes de login (anonimizados ou simulados)",
)

error_class = Table(
    "error_class", metadata,
    Column("regra_id", Integer, primary_key=True, autoincrement=False),
    Column("padrao", String(255)),
    Column("classe", String(20)),
    Column("subtipo", String(40)),
    comment="Regras de classificação dos incidentes",
)

lineage = Table(
    "lineage", metadata,
    Column("ordem", Integer, primary_key=True, autoincrement=False),
    Column("etapa", String(120)),
    Column("n", Integer),
    Column("pct_total", Float),
    comment="Funil de dados / rastreabilidade",
)

resultados_taxas = Table(
    "resultados_taxas", metadata,
    Column("dimensao", String(30), primary_key=True),
    Column("grupo", String(160), primary_key=True),
    Column("afetados", Integer, comment="participantes distintos"),
    Column("incidentes", Integer),
    Column("base", Float),
    Column("taxa_por_mil", Float),
    Column("ic_inf", Float),
    Column("ic_sup", Float),
    Column("risco_relativo", Float),
    Column("p_valor", Float),
    Column("p_ajustado", Float),
    Column("significativo", Integer),
    comment="Taxa de incidentes por grupo vs. taxa geral",
)

modelo_poisson = Table(
    "modelo_poisson", metadata,
    Column("termo", String(80), primary_key=True),
    Column("irr", Float, comment="razão de taxas de incidência"),
    Column("ic_inf", Float),
    Column("ic_sup", Float),
    Column("p_valor", Float),
    comment="GLM de Poisson com offset log(base)",
)

perfis = Table(
    "perfis", metadata,
    Column("perfil_id", Integer, primary_key=True, autoincrement=False),
    Column("rank", Integer, comment="posição no ranking (limite inferior do IC); nulo = sem base"),
    Column("perfil", String(160)), Column("modelo", String(160)), Column("zona", String(60)),
    Column("marca", String(60)), Column("chip", String(80)), Column("chip_fab", String(40)),
    Column("ram", String(60)), Column("android_play", String(80)),
    Column("android_periodo", String(160), comment="versões disponíveis no período dos casos (pesquisa pública)"),
    Column("ocorrencias", Integer), Column("ocorrencias_tecnicas", Integer), Column("afetados", Integer),
    Column("base", Float), Column("taxa_por_mil", Float), Column("ic_inf", Float), Column("ic_sup", Float),
    Column("taxa_ajustada", Float, comment="taxa encolhida para a média (ordena o ranking)"),
    Column("risco_relativo", Float), Column("p_valor", Float), Column("p_ajustado", Float),
    Column("significativo", Integer), Column("status", String(20)), Column("tem_taxa", Integer),
    Column("sintoma", String(40)), Column("sintoma_pct", Float), Column("sintomas_json", Text),
    Column("versoes_app_json", Text), Column("inicio", DateTime), Column("fim", DateTime),
    Column("resumo", Text), Column("hipotese", Text), Column("fontes_json", Text),
    comment="Perfis de aparelho (mapa e ranking do dashboard)",
)

grafo_nos = Table(
    "grafo_nos", metadata,
    Column("no", String(160), primary_key=True),
    Column("tipo", String(20)),
    Column("rotulo", String(160)),
    Column("incidentes", Integer),
    Column("lift", Float, comment="participação nos incidentes / participação na base"),
    Column("grau_ponderado", Float),
    Column("centralidade", Float),
    Column("comunidade", Integer),
)

grafo_arestas = Table(
    "grafo_arestas", metadata,
    Column("origem", String(160), primary_key=True),
    Column("destino", String(160), primary_key=True),
    Column("peso", Integer, comment="co-ocorrências em incidentes"),
    Column("lift", Float, comment="observado / esperado pela base"),
)


def get_engine() -> Engine:
    url = os.getenv("DB_URL")
    if url:
        return create_engine(url)
    return create_engine(URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "Projeto_extensao"),
        query={"charset": "utf8mb4"},
    ))


def recriar_tabelas(engine: Engine, nomes: list[str] | None = None) -> None:
    tabelas = [metadata.tables[n] for n in nomes] if nomes else None
    metadata.drop_all(engine, tables=tabelas)
    metadata.create_all(engine, tables=tabelas)


def gravar(df: pd.DataFrame, tabela: str, engine: Engine) -> None:
    """Recria a tabela com o esquema oficial e insere o DataFrame."""
    recriar_tabelas(engine, [tabela])
    cols = [c.name for c in metadata.tables[tabela].columns]
    df = df[[c for c in cols if c in df.columns]]
    df.to_sql(tabela, engine, if_exists="append", index=False, chunksize=2000)


def ler(sql: str, engine: Engine | None = None) -> pd.DataFrame:
    return pd.read_sql(sql, engine or get_engine())


def ddl_mariadb() -> str:
    from sqlalchemy.dialects import mysql
    partes = ["-- Gerado por: python -m src.db --ddl", "-- Banco: MariaDB (utf8mb4)", ""]
    for t in metadata.sorted_tables:
        partes.append(str(CreateTable(t).compile(dialect=mysql.dialect())).strip() + ";\n")
    return "\n".join(partes)


if __name__ == "__main__":
    if "--ddl" in sys.argv:
        destino = config.RAIZ / "sql" / "schema.sql"
        destino.write_text(ddl_mariadb(), encoding="utf-8")
        print(f"DDL gravado em {destino}")
    else:
        with get_engine().connect() as c:
            print("Conexão OK:", c.engine.url.render_as_string(hide_password=True))
