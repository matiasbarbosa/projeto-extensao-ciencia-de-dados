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

import pandas as pd

FONTES_CSS = """
@font-face{font-family:"Plex";src:url("/app/static/fonts/IBMPlexSans-Regular.woff2") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Plex";src:url("/app/static/fonts/IBMPlexSans-Medium.woff2") format("woff2");font-weight:500;font-display:swap}
@font-face{font-family:"Plex";src:url("/app/static/fonts/IBMPlexSans-SemiBold.woff2") format("woff2");font-weight:600;font-display:swap}
@font-face{font-family:"PlexMono";src:url("/app/static/fonts/IBMPlexMono-Regular.woff2") format("woff2");font-weight:400;font-display:swap}
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
# cores de status: escala de luminosidade + matiz (legível também sem cor, pelos rótulos)
COR_STATUS = {"critico": "#e5484d", "acima": "#f08c3a", "atencao": "#d8bf4a", "normal": "#b9c2ca",
              "sem_base": "#7f8a94"}
COR_ZONA = {"Samsung": "#b6d4f7", "Motorola": "#f5b8d4", "Xiaomi/Redmi/POCO": "#bdf0aa", "Outras": "#d6c8f7",
            "Sem marca": "#f2e59a", "iOS": "#c9d1d8"}


def _fmt(v, casas=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _registro(r: pd.Series, k_min: int) -> dict:
    poucos = (r["afetados"] or 0) < k_min
    def cont(v):
        return None if pd.isna(v) else (f"< {k_min}" if v < k_min else f"{int(v):,}".replace(",", "."))
    sint = json.loads(r["sintomas_json"]) if isinstance(r["sintomas_json"], str) else []
    tot = sum(n for _, n in sint) or 1
    return {
        "id": int(r["perfil_id"]), "nome": r["perfil"], "zona": r["zona"], "marca": r["marca"],
        "chip": r["chip"] if isinstance(r["chip"], str) else None,
        "chipFab": r["chip_fab"] if isinstance(r["chip_fab"], str) else None,
        "ram": r["ram"] if isinstance(r["ram"], str) else None,
        "androidPlay": r["android_play"], "androidPeriodo": r["android_periodo"],
        "status": r["status"], "statusRotulo": STATUS[r["status"]][0], "statusDesc": STATUS[r["status"]][1],
        "rank": None if pd.isna(r["rank"]) else int(r["rank"]),
        "ocorr": cont(r["ocorrencias"]), "tec": cont(r["ocorrencias_tecnicas"]), "afet": cont(r["afetados"]),
        "afetN": 0 if poucos else int(r["afetados"]),
        "base": None if pd.isna(r["base"]) else f"{int(r['base']):,}".replace(",", "."),
        "taxa": None if poucos else _fmt(r["taxa_por_mil"]),
        "ic": None if poucos or pd.isna(r["ic_inf"]) else f"{_fmt(r['ic_inf'])} a {_fmt(r['ic_sup'])}",
        "rr": None if poucos else _fmt(r["risco_relativo"]),
        "ajust": None if pd.isna(r.get("taxa_ajustada")) else float(r["taxa_ajustada"]),
        "sintoma": SINTOMAS.get(r["sintoma"], r["sintoma"]) if isinstance(r["sintoma"], str) else None,
        "sintomas": [] if poucos else [[SINTOMAS.get(s, s), round(100 * n / tot)] for s, n in sint],
        "apps": [] if poucos else json.loads(r["versoes_app_json"] or "[]"),
        "periodo": None if pd.isna(r["inicio"]) else
        f"{pd.Timestamp(r['inicio']):%m/%Y} a {pd.Timestamp(r['fim']):%m/%Y}",
        "resumo": r["resumo"] if isinstance(r["resumo"], str) else "",
        "hipotese": r["hipotese"] if isinstance(r["hipotese"], str) else "",
        "fontes": json.loads(r["fontes_json"] or "[]"),
        "poucos": bool(poucos),
    }


def preparar(perfis: pd.DataFrame, k_min: int) -> list[dict]:
    return [_registro(r, k_min) for _, r in perfis.iterrows()]


# ---------------------------------------------------------------------------
MAPA = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<style>
__FONTES__
:root{--chao:#3d444b;--chao2:#353b41;--tinta:#e9edf0;--tinta2:#b3bcc4;--painel:#f7f8f9;--ptinta:#1d2226;
--ptinta2:#5b6670;--linha:#dfe3e6;--teal:#1fb5ac;--teal2:#16958e;--sombra:0 8px 24px rgba(0,0,0,.35)}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--chao);font-family:"Plex",system-ui,sans-serif;
color:var(--tinta);-webkit-font-smoothing:antialiased}
::selection{background:#1fb5ac55}
#palco{position:relative;height:100vh;overflow:hidden;background:
radial-gradient(120% 90% at 65% 35%,#4a5259 0%,#3d444b 55%,#343a40 100%)}
svg{position:absolute;inset:0;width:100%;height:100%;cursor:grab;touch-action:none}
svg.arrastando{cursor:grabbing}
.cubo{cursor:pointer;transition:filter .15s ease-out}
.cubo:hover{filter:brightness(1.12)}
.cubo:focus{outline:none}.cubo:focus-visible .topo{stroke:#fff;stroke-width:2}
.rotulo-zona{font:500 12px "Plex";letter-spacing:.01em}
#painel{position:absolute;left:20px;top:20px;bottom:20px;width:330px;background:var(--painel);color:var(--ptinta);
border-radius:4px;box-shadow:var(--sombra);display:flex;flex-direction:column;overflow:hidden;z-index:3}
#painel header{padding:18px 18px 14px;border-bottom:1px solid var(--linha)}
.titulo{display:flex;gap:10px;align-items:flex-start}
.titulo svg{position:static;width:22px;height:22px;flex:none;margin-top:2px;cursor:default}
.titulo h2{margin:0;font:600 17px/1.25 "Plex";color:var(--ptinta);word-break:break-word}
.sub{margin-top:4px;font-size:12.5px;color:var(--ptinta2);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.tag{display:inline-block;padding:1px 7px;border-radius:3px;font:500 11.5px/18px "Plex";color:#2a2f34}
.acoes{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.selo{display:inline-flex;align-items:center;gap:6px;padding:7px 11px;border-radius:3px;font:500 13px "Plex";color:#fff}
.selo.claro{background:#e4e8eb;color:#3a444c}
#rolagem{overflow:auto;flex:1;scrollbar-width:thin;scrollbar-color:#c4cbd1 transparent}
details{border-bottom:1px solid var(--linha)}
summary{list-style:none;cursor:pointer;padding:12px 18px;font:600 13px "Plex";color:#3a444c;display:flex;
justify-content:space-between;align-items:center}
summary::-webkit-details-marker{display:none}
summary .seta{transition:transform .2s ease-out;width:12px;height:12px;position:static}
details[open] summary .seta{transform:rotate(180deg)}
dl{margin:0;padding:0 18px 12px}
dt{font:600 12.5px "Plex";color:#2a3036;margin-top:10px}
dd{margin:2px 0 0;font-size:13px;color:#4c5862;font-variant-numeric:tabular-nums}
dd.grande{font:600 15px "Plex";color:var(--ptinta)}
.barra{display:grid;grid-template-columns:1fr 38px;gap:8px;align-items:center;margin-top:6px;font-size:12.5px;color:#4c5862}
.barra .t{grid-column:1/-1;margin-bottom:-3px}
.barra i{display:block;height:6px;border-radius:3px;background:#dfe3e6;overflow:hidden}
.barra i b{display:block;height:100%;background:var(--teal2)}
.barra span{text-align:right;font-variant-numeric:tabular-nums}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.chips span{background:#e9edf0;border-radius:3px;padding:2px 7px;font:400 12px "PlexMono",monospace;color:#3a444c}
p.texto{margin:6px 18px 12px;font-size:13px;line-height:1.5;color:#3f4a53}
.hip{margin:4px 18px 14px;padding:10px 12px;background:#fff7e0;border-radius:3px;font-size:13px;line-height:1.5;color:#4a3d12}
.hip strong{display:block;font-weight:600;margin-bottom:2px}
ul.fontes{margin:0;padding:0 18px 14px 34px;font-size:12.5px;line-height:1.45}
ul.fontes a{color:#11756f;text-underline-offset:2px}
.aviso-poucos{margin:10px 18px;font-size:12.5px;color:#5b6670}
#dica{position:absolute;pointer-events:none;background:#1b1f23;color:#fff;padding:7px 10px;border-radius:3px;
font:500 12.5px/1.35 "Plex";box-shadow:0 4px 14px rgba(0,0,0,.4);opacity:0;transition:opacity .12s ease-out;z-index:4;
white-space:nowrap}
#dica small{display:block;font-weight:400;color:#b8c1c9}
#legenda{position:absolute;right:20px;top:18px;background:rgba(27,31,35,.82);border-radius:4px;padding:10px 12px;
font-size:12px;color:#d7dde2;z-index:2;}
#legenda h3{margin:0 0 6px;font:600 12px "Plex";color:#fff}
#legenda div{display:flex;align-items:center;gap:8px;margin-top:4px}
#legenda i{width:11px;height:11px;border-radius:2px;display:inline-block}
#controles{position:absolute;right:20px;bottom:20px;display:flex;gap:6px;z-index:2}
#controles button{font:500 12.5px "Plex";background:#f2f4f5;color:#2a3036;border:0;border-radius:3px;
height:32px;min-width:32px;padding:0 10px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.25)}
#controles button:hover{background:#fff}
#controles button[aria-pressed="true"]{background:var(--teal);color:#fff}
#controles button:focus-visible{outline:2px solid #fff;outline-offset:2px}
@media (max-width:720px){#painel{left:8px;right:8px;width:auto;top:auto;bottom:8px;height:47%}
#legenda{display:none}#controles{top:10px;bottom:auto;right:8px}#controles #reset{display:none}}
</style></head><body>
<div id="palco">
  <svg id="mapa" role="img" aria-label="Mapa de perfis de aparelho por marca"></svg>
  <aside id="painel" aria-live="polite"></aside>
  <div id="legenda"><h3>Status do perfil</h3>__LEGENDA__
    <div style="margin-top:8px;color:#aab4bd">Altura: <span id="leg-altura">participantes afetados</span></div></div>
  <div id="controles">
    <button id="h-afet" aria-pressed="true" title="Altura pelos participantes afetados">Afetados</button>
    <button id="h-taxa" aria-pressed="false" title="Altura pela taxa ajustada por mil aparelhos">Taxa</button>
    <button id="menos" aria-label="Afastar">−</button><button id="mais" aria-label="Aproximar">+</button>
    <button id="reset" title="Centralizar">Centralizar</button>
  </div>
  <div id="dica"></div>
</div>
<script>
const DADOS = __DADOS__, COR = __COR__, ZCOR = __ZCOR__;
const svg = document.getElementById('mapa'), NS = 'http://www.w3.org/2000/svg';
const TW = 46, TH = 23;                       // tamanho do losango de uma célula
let modoAltura = 'afet', selecionado = DADOS[0] ? DADOS[0].id : null, zoom = 1, pan = {x: 0, y: 0};

const ordemZonas = ['Samsung','Motorola','Xiaomi/Redmi/POCO','Outras','Sem marca','iOS'];
const zonas = ordemZonas.map(z => ({nome: z, itens: DADOS.filter(d => d.zona === z)})).filter(z => z.itens.length);
// tamanho de cada zona e posição em duas fileiras diagonais
let cursor = {x: 0, y: 0};
zonas.forEach((z, i) => {
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
zonas.forEach(z => z.itens.forEach((d, k) => { d.gx = z.ox + (k % z.cols); d.gy = z.oy + Math.floor(k / z.cols); }));

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
function desenhar() {
  svg.innerHTML = '';
  raiz = el('g', {}, svg);
  const camChao = el('g', {}, raiz), camCubos = el('g', {}, raiz), camRotulos = el('g', {}, raiz);
  zonas.forEach(z => {
    const a = P(z.ox - .7, z.oy - .7), b = P(z.ox + z.cols - .3, z.oy - .7), c = P(z.ox + z.cols - .3, z.oy + z.rows - .3), d = P(z.ox - .7, z.oy + z.rows - .3);
    el('polygon', {points: pts([a, b, c, d]), fill: 'rgba(255,255,255,.035)', stroke: ZCOR[z.nome] || '#ccc', 'stroke-opacity': .55, 'stroke-width': 1}, camChao);
    const g = el('g', {}, camRotulos), txt = `${z.nome} · ${z.itens.length}`;
    const w = txt.length * 6.6 + 16;
    el('rect', {x: d[0] - w / 2 + 6, y: d[1] + 6, width: w, height: 20, rx: 3, fill: ZCOR[z.nome] || '#ccc'}, g);
    const t = el('text', {x: d[0] + 6, y: d[1] + 20, 'text-anchor': 'middle', class: 'rotulo-zona', fill: '#22282d'}, g);
    t.textContent = txt;
  });
  [...DADOS].sort((p, q) => (p.gx + p.gy) - (q.gx + q.gy)).forEach(d => {
    const h = altura(d), s = .3, x = d.gx, y = d.gy, sel = d.id === selecionado;
    const base = sel ? '#ffffff' : COR[d.status];
    const g = el('g', {class: 'cubo', tabindex: 0, role: 'button', 'aria-label': `${d.nome}, ${d.statusRotulo}, afetados ${d.afet ?? '—'}`}, camCubos);
    el('polygon', {points: pts([P(x - s, y + s), P(x + s, y + s), P(x + s, y + s, h), P(x - s, y + s, h)]), fill: tom(base, .78)}, g);
    el('polygon', {points: pts([P(x + s, y - s), P(x + s, y + s), P(x + s, y + s, h), P(x + s, y - s, h)]), fill: tom(base, .62)}, g);
    el('polygon', {class: 'topo', points: pts([P(x - s, y - s, h), P(x + s, y - s, h), P(x + s, y + s, h), P(x - s, y + s, h)]),
      fill: tom(base, 1.06), stroke: sel ? '#1fb5ac' : 'rgba(0,0,0,.18)', 'stroke-width': sel ? 2 : .6}, g);
    if (d.status === 'critico' || d.status === 'acima' || sel) {
      const [tx, ty] = P(x, y, h + 12), rot = d.rank ? `#${d.rank}` : '•';
      const w = rot.length * 7 + 12;
      el('rect', {x: tx - w / 2, y: ty - 13, width: w, height: 17, rx: 3, fill: '#1b1f23'}, g);
      const t = el('text', {x: tx, y: ty - .5, 'text-anchor': 'middle', fill: '#fff', style: 'font:600 11px Plex'}, g); t.textContent = rot;
    }
    g.addEventListener('click', () => selecionar(d.id));
    g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selecionar(d.id); } });
    g.addEventListener('pointerenter', e => dica(d, e)); g.addEventListener('pointermove', e => dica(d, e));
    g.addEventListener('pointerleave', () => { document.getElementById('dica').style.opacity = 0; });
  });
  ajustarVista();
}
let caixa;
function ajustarVista(recalcular = true) {
  if (recalcular || !caixa) { const bb = raiz.getBBox(); caixa = {x: bb.x - 40, y: bb.y - 60, w: bb.width + 80, h: bb.height + 100}; }
  const larg = svg.clientWidth, alt = svg.clientHeight, estreito = larg < 720;
  const painel = estreito ? 0 : 370, altUtil = estreito ? alt * .5 : alt;
  const util = Math.max(200, larg - painel - (estreito ? 16 : 30));
  const esc = Math.min(util / caixa.w, altUtil / caixa.h) * zoom;
  const cx = caixa.x + caixa.w / 2, cy = caixa.y + caixa.h / 2;
  raiz.setAttribute('transform', `translate(${painel + util / 2 + pan.x},${altUtil / 2 + pan.y}) scale(${esc}) translate(${-cx},${-cy})`);
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
function selecionar(id) { selecionado = id; desenhar(); painel(); }
function painel() {
  const d = DADOS.find(x => x.id === selecionado), p = document.getElementById('painel');
  if (!d) { p.innerHTML = '<header><h2>Nenhum perfil</h2></header>'; return; }
  const cor = COR[d.status], txtSelo = ['critico', 'acima'].includes(d.status) ? '#fff' : '#22282d';
  p.innerHTML = `<header><div class="titulo">${ICONE('#3a444c')}<div><h2>${esc(d.nome)}</h2>
    <div class="sub">Perfil de aparelho${d.chip ? ` <span class="tag" style="background:${ZCOR[d.zona] || '#ddd'}">${esc(d.chipFab || d.chip)}</span>` : ''}</div></div></div>
    <div class="acoes"><span class="selo" style="background:${cor};color:${txtSelo}" title="${esc(d.statusDesc)}">${esc(d.statusRotulo)}${d.rr ? ` · ${d.rr}x` : ''}</span>
    ${d.rank ? `<span class="selo claro">#${d.rank} no ranking</span>` : ''}</div></header>
    <div id="rolagem">
    ${d.poucos ? `<p class="aviso-poucos">Menos de __KMIN__ participantes: números detalhados omitidos por privacidade.</p>` : ''}
    <details open><summary>Ocorrências ${SETA}</summary><dl>
      ${item('Participantes afetados', d.afet, 'grande')}
      ${item('Ocorrências de login (Android)', d.ocorr)}${item('Técnicas', d.tec)}
      ${item('Aparelhos ativos (Play Console)', d.base)}
      ${item('Taxa por mil aparelhos', d.taxa ? `${d.taxa} <span style="color:#7a858e">(IC 95%: ${d.ic})</span>` : null)}
      ${item('Risco relativo', d.rr ? `${d.rr} vezes a taxa dos demais perfis` : null)}
      ${item('Período dos casos', d.periodo)}
    </dl></details>
    <details open><summary>Sistema ${SETA}</summary><dl>
      ${item('Marca', esc(d.marca))}${item('Chip (SoC)', esc(d.chip))}${item('Memória', esc(d.ram))}
      ${item('Android no Play Console', esc(d.androidPlay))}
      ${item('Android provável no período dos casos', esc(d.androidPeriodo))}
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
}
// zoom, arraste e altura
document.getElementById('mais').onclick = () => { zoom = Math.min(4, zoom * 1.25); ajustarVista(false); };
document.getElementById('menos').onclick = () => { zoom = Math.max(.4, zoom / 1.25); ajustarVista(false); };
document.getElementById('reset').onclick = () => { zoom = 1; pan = {x: 0, y: 0}; ajustarVista(false); };
function modo(m) { modoAltura = m; document.getElementById('h-afet').setAttribute('aria-pressed', m === 'afet');
  document.getElementById('h-taxa').setAttribute('aria-pressed', m === 'taxa');
  document.getElementById('leg-altura').textContent = m === 'afet' ? 'participantes afetados' : 'taxa ajustada por mil'; desenhar(); }
document.getElementById('h-afet').onclick = () => modo('afet'); document.getElementById('h-taxa').onclick = () => modo('taxa');
let arr = null;
svg.addEventListener('pointerdown', e => { if (e.target.closest('.cubo')) return; arr = {x: e.clientX - pan.x, y: e.clientY - pan.y}; svg.classList.add('arrastando'); svg.setPointerCapture(e.pointerId); });
svg.addEventListener('pointermove', e => { if (!arr) return; pan = {x: e.clientX - arr.x, y: e.clientY - arr.y}; ajustarVista(false); });
svg.addEventListener('pointerup', () => { arr = null; svg.classList.remove('arrastando'); });
svg.addEventListener('wheel', e => { e.preventDefault(); zoom = Math.min(4, Math.max(.4, zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1))); ajustarVista(false); }, {passive: false});
window.addEventListener('resize', () => ajustarVista(false));
desenhar(); painel();
</script></body></html>"""


