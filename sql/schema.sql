-- Gerado por: python -m src.db --ddl
-- Banco: MariaDB (utf8mb4)

CREATE TABLE device_sdk (
	model_id INTEGER NOT NULL, 
	sdk INTEGER NOT NULL, 
	android VARCHAR(10), 
	peso FLOAT COMMENT 'fração da base do modelo atribuída à versão', 
	install_est FLOAT COMMENT 'instalações estimadas (premissa REGRA_SDK)', 
	PRIMARY KEY (model_id, sdk)
)COMMENT='Modelo x versão do Android (base estimada)';

CREATE TABLE devices_catalog (
	model_id INTEGER NOT NULL COMMENT 'ID sequencial atribuído na carga', 
	brand VARCHAR(60), 
	device VARCHAR(80) COMMENT 'codinome do aparelho', 
	manufacturer VARCHAR(80), 
	model_name VARCHAR(160), 
	ram_min_mb INTEGER, 
	ram_max_mb INTEGER, 
	ram_faixa VARCHAR(20), 
	form_factor VARCHAR(30), 
	soc VARCHAR(80), 
	gpu VARCHAR(120), 
	abis VARCHAR(120), 
	sdk_list VARCHAR(80) COMMENT 'versões de SDK separadas por ;', 
	sdk_max INTEGER, 
	install_n INTEGER COMMENT 'aparelhos ativos no Google Play Console: dispositivos Android com o app instalado e conectados aos servidores do Google nos últimos 30 dias',
	anr_rate FLOAT, 
	crash_rate FLOAT, 
	PRIMARY KEY (model_id)
)COMMENT='Catálogo do Google Play Console (uma linha por modelo)';

CREATE TABLE error_class (
	regra_id INTEGER NOT NULL, 
	padrao VARCHAR(255), 
	classe VARCHAR(20), 
	subtipo VARCHAR(40), 
	PRIMARY KEY (regra_id)
)COMMENT='Regras de classificação dos incidentes';

CREATE TABLE grafo_arestas (
	origem VARCHAR(160) NOT NULL, 
	destino VARCHAR(160) NOT NULL, 
	peso INTEGER COMMENT 'co-ocorrências em incidentes', 
	lift FLOAT COMMENT 'observado / esperado pela base', 
	PRIMARY KEY (origem, destino)
);

CREATE TABLE grafo_nos (
	no VARCHAR(160) NOT NULL, 
	tipo VARCHAR(20), 
	rotulo VARCHAR(160), 
	incidentes INTEGER, 
	lift FLOAT COMMENT 'participação nos incidentes / participação na base', 
	grau_ponderado FLOAT, 
	centralidade FLOAT, 
	comunidade INTEGER, 
	PRIMARY KEY (no)
);

CREATE TABLE incidents (
	inc_id VARCHAR(20) NOT NULL COMMENT 'ID fictício', 
	origem VARCHAR(20) COMMENT 'simulado | real_anonimizado', 
	opened_at DATETIME, 
	participante_pseud VARCHAR(16) COMMENT 'pseudônimo (hash com sal)', 
	descricao TEXT COMMENT 'texto sem dados pessoais', 
	modelo_informado VARCHAR(160), 
	model_id INTEGER, 
	sdk INTEGER, 
	android VARCHAR(10), 
	app_version VARCHAR(20), 
	rede VARCHAR(20), 
	so VARCHAR(15) COMMENT 'android | ios | ambos | desconhecido', 
	marca VARCHAR(40) COMMENT 'marca citada no texto', 
	sdk_origem VARCHAR(20) COMMENT 'texto | sdk_max_do_modelo', 
	classe_erro VARCHAR(20) COMMENT 'tecnico | conta_cadastro | fora_escopo | indefinido', 
	subtipo_erro VARCHAR(40), 
	PRIMARY KEY (inc_id)
)COMMENT='Incidentes de login (anonimizados ou simulados)';

CREATE TABLE lineage (
	ordem INTEGER NOT NULL, 
	etapa VARCHAR(120), 
	n INTEGER, 
	pct_total FLOAT, 
	PRIMARY KEY (ordem)
)COMMENT='Funil de dados / rastreabilidade';

CREATE TABLE model_mapping (
	texto_normalizado VARCHAR(160) NOT NULL, 
	model_id INTEGER, 
	metodo VARCHAR(20) COMMENT 'exato | alias | fuzzy | manual | sem_match', 
	score FLOAT, 
	PRIMARY KEY (texto_normalizado)
)COMMENT='Nome escrito no chamado -> modelo do catálogo';

CREATE TABLE modelo_poisson (
	termo VARCHAR(80) NOT NULL, 
	irr FLOAT COMMENT 'razão de taxas de incidência', 
	ic_inf FLOAT, 
	ic_sup FLOAT, 
	p_valor FLOAT, 
	PRIMARY KEY (termo)
)COMMENT='GLM de Poisson com offset log(base)';

CREATE TABLE perfis (
	perfil_id INTEGER NOT NULL, 
	`rank` INTEGER COMMENT 'posição no ranking (limite inferior do IC); nulo = sem base', 
	perfil VARCHAR(160), 
	modelo VARCHAR(160), 
	zona VARCHAR(60), 
	marca VARCHAR(60), 
	chip VARCHAR(80), 
	chip_fab VARCHAR(40), 
	ram VARCHAR(60), 
	android_play VARCHAR(80), 
	android_periodo VARCHAR(160) COMMENT 'versões disponíveis no período dos casos (pesquisa pública)', 
	ocorrencias INTEGER, 
	ocorrencias_tecnicas INTEGER, 
	afetados INTEGER, 
	base FLOAT, 
	taxa_por_mil FLOAT, 
	ic_inf FLOAT, 
	ic_sup FLOAT, 
	taxa_ajustada FLOAT COMMENT 'taxa encolhida para a média (ordena o ranking)', 
	risco_relativo FLOAT, 
	p_valor FLOAT, 
	p_ajustado FLOAT, 
	significativo INTEGER, 
	status VARCHAR(20), 
	tem_taxa INTEGER, 
	sintoma VARCHAR(40), 
	sintoma_pct FLOAT, 
	sintomas_json TEXT, 
	versoes_app_json TEXT, 
	inicio DATETIME, 
	fim DATETIME, 
	resumo TEXT, 
	hipotese TEXT, 
	fontes_json TEXT, 
	PRIMARY KEY (perfil_id)
)COMMENT='Perfis de aparelho (mapa e ranking do dashboard)';

CREATE TABLE resultados_taxas (
	dimensao VARCHAR(30) NOT NULL, 
	grupo VARCHAR(160) NOT NULL, 
	afetados INTEGER COMMENT 'participantes distintos', 
	incidentes INTEGER, 
	base FLOAT, 
	taxa_por_mil FLOAT, 
	ic_inf FLOAT, 
	ic_sup FLOAT, 
	risco_relativo FLOAT, 
	p_valor FLOAT, 
	p_ajustado FLOAT, 
	significativo INTEGER, 
	PRIMARY KEY (dimensao, grupo)
)COMMENT='Taxa de incidentes por grupo vs. taxa geral';
