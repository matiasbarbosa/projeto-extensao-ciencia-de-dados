"""Sanitizador de exportações do ServiceNow.

RODE ESTE SCRIPT NO AMBIENTE DO TRABALHO, ANTES de o arquivo sair de lá.

Etapas, nesta ordem:
  1. converte o HTML das descrições em texto (tags, &#64;, &#43;...);
  2. gera o pseudônimo do participante a partir do CPF encontrado no texto
     (HMAC-SHA256 com sal secreto). Se não houver CPF, usa a coluna do
     solicitante. Atenção: no ServiceNow o "caller" costuma ser o atendente
     da central, não o participante;
  3. coleta os nomes que aparecem em linhas "Nome:", "Participante:", em
     sequências EM MAIÚSCULAS e nas colunas de pessoas (caller, assigned_to,
     sys_updated_by), e apaga esses nomes em todo o texto do chamado;
  4. remove as linhas de dados cadastrais (CPF, matrícula, e-mail, telefone,
     endereço), rodapés de e-mail, CEP, 0800, números longos, URLs, tokens e
     números de outros tickets;
  5. troca o nome da empresa (e frases que a identificam) por EPX;
  6. troca o número do INC por um ID fictício (INC-F0001...) e grava a
     correspondência em data/private/ (fora do Git; não compartilhar);
  7. lista as linhas que ainda parecem suspeitas para revisão manual.

Uso:
  python -m src.sanitizar_servicenow export.xlsx \
      --col-texto short_description description overview \
      --col-solicitante caller_id --col-nomes assigned_to sys_updated_by \
      --col-extra priority state hold_reason \
      --empresa "SIGLA" "Nome completo da empresa" "Patrocinador"
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import re
import secrets
from pathlib import Path

import pandas as pd

from src import config

# Palavras que podem aparecer com inicial maiúscula ou EM CAIXA ALTA e não são nomes
PERMITIDAS = {
    # aparelhos / tecnologia
    "android", "ios", "iphone", "ipad", "motorola", "moto", "samsung", "galaxy", "xiaomi",
    "redmi", "poco", "realme", "oppo", "edge", "note", "google", "play", "store", "chrome",
    "safari", "webview", "app", "aplicativo", "wi-fi", "wifi", "4g", "5g", "lte", "pin",
    "token", "sms", "ok", "id", "plus", "pro", "ultra", "lite", "neo", "fusion", "power",
    "max", "mini", "fe", "api", "url", "hmg", "prd", "spe", "sap", "nat", "erro", "login",
    "senha", "biometria", "face", "smartphone", "tablet", "sim", "não", "nao", "vivo",
    "claro", "tim", "oi", "auth", "capec", "pdf", "png", "jpg", "html", "ti", "sla", "faq",
    # marcadores do próprio sanitizador
    "epx", "nome", "cpf", "matricula", "email", "telefone", "num", "inc", "token", "ip",
    "removido", "endereco", "cep",
    # palavras comuns em caixa alta nos chamados
    "mensagem", "da", "de", "do", "das", "dos", "e", "o", "a", "participante", "assistido",
    "assistida", "central", "atendimento", "caso", "urgente", "urgência", "urgencia",
    "manifestação", "manifestacao", "descrição", "descricao", "dados", "resposta", "final",
    "incidente", "sistema", "acesso", "problema", "obs", "br", "rj", "sp", "favor", "plano",
    "futuro", "família", "familia", "ouvidoria", "denúncia", "denuncia", "fale", "conosco",
    "siga", "nossas", "redes", "sociais", "reclamação", "reclamacao", "tipo", "assunto",
    "data", "protocolo", "evidências", "evidencias", "observações", "observacoes",
    "situação", "situacao", "identificada", "histórico", "historico", "análises", "analises",
    "pontos", "para", "análise", "analise", "informações", "informacoes", "dispositivo",
    "ocorrência", "ocorrencia", "complementar", "procedimentos", "realizados", "impacto",
    "acesso", "pelo", "computador", "aplicativo", "relato", "solicitação", "solicitacao",
}
CONECTORES = {"da", "de", "do", "das", "dos", "e"}

# Linhas de dados cadastrais: rótulo + valor até o fim da linha (o "." cobre letras quebradas)
RX_LINHA_CADASTRO = re.compile(
    r"(?im)^[ \t\-•*]*(cpf|matr.?cula[^:\n]{0,40}|e-?mail|tel(?:efone)?|celular|whats\w*|contato|"
    r"endere.?o|cep|rg)\b[ \t]*[:\-–]?.*$")
RX_LINHA_NOME = re.compile(
    r"(?m)^[ \t\-•*]*((?i:nome(?: completo)?|participante|assistid[ao]|titular|benefici.?ri[ao]))"
    r"[ \t]*(:|\s(?=[A-ZÀ-Ý]))[ \t]*(.{2,80})$")
RX_CAIXA_ALTA = re.compile(r"\b[A-ZÀ-Ý][A-ZÀ-Ý'\-]+(?:\s+[A-ZÀ-Ý][A-ZÀ-Ý'\-]*){1,6}\b")
RX_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}[-.\s]?\d{2}(?!\d)")
RX_CPF_ROTULO = re.compile(r"(?i)cpf\W{0,6}(\d{3}\.?\d{3}\.?\d{3}[-.\s]?\d{2})(?!\d)")


def cpf_valido(c: str) -> bool:
    d = [int(x) for x in re.sub(r"\D", "", c)]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for n in (9, 10):
        dv = (sum(d[i] * (n + 1 - i) for i in range(n)) * 10) % 11 % 10
        if dv != d[n]:
            return False
    return True


def achar_cpf(t: str) -> str | None:
    """CPF do participante: primeiro o que vem depois do rótulo 'CPF', depois qualquer CPF válido."""
    for c in RX_CPF_ROTULO.findall(t) + RX_CPF.findall(t):
        if cpf_valido(c):
            return re.sub(r"\D", "", c)
    return None

RODAPES = [
    re.compile(r"(?is)siga nossas redes sociais.*?(estritamente proibido\.?|$)"),
    re.compile(r"(?is)esta mensagem e qualquer arquivo transmitido.*?(estritamente proibido\.?|$)"),
    re.compile(r"(?is)pedimos avaliar o nosso atendimento.*?(acesse este link\.?)"),
    re.compile(r"(?is)o retorno desta mensagem n.o .{1,3} monitorado.*?(\n|$)"),
]

PADROES = [
    ("MENCAO", re.compile(r"@\[[^\]]{0,80}\]")),          # menções do tipo @[Nome Sobrenome]
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("URL", re.compile(r"https?://\S+|www\.\S+")),
    ("TOKEN", re.compile(r"\b[A-Za-z0-9_\-]{24,}\b|eyJ[\w\-]+\.[\w\-]+\.[\w\-]+")),
    ("CPF", RX_CPF),
    ("TELEFONE", re.compile(r"0800[\s-]?\d{3}[\s-]?\d{4}|(?:\+\s?55[\s-]?)?\(?\b\d{2}\)?[\s-]?9?\d{4}[\s-]?\d{3,4}(?!\d)")),
    ("CEP", re.compile(r"(?<!\d)\d{5}-\d{3}(?!\d)")),
    ("MATRICULA", re.compile(r"(?i)\b(matr.?cula|mat\.?)\s*[:nº°#-]*\s*[\d.\-]+")),
    ("INC", re.compile(r"(?i)\b(INC|RITM|REQ|S?CTASK|TASK|CHG|PRB|CS)\d{5,}")),
    ("IP", re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")),
    ("NUM", re.compile(r"\d{5,}")),
    ("ENDERECO", re.compile(r"(?i)\b(rua|av\.|avenida|praia|pra.a|edif.cio|bairro)\s[^\n.]{0,80}")),
    ("NOME", re.compile(
        r"\b((?i:sr|sra|senhor|senhora|participante|cliente|usu.rio|usu.ria|nome|atenciosamente|att))\.?"
        r"\s*[:,]?\s+([A-ZÀ-Ý][a-zà-ÿ]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][a-zà-ÿ]+)*)")),
]
SEQ_MAIUSC = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][a-zà-ÿ]+)+")
_SUSP_RX = re.compile(r"\d{5,}|@|&#\d+;")


# --------------------------------------------------------------------------
def _sal() -> bytes:
    config.DATA_PRIVATE.mkdir(parents=True, exist_ok=True)
    arq = config.DATA_PRIVATE / "sal.txt"
    if not arq.exists():
        arq.write_text(secrets.token_hex(32))
    return arq.read_text().strip().encode()


def pseudonimo(valor: str, sal: bytes) -> str:
    v = str(valor).strip()
    v = re.sub(r"\D", "", v) if re.fullmatch(r"[\d.\-\s]+", v) else v.lower()
    return hmac.new(sal, v.encode(), hashlib.sha256).hexdigest()[:12]


def html_para_texto(t: str) -> str:
    if not isinstance(t, str):
        return ""
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|blockquote|tr)>|<hr\s*/?>", "\n", t)
    t = re.sub(r"(?i)<li[^>]*>", "\n- ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(html.unescape(t)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def _tokens_nome(txt: str) -> set[str]:
    return {p for p in re.split(r"[\s,;|.()/]+", txt)
            if len(p) >= 3 and not any(c.isdigit() for c in p) and p.lower() not in PERMITIDAS}


def nomes_do_texto(t: str) -> set[str]:
    """Nomes em linhas 'Nome:'/'Participante:' e sequências EM CAIXA ALTA."""
    nomes: set[str] = set()
    for m in RX_LINHA_NOME.finditer(t):
        nomes |= _tokens_nome(m.group(3))
    for m in RX_CAIXA_ALTA.finditer(t):
        palavras = m.group(0).split()
        if any(p.lower() not in PERMITIDAS for p in palavras):
            nomes |= _tokens_nome(m.group(0))
    return nomes


def _apagar_nomes(t: str, nomes: set[str], contagem: dict) -> str:
    for n in sorted(nomes, key=len, reverse=True):
        t, k = re.subn(r"(?<![\w\[])" + re.escape(n) + r"(?![\w\]])", "[NOME]", t, flags=re.IGNORECASE)
        contagem["NOME"] = contagem.get("NOME", 0) + k
    return t


def limpar_texto(txt: str, nomes_conhecidos: set[str], empresa: list[str], contagem: dict) -> str:
    t = html_para_texto(txt)
    if not t.strip():
        return ""
    for rx in RODAPES:
        t = rx.sub(" ", t)
    for rotulo, pad in PADROES[:4]:                            # menção, e-mail, URL e token antes dos nomes
        t, k = pad.subn(f"[{rotulo}]", t)
        contagem[rotulo] = contagem.get(rotulo, 0) + k
    for e in sorted(empresa, key=len, reverse=True):          # nome da empresa, com limite de palavra
        t = re.sub(r"(?<!\w)" + re.escape(e) + r"(?!\w)", "EPX", t, flags=re.IGNORECASE)

    t = _apagar_nomes(t, nomes_conhecidos | nomes_do_texto(t), contagem)
    t, k = RX_LINHA_NOME.subn(lambda m: f"{m.group(1)}: [NOME]", t)
    contagem["LINHA_NOME"] = contagem.get("LINHA_NOME", 0) + k
    t, k = RX_LINHA_CADASTRO.subn(lambda m: f"{m.group(1).split()[0]}: [REMOVIDO]", t)
    contagem["LINHA_CADASTRO"] = contagem.get("LINHA_CADASTRO", 0) + k

    for rotulo, pad in PADROES[4:]:
        if rotulo == "NOME":
            t, k = pad.subn(lambda m: m.group(0) if m.group(2).split()[0].lower() in PERMITIDAS
                            else m.group(1) + " [NOME]", t)
        else:
            t, k = pad.subn(f"[{rotulo}]", t)
        contagem[rotulo] = contagem.get(rotulo, 0) + k

    def _talvez_nome(m: re.Match) -> str:
        palavras = [p for p in m.group(0).split() if p.lower() not in CONECTORES]
        if all(p.lower() in PERMITIDAS for p in palavras):
            return m.group(0)
        contagem["NOME_HEUR"] = contagem.get("NOME_HEUR", 0) + 1
        return "[NOME]"

    t = SEQ_MAIUSC.sub(_talvez_nome, t)
    # palavra isolada EM CAIXA ALTA colada a um [NOME] (ex.: "ROBERTO [NOME]") também é nome
    t = re.sub(r"\b[A-ZÀ-Ý]{3,}\b(?=\s+\[NOME\])|(?<=\[NOME\])\s+[A-ZÀ-Ý]{3,}\b",
               lambda m: m.group(0) if m.group(0).strip().lower() in PERMITIDAS else " [NOME]", t)
    t = re.sub(r"(\[NOME\][\s,]*){2,}", "[NOME] ", t)
    linhas = [re.sub(r"\s+", " ", l).strip() for l in t.splitlines()]
    return " / ".join(l for l in linhas if l)


def suspeito(t: str) -> bool:
    if _SUSP_RX.search(t or ""):
        return True
    for m in SEQ_MAIUSC.finditer(t or ""):
        if not all(p.lower() in PERMITIDAS | CONECTORES for p in m.group(0).split()):
            return True
    return False


def _datas(s: pd.Series) -> pd.Series:
    iso = s.astype(str).str.match(r"\d{4}-\d{2}-\d{2}").mean() > 0.5
    return pd.to_datetime(s, errors="coerce", dayfirst=not iso)


def ler_export(caminho: Path) -> pd.DataFrame:
    if caminho.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(caminho, dtype=str)
    for enc in ("utf-8-sig", "cp1252"):
        try:
            df = pd.read_csv(caminho, dtype=str, encoding=enc, sep=None, engine="python")
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError("Não consegui ler o arquivo")
    quebrados = df.apply(lambda c: c.astype(str).str.contains("\ufffd", regex=False)).any(axis=1).sum()
    if quebrados:
        print(f"AVISO: {quebrados} linhas já vieram com acentos perdidos (caractere �) no próprio export. "
              "Exporte em Excel (.xlsx) para preservar os acentos.")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--col-numero", default="number")
    ap.add_argument("--col-data", default="opened_at", help='use "" se o export não tiver data')
    ap.add_argument("--col-texto", nargs="+", default=["short_description", "description"])
    ap.add_argument("--col-solicitante", nargs="*", default=["caller_id"],
                    help="usada para pseudônimo só quando o texto não tem CPF; o nome é apagado do texto")
    ap.add_argument("--col-nomes", nargs="*", default=["assigned_to", "sys_updated_by"],
                    help="colunas com nomes/logins de pessoas: só para apagar do texto; NÃO vão para a saída")
    ap.add_argument("--col-extra", nargs="*", default=[],
                    help="colunas estruturadas seguras para manter (ex.: priority state)")
    ap.add_argument("--empresa", nargs="*", default=[],
                    help="nomes/frases que identificam a empresa, substituídos por EPX")
    ap.add_argument("--saida", type=Path, default=config.DATA_RAW / "servicenow" / "incidentes_sanitizados.csv")
    a = ap.parse_args()

    df = ler_export(a.arquivo)
    a.col_nomes = [c for c in a.col_nomes if c in df.columns]
    faltando = [c for c in [a.col_numero, *([a.col_data] if a.col_data else []), *a.col_texto,
                            *a.col_solicitante, *a.col_extra] if c not in df.columns]
    if faltando:
        raise SystemExit(f"Colunas não encontradas: {faltando}\nDisponíveis: {list(df.columns)}")

    sal = _sal()
    if a.col_data:
        df["_data"] = _datas(df[a.col_data])
        df = df.sort_values("_data").reset_index(drop=True)
    else:
        print("AVISO: sem coluna de data; o período e o gráfico mensal ficarão vazios.")
        df["_data"] = pd.NaT
        df = df.sample(frac=1, random_state=config.SEED).reset_index(drop=True)
    df["inc_id"] = [f"INC-F{i:04d}" for i in range(1, len(df) + 1)]

    texto_bruto = df[a.col_texto].fillna("").astype(str).map(html_para_texto).agg("\n".join, axis=1)

    # pseudônimo: CPF do texto > solicitante
    cpf = [achar_cpf(t) for t in texto_bruto]
    sol = df[a.col_solicitante].fillna("").astype(str).agg("|".join, axis=1) if a.col_solicitante \
        else pd.Series("", index=df.index)
    df["participante_pseud"] = [pseudonimo(c, sal) if c else (pseudonimo("sol:" + s, sal) if s.strip("|") else None)
                                for c, s in zip(cpf, sol)]
    df["pseud_origem"] = ["cpf" if c else ("solicitante" if s.strip("|") else "nenhum") for c, s in zip(cpf, sol)]

    nomes_globais: set[str] = set()
    for c in [*a.col_solicitante, *a.col_nomes]:
        for v in df[c].dropna():
            nomes_globais |= _tokens_nome(v) | ({v.strip()} if len(v.strip()) >= 3 else set())

    contagem: dict = {}
    df["descricao"] = [limpar_texto(t, nomes_globais, a.empresa, contagem) for t in texto_bruto]
    df["opened_at"] = df["_data"].dt.floor("h")

    saida = df[["inc_id", "opened_at", "participante_pseud", "pseud_origem", "descricao", *a.col_extra]]
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    saida.to_csv(a.saida, index=False, encoding="utf-8")
    corr = config.DATA_PRIVATE / "correspondencia_inc.csv"
    df[[a.col_numero, "inc_id"]].to_csv(corr, index=False)

    print(f"Linhas: {len(saida)}  ->  {a.saida}")
    print(f"Correspondência privada: {corr}  (NÃO compartilhar)")
    print("Pseudônimo por:", saida["pseud_origem"].value_counts().to_dict(),
          f"| participantes distintos: {saida['participante_pseud'].nunique()}")
    print("Substituições:", {k: v for k, v in contagem.items() if v})
    if a.col_data:
        d = df["_data"]
        print(f"Período: {d.min():%d/%m/%Y} a {d.max():%d/%m/%Y} | datas não lidas: {d.isna().sum()}"
              "  (confira com o filtro do ServiceNow)")
    susp = saida[saida["descricao"].map(suspeito)]
    if len(susp):
        print(f"\nATENÇÃO: {len(susp)} linhas para revisar manualmente antes de enviar:")
        for r in susp.itertuples():
            print(f"  {r.inc_id}: {r.descricao[:200]}")


if __name__ == "__main__":
    main()
