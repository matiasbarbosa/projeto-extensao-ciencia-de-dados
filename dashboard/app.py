"""Dashboard do projeto (Streamlit).

  streamlit run dashboard/app.py

Fonte pública: incidentes SIMULADOS, lidos do MariaDB (ou dos CSVs de
data/processed/ quando não há banco). Se existirem resultados da análise real em
data/private/real/ (fora do Git), aparece a opção de exibi-los localmente.
"""
from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from componentes import (COR_STATUS, FONTES_CSS, SINTOMAS, STATUS, mapa_html,  # noqa: E402
                         preparar, ranking_html)

from src import config, db  # noqa: E402

st.set_page_config(page_title="Perfis de falha de login · App EPX", layout="wide",
                   initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ tema
SUPERFICIE, SUPERFICIE2, TINTA, TINTA2, TEAL = "#262b30", "#1c2024", "#e6e9ec", "#a9b3bc", "#1fb5ac"
SERIE = ["#1fb5ac", "#f08c3a", "#b6d4f7", "#f5b8d4", "#d8bf4a", "#bdf0aa", "#d6c8f7", "#b9c2ca"]
pio.templates["epx"] = go.layout.Template(layout=dict(
    paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, colorway=SERIE,
    font=dict(family="Plex, system-ui, sans-serif", color=TINTA, size=13),
    xaxis=dict(gridcolor="#353c43", zerolinecolor="#4a525a", linecolor="#4a525a"),
    yaxis=dict(gridcolor="#353c43", zerolinecolor="#4a525a", linecolor="#4a525a"),
    legend=dict(bgcolor="rgba(0,0,0,0)"), hoverlabel=dict(bgcolor="#1b1f23", font_family="Plex"),
    margin=dict(l=10, r=10, t=30, b=10)))
pio.templates.default = "epx"

st.markdown(f"""<style>
{FONTES_CSS}
html, body, .stApp, .stMarkdown, button, input, textarea, select, [data-baseweb] {{
  font-family: "Plex", system-ui, sans-serif !important; }}
.stApp {{ background: {SUPERFICIE}; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ right: 12px; top: 6px; }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] {{ display: none; }}
.block-container {{ padding: 1.1rem 1.6rem 2rem; max-width: 1680px; }}
::selection {{ background: {TEAL}55; }}
* {{ scrollbar-width: thin; scrollbar-color: #4a525a transparent; }}
:focus-visible {{ outline: 2px solid {TEAL} !important; outline-offset: 2px; }}
.topo {{ display:flex; align-items:center; gap:14px; padding: 4px 0 10px; }}
.topo svg {{ flex:none }}
.topo h1 {{ margin:0; font: 600 21px/1.2 "Plex"; color:#fff; letter-spacing:-.005em }}
.topo .cam {{ font-size:13px; color:{TINTA2}; margin-top:2px }}
.pilula {{ display:inline-flex; align-items:center; gap:8px; height:34px; padding:0 12px; border-radius:3px;
  background:#1c2024; border:1px solid #3a4148; color:{TINTA}; font:500 13px "Plex"; white-space:nowrap }}
.faixa {{ margin: 0 0 12px; padding: 8px 12px; border-radius:3px; font-size:13.5px; line-height:1.45 }}
.faixa.sim {{ background:#3a3320; color:#f3e3a6 }}
.faixa.real {{ background:#173634; color:#bfeee9 }}
.resumo {{ display:flex; flex-wrap:wrap; gap:6px 22px; font-size:13.5px; color:{TINTA2}; margin:4px 0 12px }}
.resumo b {{ color:#fff; font-weight:600; font-variant-numeric: tabular-nums }}
.stTabs [data-baseweb="tab-list"] {{ gap: 22px; border-bottom: 1px solid #3a4148; }}
.stTabs [data-baseweb="tab"] {{ height: 40px; padding: 0 2px; background: transparent; color:{TINTA2}; font-weight:500 }}
.stTabs [aria-selected="true"] {{ color: #fff; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {TEAL}; height: 3px }}
.stTabs [data-baseweb="tab-border"] {{ display:none }}
p, li {{ line-height: 1.55 }}
.ranking {{ overflow:auto; border:1px solid #3a4148; border-radius:4px; max-height: 70vh }}
.ranking table {{ width:100%; border-collapse:collapse; font-size:13.5px }}
.ranking caption {{ caption-side:top; text-align:left; padding:10px 14px; color:{TINTA2}; font-size:12.5px;
  background:{SUPERFICIE2}; line-height:1.5 }}
.ranking th {{ position:sticky; top:0; background:#20252a; color:{TINTA2}; font-weight:500; text-align:left;
  padding:9px 12px; border-bottom:1px solid #3a4148; white-space:nowrap; z-index:1 }}
.ranking td {{ padding:9px 12px; border-bottom:1px solid #30363c; vertical-align:middle; color:{TINTA} }}
.ranking tbody tr:hover td {{ background:#2c3237 }}
.ranking .n {{ text-align:right; font-variant-numeric: tabular-nums; white-space:nowrap }}
.ranking .pos {{ color:{TINTA2}; font-variant-numeric: tabular-nums; width:34px }}
.ranking .nome {{ font-weight:600; color:#fff }}
.ranking .meta {{ display:flex; gap:6px; align-items:center; margin-top:3px; font-size:12.5px; color:{TINTA2} }}
.ranking .tag {{ padding:0 6px; border-radius:3px; color:#22282d; font-size:11.5px; line-height:17px }}
.ranking .st {{ display:inline-block; padding:2px 8px; border-radius:3px; font-size:12px; font-weight:500; white-space:nowrap }}
.ranking .tx {{ min-width:170px }}
.ranking .tx b {{ font-variant-numeric: tabular-nums }} .ranking .tx small {{ color:{TINTA2}; margin-left:6px }}
.ranking svg.ic {{ display:block; width:100%; height:12px; margin-top:4px }}
.ranking .mudo {{ color:#7f8a94 }}
.ranking tbody.sem th {{ position:static; background:{SUPERFICIE2}; color:{TINTA2}; padding-top:14px }}
</style>""", unsafe_allow_html=True)

NOMES_DIM = {"marca": "Marca", "android": "Versão do Android", "marca_android": "Marca x Android",
             "modelo": "Modelo", "modelo_android": "Modelo x Android", "ram": "Faixa de RAM",
             "soc": "Fabricante do chip (SoC)", "marca_soc": "Marca x chip"}
TABELAS = ["incidents", "resultados_taxas", "modelo_poisson", "grafo_nos", "grafo_arestas", "lineage", "perfis"]
DIR_REAL = config.DATA_PRIVATE / "real"


@st.cache_data(ttl=300)
def carregar(fonte: str) -> tuple[dict[str, pd.DataFrame], str]:
    if fonte == "real":
        d = {t: pd.read_csv(DIR_REAL / f"{t}.csv") for t in TABELAS[1:]}
        d["incidents"] = pd.read_csv(DIR_REAL / "incidentes_tratados_real_anonimizado.csv")
        return d, "CSVs locais em data/private/real (fora do Git)"
    try:
        eng = db.get_engine()
        d = {t: db.ler(f"SELECT * FROM {t}", eng) for t in TABELAS}
        return d, f"MariaDB ({eng.url.host or 'socket local'}/{eng.url.database})"
    except Exception:  # noqa: BLE001
        p = config.DATA_PROCESSED
        d = {t: pd.read_csv(p / f"{t}.csv") for t in TABELAS[1:]}
        d["incidents"] = pd.read_csv(p / "incidentes_tratados_simulado.csv")
        return d, "CSVs em data/processed/"


# ------------------------------------------------------------------ topo
tem_real = (DIR_REAL / "perfis.csv").exists()
c1, c2 = st.columns([5, 2], vertical_alignment="center")
with c1:
    st.markdown("""<div class="topo"><svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true">
<rect x="6" y="2.5" width="12" height="19" rx="2.5" fill="none" stroke="#1fb5ac" stroke-width="1.8"/>
<path d="M10 18.5h4" stroke="#1fb5ac" stroke-width="1.8" stroke-linecap="round"/></svg>
<div><h1>Perfis de falha de login</h1><div class="cam">App EPX · Android · Entidade de Previdência X (nome fictício)</div></div></div>""",
                unsafe_allow_html=True)
with c2:
    fonte = "simulado"
    if tem_real:
        esc = st.segmented_control("Fonte dos incidentes", ["Simulada (pública)", "Real anonimizada (local)"],
                                   default="Simulada (pública)", label_visibility="collapsed")
        fonte = "real" if esc == "Real anonimizada (local)" else "simulado"

d, origem = carregar(fonte)
inc, tx, poi = d["incidents"], d["resultados_taxas"], d["modelo_poisson"]
nos, arestas, fun, perf = d["grafo_nos"], d["grafo_arestas"], d["lineage"], d["perfis"]
inc["opened_at"] = pd.to_datetime(inc["opened_at"])
regs = preparar(perf, config.K_MIN)

if fonte == "simulado":
    st.markdown(f'<div class="faixa sim"><b>Dados de incidentes simulados.</b> O catálogo de aparelhos é real '
                f'(Google Play Console). Os incidentes foram gerados pelo simulador do projeto, calibrado só com '
                f'proporções agregadas da análise real. Nenhum incidente exibido aqui é real. Fonte: {origem}.</div>',
                unsafe_allow_html=True)
else:
    st.markdown(f'<div class="faixa real"><b>Incidentes reais anonimizados, exibição local.</b> Sem nomes, CPF, '
                f'matrícula ou número do chamado. Grupos com menos de {config.K_MIN} participantes aparecem sem '
                f'números. Não publicar. Fonte: {origem}.</div>', unsafe_allow_html=True)

tec = inc[(inc["classe_erro"] == "tecnico") & (inc.get("so", "android") == "android")]
base_total = tx.loc[tx["dimensao"] == "marca", "base"].sum()
n_crit = int((perf["status"] == "critico").sum())
ini, fim = inc["opened_at"].min(), inc["opened_at"].max()
def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.markdown(f"""<div class="resumo"><span><b>{br(len(inc))}</b> incidentes</span>
<span><b>{br(len(tec))}</b> técnicos em Android</span>
<span><b>{br(tec['participante_pseud'].nunique())}</b> participantes nesses casos</span>
<span>taxa geral <b>{br(1000 * tec['participante_pseud'].nunique() / base_total, 1)}</b> por mil aparelhos</span>
<span>perfis críticos: <b>{n_crit}</b></span>
<span>{ini:%d/%m/%Y} a {fim:%d/%m/%Y}</span></div>""", unsafe_allow_html=True)

aba = st.tabs(["Mapa", "Ranking", "Taxas por grupo", "Grafo de atributos", "Modelo estatístico", "Sobre os dados"])

# ------------------------------------------------------------------ mapa
with aba[0]:
    st.iframe(mapa_html(regs, config.K_MIN), height=780)
    st.caption("Cada bloco é um perfil de aparelho (modelo do catálogo). Clique para ver os detalhes; arraste para "
               "mover e use a roda do mouse para aproximar. A cor indica o status estatístico e o número no topo, a "
               "posição no ranking. A versão do Android no período vem de pesquisa pública e da lista de versões do "
               "Play Console: os chamados quase nunca a informam.")

# ------------------------------------------------------------------ ranking
with aba[1]:
    f1, f2, f3 = st.columns([2, 2, 3])
    stt = f1.multiselect("Status", [STATUS[s][0] for s in STATUS], placeholder="Todos")
    marcas = f2.multiselect("Marca", sorted({r["marca"] for r in regs if r["marca"]}), placeholder="Todas")
    busca = f3.text_input("Buscar modelo ou chip", placeholder="ex.: moto g35, Unisoc")
    sel = [r for r in regs
           if (not stt or r["statusRotulo"] in stt) and (not marcas or r["marca"] in marcas)
           and (not busca or busca.lower() in f"{r['nome']} {r['chip'] or ''} {r['chipFab'] or ''}".lower())]
    st.markdown(ranking_html(sel, config.K_MIN), unsafe_allow_html=True)
    st.caption("Ordenação pela taxa ajustada: cada perfil recebe o equivalente a 500 aparelhos com a taxa geral, "
               "para que um modelo com 1 caso em poucos aparelhos não passe na frente de um com evidência sólida. "
               "Status crítico: pelo menos 5 participantes, teste binomial com correção de Benjamini-Hochberg "
               "abaixo de 5% e risco relativo de 5 vezes ou mais.")

# ------------------------------------------------------------------ taxas
with aba[2]:
    st.markdown("Contagem absoluta engana: a Samsung tem dois terços da base e sempre terá mais chamados. Aqui "
                "comparamos a **taxa** (participantes afetados por mil aparelhos ativos) de cada grupo com a taxa do "
                "restante da base.")
    dims = [k for k in NOMES_DIM if k in set(tx["dimensao"])]
    dim = st.selectbox("Agrupar por", dims, format_func=NOMES_DIM.get, index=dims.index("marca_soc") if "marca_soc" in dims else 0)
    t = tx[tx["dimensao"] == dim].sort_values("taxa_por_mil", ascending=False).head(25)
    ref = 1000 * t["afetados"].sum() / tx.loc[tx["dimensao"] == dim, "base"].sum() if len(t) else 0
    t = t.assign(destaque=t["significativo"].map({1: "acima do esperado (FDR < 5%)", 0: "sem diferença clara"}),
                 err_mais=t["ic_sup"] - t["taxa_por_mil"], err_menos=t["taxa_por_mil"] - t["ic_inf"])
    fig = px.bar(t[::-1], x="taxa_por_mil", y="grupo", orientation="h", color="destaque",
                 error_x="err_mais", error_x_minus="err_menos",
                 color_discrete_map={"acima do esperado (FDR < 5%)": COR_STATUS["acima"],
                                     "sem diferença clara": COR_STATUS["normal"]},
                 labels={"taxa_por_mil": "afetados por mil aparelhos (IC 95%)", "grupo": "", "destaque": ""},
                 hover_data={"afetados": True, "base": ":.0f", "risco_relativo": ":.2f", "p_ajustado": ":.4f",
                             "err_mais": False, "err_menos": False})
    fig.add_vline(x=ref, line_dash="dash", line_color=TINTA2, annotation_text="média da dimensão")
    fig.update_layout(height=max(360, 30 * len(t)), xaxis_rangemode="tozero", legend_orientation="h", legend_y=1.06)
    st.plotly_chart(fig, width="stretch")
    if "android" in dim:
        st.caption("Base por versão do Android é estimada: o Play Console informa instalações por modelo. Regra usada: "
                   f"'{config.REGRA_SDK}' (cada modelo contado na versão mais recente que suporta).")
    st.dataframe(t.drop(columns=["destaque", "err_mais", "err_menos"]).round(4), width="stretch", hide_index=True)

# ------------------------------------------------------------------ grafo
with aba[3]:
    st.markdown("Cada nó é um atributo (marca, modelo, chip, Android, versão do app, RAM, tipo de erro). Dois atributos "
                "ficam ligados quando aparecem **no mesmo incidente técnico**; a espessura é o número de incidentes. "
                "**Lift** maior que 1 indica que o atributo aparece nos incidentes mais do que sua participação na base.")
    c1, c2, c3 = st.columns(3)
    pmin, pmax = int(arestas["peso"].min()), int(arestas["peso"].max())
    peso_min = c1.slider("Peso mínimo da aresta", pmin, max(pmin + 1, pmax), min(max(pmin, 8), pmax))
    cor_por = c2.radio("Cor dos nós", ["tipo", "comunidade"], horizontal=True)
    tipos = c3.multiselect("Tipos de nó", sorted(nos["tipo"].unique()), default=sorted(nos["tipo"].unique()))
    G = nx.Graph()
    for r in nos[nos["tipo"].isin(tipos)].itertuples():
        G.add_node(r.no, **{k: v for k, v in r._asdict().items() if k not in ("Index", "no")})
    for r in arestas[arestas["peso"] >= peso_min].itertuples():
        if r.origem in G and r.destino in G:
            G.add_edge(r.origem, r.destino, peso=r.peso, lift=r.lift)
    G.remove_nodes_from(list(nx.isolates(G)))
    if G.number_of_nodes():
        pos = nx.spring_layout(G, weight="peso", seed=config.SEED, k=1.2)
        wmax = max(nx.get_edge_attributes(G, "peso").values())
        fig = go.Figure()
        for a, b, e in G.edges(data=True):
            fig.add_trace(go.Scatter(x=[pos[a][0], pos[b][0]], y=[pos[a][1], pos[b][1]], mode="lines",
                                     line=dict(width=.5 + 6 * e["peso"] / wmax, color="rgba(185,194,202,.28)"),
                                     hoverinfo="skip", showlegend=False))
        nd = pd.DataFrame([{"no": n, "x": pos[n][0], "y": pos[n][1], **G.nodes[n]} for n in G])
        nd["grupo_cor"] = nd[cor_por].astype(str)
        for i, (g, sub) in enumerate(nd.groupby("grupo_cor")):
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers+text", name=g, text=sub["no"], textposition="top center",
                textfont=dict(color=TINTA, size=12),
                marker=dict(size=10 + 40 * (sub["incidentes"] / nd["incidentes"].max()) ** .5,
                            color=SERIE[i % len(SERIE)], line=dict(width=1, color=SUPERFICIE)),
                customdata=sub[["incidentes", "lift", "centralidade"]].fillna(-1).values,
                hovertemplate="<b>%{text}</b><br>incidentes: %{customdata[0]}<br>lift: %{customdata[1]:.2f}"
                              "<br>centralidade: %{customdata[2]:.3f}<extra></extra>"))
        fig.update_layout(height=680, xaxis=dict(visible=False), yaxis=dict(visible=False), legend_title=cor_por)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Nenhuma aresta com esse peso mínimo. Diminua o peso mínimo para ver o grafo.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Atributos mais centrais")
        st.dataframe(nos.sort_values("centralidade", ascending=False)
                     [["no", "incidentes", "lift", "grau_ponderado", "centralidade", "comunidade"]].head(15).round(3),
                     hide_index=True, width="stretch")
    with c2:
        st.subheader("Combinações de aparelho super-representadas")
        st.dataframe(arestas.dropna(subset=["lift"]).sort_values("lift", ascending=False)
                     [["origem", "destino", "peso", "lift"]].head(15).round(2), hide_index=True, width="stretch")

