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
    font=dict(family="Plex, Plex Fallback, system-ui, sans-serif", color=TINTA, size=14),
    xaxis=dict(gridcolor="#353c43", zerolinecolor="#4a525a", linecolor="#4a525a"),
    yaxis=dict(gridcolor="#353c43", zerolinecolor="#4a525a", linecolor="#4a525a"),
    legend=dict(bgcolor="rgba(0,0,0,0)"), hoverlabel=dict(bgcolor="#1b1f23", font_family="Plex, Plex Fallback, system-ui, sans-serif", font_size=13),
    margin=dict(l=10, r=10, t=30, b=10)))
pio.templates.default = "epx"

st.markdown(f"""<style>
{FONTES_CSS}
html, body, .stApp, .stMarkdown, button, input, textarea, select, [data-baseweb] {{
  font-family: var(--fam) !important; }}
:root {{ --fam: "Plex", "Plex Fallback", system-ui, sans-serif; --f-meta: .78125rem; --f-corpo: .875rem;
  --f-secao: 1.125rem; --f-titulo: 1.4rem; --medida: 75ch; }}
.stApp {{ background: {SUPERFICIE}; letter-spacing: .005em; -webkit-font-smoothing: antialiased; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ right: 12px; top: 6px; }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] {{ display: none; }}
.block-container {{ padding: 1.1rem 1.6rem 2rem; max-width: 1680px; }}
::selection {{ background: {TEAL}55; }}
* {{ scrollbar-width: thin; scrollbar-color: #4a525a transparent; }}
:focus-visible {{ outline: 2px solid {TEAL} !important; outline-offset: 2px; }}
.topo {{ display:flex; align-items:center; gap:14px; padding: 4px 0 10px; }}
.topo svg {{ flex:none }}
.topo h1 {{ margin:0; font: 600 var(--f-titulo)/1.2 var(--fam); color:#fff; letter-spacing:-.005em; text-wrap:balance }}
.topo .cam {{ font-size:var(--f-meta); color:{TINTA2}; margin-top:3px }}
.pilula {{ display:inline-flex; align-items:center; gap:8px; height:34px; padding:0 12px; border-radius:3px;
  background:#1c2024; border:1px solid #3a4148; color:{TINTA}; font:500 var(--f-corpo) var(--fam); white-space:nowrap }}
.faixa {{ margin: 0 0 12px; padding: 8px 12px; border-radius:3px; font-size:var(--f-corpo); line-height:1.5; text-wrap:pretty }}
.faixa.sim {{ background:#3a3320; color:#f3e3a6 }}
.faixa.real {{ background:#173634; color:#bfeee9 }}
.resumo {{ display:flex; flex-wrap:wrap; gap:6px 22px; font-size:var(--f-corpo); color:{TINTA2}; margin:4px 0 12px }}
.resumo b {{ color:#fff; font-weight:600; font-variant-numeric: tabular-nums }}
.stTabs [data-baseweb="tab-list"] {{ gap: 22px; border-bottom: 1px solid #3a4148; }}
.stTabs [data-baseweb="tab"] {{ height: 40px; padding: 0 2px; background: transparent; color:{TINTA2}; font-weight:500 }}
.stTabs [aria-selected="true"] {{ color: #fff; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {TEAL}; height: 3px }}
.stTabs [data-baseweb="tab-border"] {{ display:none }}
p, li {{ line-height: 1.55 }}
.stApp .stMarkdown p, .stApp .stMarkdown li {{ max-width: var(--medida); text-wrap: pretty }}
.stApp .stMarkdown li + li {{ margin-top: .2rem }}
.stApp .stMarkdown h4, .stApp [data-testid="stHeading"] h3 {{ font-size: var(--f-secao); font-weight: 600; line-height: 1.3;
  letter-spacing: 0; padding: 1.1rem 0 .35rem; text-wrap: balance }}
.stApp [data-testid="stCaptionContainer"] {{ max-width: var(--medida); font-size: var(--f-corpo); line-height: 1.5; color: {TINTA2} }}
.stApp [data-testid="stAlertContainer"] p {{ max-width: var(--medida); font-size: var(--f-corpo); line-height: 1.5 }}
.ranking {{ overflow:auto; border:1px solid #3a4148; border-radius:4px; max-height: 70vh }}
.ranking table {{ width:100%; border-collapse:collapse; font-size:var(--f-corpo); line-height:1.4 }}
.ranking caption {{ caption-side:top; text-align:left; padding:10px max(14px, calc(100% - 95ch)) 10px 14px; color:{TINTA2}; font-size:var(--f-corpo);
  background:{SUPERFICIE2}; line-height:1.5; text-wrap:pretty }}
.ranking th {{ position:sticky; top:0; background:#20252a; color:{TINTA2}; font-weight:500; font-size:var(--f-meta); text-align:left;
  padding:9px 12px; border-bottom:1px solid #3a4148; white-space:nowrap; z-index:1 }}
.ranking td {{ padding:9px 12px; border-bottom:1px solid #30363c; vertical-align:middle; color:{TINTA} }}
.ranking tbody tr:hover td {{ background:#2c3237 }}
.ranking .n {{ text-align:right; font-variant-numeric: tabular-nums; white-space:nowrap }}
.ranking .pos {{ color:{TINTA2}; font-variant-numeric: tabular-nums; width:34px }}
.ranking .nome {{ font-weight:600; color:#fff }}
.ranking .meta {{ display:flex; gap:6px; align-items:center; margin-top:3px; font-size:var(--f-meta); color:{TINTA2} }}
.ranking .tag {{ padding:0 6px; border-radius:3px; color:#22282d; font-size:var(--f-meta); line-height:18px }}
.ranking .st {{ display:inline-block; padding:2px 8px; border-radius:3px; font-size:var(--f-meta); font-weight:500; white-space:nowrap }}
.ranking .tx {{ min-width:170px }}
.ranking .tx b {{ font-variant-numeric: tabular-nums }} .ranking .tx small {{ color:{TINTA2}; margin-left:6px; font-size:var(--f-meta) }}
.ranking svg.ic {{ display:block; width:100%; height:12px; margin-top:4px }}
.ranking .mudo {{ color:#9aa5ae }}
.ranking tbody.sem th {{ position:static; background:{SUPERFICIE2}; color:{TINTA2}; padding-top:14px }}
.ranking tbody th.rot {{ position:static; background:transparent; color:{TINTA}; font-size:inherit; font-weight:inherit;
  padding:9px 12px; border-bottom:1px solid #30363c; white-space:normal }}
.ranking tbody tr:hover th.rot {{ background:#2c3237 }}
.ranking:focus-visible {{ outline-offset:-2px !important }}
.ranking.vazio {{ padding:18px 16px; color:{TINTA2}; font-size:var(--f-corpo); line-height:1.5 }}
.ranking.vazio p {{ margin:0; max-width:var(--medida) }}
.ranking .cartoes {{ display:none }}
.stApp .ranking .cartoes ol {{ list-style:none; margin:0; padding:0; display:grid; gap:10px }}
.stApp .ranking .cartoes li.cartao {{ margin:0; max-width:none; padding:12px 14px }}
.cartoes h4 {{ margin:18px 0 8px; font-size:var(--f-secao); font-weight:600; color:{TINTA2} }}
.legenda-cartoes {{ margin:0 0 12px; color:{TINTA2}; font-size:var(--f-corpo); line-height:1.5 }}
.cartao {{ background:{SUPERFICIE2}; border:1px solid #3a4148; border-radius:4px; padding:12px 14px }}
.cartao .cab {{ display:flex; align-items:flex-start; gap:10px }}
.cartao .pos {{ flex:none; width:1.6rem; padding-top:1px; color:{TINTA2}; font-variant-numeric:tabular-nums }}
.cartao .id {{ flex:1; min-width:0 }}
.cartao .nome {{ font-weight:600; color:#fff; overflow-wrap:anywhere }}
.cartao .meta {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin-top:3px; font-size:var(--f-meta); color:{TINTA2} }}
.cartao .tag {{ padding:0 6px; border-radius:3px; color:#22282d; line-height:18px }}
.cartao .st {{ flex:none; max-width:42%; padding:2px 8px; border-radius:3px; font-size:var(--f-meta); font-weight:500; line-height:1.4; text-align:center }}
.cartao .taxa {{ margin-top:10px; font-variant-numeric:tabular-nums }}
.cartao .taxa b {{ font-size:var(--f-secao); font-weight:600; color:#fff }}
.cartao .taxa small {{ margin-left:6px; color:{TINTA2}; font-size:var(--f-meta) }}
.cartao svg.ic {{ display:block; width:100%; height:12px; margin-top:4px }}
.cartao .mudo {{ color:#9aa5ae }}
.cartao .nums {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(5.5rem, 1fr)); gap:8px 12px; margin:12px 0 0; padding-top:10px;
  border-top:1px solid #30363c }}
.cartao .nums dt {{ font-size:var(--f-meta); color:{TINTA2} }}
.cartao .nums dd {{ margin:1px 0 0; font-weight:600; color:#fff; font-variant-numeric:tabular-nums }}
.cartao .txt {{ margin:10px 0 0; font-size:var(--f-corpo); line-height:1.45; color:{TINTA} }}
.cartao .txt span {{ display:block; font-size:var(--f-meta); color:{TINTA2} }}
@media (max-width: 720px) {{
  .block-container {{ padding: .8rem 1rem 2rem; }}
  .topo {{ gap:10px }} .topo h1 {{ font-size:1.2rem }}
  .resumo {{ gap:4px 16px }}
  .stTabs [data-baseweb="tab-list"] {{ gap:16px }}
  .stTabs [data-baseweb="tab"] {{ height:48px }}
  .ranking {{ border:0; max-height:none; overflow:visible }}
  .ranking table {{ display:none }}
  .ranking .cartoes {{ display:block }}
}}
@media (pointer: coarse) {{
  [data-baseweb="select"] > div, [data-baseweb="input"], .stTextInput input {{ min-height:44px }}
}}
</style>""", unsafe_allow_html=True)

