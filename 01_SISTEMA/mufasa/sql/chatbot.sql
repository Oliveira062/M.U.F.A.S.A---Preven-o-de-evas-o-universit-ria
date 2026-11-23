BEGIN;

CREATE OR REPLACE VIEW vw_chat_disciplinas_aluno WITH (security_barrier = true) AS
SELECT m.id_aluno,
       mt.nome                  AS disciplina,
       t.periodo_letivo,
       m.va1, m.va2, m.va3,
       m.nota_final,
       m.frequencia_pct,
       m.situacao,
       mt.frequencia_minima_pct
  FROM matriculas m
  JOIN turmas   t  ON t.id_turma   = m.id_turma
  JOIN materias mt ON mt.id_materia = t.id_materia
 WHERE m.id_aluno IS NOT NULL;

CREATE OR REPLACE VIEW vw_chat_indicadores WITH (security_barrier = true) AS
SELECT id_aluno, periodo_letivo, faltas_total, frequencia_pct, media_semestre_anterior,
       media_atual, tendencia_media, atividades_pendentes
  FROM indicadores_academicos;

CREATE OR REPLACE VIEW vw_chat_risco_atual WITH (security_barrier = true) AS
SELECT a.id_aluno, a.nome_ficticio, a.id_curso, a.semestre_atual,
       CASE s.nivel WHEN 'CRITICO' THEN 'Crítico' WHEN 'ALTO' THEN 'Alto'
                    WHEN 'MODERADO' THEN 'Moderado' WHEN 'BAIXO' THEN 'Baixo' END AS nivel_risco,
       s.calculado_em::date AS data_avaliacao,
       (SELECT max(i.periodo_letivo) FROM indicadores_academicos i WHERE i.id_aluno = a.id_aluno) AS periodo_letivo
  FROM alunos a
  JOIN vw_score_atual s ON s.id_aluno = a.id_aluno
 WHERE s.nivel <> 'INDETERMINADO';

CREATE OR REPLACE VIEW vw_chat_vinculo_docente WITH (security_barrier = true) AS
SELECT DISTINCT m.id_aluno, t.id_professor
  FROM matriculas m
  JOIN turmas t ON t.id_turma = m.id_turma
 WHERE m.id_aluno IS NOT NULL;

CREATE TABLE IF NOT EXISTS chat_conversas (
    id_conversa          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_usuario           BIGINT      NOT NULL REFERENCES usuarios(id_usuario),
    iniciada_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultima_interacao     TIMESTAMPTZ NOT NULL DEFAULT now(),
    encerrada_em         TIMESTAMPTZ,
    motivo_encerramento  VARCHAR(12) CHECK (motivo_encerramento IN ('INATIVIDADE', 'USUARIO'))
);
CREATE INDEX IF NOT EXISTS ix_chat_conversas_aberta ON chat_conversas(id_usuario) WHERE encerrada_em IS NULL;

CREATE TABLE IF NOT EXISTS chat_mensagens (
    id_mensagem          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_conversa          BIGINT       NOT NULL REFERENCES chat_conversas(id_conversa),
    id_usuario           BIGINT       NOT NULL REFERENCES usuarios(id_usuario),
    momento              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    pergunta_redigida    VARCHAR(600) NOT NULL,
    intencao             VARCHAR(40)  NOT NULL,
    consulta_executada   VARCHAR(80),
    registros            INTEGER      NOT NULL DEFAULT 0,
    resposta             VARCHAR(4000) NOT NULL,
    redigida_por_ia      BOOLEAN      NOT NULL DEFAULT FALSE,
    tentativa_burla      BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_chat_mensagens_usuario ON chat_mensagens(id_usuario, momento DESC);
CREATE INDEX IF NOT EXISTS ix_chat_mensagens_burla ON chat_mensagens(momento) WHERE tentativa_burla;

REVOKE ALL ON cursos, materias, turmas FROM mufasa_chat;

GRANT SELECT ON vw_chat_disciplinas_aluno, vw_chat_indicadores, vw_chat_risco_atual,
               vw_chat_vinculo_docente TO mufasa_chat;

GRANT SELECT (nome) ON materias TO mufasa_chat;

GRANT SELECT, INSERT ON chat_conversas TO mufasa_chat;
GRANT UPDATE (ultima_interacao, encerrada_em, motivo_encerramento) ON chat_conversas TO mufasa_chat;
GRANT SELECT, INSERT ON chat_mensagens TO mufasa_chat;

GRANT INSERT ON logs_tecnicos TO mufasa_chat;
GRANT SELECT, INSERT, UPDATE ON servicos_status TO mufasa_chat;
GRANT USAGE ON SEQUENCE chat_conversas_id_conversa_seq, chat_mensagens_id_mensagem_seq TO mufasa_chat;

DO $$
DECLARE
    visao TEXT;
BEGIN
    FOREACH visao IN ARRAY ARRAY['vw_chat_disciplinas_aluno', 'vw_chat_indicadores', 'vw_chat_risco_atual',
                                 'vw_chat_vinculo_docente']
    LOOP
        EXECUTE format('ALTER VIEW %I OWNER TO mufasa_dono', visao);
    END LOOP;
END $$;

ALTER ROLE mufasa_chat SET statement_timeout = '3s';

COMMIT;
