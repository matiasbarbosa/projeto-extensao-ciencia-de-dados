"""Análise estatística: taxas por grupo x taxa geral e modelo de Poisson.

Unidade de contagem: participantes distintos com incidente TÉCNICO cujo
aparelho foi casado com o catálogo (um participante com 3 chamados conta 1).
Denominador: base de instalação do Play Console (aparelhos ativos).

Para a versão do Android, o denominador é estimado (ver config.REGRA_SDK) e
só entram incidentes que informaram a versão (suposição: a falta da versão no
chamado não depende do grupo).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src import config


def fabricante_soc(soc: str) -> str:
    s = (soc or "").lower()
    for chave, rot in [("qualcomm", "Qualcomm"), ("qti", "Qualcomm"), ("mediatek", "MediaTek"),
                       ("samsung", "Samsung Exynos"), ("exynos", "Samsung Exynos"),
                       ("spreadtrum", "Unisoc"), ("unisoc", "Unisoc"), ("google", "Google Tensor")]:
        if chave in s:
            return rot
    return "Outro"


def grupo_marca(b: str) -> str:
    return {"samsung": "Samsung", "motorola": "Motorola", "redmi": "Xiaomi/Redmi/POCO",
            "poco": "Xiaomi/Redmi/POCO", "xiaomi": "Xiaomi/Redmi/POCO"}.get(b, "Outras")


def populacao(cat: pd.DataFrame, dsdk: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (modelo, versão Android) com a base estimada e atributos."""
    c = cat[cat["install_n"] > 0].copy()
    c["marca"] = c["brand"].map(grupo_marca)
    c["modelo"] = c["model_name"].str.replace(r"\s+[45]G$", "", regex=True)
    c["soc_fab"] = c["soc"].map(fabricante_soc)
    return dsdk.merge(c[["model_id", "marca", "modelo", "ram_faixa", "soc_fab", "install_n"]], on="model_id")


