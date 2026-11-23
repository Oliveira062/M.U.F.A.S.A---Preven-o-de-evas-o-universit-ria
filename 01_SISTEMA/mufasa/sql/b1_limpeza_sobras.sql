BEGIN;

DO $$
DECLARE
    removidas integer;
BEGIN
    DELETE FROM matriculas m
     WHERE m.id_aluno IS NULL
       AND m.id_matricula IS NULL
       AND NOT EXISTS (SELECT 1 FROM turmas t WHERE t.id_turma = m.id_turma);
    GET DIAGNOSTICS removidas = ROW_COUNT;
    IF removidas NOT IN (0, 2000) THEN
        RAISE EXCEPTION 'Esperava 2000 linhas de sobra, encontrei %. Nada foi removido.', removidas;
    END IF;
    RAISE NOTICE 'Linhas de sobra removidas: %', removidas;
END $$;

COMMIT;
