from sqlalchemy import text


USUARIO_POR_LOGIN = text("""
    SELECT id_usuario, login, senha_hash, perfil, id_aluno, id_professor, id_curso,
           ativo, falhas_login, bloqueado_ate, demonstracao
      FROM usuarios
     WHERE login = :login
""")

USUARIO_POR_ID = text("""
    SELECT id_usuario, login, perfil, id_aluno, id_professor, id_curso, ativo, nome,
           deve_trocar_senha, termo_versao
      FROM usuarios
     WHERE id_usuario = :id_usuario
""")

REGISTRAR_FALHA_LOGIN = text("""
    UPDATE usuarios
       SET falhas_login = falhas_login + 1,
           bloqueado_ate = CASE WHEN falhas_login + 1 >= :max_falhas
                                THEN :bloquear_ate ELSE bloqueado_ate END
     WHERE id_usuario = :id_usuario
""")

ZERAR_FALHAS_LOGIN = text("""
    UPDATE usuarios
       SET falhas_login = 0, bloqueado_ate = NULL, ultimo_login = :agora
     WHERE id_usuario = :id_usuario
""")

TOKEN_REVOGADO = text("SELECT 1 FROM tokens_revogados WHERE jti = :jti")

REVOGAR_TOKEN = text("""
    INSERT INTO tokens_revogados (jti, expira_em) VALUES (:jti, :expira_em)
""")


ALUNO_DAS_TURMAS_DO_DOCENTE = text("""
    SELECT 1
      FROM matriculas m
      JOIN turmas t ON t.id_turma = m.id_turma
     WHERE m.id_aluno = :id_aluno
       AND t.id_professor = :id_professor
     LIMIT 1
""")

ALUNO_DO_CURSO = text("""
    SELECT 1 FROM alunos WHERE id_aluno = :id_aluno AND id_curso = :id_curso
""")

ALERTA_ABERTO_DO_ALUNO = text("""
    SELECT a.id_alerta, a.id_responsavel, a.nivel, a.situacao, a.prazo_em, s.fatores_principais
      FROM alertas a
      LEFT JOIN vw_score_atual s ON s.id_aluno = a.id_aluno
     WHERE a.id_aluno = :id_aluno AND a.tipo = 'PEDAGOGICO' AND a.situacao <> 'ENCERRADO'
""")

SCORE_ATUAL = text("""
    SELECT id_score, score, nivel, nivel_origem, motivo_sobreposicao, parcial, completude,
           fatores, fatores_principais, modificadores, recomendacoes, recomendacao,
           tendencia, score_anterior, nivel_anterior, versao_modelo, versao_parametros, calculado_em
      FROM vw_score_atual
     WHERE id_aluno = :id_aluno
""")


_LISTA_BASE = """
    SELECT a.id_aluno, a.nome_ficticio, a.semestre_atual, s.nivel, s.score
      FROM alunos a
      LEFT JOIN vw_score_atual s ON s.id_aluno = a.id_aluno
     WHERE (CAST(:semestre AS INTEGER) IS NULL OR a.semestre_atual = :semestre)
       AND (CAST(:nivel AS VARCHAR) IS NULL OR s.nivel = :nivel)
       AND (CAST(:busca AS VARCHAR) IS NULL OR lower(a.nome_ficticio) LIKE :busca OR lower(a.id_aluno) LIKE :busca)
"""

_FILTRO_POR_PERFIL = {
    "DOCENTE": """
       AND EXISTS (SELECT 1 FROM matriculas m JOIN turmas t ON t.id_turma = m.id_turma
                    WHERE m.id_aluno = a.id_aluno AND t.id_professor = :id_professor)
    """,
    "COORDENACAO": "AND a.id_curso = :id_curso",
    "NUCLEO_APOIO": """AND EXISTS (SELECT 1 FROM alertas al WHERE al.id_aluno = a.id_aluno
                                       AND al.situacao <> 'ENCERRADO' AND al.id_responsavel = :id_usuario)""",
}

ORDENACOES = {
    "nome": "ORDER BY a.nome_ficticio, a.id_aluno",
    "semestre": "ORDER BY a.semestre_atual, a.id_aluno",
    "matricula": "ORDER BY a.id_aluno",
    "risco": "ORDER BY s.score DESC NULLS LAST, a.id_aluno",
}


def consulta_total_alunos(perfil: str):
    return text("SELECT count(*) FROM (" + _LISTA_BASE + _FILTRO_POR_PERFIL[perfil] + ") q")


def consulta_lista_alunos(perfil: str, ordem: str):
    return text(
        _LISTA_BASE
        + _FILTRO_POR_PERFIL[perfil]
        + "\n" + ORDENACOES[ordem]
        + "\n LIMIT :limite OFFSET :deslocamento"
    )


ALUNO_BASICO = text("""
    SELECT a.id_aluno, a.nome_ficticio, a.id_curso, c.nome AS curso, a.semestre_atual
      FROM alunos a
      LEFT JOIN cursos c ON c.id_curso = a.id_curso
     WHERE a.id_aluno = :id_aluno
""")


INDICADORES_ATUAIS = text("""
    SELECT periodo_letivo, faltas_total, frequencia_pct, disciplinas_reprovadas_historico,
           atividades_pendentes, media_semestre_anterior, media_atual, tendencia_media
      FROM indicadores_academicos
     WHERE id_aluno = :id_aluno
     ORDER BY periodo_letivo DESC
     LIMIT 1
""")