def mapa_html(registros: list[dict], k_min: int) -> str:
    legenda = "".join(f'<div><i style="background:{COR_STATUS[s]}"></i>{STATUS[s][0]}</div>'
                      for s in ["critico", "acima", "atencao", "normal", "sem_base"])
    return (MAPA.replace("__FONTES__", FONTES_CSS).replace("__LEGENDA__", legenda)
            .replace("__DADOS__", json.dumps(registros, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__COR__", json.dumps(COR_STATUS)).replace("__ZCOR__", json.dumps(COR_ZONA))
            .replace("__KMIN__", str(k_min)))


# ---------------------------------------------------------------------------
def ranking_html(registros: list[dict], k_min: int) -> str:
    com = [r for r in registros if r["rank"] is not None]
    sem = [r for r in registros if r["rank"] is None]
    max_ic = max([float(r["ic"].split(" a ")[1].replace(".", "").replace(",", ".")) for r in com if r["ic"]] + [1])
    max_ic = min(max_ic, 120)

    def num(s):
        return float(s.replace(".", "").replace(",", ".")) if s else None

    linhas = []
    for r in com:
        cor = COR_STATUS[r["status"]]
        txt = "#fff" if r["status"] in ("critico", "acima") else "#1d2226"
        if r["taxa"]:
            lo, hi = (num(x) for x in r["ic"].split(" a "))
            t = num(r["taxa"])
            esc_ = lambda v: min(100, 100 * v / max_ic)
            barra = (f'<svg class="ic" viewBox="0 0 100 14" preserveAspectRatio="none" aria-hidden="true">'
                     f'<rect x="0" y="6" width="100" height="2" fill="#3a4148"/>'
                     f'<rect x="{esc_(lo):.1f}" y="4" width="{max(1, esc_(hi) - esc_(lo)):.1f}" height="6" rx="1" fill="{cor}" opacity=".55"/>'
                     f'<rect x="{esc_(t) - .8:.1f}" y="1" width="1.6" height="12" fill="{cor}"/></svg>')
            taxa = f'<b>{r["taxa"]}</b><small>{r["ic"]}</small>{barra}'
        else:
            taxa = '<span class="mudo">poucos casos</span>'
        linhas.append(f"""<tr>
<td class="pos">{r['rank']}</td>
<td><div class="nome">{html.escape(r['nome'])}</div><div class="meta">{html.escape(r['marca'] or '')}
{f'<span class="tag" style="background:{COR_ZONA.get(r["zona"], "#ddd")}">{html.escape(r["chipFab"] or "")}</span>' if r['chipFab'] else ''}</div></td>
<td><span class="st" style="background:{cor};color:{txt}">{html.escape(r['statusRotulo'])}</span></td>
<td class="n">{r['afet']}</td><td class="n">{r['ocorr']}</td><td class="n">{r['base'] or '—'}</td>
<td class="tx">{taxa}</td><td class="n">{(r['rr'] + 'x') if r['rr'] else '—'}</td>
<td>{html.escape(r['androidPeriodo'] or '—')}</td><td>{html.escape(r['sintoma'] or '—')}</td></tr>""")
    extra = "".join(f"<tr><td class='pos'>—</td><td><div class='nome'>{html.escape(r['nome'])}</div></td>"
                    f"<td><span class='st' style='background:{COR_STATUS['sem_base']};color:#fff'>Sem base para taxa</span></td>"
                    f"<td class='n'>{r['afet']}</td><td class='n'>{r['ocorr']}</td><td class='n'>—</td>"
                    f"<td class='tx'><span class='mudo'>sem catálogo</span></td><td class='n'>—</td>"
                    f"<td>{html.escape(r['androidPeriodo'] or '—')}</td><td>{html.escape(r['sintoma'] or '—')}</td></tr>"
                    for r in sem)
    return f"""<div class="ranking"><table>
<caption>Ranking de perfis por taxa ajustada. Grupos com menos de {k_min} participantes aparecem como
"&lt; {k_min}" e sem taxa, por privacidade. A barra mostra a taxa por mil aparelhos e o intervalo de confiança de 95%
(escala de 0 a {max_ic:.0f} por mil).</caption>
<thead><tr><th>#</th><th>Perfil</th><th>Status</th><th class="n">Afetados</th><th class="n">Ocorrências</th>
<th class="n">Aparelhos</th><th>Taxa por mil (IC 95%)</th><th class="n">Risco relativo</th>
<th>Android provável no período</th><th>Sintoma predominante</th></tr></thead>
<tbody>{''.join(linhas)}</tbody>
<tbody class="sem"><tr><th colspan="10">Casos sem base para taxa</th></tr>{extra}</tbody></table></div>"""
