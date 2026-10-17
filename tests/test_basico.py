from src.catalogo import ler_catalogo
from src.extracao import achar_rede, achar_sdk, apelidos_catalogo, achar_modelo, classificar
from src.sanitizar_servicenow import limpar_texto

CAT = ler_catalogo()


def test_soma_play_console():
    assert CAT["install_n"].sum() == 88_908
    assert (CAT["install_n"] > 0).sum() == 989


def test_extracao_modelo_e_android():
    ap = apelidos_catalogo(CAT)
    nomes = CAT.set_index("model_id")["model_name"]
    mid, _ = achar_modelo("cliente com Motorola g84 5G no android 15, wifi", ap)
    assert nomes[mid] == "moto g84 5G"
    mid, _ = achar_modelo("Samsung Galaxy A54", ap)
    assert nomes[mid] == "Galaxy A54 5G"
    assert achar_sdk("versão 15 do Android") == 35
    assert achar_rede("moto g84 5G em casa") == "nao_informado"
    assert achar_rede("conectado no 5G") == "5g"


def test_classificacao():
    assert classificar("esqueci a senha")[0] == "conta_cadastro"
    assert classificar("o app volta para a tela inicial após o token")[1] == "retorno_tela_inicial"
    # textos com acentos perdidos no export (caractere de substituição)
    assert classificar("ap\ufffds digitar o c\ufffddigo volta \ufffd p\ufffdgina inicial")[1] == "retorno_tela_inicial"
    assert classificar("N\ufffdo conseguimos localizar sua conta")[0] == "conta_cadastro"
    assert classificar("erro INIP-002 ao entrar")[1] == "erro_auth"


def test_extracao_textos_de_formulario():
    import pandas as pd
    from src.extracao import enriquecer
    inc = pd.DataFrame({"descricao": [
        "3. Vers\ufffdo do dispositivo (marca/modelo): Motorola G 35 4. Data e hora da a\ufffd\ufffdo; 2. Qual \ufffd a vers\ufffdo do aplicativo EPX? 6.3.2",
        "Vers\ufffdo do dispositivo (marca/modelo): Iphone 13 / app volta para a tela inicial",
        "Marca/Modelo: sansung A 32 / Se for Android, oriente a limpeza de cache; se for iPhone, reinstale",
    ]})
    out, _ = enriquecer(inc, CAT)
    nomes = CAT.set_index("model_id")["model_name"]
    assert nomes[out.loc[0, "model_id"]] == "moto g35 5G" and out.loc[0, "app_version"] == "6.3.2"
    assert out.loc[1, "so"] == "ios"
    assert out.loc[2, "so"] == "android" and out.loc[2, "marca"] == "Samsung"


def test_sanitizacao_remove_dados_pessoais():
    t = limpar_texto("Sra. Ana Lima, CPF 123.456.789-09, mat 1234567, ana@x.com, (21) 98765-4321, ACME",
                     {"Ana Lima"}, ["ACME"], {})
    for proibido in ["Ana", "Lima", "123.456", "1234567", "ana@", "98765", "ACME"]:
        assert proibido not in t, t


def test_sanitizacao_preserva_aparelho():
    t = limpar_texto("Participante no moto g84 android 15, atendido por rafael teixeira (c123456)",
                     {"Rafael", "Teixeira", "c123456"}, [], {})
    assert "moto g84 android 15" in t
    for proibido in ["rafael", "teixeira", "c123456"]:
        assert proibido not in t.lower(), t


def test_sanitizacao_html_caixa_alta_e_cadastro():
    from src.sanitizar_servicenow import html_para_texto
    bruto = ("<p>MENSAGEM DA PARTICIPANTE JOANA PEREIRA SOUZA reclama do app. Sra. Joana usa Moto G35.</p>"
             "<p>CPF 529.982.247-25 <br />email joana.souza&#64;gmail.com <br />tel &#43;55 21 99876-543</p>"
             "<ul><li>Nome: Joana Pereira Souza</li><li>Matrícula: 1234567-8</li></ul>"
             "<p>Rua das Flores 123, Botafogo - 22250-040. ACME</p>")
    t = limpar_texto(html_para_texto(bruto), set(), ["ACME"], {})
    for proibido in ["JOANA", "Joana", "PEREIRA", "Souza", "529.982", "joana.souza", "99876", "1234567",
                     "Flores", "22250", "ACME", "&#"]:
        assert proibido not in t, (proibido, t)
    assert "Moto G35" in t and "MENSAGEM DA PARTICIPANTE" in t


def test_cpf_valido_e_pseudonimo():
    from src.sanitizar_servicenow import achar_cpf
    assert achar_cpf("tel 21987654321 CPF: 529.982.247-25") == "52998224725"
    assert achar_cpf("tel 21987654321") is None


def test_sanitizacao_mencao_e_nome_caixa_alta_isolado():
    t = limpar_texto("consegue acessar. @[FULANO DE TAL] , por favor abrir. Atendido por BELTRANO [NOME]", set(), [], {})
    assert "FULANO" not in t and "BELTRANO" not in t, t
