# Dicionário de dados

Banco: MariaDB (`sql/schema.sql`, gerado por `python -m src.db --ddl`).
Os mesmos dados ficam em CSV em `data/processed/`.

## devices_catalog — catálogo do Google Play Console (1 linha por modelo)

| coluna | tipo | descrição |
| --- | --- | --- |
| model_id | int | ID sequencial atribuído na carga |
| brand | texto | marca (minúsculas) |
| device | texto | codinome do aparelho |
| manufacturer | texto | fabricante |
| model_name | texto | nome comercial |
| ram_min_mb / ram_max_mb | int | memória total informada (MB) |
| ram_faixa | texto | até 2 GB, 3-4 GB, 6 GB, 8 GB, 12 GB+ |
| form_factor | texto | Phone, Tablet... |
| soc / gpu | texto | chip e GPU |
| abis | texto | arquiteturas, separadas por `;` |
| sdk_list | texto | níveis de API do Android, separados por `;` |
| sdk_max | int | maior nível de API listado |
| install_n | int | aparelhos ativos com o app (foto do momento da extração) |
| anr_rate / crash_rate | real | taxas percebidas pelo usuário (fração) |

## device_sdk — modelo × versão do Android

| coluna | descrição |
| --- | --- |
| model_id, sdk | chave |
| android | versão comercial (ex.: SDK 35 = Android 15) |
| peso | fração da base do modelo atribuída a essa versão (premissa `REGRA_SDK`) |
| install_est | base estimada = install_n × peso |

## incidents — incidentes de login (simulados ou anonimizados)

| coluna | descrição |
| --- | --- |
| inc_id | ID fictício (`INC-S…` simulado, `INC-F…` real anonimizado) |
| origem | `simulado` ou `real_anonimizado` |
| opened_at | abertura, truncada na hora |
| participante_pseud | pseudônimo do participante (HMAC-SHA256 com sal) |
| descricao | texto livre sem dados pessoais (não publicado quando real) |
| modelo_informado / model_id | modelo identificado no texto e casado ao catálogo |
| sdk / android | versão citada no texto ou imputada a partir do catálogo; consultar `sdk_origem` |
| sdk_origem | `texto` quando extraída do chamado; `sdk_max_do_modelo` quando imputada; vazio se desconhecida |
| app_version | versão do app citada no texto |
| rede | wifi, 4g, 5g, nao_informado |
| classe_erro | tecnico, conta_cadastro, indefinido |
| subtipo_erro | ver `error_class` |

## error_class — regras de classificação (ordem importa)

## model_mapping — texto normalizado do chamado → model_id (método e score)

## lineage — funil de dados (etapa, n, % do total)

## resultados_taxas — taxa por grupo

| coluna | descrição |
| --- | --- |
| dimensao / grupo | ex.: `marca_android` / `Motorola \| 15` |
| afetados | participantes distintos com incidente técnico |
| incidentes | número de chamados |
| base | aparelhos ativos do grupo (estimado quando envolve versão do Android) |
| taxa_por_mil | afetados por mil aparelhos |
| ic_inf / ic_sup | IC 95% exato de Poisson |
| risco_relativo | taxa do grupo / taxa do restante |
| p_valor / p_ajustado | teste binomial exato; ajuste Benjamini-Hochberg por dimensão |
| significativo | 1 se p_ajustado < 0,05 e risco_relativo > 1 |

Grupos com menos de `K_MIN` (5) afetados são omitidos.

## modelo_poisson — GLM de Poisson com offset log(base)

termo, irr (razão de taxas), ic_inf, ic_sup, p_valor. Referência: Samsung, Android 14, 8 GB.

## grafo_nos / grafo_arestas — grafo de co-ocorrência

- nó: `tipo: valor` (marca, modelo, android, app, ram, rede, erro); incidentes; lift;
  grau ponderado; centralidade de autovetor; comunidade (Louvain).
- aresta: par de atributos no mesmo incidente; peso = nº de incidentes; lift
  populacional (só pares de atributos de aparelho).

## instana_requests — requisições ao PRD (R1, pendente)

## perfis — perfis de aparelho (mapa e ranking do dashboard)

Um perfil por modelo do catálogo (nome sem 5G/4G), mais linhas sem taxa para casos com marca e
sem modelo, sem marca e de iPhone.

| coluna | descrição |
| --- | --- |
| rank | posição no ranking pela taxa ajustada (nulo = sem base para taxa) |
| perfil / modelo / zona | nome exibido, modelo normalizado, zona do mapa (marca) |
| chip / chip_fab / ram | SoC, fabricante do chip, memória do modelo no Play Console |
| android_play | versões do Android que o modelo tem no Play Console |
| android_periodo | versões listadas no catálogo para o modelo; não confirmam o sistema usado nos casos |
| ocorrencias / ocorrencias_tecnicas / afetados | incidentes de login em Android, os técnicos e participantes distintos |
| base, taxa_por_mil, ic_inf, ic_sup | aparelhos ativos, taxa e IC 95% exato de Poisson |
| taxa_ajustada | (afetados + taxa geral x 500) / (base + 500), por mil; ordena o ranking |
| risco_relativo, p_valor, p_ajustado, significativo | contra os demais perfis; binomial unilateral + Benjamini-Hochberg |
| status | critico (>= 5 afetados, significativo, RR >= 5), acima, atencao, normal, sem_base |
| sintoma, sintoma_pct, sintomas_json, versoes_app_json | sintoma predominante e distribuições |
| resumo, hipotese, fontes_json | contexto público, hipótese a validar e fontes consultadas |