# ------------------------------------------------------------------ modelo
with aba[4]:
    st.markdown("Regressão de Poisson por célula (modelo x versão do Android), com a base de aparelhos como exposição. "
                "O **IRR** (razão de taxas) mostra quantas vezes a taxa de um grupo é maior que a da categoria de "
                "referência (**Samsung, Android 14, 8 GB**), controlando pelos outros atributos. Associação, não causa.")
    p = poi[poi["ic_sup"] < 1e6].copy()
    p["sig"] = (p["p_valor"] < 0.05).map({True: "p < 0,05", False: "p ≥ 0,05"})
    p["err_mais"], p["err_menos"] = p["ic_sup"] - p["irr"], p["irr"] - p["ic_inf"]
    fig = px.scatter(p, x="irr", y="termo", color="sig", error_x="err_mais", error_x_minus="err_menos", log_x=True,
                     color_discrete_map={"p < 0,05": COR_STATUS["acima"], "p ≥ 0,05": COR_STATUS["normal"]},
                     labels={"irr": "IRR (escala logarítmica, IC 95%)", "termo": "", "sig": ""})
    fig.add_vline(x=1, line_dash="dash", line_color=TINTA2, annotation_text="igual à referência")
    fig.update_traces(marker_size=11)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(poi.round(4), hide_index=True, width="stretch")

