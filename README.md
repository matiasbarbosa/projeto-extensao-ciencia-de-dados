# Falhas de login no app EPX: perfis de aparelho Android associados aos incidentes

Projeto de Extensão em Ciência de Dados (SM262207) — Centro Universitário Unicarioca.
Parceiro: **Entidade de Previdência X (EPX)** — nome fictício; o parceiro real não é identificado.

> ⚠️ **Sobre os dados.** O catálogo de aparelhos (`data/raw/play_console_devices.csv`) é o
> export do Google Play Console do app. Os **incidentes publicados neste repositório são
> SIMULADOS** (Plano B), gerados por `src/simular_incidentes.py` a partir do catálogo real e
> **calibrados apenas com parâmetros agregados** da análise real (proporções de plataforma e de
> tipo de erro, risco relativo do grupo de maior incidência, taxas de menção de marca/modelo).
> A análise real roda localmente (`--fonte real_anonimizado`), grava em `data/private/real/`
> (fora do Git) e não alimenta o banco por padrão. Nenhum incidente, nome, CPF, matrícula ou
> número de chamado real está no repositório.

## Pergunta central

Quais características de aparelho (marca, modelo, versão do Android, RAM, chip), versão do
app e rede estão mais associadas às falhas de login, **comparadas à população total** de
aparelhos com o app?

## Como reproduzir

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # preencha usuário/senha do MariaDB
python -m src.db                # testa a conexão
python -m src.pipeline          # carrega tudo no banco e gera data/processed/*.csv
streamlit run dashboard/app.py  # dashboard
```

Sem MariaDB: use `DB_URL=sqlite:///data/processed/projeto.sqlite` no `.env`, ou
`python -m src.pipeline --sem-banco` (o dashboard lê os CSVs).

Semente fixa: `SEED = 20261014` em `src/config.py`.

## Estrutura

```
src/
  config.py               parâmetros (semente, K_MIN, regra de SDK, cenário do simulador)
  db.py                   esquema das tabelas (MariaDB/SQLite) e conexão
  catalogo.py             leitura do export "quebrado" do Play Console
  sanitizar_servicenow.py anonimização dos INCs (roda no ambiente do parceiro)
  simular_incidentes.py   Plano B: incidentes simulados + gabarito
  extracao.py             modelo/Android/app/rede a partir do texto + classificação do erro
  analise.py              taxas por grupo, IC, testes, regressão de Poisson
  grafo.py                grafo de atributos (NetworkX), centralidade, comunidades, lift
  pipeline.py             orquestra tudo
dashboard/app.py          Streamlit
sql/schema.sql            DDL do MariaDB
docs/                     dicionário de dados, guia de exportação do ServiceNow
data/raw/                 catálogo do Play Console (export servicenow fica fora do Git)
data/processed/           bases tratadas e resultados (CSV)
```

## Fluxo

1. **Ingestão** — catálogo do Play Console (989 modelos ativos, 88.908 aparelhos) e
   incidentes (simulados ou anonimizados na origem).
2. **Limpeza e tratamento** — ver seção abaixo.
3. **Rastreabilidade** — tabela `lineage` (funil: total → técnicos → casados ao catálogo →
   com versão do Android → participantes distintos → cruzados com Instana).
4. **Análise** — taxa de participantes afetados por mil aparelhos, por grupo, com IC 95%
   exato de Poisson; teste binomial exato do grupo contra a base; correção de
   Benjamini-Hochberg; risco relativo; GLM de Poisson com offset log(base).
5. **Grafo** — nós = atributos; arestas = co-ocorrência no mesmo incidente; centralidade de
   autovetor, comunidades Louvain, lift populacional.
6. **Dashboard** — Streamlit lendo do MariaDB.

## Limpeza e tratamento

- **Play Console**: vírgula separa colunas, `;` separa listas e sobram `;` no fim das linhas;
  alguns nomes têm vírgula e aspas mal escapadas. Lemos 3 colunas fixas à esquerda e 13 à
  direita; o meio é o nome do modelo. Conferência: soma da base = 88.908 (bate com o console).
- **RAM** convertida em faixa; **SDK** convertido em versão do Android.
- **Base por versão do Android** não existe no console (é por modelo), e os chamados quase nunca
  informam a versão. Premissa declarada: `REGRA_SDK = "max"` — cada modelo é contado na versão
  mais recente que suporta, e a mesma regra é usada para imputar a versão dos incidentes que não
  a citam (coluna `sdk_origem`). Alternativas: `"recente"` e `"igual"`.