def preparar_incidentes(inc: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """Incidentes técnicos em Android. A marca vem do modelo (se casado) ou do texto;
    modelo, RAM e SoC só existem quando o modelo foi casado ao catálogo."""
    attrs = pop.drop_duplicates("model_id").set_index("model_id")[["marca", "modelo", "ram_faixa", "soc_fab"]]
    t = inc[inc["classe_erro"] == "tecnico"].copy()
    if "so" in t:
        t = t[t["so"] == "android"]
    marca_txt = t["marca"] if "marca" in t else pd.Series(None, index=t.index, dtype=object)
    t = t.drop(columns=[c for c in ["marca"] if c in t]).join(attrs, on="model_id")
    t["marca"] = t["marca"].fillna(marca_txt)
    t["model_id"] = t["model_id"].astype("Int64")
    return t


def _ic_poisson(k: int, alfa: float = 0.05) -> tuple[float, float]:
    lo = stats.chi2.ppf(alfa / 2, 2 * k) / 2 if k > 0 else 0.0
    hi = stats.chi2.ppf(1 - alfa / 2, 2 * k + 2) / 2
    return lo, hi


DIMENSOES = {
    "marca": ["marca"],
    "android": ["android"],
    "marca_android": ["marca", "android"],
    "modelo": ["modelo"],
    "modelo_android": ["modelo", "android"],
    "ram": ["ram_faixa"],
    "soc": ["soc_fab"],
    "marca_soc": ["marca", "soc_fab"],
}


def taxas(tec: pd.DataFrame, pop: pd.DataFrame, k_min: int = config.K_MIN) -> pd.DataFrame:
    saida = []
    for dim, cols in DIMENSOES.items():
        precisa_sdk = "android" in cols
        d = tec.dropna(subset=cols)
        cont = d.groupby(cols)["participante_pseud"].nunique().rename("afetados")
        n_inc = d.groupby(cols).size().rename("incidentes")
        peso = "install_est"
        base = pop.groupby(cols)[peso].sum().rename("base") if precisa_sdk else \
            pop.drop_duplicates("model_id").groupby(cols)["install_n"].sum().rename("base")
        g = pd.concat([cont, n_inc, base], axis=1).fillna(0)
        K, B = g["afetados"].sum(), g["base"].sum()
        g = g[g["base"] > 0]
        linhas = []
        for chave, r in g.iterrows():
            k, b = int(r["afetados"]), float(r["base"])
            lo, hi = _ic_poisson(k)
            resto_k, resto_b = K - k, B - b
            rr = (k / b) / (resto_k / resto_b) if resto_k > 0 and resto_b > 0 else np.nan
            p = stats.binomtest(k, int(K), b / B).pvalue if K > 0 else np.nan
            linhas.append({
                "dimensao": dim,
                "grupo": " | ".join(map(str, chave)) if isinstance(chave, tuple) else str(chave),
                "afetados": k, "incidentes": int(r["incidentes"]), "base": b,
                "taxa_por_mil": 1000 * k / b, "ic_inf": 1000 * lo / b, "ic_sup": 1000 * hi / b,
                "risco_relativo": rr, "p_valor": p,
            })
        df = pd.DataFrame(linhas)
        df["p_ajustado"] = multipletests(df["p_valor"].fillna(1), method="fdr_bh")[1]
        df["significativo"] = ((df["p_ajustado"] < 0.05) & (df["risco_relativo"] > 1)).astype(int)
        saida.append(df[df["afetados"] >= k_min])   # privacidade: omite grupos pequenos
    return pd.concat(saida, ignore_index=True).sort_values(["dimensao", "taxa_por_mil"], ascending=[True, False])


def taxa_geral(tec: pd.DataFrame, cat: pd.DataFrame) -> float:
    """Participantes com incidente técnico em Android por mil aparelhos Android ativos."""
    return 1000 * tec["participante_pseud"].nunique() / cat["install_n"].sum()


def modelo_poisson(tec: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """GLM de Poisson por célula (modelo x Android) com offset log(base).

    Mostra o efeito de cada atributo controlando pelos demais (efeitos
    principais; IRR = razão de taxas em relação à categoria de referência).
    """
    d = tec.dropna(subset=["sdk", "model_id"]).copy()
    d["sdk"], d["model_id"] = d["sdk"].astype(int), d["model_id"].astype(int)
    y = d.groupby(["model_id", "sdk"])["participante_pseud"].nunique().rename("y")
    cel = pop.set_index(["model_id", "sdk"]).join(y).fillna({"y": 0}).reset_index()
    cel = cel[cel["install_est"] > 0]
    cel["android_g"] = cel["sdk"].map(lambda s: "≤12" if s <= 32 else config.SDK_PARA_ANDROID[s])
    cel["android_g"] = cel["android_g"].replace({"17": "16"})
    cel["ram_faixa"] = cel["ram_faixa"].replace({"até 2 GB": "até 4 GB", "3-4 GB": "até 4 GB",
                                                 "desconhecida": "até 4 GB"})
    formula = ("y ~ C(marca, Treatment('Samsung')) + C(android_g, Treatment('14'))"
               " + C(ram_faixa, Treatment('8 GB'))")
    m = smf.glm(formula, data=cel, family=sm.families.Poisson(),
                offset=np.log(cel["install_est"])).fit()
    ic = m.conf_int()
    out = pd.DataFrame({"termo": m.params.index, "irr": np.exp(m.params.values),
                        "ic_inf": np.exp(ic[0].values), "ic_sup": np.exp(ic[1].values),
                        "p_valor": m.pvalues.values})
    out = out[out["termo"] != "Intercept"]
    out["termo"] = out["termo"].map(lambda t: re.sub(r"C\((\w+).*?\)\[T\.(.+)\]", r"\1 = \2", t))
    out.attrs["aic"] = m.aic
    return out
