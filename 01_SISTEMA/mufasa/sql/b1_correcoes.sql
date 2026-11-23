BEGIN;

DROP VIEW IF EXISTS vw_chat_disciplinas_aluno, vw_chat_indicadores, vw_chat_risco_atual,
                    vw_chat_vinculo_docente;

ALTER TABLE universidades          ALTER COLUMN id_universidade SET NOT NULL, ADD PRIMARY KEY (id_universidade);
ALTER TABLE cursos                 ALTER COLUMN id_curso        SET NOT NULL, ADD PRIMARY KEY (id_curso);
ALTER TABLE professores            ALTER COLUMN id_professor    SET NOT NULL, ADD PRIMARY KEY (id_professor);
ALTER TABLE materias               ALTER COLUMN id_materia      SET NOT NULL, ADD PRIMARY KEY (id_materia);
ALTER TABLE turmas                 ALTER COLUMN id_turma        SET NOT NULL, ADD PRIMARY KEY (id_turma);
ALTER TABLE alunos                 ALTER COLUMN id_aluno        SET NOT NULL, ADD PRIMARY KEY (id_aluno);
ALTER TABLE socioeconomico         ALTER COLUMN id_aluno        SET NOT NULL, ADD PRIMARY KEY (id_aluno);
ALTER TABLE matriculas             ALTER COLUMN id_matricula    SET NOT NULL, ADD PRIMARY KEY (id_matricula);
ALTER TABLE avaliacoes_risco       ALTER COLUMN id_avaliacao    SET NOT NULL, ADD PRIMARY KEY (id_avaliacao);
ALTER TABLE regras_risco           ALTER COLUMN id_regra        SET NOT NULL, ADD PRIMARY KEY (id_regra);
ALTER TABLE indicadores_academicos ALTER COLUMN id_aluno        SET NOT NULL,
                                   ALTER COLUMN periodo_letivo  SET NOT NULL,
                                   ADD PRIMARY KEY (id_aluno, periodo_letivo);

ALTER TABLE matriculas ALTER COLUMN id_aluno SET NOT NULL, ALTER COLUMN id_turma SET NOT NULL,
                       ADD CONSTRAINT uq_matricula_aluno_turma UNIQUE (id_aluno, id_turma);

ALTER TABLE cursos                 ADD FOREIGN KEY (id_universidade) REFERENCES universidades(id_universidade);
ALTER TABLE materias               ADD FOREIGN KEY (id_curso)        REFERENCES cursos(id_curso);
ALTER TABLE turmas                 ADD FOREIGN KEY (id_materia)      REFERENCES materias(id_materia),
                                   ADD FOREIGN KEY (id_professor)    REFERENCES professores(id_professor);
ALTER TABLE alunos                 ADD FOREIGN KEY (id_curso)        REFERENCES cursos(id_curso);
ALTER TABLE socioeconomico         ADD FOREIGN KEY (id_aluno)        REFERENCES alunos(id_aluno);
ALTER TABLE indicadores_academicos ADD FOREIGN KEY (id_aluno)        REFERENCES alunos(id_aluno);
ALTER TABLE matriculas             ADD FOREIGN KEY (id_aluno)        REFERENCES alunos(id_aluno),
                                   ADD FOREIGN KEY (id_turma)        REFERENCES turmas(id_turma);
ALTER TABLE avaliacoes_risco       ADD FOREIGN KEY (id_aluno)        REFERENCES alunos(id_aluno);

ALTER TABLE avaliacoes_risco ALTER COLUMN data_avaliacao TYPE DATE USING data_avaliacao::date;
ALTER TABLE professores      ALTER COLUMN data_admissao  TYPE DATE USING data_admissao::date;