SOCIOECONOMICO_RESTRITO = text("""
    SELECT renda_per_capita, trabalha, horas_trabalho_dia, tempo_deslocamento_min, auxilio_bolsa
      FROM socioeconomico
     WHERE id_aluno = :id_aluno
""")

SOCIOECONOMICO_PARA_SCORE = text("""
    SELECT renda_per_capita, trabalha, horas_trabalho_dia, tempo_deslocamento_min
      FROM socioeconomico
     WHERE id_aluno = :id_aluno
""")

DADOS_SENSIVEIS_APOIO = text("""
    SELECT dados_cifrados FROM apoio_aluno WHERE id_aluno = :id_aluno
""")

HISTORICO_SCORE = text("""
    SELECT calculado_em, score, nivel, nivel_origem, completude, versao_modelo, versao_parametros
      FROM scores_risco
     WHERE id_aluno = :id_aluno
     ORDER BY calculado_em, id_score
     LIMIT :limite
""")

HISTORICO_RISCO = text("""
    SELECT periodo_letivo, tipo, data_avaliacao, risco_evasao_pct, nivel_risco
      FROM avaliacoes_risco
     WHERE id_aluno = :id_aluno
     ORDER BY data_avaliacao, id_avaliacao
     LIMIT :limite
""")


AGREGADOS_POR_SEMESTRE = text("""
    SELECT a.semestre_atual AS semestre, s.nivel AS nivel_risco, COUNT(*) AS total
      FROM alunos a
      JOIN vw_score_atual s ON s.id_aluno = a.id_aluno
     WHERE (CAST(:id_curso AS VARCHAR) IS NULL OR a.id_curso = :id_curso)
     GROUP BY a.semestre_atual, s.nivel
    HAVING COUNT(*) >= :minimo_grupo
     ORDER BY a.semestre_atual, s.nivel
""")
IDADE_ALUNO = text("SELECT idade FROM alunos WHERE id_aluno = :id_aluno")


CONSENTIMENTOS_DO_ALUNO = text("""
    SELECT finalidade, concedido, concedido_por, versao_termo, registrado_em
      FROM consentimentos
     WHERE id_aluno = :id_aluno
     ORDER BY registrado_em, id_consentimento
""")

REGISTRAR_CONSENTIMENTO = text("""
    INSERT INTO consentimentos
           (id_aluno, finalidade, concedido, concedido_por, versao_termo, registrado_em, id_usuario)
    VALUES (:id_aluno, :finalidade, :concedido, :concedido_por, :versao_termo, :registrado_em, :id_usuario)
""")

MEUS_DADOS_CADASTRO = text("""
    SELECT id_aluno, nome_ficticio, id_curso, semestre_atual, idade, bairro, tipo_ensino_medio
      FROM alunos
     WHERE id_aluno = :id_aluno
""")

MEUS_DADOS_SOCIOECONOMICO = text("""
    SELECT renda_familiar_mensal, moradores_domicilio, renda_per_capita, auxilio_bolsa, trabalha,
           horas_trabalho_dia, horas_estudo_semana, responsabilidades_familiares_h_semana,
           distancia_km, tempo_deslocamento_min, meio_transporte, prouni, fies, desconto_funcionario
      FROM socioeconomico
     WHERE id_aluno = :id_aluno
""")

MEUS_DADOS_MATRICULAS = text("""
    SELECT m.id_turma, mt.nome AS materia, m.nota_final, m.frequencia_pct, m.situacao
      FROM matriculas m
      JOIN turmas t ON t.id_turma = m.id_turma
      JOIN materias mt ON mt.id_materia = t.id_materia
     WHERE m.id_aluno = :id_aluno
     ORDER BY m.id_turma
""")

REGISTRAR_SOLICITACAO_TITULAR = text("""
    INSERT INTO solicitacoes_titular (id_aluno, tipo, descricao, situacao, registrada_em)
    VALUES (:id_aluno, :tipo, :descricao, 'ABERTA', :registrada_em)
""")

LISTAR_SOLICITACOES_TITULAR = text("""
    SELECT id_solicitacao, id_aluno, tipo, situacao, registrada_em
      FROM solicitacoes_titular
     ORDER BY registrada_em DESC, id_solicitacao DESC
     LIMIT :limite OFFSET :deslocamento
""")


REGISTRAR_AUDITORIA = text("""
    INSERT INTO auditoria_acessos
           (momento, id_requisicao, id_usuario, perfil, operacao, recurso, id_aluno_alvo, resultado, origem)
    VALUES (:momento, :id_requisicao, :id_usuario, :perfil, :operacao, :recurso, :id_aluno_alvo, :resultado, :origem)
""")

LISTAR_AUDITORIA = text("""
    SELECT momento, id_requisicao, id_usuario, perfil, operacao, recurso, id_aluno_alvo, resultado
      FROM auditoria_acessos
     WHERE (CAST(:id_aluno AS VARCHAR) IS NULL OR id_aluno_alvo = :id_aluno)
       AND (CAST(:perfil AS VARCHAR) IS NULL OR perfil = :perfil)
       AND (CAST(:resultado AS VARCHAR) IS NULL OR resultado = :resultado)
       AND (CAST(:operacao AS VARCHAR) IS NULL OR operacao = :operacao)
       AND (CAST(:de AS TIMESTAMP) IS NULL OR momento >= :de)
       AND (CAST(:ate AS TIMESTAMP) IS NULL OR momento < :ate)
     ORDER BY momento DESC, id_auditoria DESC
     LIMIT :limite OFFSET :deslocamento
""")
