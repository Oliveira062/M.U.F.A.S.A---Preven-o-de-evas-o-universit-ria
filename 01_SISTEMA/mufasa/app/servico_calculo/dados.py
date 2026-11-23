import math
from datetime import date
from decimal import Decimal

from sqlalchemy.engine import Connection

from app.calculo.indicadores import calcular_media_ponderada
from app.calculo.parametros import Parametros
from app.calculo.score import risco_por_nota
from app.servico_calculo import consultas_calculo as sql

DIAS_UTEIS_SEMANA = 5
MAIORIDADE = 18


def _numero(valor, minimo: float, maximo: float) -> float | None:
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero) or numero < minimo or numero > maximo:
        return None
    return numero


def _nao_trabalha(valor) -> bool | None:
    if valor is None:
        return None
    texto = str(valor).strip().lower()
    return texto in ("", "n", "false", "0") or texto.startswith(("não", "nao"))


def _sim(valor) -> bool:
    return valor is not None and str(valor).strip().lower() in ("sim", "s", "true", "1")


def _periodo_em_andamento(inicio, fim, hoje: date) -> bool:
    if inicio is None:
        return True
    inicio = inicio if isinstance(inicio, date) else date.fromisoformat(str(inicio))
    fim = None if fim is None else fim if isinstance(fim, date) else date.fromisoformat(str(fim))
    return inicio <= hoje and (fim is None or hoje <= fim)


def montar_dados(conexao: Connection, id_aluno: str, p: Parametros, hoje: date) -> tuple[dict, dict]:
    aluno = conexao.execute(sql.ALUNO, {"id_aluno": id_aluno}).mappings().first()
    if aluno is None:
        raise LookupError("aluno inexistente")
    linhas = conexao.execute(sql.DISCIPLINAS_DO_PERIODO, {"id_aluno": id_aluno}).mappings().all()
    ind = conexao.execute(sql.INDICADORES, {"id_aluno": id_aluno}).mappings().first() or {}
    soc = conexao.execute(sql.SOCIOECONOMICO, {"id_aluno": id_aluno}).mappings().first() or {}

    periodo = linhas[0]["periodo_letivo"] if linhas else None
    atuais = [l for l in linhas if l["periodo_letivo"] == periodo]
    disciplinas = []
    for l in atuais:
        nota = _numero(l["nota_final"], 0, 10)
        disciplinas.append({
            "nome": l["nome"], "carga_horaria": _numero(l["carga_horaria_h"], 1, 2000),
            "nota": nota, "frequencia_pct": _numero(l["frequencia_pct"], 0, 100), "situacao": l["situacao"],
            "i1": risco_por_nota(nota, p),
        })

    com_ch = [d for d in disciplinas if d["carga_horaria"]]
    media = calcular_media_ponderada([(d["nota"], d["carga_horaria"]) for d in com_ch if d["nota"] is not None])
    freq = calcular_media_ponderada([(d["frequencia_pct"], d["carga_horaria"]) for d in com_ch
                                     if d["frequencia_pct"] is not None])

    concluidas = [l for l in linhas if l["situacao"] in ("Aprovado", "Reprovado")]
    reprovadas = sum(1 for l in concluidas if l["situacao"] == "Reprovado")
    taxa = 100.0 * reprovadas / len(concluidas) if concluidas else None

    anterior = _numero(ind.get("media_semestre_anterior"), 0, 10)
    variacao = round(media - anterior, 2) if media is not None and anterior is not None else None

    renda = _numero(soc.get("renda_per_capita"), 0, 10_000_000)
    renda_sm = float(Decimal(str(renda)) / Decimal(str(p["SALARIO_MINIMO"]))) if renda is not None else None

    nao_trabalha = _nao_trabalha(soc.get("trabalha"))
    horas_dia = _numero(soc.get("horas_trabalho_dia"), 0, 24)
    if nao_trabalha:
        horas_semana = 0.0
    elif horas_dia is not None:
        horas_semana = horas_dia * DIAS_UTEIS_SEMANA
    else:
        horas_semana = None

    em_andamento = any(_periodo_em_andamento(l["inicio"], l["fim"], hoje) for l in atuais) if atuais else True

    dados = {
        "matricula": id_aluno,
        "periodo_letivo": periodo,
        "disciplinas": disciplinas,
        "media_ponderada": media,
        "percentual_frequencia": freq,
        "variacao_media": variacao,
        "medias_ultimos_periodos": [m for m in (anterior, media) if m is not None],
        "taxa_reprovacao_pct": taxa,
        "disciplinas_cursadas": len(concluidas),
        "disciplinas_reprovadas": reprovadas,
        "renda_per_capita_sm": renda_sm,
        "auxilio_ativo": _sim(soc.get("auxilio_bolsa")),
        "horas_trabalho_semana": horas_semana,
        "minutos_deslocamento": _numero(soc.get("tempo_deslocamento_min"), 0, 1440),
        "periodo_atual": _numero(aluno["semestre_atual"], 1, 30),
        "turno_noturno": any((l["turno"] or "").lower() == "noturno" for l in atuais),
        "periodo_em_andamento": em_andamento,
    }
    idade = _numero(aluno["idade"], 0, 150)
    contexto = {"id_curso": aluno["id_curso"], "menor_de_idade": idade is not None and idade < MAIORIDADE}
    return dados, contexto