CREATE TABLE IF NOT EXISTS b1_notas_originais (
    id_matricula VARCHAR(255) PRIMARY KEY REFERENCES matriculas(id_matricula),
    va1 NUMERIC, va2 NUMERIC, va3 NUMERIC, nota_final NUMERIC,
    copiado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE b1_notas_originais IS
    'Notas como vieram do dump do B1 (escala 0 a 100), antes da conversao para 0 a 10.';

INSERT INTO b1_notas_originais (id_matricula, va1, va2, va3, nota_final)
SELECT id_matricula, va1, va2, va3, nota_final FROM matriculas
ON CONFLICT (id_matricula) DO NOTHING;

UPDATE matriculas
   SET va1 = round(va1 / 10, 2), va2 = round(va2 / 10, 2), va3 = round(va3 / 10, 2),
       nota_final = round(nota_final / 10, 2)
 WHERE EXISTS (SELECT 1 FROM matriculas WHERE GREATEST(va1, va2, va3, nota_final) > 10);

ALTER TABLE matriculas
    ADD CONSTRAINT ck_matriculas_notas CHECK (
        (va1 IS NULL OR va1 BETWEEN 0 AND 10) AND (va2 IS NULL OR va2 BETWEEN 0 AND 10) AND
        (va3 IS NULL OR va3 BETWEEN 0 AND 10) AND (nota_final IS NULL OR nota_final BETWEEN 0 AND 10)),
    ADD CONSTRAINT ck_matriculas_frequencia CHECK (frequencia_pct IS NULL OR frequencia_pct BETWEEN 0 AND 100),
    ADD CONSTRAINT ck_matriculas_situacao CHECK (situacao IS NULL OR situacao IN ('Aprovado', 'Reprovado', 'Cursando'));

ALTER TABLE indicadores_academicos
    ADD CONSTRAINT ck_ind_frequencia CHECK (frequencia_pct IS NULL OR frequencia_pct BETWEEN 0 AND 100),
    ADD CONSTRAINT ck_ind_medias CHECK (
        (media_atual IS NULL OR media_atual BETWEEN 0 AND 10) AND
        (media_semestre_anterior IS NULL OR media_semestre_anterior BETWEEN 0 AND 10)),
    ADD CONSTRAINT ck_ind_contagens CHECK (
        (faltas_total IS NULL OR faltas_total >= 0) AND
        (disciplinas_reprovadas_historico IS NULL OR disciplinas_reprovadas_historico >= 0) AND
        (atividades_pendentes IS NULL OR atividades_pendentes >= 0));

ALTER TABLE socioeconomico
    ADD CONSTRAINT ck_socio_valores CHECK (
        (renda_familiar_mensal IS NULL OR renda_familiar_mensal >= 0) AND
        (renda_per_capita IS NULL OR renda_per_capita >= 0) AND
        (horas_trabalho_dia IS NULL OR horas_trabalho_dia BETWEEN 0 AND 24) AND
        (tempo_deslocamento_min IS NULL OR tempo_deslocamento_min BETWEEN 0 AND 1440));

ALTER TABLE alunos
    ADD CONSTRAINT ck_alunos_semestre CHECK (semestre_atual IS NULL OR semestre_atual BETWEEN 1 AND 20),
    ADD CONSTRAINT ck_alunos_idade CHECK (idade IS NULL OR idade BETWEEN 10 AND 120);

ALTER TABLE avaliacoes_risco
    ADD CONSTRAINT ck_avaliacoes_pct CHECK (risco_evasao_pct IS NULL OR risco_evasao_pct BETWEEN 0 AND 100);

CREATE TABLE IF NOT EXISTS apoio_aluno (
    id_aluno       VARCHAR(255) PRIMARY KEY REFERENCES alunos(id_aluno),
    dados_cifrados TEXT        NOT NULL CHECK (dados_cifrados LIKE 'gAAAAA%'),
    atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE apoio_aluno IS
    'Apoio psicossocial e acessibilidade (LGPD art. 11). Cifrado com APOIO_CHAVE, que fica fora do banco.';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mufasa_dono') THEN
        CREATE ROLE mufasa_dono NOLOGIN;
    END IF;
END $$;

GRANT USAGE, CREATE ON SCHEMA public TO mufasa_dono;

DO $$
DECLARE
    tabela TEXT;
BEGIN
    -- Lista fixa: nenhum nome vem de fora.
    FOREACH tabela IN ARRAY ARRAY['universidades', 'cursos', 'professores', 'materias', 'turmas', 'alunos',
                                  'socioeconomico', 'matriculas', 'avaliacoes_risco', 'regras_risco',
                                  'indicadores_academicos', 'b1_notas_originais', 'apoio_aluno']
    LOOP
        EXECUTE format('ALTER TABLE %I OWNER TO mufasa_dono', tabela);
    END LOOP;
END $$;

COMMIT;
