"""Componentes visuais do dashboard: mapa isométrico de perfis, ranking e cabeçalho.

O mapa é um único componente HTML/SVG/JS autocontido (sem dependências externas):
zonas por marca, um bloco por perfil de aparelho, altura proporcional aos casos,
cor pelo status estatístico e painel de detalhes ao clicar, no estilo dos mapas
de infraestrutura de ferramentas de observabilidade.
"""
from __future__ import annotations

import html
import json
import math
from collections import Counter

import pandas as pd

FONTES_CSS = """
@font-face{font-family:"Plex";src:url("/app/static/fonts/IBMPlexSans-Regular.woff2") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Plex";src:url("/app/static/fonts/IBMPlexSans-Medium.woff2") format("woff2");font-weight:500;font-display:swap}
@font-face{font-family:"Plex";src:url("/app/static/fonts/IBMPlexSans-SemiBold.woff2") format("woff2");font-weight:600;font-display:swap}
@font-face{font-family:"PlexMono";src:url("/app/static/fonts/IBMPlexMono-Regular.woff2") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Plex Fallback";src:local("Arial"),local("Liberation Sans");font-weight:400;size-adjust:100.5%;ascent-override:102%;descent-override:27.4%;line-gap-override:0%}
@font-face{font-family:"Plex Fallback";src:local("Arial"),local("Liberation Sans");font-weight:500;size-adjust:102.5%;ascent-override:100%;descent-override:26.8%;line-gap-override:0%}
@font-face{font-family:"Plex Fallback";src:local("Arial Bold"),local("Arial-BoldMT"),local("Liberation Sans Bold");font-weight:600;size-adjust:97.2%;ascent-override:105.5%;descent-override:28.3%;line-gap-override:0%}
@font-face{font-family:"PlexMono Fallback";src:local("Courier New"),local("Liberation Mono");font-weight:400;ascent-override:102.5%;descent-override:27.5%;line-gap-override:0%}
"""

SINTOMAS = {
    "retorno_tela_inicial": "Volta à tela inicial após o código",
    "erro_auth": "Erro de autenticação (AUTH/INIP)",
    "falha_login_generica": "Falha de login genérica",
    "codigo_verificacao": "Código de verificação",
    "carregamento": "Carregamento sem fim",
    "conexao_servidor": "Conexão com o servidor",
    "biometria": "Biometria",
    "fechamento": "App fecha sozinho",
    "navegador_redirecionamento": "Redirecionamento do navegador",
}
STATUS = {
    "critico": ("Crítico", "Taxa muito acima do esperado, com evidência estatística"),
    "acima": ("Acima do esperado", "Taxa acima do esperado, com evidência estatística"),
    "atencao": ("Atenção", "Taxa alta, mas com poucos casos para afirmar"),
    "normal": ("Sem diferença clara", "Dentro do esperado para o tamanho da base"),
    "sem_base": ("Sem base para taxa", "Casos sem modelo identificado ou de iPhone"),
}
# cores de status: escala de luminosidade + matiz (legível também sem cor, pelos rótulos).
# O texto sobre qualquer uma delas é TXT_STATUS (contraste mínimo 4,5:1).
COR_STATUS = {"critico": "#ec5a5f", "acima": "#f08c3a", "atencao": "#d8bf4a", "normal": "#b9c2ca",
              "sem_base": "#7f8a94"}
TXT_STATUS = "#1b1f23"
COR_ZONA = {"Samsung": "#b6d4f7", "Motorola": "#f5b8d4", "Xiaomi/Redmi/POCO": "#bdf0aa", "Outras": "#d6c8f7",
            "Sem marca": "#f2e59a", "iOS": "#c9d1d8"}