- **Plataforma** (`so`): Android, iOS ou desconhecida, a partir do texto. iOS entra no funil, mas
  não nas taxas (não há catálogo iOS).
- **Fabricante do chip** (`soc_fab`): Qualcomm, MediaTek, Samsung Exynos, Unisoc… derivado do SoC.
- **Modelo no chamado** é texto livre: corrigimos grafias comuns (sansung, motorolla, galaxi…),
  removemos numeração de formulário e trechos de modelo de resposta ("Exemplo: …"), normalizamos
  ("motorola"→"moto", "galaxy"→"gx", remove "5G/4G") e casamos com apelidos gerados do catálogo
  (maior correspondência vence), priorizando o campo "marca/modelo".
- **Texto com acentos perdidos** (export CSV do ServiceNow): as regras usam `.` no lugar de
  letras acentuadas.
- **Classificação do erro** por regras (`error_class`): técnico × conta/cadastro × fora do
  escopo × indefinido, com subtipos (retorno à tela inicial, erro AUTH, código de verificação…).
- **Incidente ≠ pessoa**: as taxas usam participantes distintos (pseudônimo gerado do CPF; o
  `caller_id` do ServiceNow é o atendente, então sem CPF cada incidente conta como 1 pessoa).

## Privacidade (LGPD)

- Dados pessoais nunca entram no repositório. O `sanitizar_servicenow.py` roda no ambiente do
  parceiro e troca nº do INC por ID fictício, solicitante por pseudônimo HMAC (sal mantido pelo
  parceiro) e remove CPF, e-mail, telefone, matrícula, URLs, tokens e nomes do texto.
- Exports brutos (`data/raw/servicenow/`) e a tabela de correspondência (`data/private/`) estão
  no `.gitignore`.
- Agregados omitem grupos com menos de 5 participantes (`K_MIN`).

## Limitações

- Só entra quem abriu chamado (viés de quem reporta).
- O Play Console é uma foto; os incidentes cobrem um período.
- Associação ≠ causa. iOS fora do escopo (sem dados).
- Cruzamento com o IBM Instana (R1) pendente.

## Prioridade de investigação: Android 15 no moto g35 5G

O **Android 15 no moto g35 5G é a primeira hipótese para testes**, não uma versão
comprovadamente responsável pelas falhas. Na análise real, os chamados técnicos desse modelo
não citam a versão do Android. Entre os 201 chamados técnicos Android, só dois a citam.
O catálogo informa versões suportadas por modelo, não a versão instalada em cada aparelho.

Na configuração `REGRA_SDK = "max"`, versões ausentes são imputadas pela versão mais recente
listada para o modelo; as taxas, o grafo e o modelo por versão dependem dessa premissa e
**não comprovam** qual Android estava instalado nem qual versão tem maior risco real.
O moto e13, outro modelo em destaque, foi lançado com Android 13 Go, reforçando que não se
deve atribuir todos os casos ao Android 15.

A escolha do Android 15 para os testes se baseia na
[documentação da Motorola para o moto g35](https://help.motorola.com/hc/3535/15/global/pt-br/CG1395067443.html)
e em uma [compilação brasileira publicada em dezembro de 2025](https://www.stockrom.net/2025/12/xt2433-1-retbr-os15-vuoa35-116-60-3.html).
Um [relato isolado](https://www.reclameaqui.com.br/motorola/motorola-moto-g35-inutilizavel-apos-atualizacao-para-android-15-bugs-travamentos-e-superaquecimento_ueoI516-IN4k7itg/)
descreve travamentos após uma atualização, mas não trata do app EPX nem prova causalidade.
Há notícia secundária sobre Android 16 no modelo; data e disponibilidade por aparelho precisam
ser confirmadas. O Play Console não identifica quem atualizou ou quando.

**Como validar:** registrar, com o time do app, a versão real do Android e do aplicativo em
novos incidentes; testar o login no moto g35 com Android 15 e comparar com outras versões
disponíveis e configurações de bateria; observar a restauração do estado ao alternar para o
app de mensagens e voltar. Conforme a
[documentação do Android](https://developer.android.com/topic/libraries/architecture/saving-states),
o sistema pode encerrar um processo em segundo plano; isso não demonstra que tenha ocorrido
nos incidentes. As proteções de OTP do Android 15 restringem o acesso de certos apps a
notificações e, por si só, também não provam uma falha de login.