NOMES_DIM = {"marca": "Marca", "android": "Versão do Android", "marca_android": "Marca x Android",
             "modelo": "Modelo", "modelo_android": "Modelo x Android", "ram": "Faixa de RAM",
             "soc": "Fabricante do chip (SoC)", "marca_soc": "Marca x chip"}
TABELAS = ["incidents", "resultados_taxas", "modelo_poisson", "grafo_nos", "grafo_arestas", "lineage", "perfis"]
DIR_REAL = config.DATA_PRIVATE / "real"


class DadosIndisponiveis(Exception):
    """Fonte de dados ausente, vazia ou ilegível; a mensagem diz o que fazer."""


def _ler_csvs(pasta: Path, arq_incidentes: str) -> dict[str, pd.DataFrame]:
    try:
        d = {t: pd.read_csv(pasta / f"{t}.csv") for t in TABELAS[1:]}
        d["incidents"] = pd.read_csv(pasta / arq_incidentes)
    except (OSError, ValueError) as e:
        raise DadosIndisponiveis(f"Não foi possível ler os arquivos em {pasta} ({type(e).__name__}).") from e
    return d


@st.cache_data(ttl=300)
def carregar(fonte: str) -> tuple[dict[str, pd.DataFrame], str]:
    if fonte == "real":
        return _ler_csvs(DIR_REAL, "incidentes_tratados_real_anonimizado.csv"), "CSVs locais em data/private/real (fora do Git)"
    try:
        eng = db.get_engine()
        d = {t: db.ler(f"SELECT * FROM {t}", eng) for t in TABELAS}
        if any(d[t].empty for t in ("incidents", "resultados_taxas", "perfis")):
            raise ValueError("tabelas principais vazias")
        return d, f"MariaDB ({eng.url.host or 'socket local'}/{eng.url.database})"
    except Exception:  # noqa: BLE001
        return _ler_csvs(config.DATA_PROCESSED, "incidentes_tratados_simulado.csv"), "CSVs em data/processed/"


