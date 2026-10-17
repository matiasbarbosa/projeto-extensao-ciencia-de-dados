"""Configurações centrais do projeto.

Tudo que é parâmetro de análise fica aqui, para que o professor (ou qualquer
pessoa) reproduza os mesmos resultados alterando um único arquivo.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

DATA_RAW = RAIZ / "data" / "raw"
DATA_PROCESSED = RAIZ / "data" / "processed"
DATA_PRIVATE = RAIZ / "data" / "private"  # fora do Git (.gitignore)

ARQ_PLAY_CONSOLE = DATA_RAW / "play_console_devices.csv"
ARQ_INCIDENTES_ANON = DATA_PROCESSED / "incidentes_anonimizados.csv"
ARQ_INCIDENTES_SIM = DATA_PROCESSED / "incidentes_simulados.csv"

# Semente fixa (exigência de reprodutibilidade do Plano de Ação)
SEED = 20261014

# Nome fictício do parceiro. O nome real não aparece em nenhum arquivo público.
PARCEIRO = "Entidade de Previdência X (EPX)"
APP = "App EPX"

# "simulado" ou "real_anonimizado" (ver .env)
FONTE_INCIDENTES = os.getenv("FONTE_INCIDENTES", "simulado")

# Privacidade: grupos com menos de K_MIN incidentes são omitidos nos agregados
K_MIN = 5

# Regra para distribuir a base de instalação de um modelo entre as versões de
# Android que ele lista (o Play Console não informa instalações por versão).
#   "max"    -> toda a base do modelo na versão mais recente que ele suporta
#               (mesma regra usada para imputar a versão dos incidentes que não a
#               informam: numerador e denominador seguem a mesma premissa)
#   "igual"  -> divide igualmente entre as versões listadas
#   "recente"-> pesos crescentes (1, 2, 3, ...) favorecendo versões mais novas
REGRA_SDK = "max"

# Mapeamento API level -> versão comercial do Android
SDK_PARA_ANDROID = {
    21: "5.0", 22: "5.1", 23: "6", 24: "7.0", 25: "7.1", 26: "8.0", 27: "8.1",
    28: "9", 29: "10", 30: "11", 31: "12", 32: "12L", 33: "13", 34: "14",
    35: "15", 36: "16", 37: "17",
}

# ---------------------------------------------------------------------------
# CENÁRIO DO SIMULADOR (Plano B)
# Calibrado em 15/10/2026 com resultados AGREGADOS da análise real (incidentes
# anonimizados, processados localmente e não publicados). Nenhum incidente real
# é copiado: só proporções e o risco relativo do grupo de maior incidência.
# ---------------------------------------------------------------------------
CENARIO = {
    "n_incidentes": 504,
    # grupo de maior incidência na análise real: Motorola com chip Unisoc
    # (moto g35 5G, moto e13...).
    "culpado": {"brand": "motorola", "soc_fab": "Unisoc"},
    "multiplicador_culpado": 12.3,  # reproduz a fatia real do grupo (~15% dos técnicos com modelo)
    "multiplicador_marca": 1.7,          # demais Motorola
    "prop_ios": 0.065,
    "classes_android": {"tecnico": 0.773, "indefinido": 0.154, "conta_cadastro": 0.073},
    "subtipos_culpado": {"retorno_tela_inicial": 0.45, "falha_login_generica": 0.30, "erro_auth": 0.15,
                         "codigo_verificacao": 0.05, "carregamento": 0.05},
    "subtipos_outros": {"retorno_tela_inicial": 0.30, "falha_login_generica": 0.27, "erro_auth": 0.21,
                        "codigo_verificacao": 0.09, "carregamento": 0.04, "biometria": 0.04,
                        "conexao_servidor": 0.03, "fechamento": 0.01, "navegador_redirecionamento": 0.01},
    "subtipos_conta": {"senha": 0.32, "matricula": 0.24, "conta_nao_localizada": 0.20,
                       "conta_bloqueada": 0.14, "dados_cadastrais": 0.10},
    "p_cita_aparelho": 0.55,
    "p_modelo_dado_marca": 0.68,
    "p_cita_app": 0.38,
    "versoes_app": {"6.1.0": 3, "6.1.1": 6, "6.1.2": 17, "6.2.0": 5, "6.2.1": 9, "6.2.3": 2, "6.2.5": 4,
                    "6.2.6": 6, "6.3.0": 12, "6.3.1": 3, "6.3.2": 7, "6.3.4": 5, "6.3.6": 5, "6.3.7": 2,
                    "6.3.8": 11},
    "prop_participantes_distintos": 0.92,
    "periodo": ("2025-02-21", "2026-10-15"),
    "forma_tempo": 4.0,                  # concentra os casos no fim do período, como na base real
}
