def calcular_faltas_restantes(aulas_previstas: int, faltas: int):
    if aulas_previstas is None or aulas_previstas <= 0 or faltas is None:
        return None
    limite_faltas = int(aulas_previstas * 0.25)
    return max(0, limite_faltas - int(faltas))


def calcular_percentual_frequencia(aulas_realizadas: int, faltas: int):
    if aulas_realizadas is None or aulas_realizadas <= 0:
        return None
    if faltas is None:
        return None
    percentual = (1 - (faltas / aulas_realizadas)) * 100.0
    return round(max(0.0, min(100.0, percentual)), 2)


def calcular_media_ponderada(notas: list[tuple[float, float]]):
    if not notas:
        return None
    soma_pesos = sum(peso for _, peso in notas)
    if soma_pesos == 0:
        return None
    soma = sum(nota * peso for nota, peso in notas)
    return round(soma / soma_pesos, 3)


def calcular_taxa_reprovacao(disciplinas_cursadas: int, reprovacoes: int):
    if disciplinas_cursadas is None or disciplinas_cursadas <= 0:
        return None
    if reprovacoes is None:
        return None
    return round(reprovacoes / disciplinas_cursadas, 3)


def calcular_completude_cadastro(campos_preenchidos: int, campos_totais: int) -> float:
    if campos_totais is None or campos_totais <= 0:
        return 0.0
    return round(campos_preenchidos / campos_totais, 4)
