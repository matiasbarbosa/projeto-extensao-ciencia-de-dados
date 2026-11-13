"""Pesquisa pública sobre os perfis de aparelho (fontes abertas).

Nada aqui vem dos dados do parceiro. São fatos públicos sobre os aparelhos e sobre o
Android, usados para contextualizar os perfis no dashboard. A "hipótese" de cada
perfil é uma explicação plausível a ser validada com o time do app, não um resultado
estatístico.
"""
from __future__ import annotations

FONTES = {
    "moto_g35_a15": ("Motorola - Novidades do Android 15 no moto g35 5G",
                     "https://help.motorola.com/hc/3535/15/global/pt-br/CG1395067443.html"),
    "moto_g35_a15_rom": ("StockROM - moto g35 5G XT2433-1 Android 15 RETBR (VUOA35.116-60-3), dez/2025",
                         "https://www.stockrom.net/2025/12/xt2433-1-retbr-os15-vuoa35-116-60-3.html"),
    "moto_g35_ra": ("Reclame Aqui - moto g35 após atualização para o Android 15 (23/02/2026)",
                    "https://www.reclameaqui.com.br/motorola/motorola-moto-g35-inutilizavel-apos-atualizacao-para-android-15-bugs-travamentos-e-superaquecimento_ueoI516-IN4k7itg/"),
    "moto_g35_a16": ("Dicas Tech - notícia sobre Android 16 no moto g35 (fonte secundária)",
                     "https://dicastech.com.br/android-16-moto-g35-o-que-muda/"),
    "moto_e13": ("Smartprix - moto e13: Android 13 (Go edition), Unisoc T606, 2 GB de RAM",
                 "https://www.smartprix.com/mobiles/motorola-moto-e13-ppd1rrcb44fr"),
    "dkma_motorola": ("Don't kill my app! - Motorola: 'Melhorar bateria quando inativo', bateria adaptativa e "
                      "restrição em segundo plano encerram apps", "https://dontkillmyapp.com/motorola"),
    "android15": ("Android Developers - Android 15: proteção de OTP em notificações para apps não confiáveis",
                  "https://developer.android.com/about/versions/15/behavior-changes-all#security-privacy"),
    "estado_app": ("Android Developers - preservação do estado após encerramento do processo",
                   "https://developer.android.com/topic/libraries/architecture/saving-states"),
    "play_console": ("Catálogo do Google Play Console do app (versões de SDK por modelo)", None),
    "b2c_troubleshoot": ("Microsoft Learn — solução de problemas do Azure AD B2C", "https://learn.microsoft.com/en-us/azure/active-directory-b2c/troubleshoot"),
    "b2c_errors": ("Microsoft Learn — códigos e mensagens de erro do Azure AD B2C", "https://learn.microsoft.com/en-us/azure/active-directory-b2c/error-codes"),
}

PERFIL_PESQUISA = {
    "moto g35 5G": {
        "resumo": "Intermediário de entrada com chip Unisoc T760 (6 nm) e 4 GB de RAM na versão mais comum. "
                  "A Motorola documenta o Android 15 para o modelo. A versão instalada nos casos não foi confirmada.",
        "hipotese": "Prioridade de teste: Android 15 no moto g35 5G. Ao alternar para outro app para consultar "
                    "o código, o processo pode ser encerrado e o estado do login pode não ser restaurado. "
                    "Isso é uma hipótese, não uma causa comprovada; testar também outras versões e configurações de bateria.",
        "fontes": ["moto_g35_a15", "moto_g35_a15_rom", "moto_g35_ra", "moto_g35_a16", "dkma_motorola", "estado_app", "android15"],
    },
    "moto e13": {
        "resumo": "Aparelho de entrada com chip Unisoc T606, vendido em variantes de RAM e lançado com Android 13 Go edition.",
        "fontes": ["moto_e13", "dkma_motorola", "estado_app"],
    },
}

HIPOTESE_MOTOROLA_UNISOC = (
    "Ao alternar para outro app para consultar o código, restrições de bateria ou pressão de memória podem "
    "encerrar o processo. Se o estado do login não for restaurado, o app pode voltar à tela inicial. "
    "Mecanismo não confirmado: hipótese a testar com o time do app.")


def versoes_do_modelo(sdk_list: str | None) -> str:
    """Versões listadas no catálogo, sem inferir o sistema instalado nos casos."""
    from src.config import SDK_PARA_ANDROID
    if sdk_list:
        vers = [SDK_PARA_ANDROID.get(int(s), s) for s in str(sdk_list).split(";") if s.strip().isdigit()]
        if vers:
            return f"Android {', '.join(vers)} (catálogo; uso nos casos não confirmado)"
    return "não informada"


def fontes_de(modelo: str, marca: str | None, soc_fab: str | None) -> list[tuple[str, str | None]]:
    chaves = list(PERFIL_PESQUISA.get(modelo, {}).get("fontes", []))
    if marca == "Motorola" and "dkma_motorola" not in chaves:
        chaves.append("dkma_motorola")
    chaves.append("play_console")
    # A pesquisa B2C é contextual: não afirma que o perfil causou o erro.
    # Os links oficiais ajudam a comparar os sintomas com a documentação do autenticador.
    for chave in ("b2c_troubleshoot", "b2c_errors"):
        if chave not in chaves:
            chaves.append(chave)
    return [FONTES[c] for c in chaves]
