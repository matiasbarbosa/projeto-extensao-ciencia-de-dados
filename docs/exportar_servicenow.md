# Como exportar os incidentes do ServiceNow

> Faça tudo **no computador do trabalho**. O arquivo bruto não sai de lá; só sai a
> versão gerada pelo `src/sanitizar_servicenow.py`, depois de revisada.
> Antes de enviar qualquer coisa para fora (inclusive para ferramentas de IA),
> confirme que a política interna da empresa permite.

## Opção 1 — Pela lista (mais simples)

1. Abra **Incident > All** (ou a lista/filtro que você já usa para os INCs de login).
2. Monte o filtro (ex.: *Short description contém "login"* OU *Category = Acesso*,
   período desejado). Clique com o botão direito no "breadcrumb" do filtro e
   **Copy query** para guardar a consulta.
3. Clique na engrenagem (Personalize List Columns) e deixe só:
   - `Number`, `Opened`, `Short description`, `Description`, `Category`, `Subcategory`,
     `Close notes`, `Caller` (será pseudonimizado), e campos de aparelho se existirem
     (ex.: `u_modelo`, `u_versao_android`, `u_versao_app`).
4. Clique com o botão direito no cabeçalho de qualquer coluna → **Export** → **Excel (.xlsx)**.
   Prefira Excel: o export CSV da instância pode perder os acentos (aparecem como `�`).
   Inclua `opened_at`.

## Opção 2 — Pela URL (repetível)

```
https://<instancia>.service-now.com/incident_list.do?CSV
  &sysparm_query=<query copiada no passo 2>
  &sysparm_fields=number,opened_at,short_description,description,category,subcategory,close_notes,caller_id
  &sysparm_display_value=true
```

(cole tudo numa linha só; o navegador baixa o CSV com o seu login).

## Opção 3 — API REST (se tiver permissão)

```bash
curl -u "$USUARIO" -H "Accept: application/json" \
  "https://<instancia>.service-now.com/api/now/table/incident?sysparm_query=<query>&sysparm_fields=number,opened_at,short_description,description,close_notes,caller_id&sysparm_limit=1000"
```

## Observações

- **Comentários e work notes** são campos de "journal" e normalmente não saem no export da
  lista. Se a descrição do problema estiver lá, adicione a coluna
  `Additional comments and Work notes` (`comments_and_work_notes`) ou use a API com
  `sysparm_display_value=true`.
- O limite padrão de exportação é alto o suficiente para ~500 linhas.

## Depois de exportar: sanitizar

```bash
python -m src.sanitizar_servicenow export.xlsx \
  --col-numero number --col-data opened_at \
  --col-texto short_description description close_notes \
  --col-solicitante caller_id \
  --col-nomes assigned_to sys_updated_by \
  --col-extra priority state hold_reason \
  --empresa "SIGLA" "Nome completo da empresa" "Nome do patrocinador"
```

- `--col-solicitante`: vira pseudônimo (necessário para contar participantes distintos).
- `--col-nomes`: nomes/logins de atendentes; servem só para apagar esses nomes do texto e
  **não** vão para a saída.
- `--col-extra`: campos estruturados sem dado pessoal que podem ser mantidos.
- Qualquer coluna não listada é descartada (ex.: `assignment_group`, `sys_tags`, `follow_up`).

O script grava `data/raw/servicenow/incidentes_sanitizados.csv` (fora do Git) e lista as
linhas que ainda parecem conter dados pessoais. **Revise essas linhas à mão.** A tabela
`data/private/correspondencia_inc.csv` (INC real → ID fictício) e o sal ficam só com a
empresa.

Para rodar a análise com os dados reais anonimizados:

```bash
python -m src.pipeline --fonte real_anonimizado
```