def _fmt(v, casas=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _txt(v) -> str | None:
    return v.strip() or None if isinstance(v, str) else None


def _lista(v) -> list:
    """Lista lida de uma coluna JSON; célula vazia, NaN ou JSON malformado viram lista vazia."""
    if not isinstance(v, str) or not v.strip():
        return []
    try:
        dado = json.loads(v)
    except ValueError:
        return []
    return dado if isinstance(dado, list) else []


def _pares(v, tipo2=None) -> list[list]:
    """Pares [rótulo, valor] de uma coluna JSON, descartando itens fora desse formato."""
    saida = []
    for x in _lista(v):
        if isinstance(x, (list, tuple)) and len(x) == 2:
            if tipo2 is None or isinstance(x[1], tipo2):
                saida.append(list(x))
    return saida


def _url_segura(u) -> str | None:
    return u if isinstance(u, str) and u.lower().startswith(("http://", "https://")) else None


def _registro(r: pd.Series, k_min: int) -> dict:
    afetados = 0 if pd.isna(r["afetados"]) else int(r["afetados"])
    poucos = afetados < k_min
    def cont(v):
        return None if pd.isna(v) else (f"< {k_min}" if v < k_min else f"{int(v):,}".replace(",", "."))
    sint = _pares(r["sintomas_json"], (int, float))
    tot = sum(n for _, n in sint) or 1
    status = r["status"] if r["status"] in STATUS else "sem_base"
    zona = r["zona"] if r["zona"] in COR_ZONA else "Outras"
    ic_ok = not poucos and not pd.isna(r["ic_inf"]) and not pd.isna(r["ic_sup"])
    periodo_ok = not pd.isna(r["inicio"]) and not pd.isna(r["fim"])
    return {
        "id": int(r["perfil_id"]), "nome": _txt(r["perfil"]) or f"Perfil {int(r['perfil_id'])}", "zona": zona,
        "marca": _txt(r["marca"]),
        "chip": _txt(r["chip"]),
        "chipFab": _txt(r["chip_fab"]),
        "ram": _txt(r["ram"]),
        "androidPlay": _txt(r["android_play"]), "androidPeriodo": _txt(r["android_periodo"]),
        "status": status, "statusRotulo": STATUS[status][0], "statusDesc": STATUS[status][1],
        "rank": None if pd.isna(r["rank"]) else int(r["rank"]),
        "ocorr": cont(r["ocorrencias"]), "tec": cont(r["ocorrencias_tecnicas"]), "afet": cont(r["afetados"]),
        "afetN": 0 if poucos else afetados,
        "base": None if pd.isna(r["base"]) else f"{int(r['base']):,}".replace(",", "."),
        "taxa": None if poucos else _fmt(r["taxa_por_mil"]),
        "ic": f"{_fmt(r['ic_inf'])} a {_fmt(r['ic_sup'])}" if ic_ok else None,
        "rr": None if poucos else _fmt(r["risco_relativo"]),
        "ajust": None if pd.isna(r.get("taxa_ajustada")) else float(r["taxa_ajustada"]),
        "sintoma": SINTOMAS.get(r["sintoma"], r["sintoma"]) if isinstance(r["sintoma"], str) else None,
        "sintomas": [] if poucos else [[SINTOMAS.get(s, str(s)), round(100 * n / tot)] for s, n in sint],
        "apps": [] if poucos else [[str(v), n] for v, n in _pares(r["versoes_app_json"], (int, float))],
        "periodo": f"{pd.Timestamp(r['inicio']):%m/%Y} a {pd.Timestamp(r['fim']):%m/%Y}" if periodo_ok else None,
        "resumo": r["resumo"] if isinstance(r["resumo"], str) else "",
        "hipotese": r["hipotese"] if isinstance(r["hipotese"], str) else "",
        "fontes": [[str(t), _url_segura(u)] for t, u in _pares(r["fontes_json"])],
        "poucos": bool(poucos),
    }


def preparar(perfis: pd.DataFrame, k_min: int) -> list[dict]:
    return [_registro(r, k_min) for _, r in perfis.iterrows()]


# ---------------------------------------------------------------------------
MAPA = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
__FONTES__
:root{--chao:#3d444b;--chao2:#353b41;--tinta:#e9edf0;--tinta2:#b3bcc4;--painel:#f7f8f9;--ptinta:#1d2226;
--ptinta2:#5b6670;--linha:#dfe3e6;--teal:#1fb5ac;--teal2:#16958e;--sombra:0 8px 24px rgba(0,0,0,.35);
--f-meta:.78125rem;--f-corpo:.875rem;--f-secao:1.125rem;--fam:"Plex","Plex Fallback",system-ui,sans-serif;
--fam-mono:"PlexMono","PlexMono Fallback",ui-monospace,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--chao);font-family:var(--fam);line-height:1.4;
color:var(--tinta);-webkit-font-smoothing:antialiased}
::selection{background:#1fb5ac55}
#palco{position:relative;height:100vh;overflow:hidden;background:
radial-gradient(120% 90% at 65% 35%,#4a5259 0%,#3d444b 55%,#343a40 100%)}
svg{position:absolute;inset:0;width:100%;height:100%;cursor:grab;touch-action:pan-y}
svg.arrastando{cursor:grabbing}
.cubo{cursor:pointer;transition:filter .15s ease-out}
@media (hover:hover){.cubo:hover{filter:brightness(1.12)}}
.cubo:focus{outline:none}.cubo:focus-visible .topo{stroke:#fff;stroke-width:2}
.rotulo-zona{font:500 var(--f-meta) var(--fam);letter-spacing:.01em}
#painel{position:absolute;left:20px;top:20px;bottom:20px;width:330px;background:var(--painel);color:var(--ptinta);
border-radius:4px;box-shadow:var(--sombra);display:flex;flex-direction:column;overflow:hidden;z-index:3}
#painel header{padding:18px 18px 14px;border-bottom:1px solid var(--linha)}
.titulo{display:flex;gap:10px;align-items:flex-start}
.titulo svg{position:static;width:22px;height:22px;flex:none;margin-top:2px;cursor:default}
.titulo h2{margin:0;font:600 var(--f-secao)/1.25 var(--fam);color:var(--ptinta);word-break:break-word;text-wrap:balance}
.sub{margin-top:4px;font-size:var(--f-meta);color:var(--ptinta2);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.tag{display:inline-block;padding:1px 7px;border-radius:3px;font:500 var(--f-meta)/18px var(--fam);color:#2a2f34}
.acoes{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.selo{display:inline-flex;align-items:center;gap:6px;padding:7px 11px;border-radius:3px;font:500 var(--f-corpo)/1.2 var(--fam);color:#1b1f23}
.selo.claro{background:#e4e8eb;color:#3a444c}
#rolagem{overflow:auto;flex:1;scrollbar-width:thin;scrollbar-color:#c4cbd1 transparent}
details{border-bottom:1px solid var(--linha)}
summary{list-style:none;cursor:pointer;padding:12px 18px;min-height:44px;font:600 var(--f-corpo)/1.3 var(--fam);color:#2a3036;display:flex;
justify-content:space-between;align-items:center}
summary::-webkit-details-marker{display:none}
summary .seta{transition:transform .2s ease-out;width:12px;height:12px;position:static}
details[open] summary .seta{transform:rotate(180deg)}
dl{margin:0;padding:0 18px 12px}
dt{font:500 var(--f-meta)/1.3 var(--fam);color:#4c5862;margin-top:10px}
dd{margin:2px 0 0;font-size:var(--f-corpo);line-height:1.4;color:var(--ptinta);font-variant-numeric:tabular-nums}
dd.grande{font:600 var(--f-secao)/1.25 var(--fam);color:var(--ptinta)}
.barra{display:grid;grid-template-columns:1fr 40px;gap:8px;align-items:center;margin-top:6px;font-size:var(--f-corpo);line-height:1.35;color:#3a444c}
.barra .t{grid-column:1/-1;margin-bottom:-3px}
.barra i{display:block;height:6px;border-radius:3px;background:#dfe3e6;overflow:hidden}
.barra i b{display:block;height:100%;background:var(--teal2)}
.barra span{text-align:right;font-variant-numeric:tabular-nums}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.chips span{background:#e9edf0;border-radius:3px;padding:2px 7px;font:400 var(--f-meta)/1.4 var(--fam-mono);color:#3a444c}
p.texto{margin:6px 18px 12px;font-size:var(--f-corpo);line-height:1.55;color:#3f4a53}
.hip{margin:4px 18px 14px;padding:10px 12px;background:#fff7e0;border-radius:3px;font-size:var(--f-corpo);line-height:1.5;color:#4a3d12}
.hip strong{display:block;font-weight:600;margin-bottom:2px}
ul.fontes{margin:0;padding:0 18px 14px 34px;font-size:var(--f-meta);line-height:1.5}
ul.fontes li+li{margin-top:4px}
ul.fontes a{color:#11756f;text-underline-offset:2px}
.aviso-poucos{margin:10px 18px;font-size:var(--f-corpo);line-height:1.5;color:#5b6670}
#dica{position:absolute;pointer-events:none;background:#1b1f23;color:#fff;padding:7px 10px;border-radius:3px;
font:500 var(--f-corpo)/1.35 var(--fam);box-shadow:0 4px 14px rgba(0,0,0,.4);opacity:0;transition:opacity .12s ease-out;z-index:4;
white-space:nowrap}
#dica small{display:block;font-size:var(--f-meta);font-weight:400;color:#b8c1c9}
#legenda{position:absolute;right:20px;top:18px;background:rgba(27,31,35,.82);border-radius:4px;padding:10px 12px;
font-size:var(--f-meta);color:#d7dde2;z-index:2;}
#legenda h3{margin:0 0 6px;font:600 var(--f-meta) var(--fam);color:#fff}
#legenda div{display:flex;align-items:center;gap:8px;margin-top:4px}
#legenda i{width:12px;height:12px;border-radius:2px;display:inline-block;flex:none;position:relative}
#legenda .dica-leg{margin:0 0 4px;color:#aab4bd}
#legenda button{display:flex;align-items:center;gap:8px;width:100%;margin:2px -6px;padding:4px 6px;border:0;border-radius:3px;
background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer}
#legenda button:hover{background:rgba(255,255,255,.08)}
#legenda button[aria-pressed="true"]{background:rgba(255,255,255,.18);color:#fff}
#legenda button:focus-visible{outline:2px solid #fff;outline-offset:1px}
#legenda .qtd{margin-left:auto;padding-left:10px;font-variant-numeric:tabular-nums;color:#aab4bd}
.g-critico{box-shadow:0 0 0 1.5px #fff}
.g-atencao::after{content:"";position:absolute;inset:3.5px;background:rgba(27,31,35,.6)}
.g-sem_base{border:1.5px dashed #1b1f23}
#controles{position:absolute;right:20px;bottom:20px;display:flex;gap:6px;z-index:2}
#controles button{font:500 var(--f-corpo) var(--fam);background:#f2f4f5;color:#2a3036;border:0;border-radius:3px;
height:32px;min-width:32px;padding:0 10px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.25)}
#controles button:hover{background:#fff}
#controles button[aria-pressed="true"]{background:var(--teal);color:#1b1f23}
#controles button:focus-visible{outline:2px solid #fff;outline-offset:2px}
.nav button,#leg-btn{font:500 var(--f-corpo) var(--fam);border:0;border-radius:3px;cursor:pointer;display:inline-flex;align-items:center;
justify-content:center;gap:6px;height:36px;padding:0 10px}
.nav{display:none}
.nav button{flex:1;background:#e4e8eb;color:#2a3036}
.nav button:disabled{opacity:.45;cursor:default}
.nav button svg{position:static;width:12px;height:12px;cursor:default;flex:none}
.nav button:focus-visible,#leg-btn:focus-visible{outline:2px solid var(--teal2);outline-offset:2px}
#leg-btn{display:none;position:absolute;left:8px;top:8px;z-index:3;background:rgba(27,31,35,.82);color:#e9edf0;box-shadow:0 2px 6px rgba(0,0,0,.25)}
#leg-btn[aria-expanded="true"]{background:#f2f4f5;color:#2a3036}
@media (pointer:coarse){#controles{gap:8px}#controles button,.nav button,#leg-btn{height:44px;min-width:44px}
#legenda button{min-height:44px}
summary{padding:14px 18px}ul.fontes li a{display:inline-block;padding:8px 0}ul.fontes li+li{margin-top:0}}
@media (hover:none){#dica{display:none}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (max-width:900px){
#painel{left:8px;right:8px;width:auto;top:auto;bottom:8px;height:47%}
#painel.recolhido{height:auto}#painel.recolhido #rolagem{display:none}
#painel header{padding:12px 14px 10px}
.titulo h2{font-size:1rem}
.acoes{margin-top:10px}
.nav{display:flex;gap:8px;margin-top:10px}
#leg-btn{display:inline-flex}
#legenda{display:none;left:8px;right:auto;top:56px}#legenda.aberta{display:block}
#controles{top:8px;bottom:auto;right:8px}#controles #reset{display:none}}
</style></head><body>
<div id="palco">
  <svg id="mapa" role="group" aria-label="Mapa de perfis de aparelho por marca. Cada bloco é um botão. Use as setas para percorrer os perfis, Início e Fim para ir ao primeiro e ao último, e Enter para selecionar."></svg>
  <aside id="painel" aria-live="polite"></aside>
  <button id="leg-btn" aria-expanded="false" aria-controls="legenda">Legenda</button>
  <div id="legenda"><h3>Status do perfil</h3><p class="dica-leg">Clique para destacar um status</p>__LEGENDA__
    <div style="margin-top:8px;color:#aab4bd">Altura: <span id="leg-altura"></span></div></div>
  <div id="controles">
    <button id="h-afet" aria-pressed="true" title="Altura pelos participantes afetados">Afetados</button>
    <button id="h-taxa" aria-pressed="false" title="Altura pela taxa ajustada por mil aparelhos">Taxa</button>
    <button id="menos" aria-label="Afastar">−</button><button id="mais" aria-label="Aproximar">+</button>
    <button id="reset" title="Centralizar">Centralizar</button>
  </div>
  <div id="dica"></div>
</div>
<script>
const DADOS = __DADOS__, COR = __COR__, ZCOR = __ZCOR__, TXT = '__TXT__';
const svg = document.getElementById('mapa'), NS = 'http://www.w3.org/2000/svg';
const TW = 46, TH = 23;                       // tamanho do losango de uma célula
let filtro = null, modoAltura = 'afet', selecionado = DADOS[0] ? DADOS[0].id : null, foco = selecionado, zoom = 1, zmin = .4, pan = {x: 0, y: 0}, ult = null;
const estreito = window.matchMedia('(max-width:900px)');
const ordem = [...DADOS].sort((a, b) => (a.rank ?? 1e9) - (b.rank ?? 1e9));

const ordemZonas = ['Samsung','Motorola','Xiaomi/Redmi/POCO','Outras','Sem marca','iOS'];
const zonas = ordemZonas.map(z => ({nome: z, itens: DADOS.filter(d => d.zona === z)})).filter(z => z.itens.length);
// tamanho de cada zona e posição em duas fileiras diagonais
zonas.forEach(z => {
  z.cols = Math.max(2, Math.ceil(Math.sqrt(z.itens.length * 1.3)));
  z.rows = Math.max(2, Math.ceil(z.itens.length / z.cols));
});
const fileira = [zonas.slice(0, 3), zonas.slice(3)];
let oy = 0;
fileira.forEach(f => {
  let ox = 0, alt = 0;
  f.forEach(z => { z.ox = ox; z.oy = oy; ox += z.cols + 2.2; alt = Math.max(alt, z.rows); });
  oy += alt + 2.6;
});
zonas.forEach(z => z.itens.forEach((d, k) => { d.gx = z.ox + (k % z.cols); d.gy = z.oy + Math.floor(k / z.cols); d.z = z; d.k = k; }));
const ordemMapa = zonas.flatMap(z => z.itens);
const TEXTO_ALTURA = {afet: 'participantes afetados, em raiz quadrada (4× os casos = 2× a altura)', taxa: 'taxa ajustada por mil, em raiz quadrada (4× a taxa = 2× a altura)'};

const maxAfet = Math.max(1, ...DADOS.map(d => d.afetN));
const maxAj = Math.max(1, ...DADOS.map(d => d.ajust || 0));
function altura(d) {
  const v = modoAltura === 'afet' ? d.afetN / maxAfet : (d.ajust || 0) / maxAj;
  return 6 + 74 * Math.sqrt(Math.max(0, v));
}
const P = (x, y, z = 0) => [(x - y) * TW / 2, (x + y) * TH / 2 - z];
const pts = a => a.map(p => p.join(',')).join(' ');
function el(tag, at, pai) { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); pai && pai.appendChild(e); return e; }
function tom(hex, f) { const n = parseInt(hex.slice(1), 16); let r = n >> 16, g = n >> 8 & 255, b = n & 255;
  const m = c => Math.max(0, Math.min(255, Math.round(c * f))); return `rgb(${m(r)},${m(g)},${m(b)})`; }

let raiz;
const cubos = {};
function desenhar() {
  svg.innerHTML = '';
  raiz = el('g', {}, svg);
  const camChao = el('g', {}, raiz), camCubos = el('g', {}, raiz), camRotulos = el('g', {}, raiz);
  zonas.forEach(z => {
    const a = P(z.ox - .7, z.oy - .7), b = P(z.ox + z.cols - .3, z.oy - .7), c = P(z.ox + z.cols - .3, z.oy + z.rows - .3), d = P(z.ox - .7, z.oy + z.rows - .3);
    el('polygon', {points: pts([a, b, c, d]), fill: 'rgba(255,255,255,.035)', stroke: ZCOR[z.nome] || '#ccc', 'stroke-opacity': .55, 'stroke-width': 1}, camChao);
    const g = el('g', {}, camRotulos), txt = `${z.nome} · ${z.itens.length}`;
    const w = txt.length * 6.9 + 16;
    el('rect', {x: d[0] + 4 - w, y: d[1] + 4, width: w, height: 20, rx: 3, fill: ZCOR[z.nome] || '#ccc'}, g);
    const t = el('text', {x: d[0] + 4 - w / 2, y: d[1] + 18, 'text-anchor': 'middle', class: 'rotulo-zona', fill: '#22282d'}, g);
    t.textContent = txt;
  });
  [...DADOS].sort((p, q) => (p.gx + p.gy) - (q.gx + q.gy)).forEach(d => {
    const h = altura(d), s = .3, x = d.gx, y = d.gy, sel = d.id === selecionado;
    const base = sel ? '#ffffff' : COR[d.status], crit = d.status === 'critico' && !sel, sb = d.status === 'sem_base' && !sel;
    const g = el('g', {class: 'cubo', tabindex: d.id === foco ? 0 : -1, role: 'button', 'aria-pressed': sel, 'aria-label': `${d.nome}, ${d.statusRotulo}, afetados ${d.afet ?? '—'}`,
      opacity: filtro && !sel && d.status !== filtro ? .2 : 1}, camCubos);
    cubos[d.id] = g;
    el('polygon', {points: pts([P(x - .5, y - .5), P(x + .5, y - .5), P(x + .5, y + .5), P(x - .5, y + .5)]), fill: 'transparent'}, g);
    el('polygon', {points: pts([P(x - s, y + s), P(x + s, y + s), P(x + s, y + s, h), P(x - s, y + s, h)]), fill: tom(base, .78)}, g);
    el('polygon', {points: pts([P(x + s, y - s), P(x + s, y + s), P(x + s, y + s, h), P(x + s, y - s, h)]), fill: tom(base, .62)}, g);
    el('polygon', {class: 'topo', points: pts([P(x - s, y - s, h), P(x + s, y - s, h), P(x + s, y + s, h), P(x - s, y + s, h)]),
      fill: tom(base, 1.06), stroke: sel ? '#1fb5ac' : crit ? '#fff' : sb ? TXT : 'rgba(0,0,0,.18)',
      'stroke-width': sel ? 2 : crit ? 1.6 : sb ? 1.2 : .6, 'stroke-dasharray': sb ? '3 2' : 'none'}, g);
    if (d.status === 'atencao' && !sel) {
      const q = .13;
      el('polygon', {points: pts([P(x - q, y - q, h), P(x + q, y - q, h), P(x + q, y + q, h), P(x - q, y + q, h)]), fill: 'rgba(27,31,35,.6)', 'pointer-events': 'none'}, g);
    }
    if (d.status === 'critico' || d.status === 'acima' || sel) {
      const [tx, ty] = P(x, y, h + 12), rot = d.rank ? `#${d.rank}` : '•', cheio = crit;
      const w = rot.length * 7.6 + 12;
      el('rect', {x: tx - w / 2, y: ty - 14, width: w, height: 18, rx: 3, fill: cheio ? COR.critico : '#1b1f23', stroke: cheio ? '#fff' : 'none', 'stroke-width': 1.4}, g);
      const t = el('text', {x: tx, y: ty - .5, 'text-anchor': 'middle', fill: cheio ? TXT : '#fff', style: 'font:600 12px "Plex","Plex Fallback",sans-serif'}, g); t.textContent = rot;
    }
    g.addEventListener('click', () => selecionar(d.id));
    g.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selecionar(d.id); return; }
      const alvo = vizinho(d, e.key); if (alvo) { e.preventDefault(); moverFoco(alvo.id); }
    });
    g.addEventListener('pointerenter', e => dica(d, e)); g.addEventListener('pointermove', e => dica(d, e));
    g.addEventListener('pointerleave', () => { document.getElementById('dica').style.opacity = 0; });
  });
  ajustarVista();
}
function vizinho(d, tecla) {
  const i = ordemMapa.indexOf(d), z = d.z, zi = zonas.indexOf(z);
  switch (tecla) {
    case 'ArrowRight': return ordemMapa[i + 1];
    case 'ArrowLeft': return ordemMapa[i - 1];
    case 'ArrowDown': return z.itens[d.k + z.cols];
    case 'ArrowUp': return z.itens[d.k - z.cols];
    case 'PageDown': return zonas[zi + 1] && zonas[zi + 1].itens[0];
    case 'PageUp': return zonas[zi - 1] && zonas[zi - 1].itens[0];
    case 'Home': return ordemMapa[0];
    case 'End': return ordemMapa[ordemMapa.length - 1];
  }
}
function moverFoco(id) {
  if (cubos[foco]) cubos[foco].setAttribute('tabindex', -1);
  foco = id; cubos[id].setAttribute('tabindex', 0); cubos[id].focus({preventScroll: true});
}
let caixa;
function ajustarVista(recalcular = true) {
  if (recalcular || !caixa) { const bb = raiz.getBBox(); caixa = {x: bb.x - 40, y: bb.y - 60, w: bb.width + 80, h: bb.height + 100}; }
  const larg = svg.clientWidth, alt = svg.clientHeight, est = estreito.matches, pn = document.getElementById('painel');
  const x0 = est ? 8 : pn.offsetWidth + 40, y0 = est ? 56 : 0;
  const util = Math.max(200, larg - x0 - (est ? 8 : 30));
  const altUtil = est ? Math.max(160, pn.offsetTop - 8 - y0) : alt;
  const ajusteL = util / caixa.w, ajusteA = altUtil / caixa.h, ajuste = Math.min(ajusteL, ajusteA);
  const base = est ? ajusteA : ajuste;
  zmin = est ? Math.min(1, ajuste / base) : .4;
  zoom = Math.min(4, Math.max(zmin, zoom));
  const esc = base * zoom, cx = caixa.x + caixa.w / 2, cy = caixa.y + caixa.h / 2;
  const lx = Math.max(0, (caixa.w * esc - util) / 2) + util * .2, ly = Math.max(0, (caixa.h * esc - altUtil) / 2) + altUtil * .2;
  pan = {x: Math.max(-lx, Math.min(lx, pan.x)), y: Math.max(-ly, Math.min(ly, pan.y))};
  ult = {esc, cx, cy};
  raiz.setAttribute('transform', `translate(${x0 + util / 2 + pan.x},${y0 + altUtil / 2 + pan.y}) scale(${esc}) translate(${-cx},${-cy})`);
}
function centrar() {
  const d = DADOS.find(x => x.id === selecionado);
  if (!d || !ult) return;
  const [px, py] = P(d.gx, d.gy, altura(d) / 2);
  pan = {x: -ult.esc * (px - ult.cx), y: -ult.esc * (py - ult.cy)};
  ajustarVista(false);
}
function dica(d, e) {
  const t = document.getElementById('dica');
  t.innerHTML = `${esc(d.nome)}<small>${d.statusRotulo} · afetados ${d.afet ?? '—'}${d.taxa ? ` · ${d.taxa} por mil` : ''}</small>`;
  t.style.left = (e.clientX + 14) + 'px'; t.style.top = (e.clientY + 14) + 'px'; t.style.opacity = 1;
}
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const SETA = '<svg class="seta" viewBox="0 0 12 12"><path d="M2 8l4-4 4 4" fill="none" stroke="#5b6670" stroke-width="1.6"/></svg>';
const ICONE = c => `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="2.5" width="12" height="19" rx="2.5" fill="none" stroke="${c}" stroke-width="1.8"/><path d="M10 18.5h4" stroke="${c}" stroke-width="1.8" stroke-linecap="round"/></svg>`;
function item(t, v, cls = '') { return v == null || v === '' ? '' : `<dt>${t}</dt><dd class="${cls}">${v}</dd>`; }
function selecionar(id, focar = true) { selecionado = id; foco = id; desenhar(); painel(); ajustarVista(false); if (focar && cubos[id]) cubos[id].focus({preventScroll: true}); }
function navegar(passo, origem) {
  const i = ordem.findIndex(x => x.id === selecionado), alvo = ordem[i + passo];
  if (!alvo) return;
  selecionar(alvo.id, false); centrar();
  const b = document.getElementById(origem);
  (b && !b.disabled ? b : document.getElementById('alterna')).focus({preventScroll: true});
}
const CHEV = d => `<svg viewBox="0 0 12 12" aria-hidden="true"><path d="${d}" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`;
function painel() {
  const d = DADOS.find(x => x.id === selecionado), p = document.getElementById('painel');
  if (!d) { p.innerHTML = '<header><h2>Nenhum perfil</h2></header>'; return; }
  const cor = COR[d.status], txtSelo = TXT, rec = p.classList.contains('recolhido'), i = ordem.findIndex(x => x.id === d.id);
  p.innerHTML = `<header><div class="titulo">${ICONE('#3a444c')}<div><h2>${esc(d.nome)}</h2>
    <div class="sub">Perfil de aparelho${d.chip ? ` <span class="tag" style="background:${ZCOR[d.zona] || '#ddd'}">${esc(d.chipFab || d.chip)}</span>` : ''}</div></div></div>
    <div class="acoes"><span class="selo" style="background:${cor};color:${txtSelo}" title="${esc(d.statusDesc)}">${esc(d.statusRotulo)}${d.rr ? ` · ${d.rr}x` : ''}</span>
    ${d.rank ? `<span class="selo claro">#${d.rank} no ranking</span>` : ''}</div>
    <div class="nav" role="group" aria-label="Navegar entre perfis, na ordem do ranking">
      <button id="ant" aria-label="Perfil anterior no ranking" ${i === 0 ? 'disabled' : ''}>${CHEV('M8 2L4 6l4 4')}Anterior</button>
      <button id="prox" aria-label="Próximo perfil no ranking" ${i === ordem.length - 1 ? 'disabled' : ''}>Próximo${CHEV('M4 2l4 4-4 4')}</button>
      <button id="alterna" aria-expanded="${!rec}" aria-controls="rolagem">${rec ? 'Detalhes' : 'Recolher'}</button>
    </div></header>
    <div id="rolagem">
    ${d.poucos ? `<p class="aviso-poucos">Menos de __KMIN__ participantes: números detalhados omitidos por privacidade.</p>` : ''}
    <details open><summary>Ocorrências ${SETA}</summary><dl>
      ${item('Participantes afetados', d.afet, 'grande')}
      ${item('Ocorrências de login (Android)', d.ocorr)}${item('Técnicas', d.tec)}
      ${item('Aparelhos ativos (Play Console)', d.base)}
      ${item('Taxa por mil aparelhos', d.taxa ? `${d.taxa} <span style="color:#5b6670">(IC 95%: ${d.ic})</span>` : null)}
      ${item('Risco relativo', d.rr ? `${d.rr} vezes a taxa dos demais perfis` : null)}
      ${item('Período dos casos', d.periodo)}
    </dl></details>
    <details open><summary>Sistema ${SETA}</summary><dl>
      ${item('Marca', esc(d.marca))}${item('Chip (SoC)', esc(d.chip))}${item('Memória', esc(d.ram))}
      ${item('Android listado para o modelo', esc(d.androidPeriodo))}
    </dl></details>
    ${d.sintomas.length ? `<details open><summary>Sintomas relatados ${SETA}</summary><dl>${d.sintomas.map(([s, v]) =>
      `<div class="barra"><span class="t">${esc(s)}</span><i><b style="width:${v}%"></b></i><span>${v}%</span></div>`).join('')}</dl></details>` : ''}
    ${d.apps.length ? `<details open><summary>Versões do app nos casos ${SETA}</summary><dl><div class="chips">${d.apps.map(([v, n]) =>
      `<span>${esc(v)} · ${n}</span>`).join('')}</div></dl></details>` : ''}
    ${d.resumo || d.hipotese || d.fontes.length ? `<details open><summary>Contexto público ${SETA}</summary>
      ${d.resumo ? `<p class="texto">${esc(d.resumo)}</p>` : ''}
      ${d.hipotese ? `<div class="hip"><strong>Hipótese, a validar</strong>${esc(d.hipotese)}</div>` : ''}
      ${d.fontes.length ? `<ul class="fontes">${d.fontes.map(([t, u]) => u ? `<li><a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a></li>` : `<li>${esc(t)}</li>`).join('')}</ul>` : ''}
    </details>` : ''}
    </div>`;
  document.getElementById('ant').onclick = () => navegar(-1, 'ant');
  document.getElementById('prox').onclick = () => navegar(1, 'prox');
  document.getElementById('alterna').onclick = () => { p.classList.toggle('recolhido'); painel(); ajustarVista(true); centrar();
    document.getElementById('alterna').focus({preventScroll: true}); };
}
const lb = document.getElementById('leg-btn');
lb.onclick = () => { const a = document.getElementById('legenda').classList.toggle('aberta'); lb.setAttribute('aria-expanded', a); };
// zoom, arraste e altura
document.getElementById('mais').onclick = () => { zoom = Math.min(4, zoom * 1.25); ajustarVista(false); };
document.getElementById('menos').onclick = () => { zoom = Math.max(zmin, zoom / 1.25); ajustarVista(false); };
document.getElementById('reset').onclick = () => { zoom = 1; pan = {x: 0, y: 0}; ajustarVista(false); };
function modo(m) { modoAltura = m; document.getElementById('h-afet').setAttribute('aria-pressed', m === 'afet');
  document.getElementById('h-taxa').setAttribute('aria-pressed', m === 'taxa');
  document.getElementById('leg-altura').textContent = TEXTO_ALTURA[m]; desenhar(); }
document.getElementById('leg-altura').textContent = TEXTO_ALTURA.afet;
document.querySelectorAll('#legenda [data-status]').forEach(b => b.onclick = () => {
  filtro = filtro === b.dataset.status ? null : b.dataset.status;
  document.querySelectorAll('#legenda [data-status]').forEach(x => x.setAttribute('aria-pressed', x.dataset.status === filtro));
  desenhar(); });
document.getElementById('h-afet').onclick = () => modo('afet'); document.getElementById('h-taxa').onclick = () => modo('taxa');
let arr = null, pinca = null;
const toques = new Map();
function fimGesto(e) { toques.delete(e.pointerId); arr = null; if (toques.size < 2) pinca = null; svg.classList.remove('arrastando'); }
function medidas() { const [a, b] = [...toques.values()]; return {d: Math.hypot(a.x - b.x, a.y - b.y) || 1, x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}; }
svg.addEventListener('pointerdown', e => {
  const toque = e.pointerType === 'touch';
  if (!toque && e.target.closest('.cubo')) return;
  toques.set(e.pointerId, {x: e.clientX, y: e.clientY, x0: e.clientX});
  if (toques.size === 2) { arr = null; toques.forEach((_, id) => svg.setPointerCapture(id)); const m = medidas(); pinca = {...m, zoom, pan: {...pan}}; return; }
  if (!toque) { svg.setPointerCapture(e.pointerId); arr = {x: e.clientX - pan.x, y: e.clientY - pan.y}; svg.classList.add('arrastando'); }
});
svg.addEventListener('pointermove', e => {
  const t = toques.get(e.pointerId);
  if (t) { t.x = e.clientX; t.y = e.clientY; }
  if (pinca && toques.size === 2) {
    const m = medidas();
    zoom = Math.min(4, Math.max(zmin, pinca.zoom * m.d / pinca.d));
    pan = {x: pinca.pan.x + m.x - pinca.x, y: pinca.pan.y + m.y - pinca.y}; ajustarVista(false); return;
  }
  if (t && e.pointerType === 'touch' && !arr && toques.size === 1 && Math.abs(e.clientX - t.x0) > 8) {
    svg.setPointerCapture(e.pointerId); arr = {x: e.clientX - pan.x, y: 0};
  }
  if (!arr) return;
  pan = {x: e.clientX - arr.x, y: e.pointerType === 'touch' ? pan.y : e.clientY - arr.y}; ajustarVista(false);
});
['pointerup', 'pointercancel', 'lostpointercapture'].forEach(t => svg.addEventListener(t, fimGesto));
window.addEventListener('blur', () => { toques.clear(); arr = null; pinca = null; svg.classList.remove('arrastando'); });
svg.addEventListener('wheel', e => { e.preventDefault(); zoom = Math.min(4, Math.max(zmin, zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1))); ajustarVista(false); }, {passive: false});
window.addEventListener('resize', () => ajustarVista(false));
desenhar(); painel();
if (estreito.matches) { ajustarVista(true); centrar(); }
</script></body></html>"""


def mapa_html(registros: list[dict], k_min: int) -> str:
    n = Counter(r["status"] for r in registros)
    legenda = "".join(f'<button type="button" data-status="{s}" aria-pressed="false">'
                      f'<i class="g-{s}" style="background:{COR_STATUS[s]}"></i>{STATUS[s][0]}'
                      f'<span class="qtd">{n.get(s, 0)}</span></button>'
                      for s in ["critico", "acima", "atencao", "normal", "sem_base"])
    return (MAPA.replace("__FONTES__", FONTES_CSS).replace("__LEGENDA__", legenda)
            .replace("__DADOS__", json.dumps(registros, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__COR__", json.dumps(COR_STATUS)).replace("__ZCOR__", json.dumps(COR_ZONA))
            .replace("__KMIN__", str(k_min)).replace("__TXT__", TXT_STATUS))


# ---------------------------------------------------------------------------
def ranking_html(registros: list[dict], k_min: int) -> str:
    if not registros:
        return ('<div class="ranking vazio" role="status"><p>Nenhum perfil encontrado com esses filtros. '
                'Limpe a busca ou remova algum status ou marca para ver a lista completa.</p></div>')
    com = [r for r in registros if r["rank"] is not None]
    sem = [r for r in registros if r["rank"] is None]
    max_ic = max([float(r["ic"].split(" a ")[1].replace(".", "").replace(",", ".")) for r in com if r["ic"]] + [1])
    max_ic_real = max_ic
    max_ic = min(max_ic, 120)
    nota_corte = ('; a seta no fim da barra indica intervalo que passa desse limite, e o valor completo está no texto'
                  if max_ic_real > max_ic else '')

    def num(s):
        return float(s.replace(".", "").replace(",", ".")) if s else None

    linhas, cartoes = [], []
    for r in com:
        cor = COR_STATUS[r["status"]]
        txt = TXT_STATUS
        if r["taxa"] and r["ic"]:
            lo, hi = (num(x) for x in r["ic"].split(" a "))
            t = num(r["taxa"])
            esc_ = lambda v: min(100, 100 * v / max_ic)
            seta = f'<path d="M95 2l5 5-5 5z" fill="{cor}"/>' if hi > max_ic else ""
            barra = (f'<svg class="ic" viewBox="0 0 100 14" preserveAspectRatio="none" aria-hidden="true">'
                     f'<rect x="0" y="6" width="100" height="2" fill="#3a4148"/>'
                     f'<rect x="{esc_(lo):.1f}" y="4" width="{max(1, esc_(hi) - esc_(lo)):.1f}" height="6" rx="1" fill="{cor}" opacity=".55"/>'
                     f'<rect x="{esc_(t) - .8:.1f}" y="1" width="1.6" height="12" fill="{cor}"/>{seta}</svg>')
            taxa = f'<b>{r["taxa"]}</b><small>{r["ic"]}</small>{barra}'
            taxa_c = (f'<div class="taxa"><b>{r["taxa"]}</b> por mil <small>IC 95%: {r["ic"]}</small>{barra}</div>')
        else:
            taxa = '<span class="mudo">poucos casos</span>'
            taxa_c = '<div class="taxa mudo">Poucos casos para calcular a taxa</div>'
        tag_c = (f'<span class="tag" style="background:{COR_ZONA.get(r["zona"], "#ddd")}">{html.escape(r["chipFab"])}</span>'
                 if r["chipFab"] else "")
        cartoes.append(f"""<li class="cartao"><div class="cab"><span class="pos">{r['rank']}</span>
<div class="id"><div class="nome">{html.escape(r['nome'])}</div><div class="meta">{html.escape(r['marca'] or '')} {tag_c}</div></div>
<span class="st" style="background:{cor};color:{txt}">{html.escape(r['statusRotulo'])}</span></div>{taxa_c}
<dl class="nums"><div><dt>Afetados</dt><dd>{r['afet'] or '—'}</dd></div><div><dt>Ocorrências</dt><dd>{r['ocorr'] or '—'}</dd></div>
<div><dt>Aparelhos</dt><dd>{r['base'] or '—'}</dd></div><div><dt>Risco relativo</dt><dd>{(r['rr'] + 'x') if r['rr'] else '—'}</dd></div></dl>
<p class="txt"><span>Android provável</span>{html.escape(r['androidPeriodo'] or '—')}</p>
<p class="txt"><span>Sintoma predominante</span>{html.escape(r['sintoma'] or '—')}</p></li>""")
        linhas.append(f"""<tr>
<td class="pos">{r['rank']}</td>
<th scope="row" class="rot"><div class="nome">{html.escape(r['nome'])}</div><div class="meta">{html.escape(r['marca'] or '')}
{f'<span class="tag" style="background:{COR_ZONA.get(r["zona"], "#ddd")}">{html.escape(r["chipFab"] or "")}</span>' if r['chipFab'] else ''}</div></th>
<td><span class="st" style="background:{cor};color:{txt}">{html.escape(r['statusRotulo'])}</span></td>
<td class="n">{r['afet'] or '—'}</td><td class="n">{r['ocorr'] or '—'}</td><td class="n">{r['base'] or '—'}</td>
<td class="tx">{taxa}</td><td class="n">{(r['rr'] + 'x') if r['rr'] else '—'}</td>
<td>{html.escape(r['androidPeriodo'] or '—')}</td><td>{html.escape(r['sintoma'] or '—')}</td></tr>""")
    extra = "".join(f"<tr><td class='pos'>—</td><th scope='row' class='rot'><div class='nome'>{html.escape(r['nome'])}</div></th>"
                    f"<td><span class='st' style='background:{COR_STATUS['sem_base']};color:{TXT_STATUS}'>Sem base para taxa</span></td>"
                    f"<td class='n'>{r['afet'] or '—'}</td><td class='n'>{r['ocorr'] or '—'}</td><td class='n'>—</td>"
                    f"<td class='tx'><span class='mudo'>sem catálogo</span></td><td class='n'>—</td>"
                    f"<td>{html.escape(r['androidPeriodo'] or '—')}</td><td>{html.escape(r['sintoma'] or '—')}</td></tr>"
                    for r in sem)
    cartoes_sem = "".join(
        f"""<li class="cartao"><div class="cab"><span class="pos">—</span><div class="id"><div class="nome">{html.escape(r['nome'])}</div></div>
<span class="st" style="background:{COR_STATUS['sem_base']};color:{TXT_STATUS}">Sem base para taxa</span></div>
<div class="taxa mudo">Sem catálogo para calcular a taxa</div>
<dl class="nums"><div><dt>Afetados</dt><dd>{r['afet'] or '—'}</dd></div><div><dt>Ocorrências</dt><dd>{r['ocorr'] or '—'}</dd></div></dl>
<p class="txt"><span>Android provável</span>{html.escape(r['androidPeriodo'] or '—')}</p>
<p class="txt"><span>Sintoma predominante</span>{html.escape(r['sintoma'] or '—')}</p></li>""" for r in sem)
    return f"""<div class="ranking" role="region" aria-label="Ranking de perfis, tabela rolável" tabindex="0"><table>
<caption>Ranking de perfis por taxa ajustada. Grupos com menos de {k_min} participantes aparecem como
"&lt; {k_min}" e sem taxa, por privacidade. A barra mostra a taxa por mil aparelhos e o intervalo de confiança de 95%
(escala de 0 a {max_ic:.0f} por mil{nota_corte}).</caption>
<thead><tr><th scope="col">#</th><th scope="col">Perfil</th><th scope="col">Status</th><th scope="col" class="n">Afetados</th><th scope="col" class="n">Ocorrências</th>
<th scope="col" class="n">Aparelhos</th><th scope="col">Taxa por mil (IC 95%)</th><th scope="col" class="n">Risco relativo</th>
<th scope="col">Android provável no período</th><th scope="col">Sintoma predominante</th></tr></thead>
<tbody>{''.join(linhas)}</tbody>
<tbody class="sem"><tr><th colspan="10" scope="colgroup">Casos sem base para taxa</th></tr>{extra}</tbody></table>
<div class="cartoes"><p class="legenda-cartoes">{ "Perfis ordenados pela taxa ajustada. Grupos com menos de %d participantes aparecem sem taxa, por privacidade. A barra vai de 0 a %.0f por mil aparelhos e mostra a taxa e o IC 95%%%s." % (k_min, max_ic, nota_corte) }</p>
<ol>{''.join(cartoes)}</ol>
<h4>Casos sem base para taxa</h4><ol>{cartoes_sem}</ol></div></div>"""
