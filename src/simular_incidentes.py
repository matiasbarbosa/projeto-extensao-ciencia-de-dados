"""Simulador de incidentes (Plano B).

DADOS SIMULADOS. Nenhum incidente aqui é real. O simulador usa o catálogo
REAL do Play Console como população e sorteia incidentes segundo
config.CENARIO, cujos parâmetros foram CALIBRADOS com resultados AGREGADOS da
análise real (feita localmente, sobre incidentes anonimizados que não são
publicados): proporções de plataforma, de classe e de subtipo de erro, risco
relativo do grupo de maior incidência, taxa de menção de marca/modelo/versão.

Serve para publicar e demonstrar o método (pipeline, testes, grafo,
dashboard) sem expor dados do parceiro. Gera também um gabarito para medir a
qualidade da extração a partir do texto livre.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.analise import fabricante_soc
from src.catalogo import explodir_sdk, ler_catalogo

TEXTOS_TECNICOS = {
    "retorno_tela_inicial": [
        "Após digitar o código de verificação o app volta para a tela inicial.",
        "Informa CPF, senha e código e o aplicativo retorna para a tela inicial informando que o acesso foi cancelado.",
        "Depois de validar o código o app fica em looping e volta para o início.",
    ],
    "erro_auth": ["Ao tentar entrar aparece o erro AUTH-010.", "Mensagem de erro AUTH003 ao validar o acesso."],
    "falha_login_generica": ["Aparece a mensagem Falha no Login.",
                             "Mensagem: Não foi possível efetuar o login neste momento."],
    "codigo_verificacao": ["O código de verificação não chega por SMS.", "Código de validação inválido ao digitar."],
    "carregamento": ["O app fica carregando e não conclui o acesso.", "Fica girando com a mensagem aguarde."],
    "conexao_servidor": ["Erro de conexão com o servidor ao fazer login."],
    "biometria": ["A biometria não funciona para entrar no app."],
    "fechamento": ["O app fecha sozinho ao tentar entrar."],
    "navegador_redirecionamento": ["Mensagem: o navegador não pode abrir a página porque o endereço é inválido."],
}
TEXTOS_CONTA = {
    "senha": ["Participante informa senha inválida, mas afirma digitar corretamente.", "Esqueci a senha e não consigo redefinir."],
    "matricula": ["Possui duas matrículas e o sistema direciona para a matrícula encerrada."],
    "conta_nao_localizada": ["Ao informar o CPF aparece: Não conseguimos localizar sua conta."],
    "conta_bloqueada": ["Conta bloqueada após tentativas de acesso."],
    "dados_cadastrais": ["Mensagem de dados inválidos ao informar CPF e matrícula."],
}
TEXTO_INDEFINIDO = ["Participante não consegue acessar o aplicativo.", "Participante reclama que continua sem acesso ao app."]


def _escrever_modelo(rng: np.random.Generator, brand: str, modelo: str) -> str:
    """Escreve o modelo do jeito 'livre' que aparece nos chamados."""
    m = modelo
    op = rng.integers(0, 5)
    if op == 0:
        m = m.lower()
    elif op == 1:
        m = m.replace(" 5G", "").replace(" 4G", "")
    elif op == 2 and brand == "motorola":
        m = m.replace("moto ", "Motorola ")
    elif op == 3 and brand == "samsung":
        m = "Samsung " + m
    return m


def _escolher(rng, d: dict) -> str:
    k = list(d)
    p = np.array([d[x] for x in k], dtype=float)
    return k[rng.choice(len(k), p=p / p.sum())]


def simular(cenario: dict = config.CENARIO, seed: int = config.SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    cat = ler_catalogo()
    cat["soc_fab"] = cat["soc"].map(fabricante_soc)
    pop = explodir_sdk(cat).merge(cat[["model_id", "brand", "model_name", "soc_fab"]], on="model_id")

    culp = cenario["culpado"]
    alvo = pd.Series(True, index=pop.index)
    for k, v in culp.items():
        alvo &= pop[k] == v
    mesma_marca = (pop["brand"] == culp.get("brand")) & ~alvo
    mult = np.where(alvo, cenario["multiplicador_culpado"],
                    np.where(mesma_marca, cenario.get("multiplicador_marca", 1.0), 1.0))
    w_tec = pop["install_est"] * mult
    w_base = pop["install_est"]

    n = cenario["n_incidentes"]
    ini, fim = (pd.Timestamp(d) for d in cenario["periodo"])
    versoes = cenario["versoes_app"]
    n_part = int(n * cenario["prop_participantes_distintos"])
    pool = [f"P{i:05d}" for i in range(n_part)]

    linhas, gabarito = [], []
    for i in range(n):
        ios = rng.random() < cenario["prop_ios"]
        classe = _escolher(rng, cenario["classes_android"])
        w = w_tec if classe == "tecnico" and not ios else w_base
        j = rng.choice(pop.index, p=w / w.sum())
        r = pop.loc[j]
        grupo_culpado = bool(alvo.loc[j]) and not ios

        if classe == "tecnico":
            dist = cenario["subtipos_culpado"] if grupo_culpado else cenario["subtipos_outros"]
            subtipo = _escolher(rng, dist)
            texto = rng.choice(TEXTOS_TECNICOS[subtipo])
        elif classe == "conta_cadastro":
            subtipo = _escolher(rng, cenario["subtipos_conta"])
            texto = rng.choice(TEXTOS_CONTA[subtipo])
        else:
            subtipo, texto = "indefinido", rng.choice(TEXTO_INDEFINIDO)

        partes = ["Participante relata dificuldade de acesso ao aplicativo EPX."]
        cita_aparelho = rng.random() < cenario["p_cita_aparelho"]
        if ios:
            if cita_aparelho:
                partes.append(f"Versão do dispositivo (marca/modelo): iPhone {rng.choice([11, 12, 13, 14, 15, 16])}")
        elif cita_aparelho:
            if rng.random() < cenario["p_modelo_dado_marca"]:
                partes.append(f"Versão do dispositivo (marca/modelo): {_escrever_modelo(rng, r.brand, r.model_name)}")
            else:
                partes.append(f"Marca: {r.brand.capitalize() if r.brand != 'poco' else 'POCO'} (não sabe o modelo)")
        app = _escolher(rng, versoes)
        cita_app = rng.random() < cenario["p_cita_app"]
        if cita_app:
            partes.append(f"Qual é a versão do aplicativo EPX? {app}")
        partes.append(f"Em que momento ocorre o erro? {texto}")

        data = ini + (fim - ini) * float(rng.beta(cenario["forma_tempo"], 1.0))
        part = pool[i] if i < n_part else pool[rng.integers(0, n_part)]
        inc_id = f"INC-S{i + 1:04d}"
        linhas.append({"inc_id": inc_id, "opened_at": data.floor("h"), "participante_pseud": part,
                       "descricao": " / ".join(partes)})
        gabarito.append({"inc_id": inc_id, "so": "ios" if ios else "android", "model_id": None if ios else r.model_id,
                         "app_version": app if cita_app else None, "classe_erro": classe, "subtipo_erro": subtipo,
                         "grupo_culpado": grupo_culpado, "cita_aparelho": cita_aparelho})

    inc = pd.DataFrame(linhas).sort_values("opened_at").reset_index(drop=True)
    return inc, pd.DataFrame(gabarito)


if __name__ == "__main__":
    inc, gab = simular()
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    inc.to_csv(config.ARQ_INCIDENTES_SIM, index=False)
    gab.to_csv(config.DATA_PROCESSED / "incidentes_simulados_gabarito.csv", index=False)
    print(inc.head(), f"\n{len(inc)} incidentes SIMULADOS -> {config.ARQ_INCIDENTES_SIM}")
