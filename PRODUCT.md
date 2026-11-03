# Product

<!-- impeccable:product-schema 1 -->

> Arquivo versionado em repositório público. Usa só o nome fictício do parceiro (EPX).
> Não registrar aqui o nome real do parceiro, contagens internas (incidentes, base de
> aparelhos) nem nomes de pessoas do parceiro.

## Platform

web

## Usuários

- **Principal: a professora orientadora (Ana Carolina Carius, Unicarioca, disciplina SM262207).**
  Avalia o projeto contra o Plano de Ação: clareza do recorte, método, rastreabilidade entre
  fontes, tratamento e limpeza, cumprimento da LGPD, honestidade sobre dados simulados e
  acessibilidade das visualizações. Abre o dashboard para conferir se o método se sustenta,
  não para operar.
- **Principal: a equipe técnica do parceiro (time do app e suporte da EPX).** Precisa saber
  quais perfis de aparelho Android (marca, modelo, versão do Android, versão do app, RAM, chip,
  rede) concentram as falhas de login *em taxa, não em volume*, para priorizar onde investigar.
  Usa os resultados reais na execução local; a versão publicada demonstra o método.
- **Secundário: leigos (resumo executivo).** São atendidos pelo resumo executivo ou infográfico
  exigido pelo Plano de Ação, não pelo dashboard.

## Propósito

Diagnóstico analítico dos perfis de aparelho Android associados às falhas de login no app EPX,
comparando cada grupo à população total de aparelhos com o app instalado. O produto é um
pipeline reproduzível (Python) mais um dashboard Streamlit.

Pergunta central: quais características de aparelho, versão do Android, versão do app e rede
estão mais associadas às falhas de login, comparadas à população total de aparelhos com o app?

Sucesso significa: a professora consegue seguir cada número desde a fonte até o gráfico, e a
equipe do parceiro sai sabendo quais grupos têm taxa acima do esperado, com intervalo de
confiança, e quais não têm diferença clara. **Não** se busca a causa raiz.

## Posicionamento

Compara **taxas** contra a base instalada real do Google Play Console em vez de contar chamados.
Uma marca que domina a base sempre terá mais incidentes; o projeto mostra quem está acima do
esperado para o seu tamanho. Junta ServiceNow, Google Play Console e (pendente) IBM Instana com
rastreabilidade explícita (funil de dados) e usa um grafo de co-ocorrência de atributos para
revelar combinações super-representadas.

## Contexto Operacional

- Projeto individual de extensão, EAD, com entregas por etapas e data final fixa.
- Fontes:
  - **ServiceNow**: incidentes de login, anonimizados no ambiente do parceiro por
    `src/sanitizar_servicenow.py` antes de sair (ID fictício, pseudônimo HMAC com sal mantido
    pelo parceiro, remoção de dados pessoais do texto).
  - **Google Play Console**: catálogo de aparelhos com o app instalado e base de instalação por
    modelo (aparelhos ativos, não pessoas).
  - **IBM Instana**: requisições ao ambiente de produção; cruzamento R1 ainda pendente.
- Relacionamentos: R1 ServiceNow ↔ Instana (por pseudônimo do participante), R2 ServiceNow ↔
  Play Console (por modelo, via correspondência de nome livre), R3 Instana ↔ Play Console
  (validação, se o Instana capturar aparelho).
- O dashboard lê do MariaDB (ou SQLite) e cai para os CSVs de `data/processed/` quando não há
  banco, para funcionar hospedado.
- Fluxo: ingestão → limpeza e tratamento → rastreabilidade (funil) → análise (taxas por mil,
  IC 95% exato de Poisson, teste binomial, Benjamini-Hochberg, risco relativo, GLM de Poisson)
  → grafo (NetworkX, centralidade, Louvain, lift) → dashboard.

## Restrições e capacidades

- **Dados do dashboard publicado: simulados (Plano B).** A versão hospedada usa incidentes
  gerados por `src/simular_incidentes.py` a partir do catálogo real, rotulados como simulados em
  toda tela e entregável. Resultados com incidentes reais anonimizados ficam **só na execução
  local** e no relatório. Conclusões do simulado valem para o método, não para a causa real.
- O dashboard publicado precisa ficar no ar por 6 meses (exigência do Plano de Ação).
- Nunca exibir nem versionar dados pessoais (nome, CPF, matrícula, e-mail, telefone, número
  original do chamado). Só agregados; grupos com menos de `K_MIN` (5) participantes são omitidos.
- Incidente ≠ aparelho ≠ pessoa: as taxas usam participantes distintos.
- A base por versão do Android é **estimada** (o Play Console informa por modelo); a regra
  `REGRA_SDK` precisa estar declarada sempre que essa dimensão aparecer.
- Resultados são **associação, não causa**. iOS fora do escopo por falta de dados; nunca afirmar
  que iOS "não tem o problema".
- Viés de quem reporta: só entra quem abriu chamado. O Play Console é uma foto de um momento; os
  incidentes cobrem um período.
- Reprodutibilidade: semente fixa em `src/config.py`, README, `requirements.txt`, scripts
  versionados.
- Terminologia: "participantes" (não "clientes" ou "usuários"), "incidentes", "técnico" versus
  "conta/cadastro", "taxa por mil aparelhos", "acima do esperado (FDR < 5%)".
- Uso acadêmico dos dados autorizado pelo parceiro (registro no Plano de Ação, fora do
  repositório). Entregáveis públicos seguem com base simulada e agregados, por sigilo.
- Em aberto: cruzamento com Instana (R1); se o Instana tem monitoramento mobile.

## Compromissos

- Idioma: português do Brasil. Tom direto, factual, sem exagero; explica a estatística em
  linguagem simples antes de mostrar o número.
- Parceiro sempre como "Entidade de Previdência X (EPX)", app como "App EPX".
- Aviso de dados simulados visível e inequívoco sempre que a fonte for o simulador.

## Evidências disponíveis

- Catálogo real do Play Console: `data/raw/play_console_devices.csv`.
- Incidentes simulados e gabarito do simulador: `data/processed/incidentes_simulados*.csv`.
- Resultados publicáveis: `data/processed/resultados_taxas.csv`, `modelo_poisson.csv`,
  `grafo_nos.csv`, `grafo_arestas.csv`, `lineage.csv`.
- Incidentes reais anonimizados existem só localmente (`data/raw/servicenow/`, fora do Git).
- Documentação: `docs/dicionario_dados.md`, `docs/exportar_servicenow.md`, `README.md`.
- Não existem e não devem ser inventados: depoimentos, validação do parceiro sobre os achados,
  causa raiz confirmada, dados de iOS, cruzamento com Instana.

## Princípios

1. **Taxa antes de volume.** Todo grupo é lido contra sua base instalada, com intervalo de
   confiança; contagem absoluta nunca aparece sozinha como conclusão.
2. **Rastreável de ponta a ponta.** Cada número se liga à fonte e à etapa do funil que o produziu.
3. **Honestidade sobre os dados.** Simulado é rotulado como simulado; estimativas e premissas
   (como a regra de SDK) ficam explícitas onde o número aparece.
4. **Privacidade por construção.** Pseudonimização na origem, só agregados, supressão de grupos
   pequenos.
5. **Associação, não causa.** A linguagem nunca promete mais do que o método sustenta.

## Accessibilidade

- Exigência do Plano de Ação: visualizações acessíveis e sem distorção de escala (eixos de taxa
  começam em zero; escala logarítmica só quando declarada, como no IRR).
- Paleta segura para daltonismo; a cor nunca é o único portador de significado (rótulos e legendas
  textuais junto).
