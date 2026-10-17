"""Pesquisa pública sobre os perfis de aparelho (fontes abertas, consultadas em 16/10/2026).

Nada aqui vem dos dados do parceiro. São fatos públicos sobre os aparelhos e sobre o
Android, usados para contextualizar os perfis no dashboard. A "hipótese" de cada
perfil é uma explicação plausível a ser validada com o time do app, não um resultado
estatístico.
"""
from __future__ import annotations

import pandas as pd

# Linha do tempo de versões do Android por modelo: (versão, a partir de, descrição, fonte)
FONTES = {
    "moto_g35_a15": ("Motorola - Novidades do Android 15 no moto g35 5G",
                     "https://help.motorola.com/hc/3535/15/global/pt-br/CG1395067443.html"),
    "moto_g35_a15_rom": ("StockROM - moto g35 5G XT2433-1 Android 15 RETBR (VUOA35.116-60-3), dez/2025",
                         "https://www.stockrom.net/2025/12/xt2433-1-retbr-os15-vuoa35-116-60-3.html"),
    "moto_g35_ra": ("Reclame Aqui - moto g35 após atualização para o Android 15 (23/02/2026)",
                    "https://www.reclameaqui.com.br/motorola/motorola-moto-g35-inutilizavel-apos-atualizacao-para-android-15-bugs-travamentos-e-superaquecimento_ueoI516-IN4k7itg/"),
    "moto_g35_a16": ("Dicas Tech - Android 16 no moto g35 (liberado em maio/2026, segundo o TudoCelular)",
                     "https://dicastech.com.br/android-16-moto-g35-o-que-muda/"),
    "moto_e13": ("Smartprix - moto e13: Android 13 (Go edition), Unisoc T606, 2 GB de RAM",
                 "https://www.smartprix.com/mobiles/motorola-moto-e13-ppd1rrcb44fr"),
    "dkma_motorola": ("Don't kill my app! - Motorola: 'Melhorar bateria quando inativo', bateria adaptativa e "
                      "restrição em segundo plano encerram apps", "https://dontkillmyapp.com/motorola"),
    "android15": ("Android Developers - Mudanças do Android 15 para todos os apps (proteção de OTP, "
                  "estado 'stopped')", "https://developer.android.com/about/versions/15/behavior-changes-all"),
    "play_console": ("Catálogo do Google Play Console do app (versões de SDK por modelo)", None),
}

LINHA_DO_TEMPO = {
    "moto g35 5G": [
        ("14", "2025-01-01", "lançado com Android 14", "moto_g35_ra"),
        ("15", "2025-12-01", "Android 15 oficial no Brasil (builds VUOA35)", "moto_g35_a15_rom"),
        ("16", "2026-05-07", "Android 16 liberado em fases", "moto_g35_a16"),
    ],
    "moto e13": [
        ("13", "2023-02-01", "Android 13 Go edition, sem atualização de versão", "moto_e13"),
    ],
}

PERFIL_PESQUISA = {
    "moto g35 5G": {
        "resumo": "Intermediário de entrada com chip Unisoc T760 (6 nm) e 4 GB de RAM na versão mais comum. "
                  "Saiu com Android 14 e recebeu Android 15 e Android 16.",
        "fontes": ["moto_g35_ra", "moto_g35_a15", "moto_g35_a15_rom", "moto_g35_a16", "dkma_motorola", "android15"],
    },
    "moto e13": {
        "resumo": "Aparelho de entrada com chip Unisoc T606 e 2 GB de RAM, rodando Android 13 Go edition, que "
                  "encerra processos em segundo plano de forma agressiva.",
        "fontes": ["moto_e13", "dkma_motorola"],
    },
}

HIPOTESE_MOTOROLA_UNISOC = (
    "Ao sair do app para ler o código de verificação, o gerenciamento de bateria da Motorola e a pouca "
    "memória dos aparelhos com chip Unisoc encerram o app em segundo plano. Ao voltar, o login recomeça na "
    "tela inicial, o que aparece nos chamados como \"volta para a tela inicial\" ou \"acesso cancelado\". "
    "A partir do Android 15, o sistema também protege de forma mais restrita as telas e notificações que "
    "exibem códigos de uso único (OTP). Hipótese a validar com o time do app.")


def versoes_no_periodo(modelo: str, ini: pd.Timestamp | None, fim: pd.Timestamp | None,
                       sdk_list: str | None) -> str:
    """Versões do Android disponíveis para o modelo durante o período dos casos."""
    from src.config import SDK_PARA_ANDROID
    linha = LINHA_DO_TEMPO.get(modelo)
    if linha and ini is not None and pd.notna(ini):
        disp = [v for v, desde, *_ in linha if pd.Timestamp(desde) <= (fim if pd.notna(fim) else ini)]
        atual_no_inicio = [v for v, desde, *_ in linha if pd.Timestamp(desde) <= ini]
        if disp:
            primeira = atual_no_inicio[-1] if atual_no_inicio else disp[0]
            seguintes = [v for v in disp if int(v) > int(primeira)]
            texto = f"Android {primeira}"
            if seguintes:
                texto += " → " + " → ".join(f"Android {v}" for v in seguintes)
            return texto
    if sdk_list:
        vers = [SDK_PARA_ANDROID.get(int(s), s) for s in str(sdk_list).split(";") if s.strip().isdigit()]
        if vers:
            return f"Android {vers[-1]} (mais recente suportada; também {', '.join(vers[:-1])})" if len(vers) > 1 \
                else f"Android {vers[0]}"
    return "não informada"


def fontes_de(modelo: str, marca: str | None, soc_fab: str | None) -> list[tuple[str, str | None]]:
    chaves = list(PERFIL_PESQUISA.get(modelo, {}).get("fontes", []))
    if marca == "Motorola" and "dkma_motorola" not in chaves:
        chaves.append("dkma_motorola")
    chaves.append("play_console")
    return [FONTES[c] for c in chaves]