def _parar_sem_dados(msg: str):
    st.error(f"**Os dados do dashboard não estão disponíveis.** {msg} Gere os resultados com "
             "`python -m src.pipeline --sem-banco` e recarregue a página.")
    st.stop()


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

aviso_fonte = None
try:
    d, origem = carregar(fonte)
except DadosIndisponiveis as e:
    if fonte != "real":
        _parar_sem_dados(str(e))
    fonte = "simulado"
    aviso_fonte = f"Não foi possível abrir os resultados reais locais. Exibindo a base simulada. {e}"
    try:
        d, origem = carregar(fonte)
    except DadosIndisponiveis as e2:
        _parar_sem_dados(str(e2))
if aviso_fonte:
    st.warning(aviso_fonte)
inc, tx, poi = d["incidents"], d["resultados_taxas"], d["modelo_poisson"]
nos, arestas, fun, perf = d["grafo_nos"], d["grafo_arestas"], d["lineage"], d["perfis"]
inc["opened_at"] = pd.to_datetime(inc["opened_at"], errors="coerce")


@st.cache_data(ttl=300)
def perfis_do_mapa(fonte: str) -> tuple[list[dict], str]:
    """Registros dos perfis e o HTML do mapa, calculados uma vez por fonte."""
    regs_ = preparar(carregar(fonte)[0]["perfis"], config.K_MIN)
    return regs_, mapa_html(regs_, config.K_MIN)


