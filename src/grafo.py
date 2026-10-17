"""Grafo de atributos por co-ocorrência (NetworkX).

Cada incidente técnico vira um conjunto de nós (marca, modelo, versão do
Android, versão do app, faixa de RAM, rede, subtipo do erro). Dois nós ficam
ligados quando aparecem no mesmo incidente; o peso é o número de incidentes.

Métricas:
- grau ponderado e centralidade de autovetor: quais atributos "puxam" os
  incidentes;
- comunidades (Louvain): grupos de atributos que andam juntos;
- lift populacional: para atributos de aparelho, compara a participação nos
  incidentes com a participação na base do Play Console (lift > 1 indica
  super-representação; como as contagens absolutas favorecem as marcas
  grandes, o lift é o que importa).
"""
from __future__ import annotations

from itertools import combinations

import networkx as nx
import pandas as pd

from src import config

TIPOS = {"marca": "marca", "modelo": "modelo", "android": "android",
         "app_version": "app", "ram_faixa": "ram", "soc_fab": "chip", "rede": "rede",
         "subtipo_erro": "erro"}
ATRIB_APARELHO = {"marca", "modelo", "android", "ram_faixa", "soc_fab"}


def _nos_do_incidente(r: pd.Series) -> list[tuple[str, str]]:
    nos = []
    for col, tipo in TIPOS.items():
        v = r.get(col)
        if pd.notna(v) and v not in ("nao_informado", "indefinido", None):
            nos.append((col, f"{tipo}: {v}"))
    return nos


def construir(tec: pd.DataFrame, pop: pd.DataFrame, k_min: int = config.K_MIN) -> nx.Graph:
    G = nx.Graph()
    W = pop["install_est"].sum()
    contagem_no: dict[str, int] = {}
    col_do_no: dict[str, str] = {}
    for _, r in tec.iterrows():
        nos = _nos_do_incidente(r)
        for col, n in nos:
            contagem_no[n] = contagem_no.get(n, 0) + 1
            col_do_no[n] = col
        for (c1, a), (c2, b) in combinations(nos, 2):
            if G.has_edge(a, b):
                G[a][b]["peso"] += 1
            else:
                G.add_edge(a, b, peso=1, cols=(c1, c2))

    for n, k in contagem_no.items():
        if n not in G:
            G.add_node(n)
        col = col_do_no[n]
        G.nodes[n].update(tipo=TIPOS[col], rotulo=n.split(": ", 1)[1], incidentes=k, lift=None)
        if col in ATRIB_APARELHO:
            valor = n.split(": ", 1)[1]
            base = pop.loc[pop[col].astype(str) == valor, "install_est"].sum()
            n_conhecidos = tec[col].notna().sum()
            if base > 0 and n_conhecidos:
                G.nodes[n]["lift"] = (k / n_conhecidos) / (base / W)

    for a, b, d in G.edges(data=True):
        c1, c2 = d.pop("cols")
        d["lift"] = None
        if c1 in ATRIB_APARELHO and c2 in ATRIB_APARELHO and c1 != c2:
            va, vb = G.nodes[a]["rotulo"], G.nodes[b]["rotulo"]
            base = pop.loc[(pop[c1].astype(str) == va) & (pop[c2].astype(str) == vb), "install_est"].sum()
            n_conhecidos = tec[[c1, c2]].notna().all(axis=1).sum()
            if base > 0 and n_conhecidos:
                d["lift"] = (d["peso"] / n_conhecidos) / (base / W)

    # privacidade e legibilidade: só nós e arestas com pelo menos k_min incidentes
    G.remove_edges_from([(a, b) for a, b, d in G.edges(data=True) if d["peso"] < k_min])
    G.remove_nodes_from([n for n, d in G.nodes(data=True) if d.get("incidentes", 0) < k_min])
    G.remove_nodes_from(list(nx.isolates(G)))

    grau = dict(G.degree(weight="peso"))
    try:
        cent = nx.eigenvector_centrality(G, weight="peso", max_iter=2000)
    except nx.PowerIterationFailedConvergence:
        cent = nx.degree_centrality(G)
    comunidades = nx.community.louvain_communities(G, weight="peso", seed=config.SEED)
    for i, com in enumerate(comunidades):
        for n in com:
            G.nodes[n]["comunidade"] = i
    for n in G:
        G.nodes[n]["grau_ponderado"] = grau[n]
        G.nodes[n]["centralidade"] = cent[n]
    return G


def para_tabelas(G: nx.Graph) -> tuple[pd.DataFrame, pd.DataFrame]:
    nos = pd.DataFrame([{"no": n, **d} for n, d in G.nodes(data=True)])
    arestas = pd.DataFrame([{"origem": a, "destino": b, **d} for a, b, d in G.edges(data=True)])
    return nos, arestas
