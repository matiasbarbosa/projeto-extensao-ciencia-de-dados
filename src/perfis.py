"""Perfis de aparelho para o mapa e o ranking do dashboard.

Um perfil é um modelo do catálogo (nome sem o sufixo 5G/4G) com seus atributos
(marca, chip, RAM, versões do Android). Para cada perfil: ocorrências de login
em Android, ocorrências técnicas, participantes afetados, taxa por mil aparelhos
com IC 95% exato de Poisson, risco relativo contra os demais perfis, teste
binomial exato com correção de Benjamini-Hochberg e status.

Também entram, sem taxa (não há base para elas), as ocorrências com marca mas
sem modelo, as sem marca e as de iPhone, para que o ranking cubra todos os casos.

O ranking ordena pela taxa AJUSTADA (encolhimento empírico-bayesiano): soma-se a
cada perfil o equivalente a PESO_PRIOR aparelhos com a taxa geral, assim
taxa_ajustada = (afetados + taxa_geral * PESO_PRIOR) / (base + PESO_PRIOR).
Um perfil com 1 caso em 4 aparelhos não passa na frente de um perfil com 12
casos em 708; perfis grandes quase não mudam.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src import config
from src.analise import _ic_poisson
PESO_PRIOR = 500  # aparelhos "emprestados" da taxa geral no ajuste do ranking

from src.perfis_pesquisa import (HIPOTESE_MOTOROLA_UNISOC, PERFIL_PESQUISA, fontes_de,
                                 versoes_no_periodo)


def _android_lista(sdk_list: str) -> str:
    vers = [config.SDK_PARA_ANDROID.get(int(s), s) for s in str(sdk_list or "").split(";") if s.strip().isdigit()]
    return ", ".join(vers) if vers else "—"


def _ram_texto(ram: str, faixa: str) -> str:
    """'3547-7794MB' -> '3,5 a 7,8 GB (variantes do modelo no Play Console)'."""
    import re
    n = [int(x) for x in re.findall(r"\d+", str(ram or ""))]
    if not n:
        return faixa
    gb = [f"{v / 1024:.1f}".replace(".", ",") for v in n]
    return f"{gb[0]} GB" if len(gb) == 1 or gb[0] == gb[-1] else f"{gb[0]} a {gb[-1]} GB (variantes do modelo)"


def _status(r) -> str:
    if r["afetados"] >= config.K_MIN and r["significativo"] and r["risco_relativo"] >= 5:
        return "critico"
    if r["afetados"] >= config.K_MIN and r["significativo"]:
        return "acima"
    if r["risco_relativo"] >= 2 and r["afetados"] >= 2:
        return "atencao"
    return "normal"


def _top(series: pd.Series, n: int = 3) -> str:
    vc = series.dropna().value_counts()
    return json.dumps([[str(k), int(v)] for k, v in vc.head(n).items()], ensure_ascii=False)


def construir(inc: pd.DataFrame, cat: pd.DataFrame, pop: pd.DataFrame, tec: pd.DataFrame) -> pd.DataFrame:
    login = inc[inc["classe_erro"] != "fora_escopo"].copy()
    so = login["so"] if "so" in login else pd.Series("android", index=login.index)
    andr = login[so == "android"].copy()

    # atributos por modelo (agrupando variantes de mesmo nome sem 5G/4G)
    pm = pop.drop_duplicates("model_id").merge(
        cat[["model_id", "model_name", "soc", "sdk_list", "ram"]], on="model_id")
    rep = pm.sort_values("install_n", ascending=False).drop_duplicates("modelo")
    base = pm.groupby("modelo")["install_n"].sum()
    attrs = rep.set_index("modelo")[["model_name", "marca", "soc", "soc_fab", "ram_faixa", "ram", "sdk_list"]]
    modelo_de = pm.set_index("model_id")["modelo"]

    andr["modelo"] = andr["model_id"].map(lambda m: modelo_de.get(int(m)) if pd.notna(m) else None)
    tec = tec.copy()
    tec["modelo"] = tec["model_id"].map(lambda m: modelo_de.get(int(m)) if pd.notna(m) else None)

    com_modelo = andr.dropna(subset=["modelo"])
    tec_m = tec.dropna(subset=["modelo"])
    K = tec_m["participante_pseud"].nunique()
    B = base.sum()
    linhas = []
    for modelo, g in com_modelo.groupby("modelo"):
        t = tec_m[tec_m["modelo"] == modelo]
        a = attrs.loc[modelo]
        k = t["participante_pseud"].nunique()
        b = float(base.get(modelo, 0))
        lo, hi = _ic_poisson(k)
        rr = (k / b) / ((K - k) / (B - b)) if b > 0 and K - k > 0 else np.nan
        p = stats.binomtest(k, int(K), b / B, alternative="greater").pvalue if K and b else np.nan
        datas = pd.to_datetime(g["opened_at"])
        ini, fim = datas.min(), datas.max()
        sint = t["subtipo_erro"].value_counts(normalize=True)
        nome = a["model_name"]
        pesq = PERFIL_PESQUISA.get(nome, {})
        linhas.append({
            "perfil": nome, "modelo": modelo, "zona": a["marca"], "marca": a["marca"], "chip": a["soc"],
            "chip_fab": a["soc_fab"], "ram": _ram_texto(a["ram"], a["ram_faixa"]), "android_play": _android_lista(a["sdk_list"]),
            "android_periodo": versoes_no_periodo(nome, ini, fim, a["sdk_list"]),
            "ocorrencias": len(g), "ocorrencias_tecnicas": len(t), "afetados": k, "base": b,
            "taxa_por_mil": 1000 * k / b if b else np.nan, "ic_inf": 1000 * lo / b if b else np.nan,
            "ic_sup": 1000 * hi / b if b else np.nan, "risco_relativo": rr, "p_valor": p,
            "sintoma": sint.index[0] if len(sint) else None,
            "sintoma_pct": float(sint.iloc[0]) if len(sint) else None,
            "sintomas_json": _top(t["subtipo_erro"], 4), "versoes_app_json": _top(g["app_version"], 3),
            "inicio": ini, "fim": fim, "tem_taxa": 1,
            "resumo": pesq.get("resumo", ""),
            "hipotese": HIPOTESE_MOTOROLA_UNISOC if (a["marca"] == "Motorola" and a["soc_fab"] == "Unisoc") else "",
            "fontes_json": json.dumps(fontes_de(nome, a["marca"], a["soc_fab"]), ensure_ascii=False),
        })
    perf = pd.DataFrame(linhas)
    perf["p_ajustado"] = multipletests(perf["p_valor"].fillna(1), method="fdr_bh")[1]
    perf["significativo"] = ((perf["p_ajustado"] < 0.05) & (perf["risco_relativo"] > 1)).astype(int)
    perf["status"] = perf.apply(_status, axis=1)
    taxa_geral = K / B
    perf["taxa_ajustada"] = 1000 * (perf["afetados"] + taxa_geral * PESO_PRIOR) / (perf["base"] + PESO_PRIOR)
    perf = perf.sort_values(["taxa_ajustada", "afetados"], ascending=False).reset_index(drop=True)
    perf["rank"] = range(1, len(perf) + 1)

    # casos sem base para taxa: marca sem modelo, sem marca e iPhone
    extras = []
    sem_modelo = andr[andr["modelo"].isna()]
    for marca, g in sem_modelo.groupby(sem_modelo["marca"].fillna("Marca não informada")):
        extras.append((f"{marca} · modelo não informado", marca if marca != "Marca não informada" else "Sem marca", g))
    ios = login[so == "ios"]
    if len(ios):
        extras.append(("iPhone · fora do escopo", "iOS", ios))
    for nome, zona, g in extras:
        datas = pd.to_datetime(g["opened_at"])
        t = g[g["classe_erro"] == "tecnico"]
        sint = t["subtipo_erro"].value_counts(normalize=True)
        extras_row = {
            "perfil": nome, "modelo": nome, "zona": zona, "marca": zona, "chip": None, "chip_fab": None,
            "ram": None, "android_play": "—", "android_periodo": "iOS" if zona == "iOS" else "não informada",
            "ocorrencias": len(g), "ocorrencias_tecnicas": len(t), "afetados": t["participante_pseud"].nunique(),
            "base": np.nan, "taxa_por_mil": np.nan, "taxa_ajustada": np.nan, "ic_inf": np.nan, "ic_sup": np.nan, "risco_relativo": np.nan,
            "p_valor": np.nan, "p_ajustado": np.nan, "significativo": 0, "status": "sem_base",
            "sintoma": sint.index[0] if len(sint) else None, "sintoma_pct": float(sint.iloc[0]) if len(sint) else None,
            "sintomas_json": _top(t["subtipo_erro"], 4), "versoes_app_json": _top(g["app_version"], 3),
            "inicio": datas.min(), "fim": datas.max(), "tem_taxa": 0, "rank": None, "resumo": "",
            "hipotese": "", "fontes_json": "[]",
        }
        perf = pd.concat([perf, pd.DataFrame([extras_row])], ignore_index=True)
    perf.insert(0, "perfil_id", range(1, len(perf) + 1))
    return perf