try:
    regs, html_mapa = perfis_do_mapa(fonte)
except (KeyError, ValueError, TypeError) as e:
    _parar_sem_dados(f"A tabela de perfis está incompleta ou fora do formato esperado ({type(e).__name__}: {e}).")


def prioridade_de_teste(registros: list[dict]) -> str | None:
    """Primeira frase da hipótese do perfil mais bem colocado que a traz, lida dos dados."""
    marca = "Prioridade de teste:"
    for r in sorted((r for r in registros if r["rank"] is not None), key=lambda r: r["rank"]):
        if r["hipotese"].startswith(marca):
            return r["hipotese"].split(". ")[0].removeprefix(marca).strip().rstrip(".")
    return None


prioridade = prioridade_de_teste(regs)

if fonte == "simulado":
    st.markdown(f'<div class="faixa sim"><b>Dados de incidentes simulados.</b> O catálogo de aparelhos é real '
                f'(Google Play Console). Os incidentes foram gerados pelo simulador do projeto, calibrado só com '
                f'proporções agregadas da análise real. Nenhum incidente exibido aqui é real. Fonte: {origem}.</div>',
                unsafe_allow_html=True)
else:
    st.markdown(f'<div class="faixa real"><b>Incidentes reais anonimizados, exibição local.</b> Sem nomes, CPF, '
                f'matrícula ou número do chamado. Grupos com menos de {config.K_MIN} participantes aparecem sem '
                f'números. Não publicar. Fonte: {origem}.</div>', unsafe_allow_html=True)

