"""Carga do catálogo de aparelhos do Google Play Console.

O export vem "quebrado": vírgula separa colunas, ';' separa itens das listas
(ABIs e versões de SDK) e há ';' sobrando no fim das linhas. Alguns nomes de
modelo têm vírgula e aspas mal escapadas, por isso o csv.reader erra.
Solução: as 3 primeiras e as 13 últimas colunas têm posição fixa; o que sobra
no meio é o nome do modelo.

Conferência: a soma de Install base deve bater com o total do Play Console.
"""
from __future__ import annotations

import re

import pandas as pd

from src import config

COLS_DIREITA = ["ram", "form_factor", "soc", "gpu", "screen", "dpi", "abis",
                "sdk_list", "gl", "install", "anr", "crash", "battery"]


def _faixa_ram(mb: float | None) -> str:
    if mb is None or pd.isna(mb):
        return "desconhecida"
    for limite, rotulo in [(2600, "até 2 GB"), (4600, "3-4 GB"), (6700, "6 GB"),
                           (8800, "8 GB")]:
        if mb < limite:
            return rotulo
    return "12 GB+"


def _pct(txt: str) -> float | None:
    try:
        return float(txt.strip().rstrip("%")) / 100
    except ValueError:
        return None


def ler_catalogo(caminho=config.ARQ_PLAY_CONSOLE) -> pd.DataFrame:
    linhas = caminho.read_text(encoding="utf-8", errors="replace").splitlines()
    recs, descartadas = [], 0
    for linha in linhas[1:]:
        partes = linha.rstrip().rstrip(";").split(",")
        if len(partes) < 17:
            descartadas += 1
            continue
        esq, dir_ = partes[:3], partes[-13:]
        modelo = ",".join(partes[3:-13]).strip().strip('"').replace('""', '"').strip()
        recs.append(esq + [modelo] + dir_)
    df = pd.DataFrame(recs, columns=["brand", "device", "manufacturer", "model_name"] + COLS_DIREITA)
    df["brand"] = df["brand"].str.strip().str.lower()
    df["install_n"] = pd.to_numeric(df["install"], errors="coerce").fillna(0).astype(int)

    ram = df["ram"].str.extract(r"(\d+)(?:-(\d+))?MB")
    df["ram_min_mb"] = pd.to_numeric(ram[0], errors="coerce")
    df["ram_max_mb"] = pd.to_numeric(ram[1], errors="coerce").fillna(df["ram_min_mb"])
    df["ram_faixa"] = df["ram_max_mb"].map(_faixa_ram)

    df["sdk_list"] = df["sdk_list"].str.replace("\t", ";").str.strip(";")
    df["abis"] = df["abis"].str.replace("\t", ";")
    df["sdk_max"] = df["sdk_list"].map(
        lambda s: max((int(x) for x in re.findall(r"\d+", s)), default=None))
    df["anr_rate"] = df["anr"].map(_pct)
    df["crash_rate"] = df["crash"].map(_pct)
    df.insert(0, "model_id", range(1, len(df) + 1))
    df.attrs["descartadas"] = descartadas
    return df


def explodir_sdk(cat: pd.DataFrame, regra: str = config.REGRA_SDK) -> pd.DataFrame:
    """Uma linha por (modelo, versão do Android) com a base estimada."""
    linhas = []
    for r in cat[cat["install_n"] > 0].itertuples():
        sdks = sorted({int(x) for x in re.findall(r"\d+", r.sdk_list or "")})
        if not sdks:
            continue
        if regra == "igual":
            pesos = [1] * len(sdks)
        elif regra == "max":
            pesos = [0] * (len(sdks) - 1) + [1]
        else:
            pesos = list(range(1, len(sdks) + 1))
        total = sum(pesos)
        for s, p in zip(sdks, pesos):
            if p == 0:
                continue
            linhas.append({
                "model_id": r.model_id, "sdk": s,
                "android": config.SDK_PARA_ANDROID.get(s, str(s)),
                "peso": p / total, "install_est": r.install_n * p / total,
            })
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    cat = ler_catalogo()
    ativos = cat[cat["install_n"] > 0]
    print(f"Modelos no catálogo: {len(cat):,} | com instalação: {len(ativos):,}")
    print(f"Soma da base de instalação: {cat['install_n'].sum():,}")
    print(f"Linhas descartadas (sem dados): {cat.attrs['descartadas']}")
    print((ativos.groupby("brand")["install_n"].sum() / ativos["install_n"].sum())
          .sort_values(ascending=False).head(6).round(3))
