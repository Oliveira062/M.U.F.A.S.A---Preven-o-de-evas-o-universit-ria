BEGIN;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    login          VARCHAR(64)  NOT NULL UNIQUE CHECK (login ~ '^[A-Za-z0-9._@-]{3,64}$'),
    senha_hash     VARCHAR(100) NOT NULL CHECK (senha_hash LIKE '$2b$%'),
    perfil         VARCHAR(20)  NOT NULL CHECK (perfil IN ('ALUNO','DOCENTE','COORDENACAO','NUCLEO_APOIO',
                                                           'FINANCEIRO','DIRECAO','ADMIN','ENCARREGADO_DADOS')),
    id_aluno       VARCHAR(10),
    id_professor   VARCHAR(10),
    id_curso       VARCHAR(10),
    ativo          BOOLEAN      NOT NULL DEFAULT TRUE,
    falhas_login   SMALLINT     NOT NULL DEFAULT 0,
    bloqueado_ate  TIMESTAMPTZ,
    ultimo_login   TIMESTAMPTZ,
    criado_em      TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CHECK (perfil <> 'ALUNO'   OR id_aluno IS NOT NULL),
    CHECK (perfil <> 'DOCENTE' OR id_professor IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_aluno ON usuarios(id_aluno) WHERE id_aluno IS NOT NULL;

CREATE TABLE IF NOT EXISTS tokens_revogados (
    jti        VARCHAR(64) PRIMARY KEY,
    expira_em  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS auditoria_acessos (
    id_auditoria   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    momento        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    id_requisicao  VARCHAR(32),
    id_usuario     BIGINT,
    perfil         VARCHAR(20),
    operacao       VARCHAR(40)  NOT NULL,
    recurso        VARCHAR(200) NOT NULL,
    id_aluno_alvo  VARCHAR(10),
    resultado      VARCHAR(12)  NOT NULL CHECK (resultado IN ('PERMITIDO','NEGADO','BLOQUEADO')),
    origem         VARCHAR(45)
);
CREATE INDEX IF NOT EXISTS ix_auditoria_aluno   ON auditoria_acessos(id_aluno_alvo, momento);
CREATE INDEX IF NOT EXISTS ix_auditoria_momento ON auditoria_acessos(momento);

CREATE TABLE IF NOT EXISTS consentimentos (
    id_consentimento BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_aluno         VARCHAR(10)  NOT NULL,
    finalidade       VARCHAR(30)  NOT NULL CHECK (finalidade IN ('DADOS_SAUDE')),
    concedido        BOOLEAN      NOT NULL,
    concedido_por    VARCHAR(12)  NOT NULL CHECK (concedido_por IN ('TITULAR','RESPONSAVEL')),
    versao_termo     VARCHAR(10)  NOT NULL,
    registrado_em    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    id_usuario       BIGINT       NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_consentimentos_aluno ON consentimentos(id_aluno, finalidade, registrado_em);

CREATE TABLE IF NOT EXISTS solicitacoes_titular (
    id_solicitacao BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_aluno       VARCHAR(10)   NOT NULL,
    tipo           VARCHAR(40)   NOT NULL,
    descricao      VARCHAR(1000) NOT NULL DEFAULT '',
    situacao       VARCHAR(12)   NOT NULL DEFAULT 'ABERTA' CHECK (situacao IN ('ABERTA','EM_ANALISE','ATENDIDA','NEGADA')),
    registrada_em  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    respondida_em  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_b3_avaliacoes_aluno_data ON avaliacoes_risco(id_aluno, data_avaliacao DESC);
CREATE INDEX IF NOT EXISTS ix_b3_matriculas_aluno      ON matriculas(id_aluno);
CREATE INDEX IF NOT EXISTS ix_b3_turmas_professor      ON turmas(id_professor);
CREATE INDEX IF NOT EXISTS ix_b3_indicadores_aluno     ON indicadores_academicos(id_aluno, periodo_letivo DESC);
CREATE INDEX IF NOT EXISTS ix_b3_alunos_curso          ON alunos(id_curso);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mufasa_api') THEN
        CREATE ROLE mufasa_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mufasa_chat') THEN
        CREATE ROLE mufasa_chat LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END $$;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO mufasa_api, mufasa_chat;

GRANT SELECT ON alunos, cursos, materias, turmas, matriculas, indicadores_academicos,
               socioeconomico, avaliacoes_risco, professores TO mufasa_api;

GRANT SELECT ON usuarios TO mufasa_api;
GRANT UPDATE (falhas_login, bloqueado_ate, ultimo_login) ON usuarios TO mufasa_api;
GRANT SELECT, INSERT ON tokens_revogados TO mufasa_api;
GRANT SELECT, INSERT ON auditoria_acessos TO mufasa_api;
GRANT SELECT, INSERT ON consentimentos TO mufasa_api;
GRANT SELECT, INSERT ON solicitacoes_titular TO mufasa_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mufasa_api;

GRANT SELECT ON cursos, materias, turmas TO mufasa_chat;

CREATE OR REPLACE FUNCTION bloquear_alteracao_auditoria() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'auditoria_acessos e somente de insercao';
END $$;

DROP TRIGGER IF EXISTS tg_auditoria_imutavel ON auditoria_acessos;
CREATE TRIGGER tg_auditoria_imutavel
    BEFORE UPDATE OR DELETE ON auditoria_acessos
    FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao_auditoria();

COMMIT;