em_android = inc["so"].eq("android") if "so" in inc else True
tec = inc[(inc["classe_erro"] == "tecnico") & em_android]
base_total = tx.loc[tx["dimensao"] == "marca", "base"].sum()
n_crit = int((perf["status"] == "critico").sum())
ini, fim = inc["opened_at"].min(), inc["opened_at"].max()
periodo_txt = f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}" if pd.notna(ini) and pd.notna(fim) else "período indisponível"
def grafico(fig):
    """Gráficos sem zoom por arraste: no celular, deslizar sobre eles precisa rolar a página."""
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def br(v, casas=0):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.markdown(f"""<div class="resumo"><span><b>{br(len(inc))}</b> incidentes</span>
<span><b>{br(len(tec))}</b> técnicos em Android</span>
<span><b>{br(tec['participante_pseud'].nunique())}</b> participantes nesses casos</span>
<span>taxa geral <b>{br(1000 * tec['participante_pseud'].nunique() / base_total if base_total else None, 1)}</b> por mil aparelhos</span>
<span>perfis críticos: <b>{n_crit}</b></span>
<span>{periodo_txt}</span></div>""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def montar_grafo(fonte: str, tipos: tuple, peso_min: int) -> tuple[pd.DataFrame, list[tuple]]:
    """Nós com posição (layout em mola) e arestas filtradas. O layout é caro, então fica em cache."""
    nos_, arestas_ = carregar(fonte)[0]["grafo_nos"], carregar(fonte)[0]["grafo_arestas"]
    G = nx.Graph()
    for r in nos_[nos_["tipo"].isin(tipos)].itertuples():
        G.add_node(r.no, **{k: v for k, v in r._asdict().items() if k not in ("Index", "no")})
    for r in arestas_[arestas_["peso"] >= peso_min].itertuples():
        if r.origem in G and r.destino in G:
            G.add_edge(r.origem, r.destino, peso=r.peso)
    G.remove_nodes_from(list(nx.isolates(G)))
    if not G.number_of_nodes():
        return pd.DataFrame(), []
    pos = nx.spring_layout(G, weight="peso", seed=config.SEED, k=1.2)
    nd = pd.DataFrame([{"no": n, "x": pos[n][0], "y": pos[n][1], **G.nodes[n]} for n in G])
    return nd, [(a, b, e["peso"]) for a, b, e in G.edges(data=True)]


def faixas_de_arestas(nd: pd.DataFrame, ligacoes: list[tuple], faixas: int = 8):
    """Agrupa as arestas por espessura: um traço por faixa (com None entre segmentos), não um por aresta."""
    wmax = max(w for _, _, w in ligacoes)
    grupos: dict[int, tuple[list, list]] = {}
    for a, b, w in ligacoes:
        k = min(faixas - 1, int(faixas * w / wmax))
        xs, ys = grupos.setdefault(k, ([], []))
        xs += [nd.at[a, "x"], nd.at[b, "x"], None]
        ys += [nd.at[a, "y"], nd.at[b, "y"], None]
    return [(xs, ys, .5 + 6 * (k + .5) / faixas) for k, (xs, ys) in sorted(grupos.items())]


aba = st.tabs(["Mapa", "Ranking", "Taxas por grupo", "Grafo de atributos", "Modelo estatístico", "Sobre os dados"],
              on_change="rerun")

# ------------------------------------------------------------------ mapa
def aba_mapa():
    if prioridade:
        st.info(f"Prioridade de teste: {prioridade}. É uma hipótese de investigação, não uma versão confirmada nos chamados nem uma "
                "causa comprovada.")
    st.iframe(html_mapa, height=780)
    st.caption("Cada bloco é um perfil de aparelho (modelo do catálogo). Clique ou toque para ver os detalhes. No "
               "computador, arraste para mover e use a roda do mouse para aproximar. No celular, arraste na horizontal "
               "para percorrer o mapa, use dois dedos para dar zoom e os botões Anterior e Próximo para seguir o "
               "ranking; deslizar na vertical rola a página. A cor indica o status estatístico (veja a legenda) e o número no topo, a "
               "posição no ranking. As versões listadas no catálogo não confirmam o Android instalado nos casos.")

# ------------------------------------------------------------------ ranking
@st.fragment
def aba_ranking():
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
@st.fragment
def aba_taxas():
    dims = [k for k in NOMES_DIM if k in set(tx["dimensao"])]
    if not dims:
        st.info("Não há taxas calculadas para exibir. Rode o pipeline para gerar `resultados_taxas.csv`.")
        return
    marcas_base = tx[tx["dimensao"] == "marca"].set_index("grupo")["base"].dropna()
    if len(marcas_base) and marcas_base.sum() > 0:
        st.markdown(f"Contagem absoluta engana: a marca com mais aparelhos ({marcas_base.idxmax()}, "
                    f"{100 * marcas_base.max() / marcas_base.sum():.0f}% da base) sempre terá mais chamados. Aqui "
                    "comparamos a **taxa** (participantes afetados por mil aparelhos ativos) de cada grupo com a "
                    "taxa do restante da base.")
    else:
        st.markdown("Contagem absoluta engana: o grupo com mais aparelhos sempre terá mais chamados. Aqui comparamos "
                    "a **taxa** (participantes afetados por mil aparelhos ativos) de cada grupo com a taxa do "
                    "restante da base.")
    dim = st.selectbox("Agrupar por", dims, format_func=NOMES_DIM.get, index=dims.index("marca_soc") if "marca_soc" in dims else 0)
    t = tx[tx["dimensao"] == dim].sort_values("taxa_por_mil", ascending=False).head(25)
    base_dim = tx.loc[tx["dimensao"] == dim, "base"].sum()
    ref = 1000 * t["afetados"].sum() / base_dim if len(t) and base_dim else 0
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
    grafico(fig)
    if "android" in dim:
        st.caption("As versões e taxas não são observações confirmadas por chamado: a base por versão é estimada "
                   "e versões ausentes são imputadas. Regra usada: "
                   f"'{config.REGRA_SDK}' (cada modelo contado na versão mais recente que suporta).")
    st.dataframe(t.drop(columns=["destaque", "err_mais", "err_menos"]).round(4), width="stretch", hide_index=True)

# ------------------------------------------------------------------ grafo
@st.fragment
def aba_grafo():
    st.markdown("Cada nó é um atributo (marca, modelo, chip, Android, versão do app, RAM, tipo de erro). Dois atributos "
                "ficam ligados quando aparecem **no mesmo incidente técnico**; a espessura é o número de incidentes. "
                 "**Lift** maior que 1 indica que o atributo aparece nos incidentes mais do que sua participação na base.")
    st.caption("Os nós de Android podem usar versões imputadas pelo catálogo, não informadas no chamado.")
    if arestas.empty or nos.empty or arestas["peso"].dropna().empty:
        st.info("O grafo ainda não foi gerado. Rode o pipeline para criar `grafo_nos.csv` e `grafo_arestas.csv`.")
        return
    c1, c2, c3 = st.columns(3)
    pmin, pmax = int(arestas["peso"].min()), int(arestas["peso"].max())
    peso_min = c1.slider("Peso mínimo da aresta", pmin, max(pmin + 1, pmax), min(max(pmin, 8), pmax))
    cor_por = c2.radio("Cor dos nós", ["tipo", "comunidade"], horizontal=True)
    tipos = c3.multiselect("Tipos de nó", sorted(nos["tipo"].dropna().unique()), default=sorted(nos["tipo"].dropna().unique()))
    nd, ligacoes = montar_grafo(fonte, tuple(tipos), peso_min)
    if not tipos:
        st.info("Selecione ao menos um tipo de nó para ver o grafo.")
    elif len(nd):
        fig = go.Figure()
        for xs, ys, largura in faixas_de_arestas(nd.set_index("no"), ligacoes):
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(width=largura, color="rgba(185,194,202,.28)"),
                                     hoverinfo="skip", showlegend=False))
        nd["grupo_cor"] = nd[cor_por].astype(str)
        maior = max(1, nd["incidentes"].max()) if nd["incidentes"].notna().any() else 1
        for i, (g, sub) in enumerate(nd.groupby("grupo_cor")):
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers+text", name=g, text=sub["no"], textposition="top center",
                textfont=dict(color=TINTA, size=13),
                marker=dict(size=10 + 40 * (sub["incidentes"].fillna(0) / maior) ** .5,
                            color=SERIE[i % len(SERIE)], line=dict(width=1, color=SUPERFICIE)),
                customdata=[[br(i), br(lf, 2), br(c, 3)] for i, lf, c in
                            zip(sub["incidentes"], sub["lift"], sub["centralidade"])],
                hovertemplate="<b>%{text}</b><br>incidentes: %{customdata[0]}<br>lift: %{customdata[1]}"
                              "<br>centralidade: %{customdata[2]}<extra></extra>"))
        fig.update_layout(height=680, xaxis=dict(visible=False), yaxis=dict(visible=False), legend_title=cor_por)
        grafico(fig)
    else:
        st.info("Nenhuma aresta com esse peso mínimo e esses tipos de nó. Diminua o peso mínimo ou inclua mais tipos.")
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
def aba_modelo():
    st.markdown("Regressão de Poisson por célula (modelo x versão do Android), com a base de aparelhos como exposição. "
                "O **IRR** (razão de taxas) mostra quantas vezes a taxa de um grupo é maior que a da categoria de "
                 "referência (**Samsung, Android 14, 8 GB**), controlando pelos outros atributos. Associação, não causa.")
    st.caption("As versões de Android ausentes e a base por versão são estimadas; os coeficientes não demonstram "
               "risco real de uma versão específica.")
    p = poi[poi["ic_sup"] < 1e6].copy()
    if p.empty:
        st.info("O modelo não tem coeficientes estimados para exibir. Rode o pipeline para gerar `modelo_poisson.csv`.")
        return
    p["sig"] = (p["p_valor"] < 0.05).map({True: "p < 0,05", False: "p ≥ 0,05"})
    p["err_mais"], p["err_menos"] = p["ic_sup"] - p["irr"], p["irr"] - p["ic_inf"]
    fig = px.scatter(p, x="irr", y="termo", color="sig", error_x="err_mais", error_x_minus="err_menos", log_x=True,
                     color_discrete_map={"p < 0,05": COR_STATUS["acima"], "p ≥ 0,05": COR_STATUS["normal"]},
                     labels={"irr": "IRR (escala logarítmica, IC 95%)", "termo": "", "sig": ""})
    fig.add_vline(x=1, line_dash="dash", line_color=TINTA2, annotation_text="igual à referência")
    fig.update_traces(marker_size=11)
    grafico(fig)
    st.dataframe(poi.round(4), hide_index=True, width="stretch")

# ------------------------------------------------------------------ sobre
def aba_sobre():
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"""
#### Fontes
- **Google Play Console**: catálogo de aparelhos com o app instalado (modelo, marca, RAM, chip, versões do Android,
  base de instalação). A base conta aparelhos ativos, não pessoas.
- **ServiceNow**: incidentes de login. {"**Nesta visão, simulados.**" if fonte == "simulado" else "Anonimizados na origem."}
- **Pesquisa pública** (só para contexto dos perfis): páginas de suporte da Motorola, notícias sobre atualizações,
  Don't kill my app! e documentação do Android. As fontes aparecem no painel de cada perfil.
- **IBM Instana**: seus registros permanecem no ambiente corporativo de trabalho. Por conterem dados sensíveis,
  não são exportados nem integrados ao projeto, ao repositório ou a este dashboard.

#### Limitações
- Incidente não é aparelho nem pessoa: as taxas contam participantes distintos.
- Só entra quem abriu chamado (viés de quem reporta).
- Os chamados quase nunca informam a versão do Android. A base por versão é estimada e versões ausentes são
  imputadas (regra '{config.REGRA_SDK}'). As versões listadas no catálogo não confirmam a versão de cada caso.
{f"- **{prioridade}** é prioridade de teste, não uma causa confirmada nem uma versão comprovada nos casos." if prioridade else ""}
- O Play Console é uma foto de um momento; os incidentes cobrem um período.
- A ferramenta IBM Instana não compõe a base acadêmica: consultas operacionais ocorrem somente no ambiente de trabalho;
  nenhum dado do Instana é exibido aqui.
- Resultados indicam **associação**, não causa. A hipótese técnica de cada perfil precisa ser validada pelo time do app.
- iOS fica fora das taxas, por falta de catálogo.

#### Privacidade (LGPD)
Nenhum nome, CPF, matrícula ou número original de chamado é armazenado ou exibido. Os participantes são
pseudônimos (HMAC com chave mantida pelo parceiro). Grupos com menos de {config.K_MIN} participantes aparecem sem números.
""")
    with col2:
        st.markdown("#### Funil de dados (rastreabilidade)")
        if fun.empty:
            st.info("O funil de dados não está disponível nesta fonte.")
        else:
            fig = go.Figure(go.Funnel(y=fun["etapa"], x=fun["n"], textinfo="value+percent initial",
                                      marker_color=TEAL, connector=dict(fillcolor="#30363c")))
            fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10))
            grafico(fig)
        sub = (tec.assign(sintoma=tec["subtipo_erro"].map(SINTOMAS)).groupby("sintoma").size()
               .reset_index(name="n").sort_values("n"))
        st.markdown("#### Sintomas nos casos técnicos em Android")
        if sub.empty:
            st.info("Não há casos técnicos em Android com sintoma classificado.")
        else:
            fig = px.bar(sub, x="n", y="sintoma", orientation="h", labels={"n": "incidentes", "sintoma": ""},
                         color_discrete_sequence=[TEAL])
            fig.update_layout(height=340)
            grafico(fig)


for tab, desenha in zip(aba, [aba_mapa, aba_ranking, aba_taxas, aba_grafo, aba_modelo, aba_sobre]):
    if tab.open:
        with tab:
            desenha()
