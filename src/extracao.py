"""Extração de atributos do texto livre e classificação dos incidentes.

- pré-processamento: corrige grafias comuns (sansung, motorolla, galaxi...),
  remove numeração de formulário ("4. Data e hora") e trechos de modelo de
  resposta ("Exemplo: ...", "se for Android ... se for iPhone ...");
- sistema operacional (Android / iOS) e marca, mesmo sem modelo;
- modelo do aparelho: casamento do texto normalizado com apelidos gerados a
  partir do catálogo do Play Console (tabela model_mapping);
- versão do Android, versão do app e rede: expressões regulares;
- classe do erro (técnico x conta/cadastro x fora do escopo): regras ordenadas
  (tabela error_class).

As expressões usam "." no lugar de letras acentuadas porque parte dos exports
do ServiceNow chega com acentos perdidos (caractere �).
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from src import config

# --------------------------------------------------------------------------
# Regras de classificação (ordem importa: a primeira que casar vence)
# --------------------------------------------------------------------------
REGRAS = [
    # fora do escopo (não é falha de login)
    (r"cobertura|pec.lio|protocolos? .{0,40}(n.o|sem) (foram )?(enviad|registrad|processad)|requisi..o em an.lise",
     "fora_escopo", "outro_servico"),
    (r"(informa..es|funcionalidades|dados) (est.o |ficam )?(sempre )?(zerad|indispon.ve)", "fora_escopo", "pos_login"),
    # conta / cadastro
    (r"n.o conseguimos (localizar|encontrar) (a |sua )?conta|conta n.o (foi )?(encontrada|localizada)|"
     r"cpf n.o (encontrado|localizado)|primeiro acesso", "conta_cadastro", "conta_nao_localizada"),
    (r"duas matr.culas|matr.cula (encerrada|vinculada)|troca de matr.cula|(solicita|pede) (a )?matr.cula",
     "conta_cadastro", "matricula"),
    (r"bloque", "conta_cadastro", "conta_bloqueada"),
    (r"senha (ou matr.cula )?(est. )?(incorreta|inv.lida|errada|expirada)|esqueci (a )?senha|redefini..o de senha|"
     r"redefinir (a )?senha|trocar (a )?senha|cadastrar (nova )?senha|erro de senha", "conta_cadastro", "senha"),
    (r"dados inv.lidos|dados divergentes|dados informados incorretamente|atualiza..o cadastral|meu cadastro",
     "conta_cadastro", "dados_cadastrais"),
    # técnico
    (r"(volta|voltando|devolv\w*|retorn\w*)\s(para|pra|ao?|.)?\s?(a |.)?\s?(tela|p.gina) (inicial|de login|de identifica..o)|"
     r"(retorn\w*|volta\w*) (ao|para o) in.cio|volta (para|pra) (colocar|digitar|pedir)|"
     r"n.o (consegue )?avan.a\w* da tela|acesso (foi )?cancelado|voc. cancelou|looping|loop|reinicia|"
     r"perde a sess.o|segundo plano|fecha ao (trocar|abrir|voltar)", "tecnico", "retorno_tela_inicial"),
    (r"safari|endere.o (.|e) inv.lido|n.o pode abrir a p.gina", "tecnico", "navegador_redirecionamento"),
    (r"\b(auth|inip)\s?-?\s?0\d\d|coderror", "tecnico", "erro_auth"),
    (r"c.digo (de )?(verifica..o|valida..o|libera..o)?\s?(inv.lido|n.o chega|n.o recebe|expirad|n.o funciona)|"
     r"n.o (recebe|chega) (o )?(c.digo|sms|token)|etapa do c.digo|verificar c.digo|token|sms",
     "tecnico", "codigo_verificacao"),
    (r"biometria|digital|reconhecimento facial", "tecnico", "biometria"),
    (r"tela branca|carregando|n.o carrega|fica (rodando|girando)|travad|congela|aguarde", "tecnico", "carregamento"),
    (r"fecha sozinho|crash|para de funcionar|n.o abre|p.gina n.o responde", "tecnico", "fechamento"),
    (r"conex.o|timeout|tempo esgotado|sem resposta|servidor|erro (inesperado|gen.rico|desconhecido)|unable to",
     "tecnico", "conexao_servidor"),
    (r"falha no login|n.o foi poss.vel (efetuar|validar|acessar|realizar)|erro de login|mensagem de erro",
     "tecnico", "falha_login_generica"),
]
_REGRAS_RE = [(re.compile(p, re.IGNORECASE), c, s) for p, c, s in REGRAS]


def tabela_regras() -> pd.DataFrame:
    return pd.DataFrame([{"regra_id": i + 1, "padrao": p[:255], "classe": c, "subtipo": s}
                         for i, (p, c, s) in enumerate(REGRAS)])


def classificar(texto: str) -> tuple[str, str]:
    for rx, classe, subtipo in _REGRAS_RE:
        if rx.search(texto or ""):
            return classe, subtipo
    return "indefinido", "indefinido"


# --------------------------------------------------------------------------
# Pré-processamento
# --------------------------------------------------------------------------
GRAFIAS = [
    (r"\bs[ae]n?s[uo]n?[gn]\b|\bsamsumg\b|\bsamgung\b", "samsung"),
    (r"\bgalax[iy]\b", "galaxy"),
    (r"\bmotorol+a\b|\bmotorolla\b|\bmotorla\b", "motorola"),
    (r"\bx[iao]{2,4}m[iy]\b|\bxiaom\b", "xiaomi"),
    (r"\bpoc+o\b", "poco"),
    (r"\bi\s?phone", "iphone"),
    (r"\bhw?a[wu]?e[iy]\b|\bhuaw[ae][iy]\b", "huawei"),
]
_GRAFIAS_RE = [(re.compile(p, re.IGNORECASE), s) for p, s in GRAFIAS]
_RUIDO = [
    re.compile(r"(?i)exemplo\s*:[^/|]*"),
    re.compile(r"(?i)se (for|.) (android|iphone|ios)[^/|]*"),
    re.compile(r"(?i)for (android|iphone|ios)[^/|]*"),
    re.compile(r"(?<![\d.])\b\d{1,2}[.)]\s+(?=[^\d\s])"),   # "4. Data e hora" (numeração de formulário)
]


def preprocessar(t: str) -> str:
    t = str(t or "")
    for rx in _RUIDO:
        t = rx.sub(" / ", t)
    for rx, s in _GRAFIAS_RE:
        t = rx.sub(s, t)
    return t


# --------------------------------------------------------------------------
# Normalização de nomes de modelo
# --------------------------------------------------------------------------
def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


def normalizar(t: str) -> str:
    t = _sem_acento(str(t)).lower()
    t = re.sub(r"\bmotorola\b", "moto", t)
    t = re.sub(r"\bgalaxy\b", "gx", t)
    t = re.sub(r"\b(samsung|xiaomi|celular|aparelho|smartphone)\b", " ", t)
    t = re.sub(r"\b[45]g\b", " ", t)
    return re.sub(r"[^a-z0-9+]", "", t)


def apelidos_catalogo(cat: pd.DataFrame) -> dict[str, int]:
    """apelido normalizado -> model_id (em colisão, fica o de maior base)."""
    ativos = cat[cat["install_n"] > 0].sort_values("install_n")
    apelidos: dict[str, int] = {}
    for r in ativos.itertuples():
        base = normalizar(r.model_name)
        cand = {base}
        if base.startswith("gx"):
            cand.add(base[2:])            # "Samsung A54" sem a palavra Galaxy
        if base.startswith("moto") and len(base) > 6:
            cand.add(base[4:])            # "g84", "edge60fusion"
        if r.brand in {"redmi", "poco"}:
            cand.add(normalizar(f"{r.brand} {r.model_name}"))
        for c in cand:
            if (len(c) >= 3 or c.startswith("gx")) and re.search(r"\d", c):
                apelidos[c] = r.model_id   # ordenado por base: o maior sobrescreve
    return apelidos


def achar_modelo(texto: str, apelidos: dict[str, int]) -> tuple[int | None, str | None]:
    n = normalizar(texto)
    melhor = None
    for ap, mid in apelidos.items():
        i = n.find(ap)
        while i != -1:
            antes = n[i - 1] if i > 0 else ""
            depois = n[i + len(ap)] if i + len(ap) < len(n) else ""
            if not antes.isdigit() and not depois.isdigit():
                if melhor is None or len(ap) > len(melhor[1]):
                    melhor = (mid, ap)
                break
            i = n.find(ap, i + 1)
    return melhor if melhor else (None, None)


RX_CAMPO_MODELO = re.compile(
    r"(?i)(?:marca\s*/\s*modelo|marca e modelo|modelo do (?:aparelho|celular)|dispositivo\s*\(marca\s*/\s*modelo\)"
    r"|aparelho|celular|smartphone)\s*\)?\s*[:?\-]*\s*/?\s*([^/|]{2,60})")

MARCAS = [
    ("Samsung", r"samsung|galaxy"), ("Motorola", r"\bmoto\b|motorola|\bmoto\s?[gez]\s?\d"),
    ("Xiaomi/Redmi/POCO", r"xiaomi|redmi|\bpoco\b"),
    ("Outras", r"\blg\b|huawei|realme|\basus\b|nokia|\btcl\b|\bpositivo\b|multilaser|infinix|\boppo\b|\bzte\b|lenovo|\bsony\b"),
]
_MARCAS_RE = [(m, re.compile(p, re.IGNORECASE)) for m, p in MARCAS]
RX_IOS = re.compile(r"(?i)iphone|\bios\b|\bipad\b|\bapple\b")


def achar_marca(texto: str) -> str | None:
    """Marca Android citada (prioriza o campo 'marca/modelo')."""
    campo = RX_CAMPO_MODELO.search(texto or "")
    for alvo in ([campo.group(1)] if campo else []) + [texto or ""]:
        achadas = [m for m, rx in _MARCAS_RE if rx.search(alvo)]
        if achadas:
            return achadas[0]
    return None


def achar_so(texto: str, marca: str | None, model_id) -> str:
    ios = bool(RX_IOS.search(texto or ""))
    android = pd.notna(marca) or pd.notna(model_id) or bool(re.search(r"(?i)android", texto or ""))
    if ios and android:
        campo = RX_CAMPO_MODELO.search(texto or "")
        if campo and RX_IOS.search(campo.group(1)) and not any(rx.search(campo.group(1)) for _, rx in _MARCAS_RE):
            return "ios"
        return "ambos" if campo is None or RX_IOS.search(campo.group(1)) else "android"
    return "ios" if ios else ("android" if android else "desconhecido")


_ANDROID_PARA_SDK = {v: k for k, v in config.SDK_PARA_ANDROID.items()}
RX_ANDROID = re.compile(r"(?i)android\s*(?:vers.o\s*)?(\d{1,2})(?:\.\d)?\b|vers.o\s*(\d{1,2})\s*do\s*android")
RX_APP = re.compile(r"(?i)(?:vers.o do (?:aplicativo|app)|aplicativo|app)\D{0,30}?(\d\s?[.,]\s?\d{1,2}(?:\s?[.,]\s?\d{1,2})?)\b")
RX_REDE = [("wifi", re.compile(r"wi-?fi", re.I)), ("5g", re.compile(r"\b5g\b(?! *[a-z])", re.I)),
           ("4g", re.compile(r"\b4g\b|dados m.veis|rede m.vel", re.I))]


def achar_sdk(texto: str) -> int | None:
    m = RX_ANDROID.search(texto or "")
    if not m:
        return None
    return _ANDROID_PARA_SDK.get(m.group(1) or m.group(2))


def achar_app(texto: str) -> str | None:
    """Versão do app no formato X.Y.Z (aceita '6,2.1', '6. 1')."""
    m = RX_APP.search(texto or "")
    if not m:
        return None
    partes = re.split(r"\s?[.,]\s?", m.group(1).replace(" ", ""))
    if not partes or not 4 <= int(partes[0]) <= 9:      # descarta datas, etc.
        return None
    if len(partes) == 2 and len(partes[1]) == 2:        # "6.12" digitado sem o segundo ponto
        partes = [partes[0], partes[1][0], partes[1][1]]
    partes = [str(int(p)) for p in partes] + ["0"] * (3 - len(partes))
    return ".".join(partes[:3])


def achar_rede(texto: str) -> str:
    sem_modelo = re.sub(r"\b\w*\d\w*\s+5g\b", "", texto or "", flags=re.I)  # "moto g84 5G" não é rede
    for rotulo, rx in RX_REDE:
        if rx.search(sem_modelo):
            return rotulo
    return "nao_informado"


def enriquecer(inc: pd.DataFrame, cat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica extração e classificação. Retorna (incidentes, model_mapping)."""
    apelidos = apelidos_catalogo(cat)
    nomes = cat.set_index("model_id")["model_name"]
    sdk_max = cat.set_index("model_id")["sdk_max"]
    out = inc.copy()
    txt = out["descricao"].map(preprocessar)

    def _modelo(t: str):
        campo = RX_CAMPO_MODELO.search(t)
        if campo:
            achado = achar_modelo(campo.group(1), apelidos)
            if achado[0] is not None:
                return achado
        return achar_modelo(t, apelidos)

    achados = txt.map(_modelo)
    out["model_id"] = achados.map(lambda x: x[0]).astype("Int64")
    out["modelo_informado"] = out["model_id"].map(lambda m: nomes.get(m) if pd.notna(m) else None)
    out["marca"] = txt.map(achar_marca)
    out["so"] = [achar_so(t, m, mid) for t, m, mid in zip(txt, out["marca"], out["model_id"])]
    out.loc[out["so"] == "ios", ["marca", "model_id", "modelo_informado"]] = None

    # versão do Android: a citada no texto; se não houver, a mais recente que o modelo
    # suporta no Play Console (premissa declarada em config.REGRA_SDK = "max")
    out["sdk"] = txt.map(achar_sdk).astype("Int64")
    out["sdk_origem"] = out["sdk"].map(lambda s: "texto" if pd.notna(s) else None)
    imput = out["sdk"].isna() & out["model_id"].notna()
    out.loc[imput, "sdk"] = out.loc[imput, "model_id"].map(sdk_max).astype("Int64")
    out.loc[imput, "sdk_origem"] = "sdk_max_do_modelo"
    out["android"] = out["sdk"].map(lambda s: config.SDK_PARA_ANDROID.get(int(s)) if pd.notna(s) else None)

    out["app_version"] = txt.map(achar_app)
    out["rede"] = txt.map(achar_rede)
    cls = txt.map(classificar)
    out["classe_erro"] = cls.map(lambda x: x[0])
    out["subtipo_erro"] = cls.map(lambda x: x[1])

    mapping = (pd.DataFrame({"texto_normalizado": achados.map(lambda x: x[1]), "model_id": out["model_id"]})
               .dropna().drop_duplicates("texto_normalizado"))
    mapping["metodo"], mapping["score"] = "alias", 1.0
    return out, mapping