# ------------------------------------------------------------------ sobre
with aba[5]:
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"""
#### Fontes
- **Google Play Console**: catálogo de aparelhos com o app instalado (modelo, marca, RAM, chip, versões do Android,
  base de instalação). A base conta aparelhos ativos, não pessoas.
- **ServiceNow**: incidentes de login. {"**Nesta visão, simulados.**" if fonte == "simulado" else "Anonimizados na origem."}
- **Pesquisa pública** (só para contexto dos perfis): páginas de suporte da Motorola, notícias sobre atualizações,
  Don't kill my app! e documentação do Android. As fontes aparecem no painel de cada perfil.
- **IBM Instana** (R1): cruzamento pendente.

#### Limitações
- Incidente não é aparelho nem pessoa: as taxas contam participantes distintos.
- Só entra quem abriu chamado (viés de quem reporta).
- Os chamados quase nunca informam a versão do Android. A base por versão é estimada (regra '{config.REGRA_SDK}'),
  e a versão provável no período vem de pesquisa pública.
- O Play Console é uma foto de um momento; os incidentes cobrem um período.
- Resultados indicam **associação**, não causa. A hipótese técnica de cada perfil precisa ser validada pelo time do app.
- iOS fica fora das taxas, por falta de catálogo.

#### Privacidade (LGPD)
Nenhum nome, CPF, matrícula ou número original de chamado é armazenado ou exibido. Os participantes são
pseudônimos (HMAC com chave mantida pelo parceiro). Grupos com menos de {config.K_MIN} participantes aparecem sem números.
""")
    with col2:
        st.markdown("#### Funil de dados (rastreabilidade)")
        fig = go.Figure(go.Funnel(y=fun["etapa"], x=fun["n"], textinfo="value+percent initial",
                                  marker_color=TEAL, connector=dict(fillcolor="#30363c")))
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")
        sub = (tec.assign(sintoma=tec["subtipo_erro"].map(SINTOMAS)).groupby("sintoma").size()
               .reset_index(name="n").sort_values("n"))
        st.markdown("#### Sintomas nos casos técnicos em Android")
        fig = px.bar(sub, x="n", y="sintoma", orientation="h", labels={"n": "incidentes", "sintoma": ""},
                     color_discrete_sequence=[TEAL])
        fig.update_layout(height=340)
        st.plotly_chart(fig, width="stretch")
