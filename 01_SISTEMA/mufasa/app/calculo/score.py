import math
from dataclasses import dataclass

from app.calculo.parametros import PADRAO, PESOS_POR_FATOR, Parametros

VERSAO_MODELO = "deterministico-v1.1"
VERSAO_CODIGO = "3.0"

FATORES = tuple(PESOS_POR_FATOR)
ID_FATOR = {f: f"I{i}" for i, f in enumerate(FATORES, start=1)}

ROTULOS = {
    "notas": "desempenho acadêmico",
    "frequencia": "frequência",
    "reprovacao": "histórico de reprovações",
    "engajamento_ava": "participação no ambiente virtual",
    "financeiro": "situação financeira",
    "trabalho": "jornada de trabalho",
    "deslocamento": "tempo de deslocamento",
    "saude_mental": "saúde mental",
    "saude_fisica": "saúde física",
    "moradia": "situação de moradia",
    "dependentes": "dependentes sob cuidado",
}

NOMES_NIVEL = {"BAIXO": "baixo", "MODERADO": "moderado", "ALTO": "alto", "CRITICO": "crítico",
               "INDETERMINADO": "indeterminado"}
ORDEM_NIVEL = {"INDETERMINADO": -1, "BAIXO": 0, "MODERADO": 1, "ALTO": 2, "CRITICO": 3}

ACIONAVEL = {"notas": True, "frequencia": True, "reprovacao": True, "engajamento_ava": True,
             "financeiro": True, "trabalho": False, "deslocamento": True, "saude_mental": True,
             "saude_fisica": False, "moradia": True, "dependentes": True}

RECOMENDACAO_NIVEL = {
    "BAIXO": "Acompanhamento regular.",
    "MODERADO": "Alerta preventivo: lista de observação, com o docente notificado.",
    "ALTO": "Intervenção recomendada: alerta na fila, com responsável designado, em até 5 dias úteis.",
    "CRITICO": "Busca ativa imediata, com acionamento do núcleo de apoio, em até 48 horas.",
    "INDETERMINADO": "Tarefa de correção de dados: completar o cadastro antes de classificar.",
}

AVISO_PESOS = ("Score calculado por modelo determinístico de pesos heurísticos, versão 1.1. Não constitui "
               "previsão individual nem decisão automatizada.")


def _valido(valor, minimo: float, maximo: float):
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero) or numero < minimo or numero > maximo:
        return None
    return numero


def arredondar(valor: float) -> int:
    return int(math.floor(valor + 0.5))


def _num(valor: float, casas: int = 1, fixo: bool = False) -> str:
    texto = f"{valor:.{casas}f}".replace(".", ",")
    if casas and not fixo and texto.endswith("," + "0" * casas):
        texto = texto[:-(casas + 1)]
    return texto


def _reta(trechos, x):
    for inicio, fim, p0, p1 in trechos:
        if inicio <= x < fim:
            return p0 + (p1 - p0) * (x - inicio) / (fim - inicio)
    return None


def classificar_nivel_risco(score, p: Parametros = PADRAO) -> str:
    if score is None:
        return "INDETERMINADO"
    if score <= p["CORTE_BAIXO"]:
        return "BAIXO"
    if score <= p["CORTE_MODERADO"]:
        return "MODERADO"
    if score <= p["CORTE_ALTO"]:
        return "ALTO"
    return "CRITICO"


def risco_por_nota(media, p: Parametros = PADRAO):
    m = _valido(media, 0.0, 10.0)
    if m is None:
        return None
    conf, minima, crit = p["NOTA_CONFORTAVEL"], p["NOTA_MINIMA"], p["NOTA_CRITICA"]
    if m >= conf:
        return 0.0
    return round(_reta(((minima, conf, 40.0, 0.0), (crit, minima, 80.0, 40.0), (0.0, crit, 100.0, 80.0)), m), 2)


def risco_por_frequencia(frequencia, p: Parametros = PADRAO):
    f = _valido(frequencia, 0.0, 100.0)
    if f is None:
        return None
    conf, minima, crit = p["FREQUENCIA_CONFORTAVEL"], p["FREQUENCIA_MINIMA"], p["FREQUENCIA_CRITICA"]
    if f >= conf:
        return 0.0
    return round(_reta(((minima, conf, 40.0, 0.0), (crit, minima, 80.0, 40.0), (0.0, crit, 100.0, 80.0)), f), 2)


def risco_por_reprovacao(taxa_pct, reprovou_pre_requisito: bool = False, terceira_tentativa: bool = False):
    tr = _valido(taxa_pct, 0.0, 100.0)
    if tr is None:
        return None
    if tr == 0:
        base = 0.0
    elif tr <= 15:
        base = 25.0
    elif tr <= 30:
        base = 50.0
    elif tr <= 50:
        base = 75.0
    else:
        base = 100.0
    base += 15.0 if reprovou_pre_requisito else 0.0
    base += 20.0 if terceira_tentativa else 0.0
    return min(100.0, base)


def risco_por_engajamento_ava(engajamento=None, taxa_entrega=None, dias_sem_acesso=None,
                              p: Parametros = PADRAO):
    eng = _valido(engajamento, 0.0, 1000.0)
    ent = _valido(taxa_entrega, 0.0, 1.0)
    dias = _valido(dias_sem_acesso, 0.0, 10_000.0)
    if eng is None and ent is None and dias is None:
        return None
    if (dias is not None and dias > p["AVA_DIAS_SEM_ACESSO"]) or (ent is not None and ent < 0.40):
        return 100.0
    if (eng is not None and eng < 0.3) or (ent is not None and ent < 0.70):
        return 65.0
    if (eng is not None and eng < 0.7) or (ent is not None and ent < 0.90):
        return 35.0
    return 0.0


def risco_por_renda_per_capita(renda_sm, auxilio_ativo: bool = False, mensalidades_atraso: int = 0,
                               cadunico_sem_renda: bool = False, p: Parametros = PADRAO):
    r = _valido(renda_sm, 0.0, 1000.0)
    if r is None:
        if not cadunico_sem_renda:
            return None
        base = 85.0
    elif r <= p["RENDA_EXTREMA"]:
        base = 100.0
    elif r <= p["RENDA_VULNERAVEL"]:
        base = 85.0
    elif r < p["RENDA_UM_SM"]:
        base = 60.0
    elif r <= p["RENDA_AUXILIO"]:
        base = 30.0
    else:
        base = 0.0
    atrasos = int(_valido(mensalidades_atraso, 0, 1000) or 0)
    base += 35.0 if atrasos >= 2 else 20.0 if atrasos == 1 else 0.0
    base -= 20.0 if auxilio_ativo else 0.0
    return max(0.0, min(100.0, base))


def risco_por_trabalho(horas_semana, mesmo_turno: bool = False, estagio_na_area: bool = False,
                       informal: bool = False, p: Parametros = PADRAO):
    h = _valido(horas_semana, 0.0, 168.0)
    if h is None:
        return None
    if h <= 0:
        return 0.0
    if mesmo_turno:
        return 100.0
    if h <= p["JORNADA_LIMITE"]:
        base = 20.0
    elif h <= 30:
        base = 50.0
    elif h <= 40:
        base = 75.0
    else:
        base = 100.0
    base -= 15.0 if estagio_na_area else 0.0
    base += 10.0 if informal else 0.0
    return max(0.0, min(100.0, base))


def risco_por_deslocamento(minutos, dois_ou_mais_onibus: bool = False, p: Parametros = PADRAO):
    m = _valido(minutos, 0.0, 1440.0)
    if m is None:
        return None
    if m <= 20:
        base = 0.0
    elif m <= 40:
        base = 25.0
    elif m <= p["DESLOCAMENTO_LIMITE"]:
        base = 50.0
    elif m <= 90:
        base = 75.0
    else:
        base = 100.0
    return min(100.0, base + (15.0 if dois_ou_mais_onibus else 0.0))


SAUDE_MENTAL = {"NENHUMA": 0.0, "COM_ACOMPANHAMENTO": 40.0, "SEM_ACOMPANHAMENTO": 70.0, "AFASTAMENTO": 90.0}
SAUDE_FISICA = {"NENHUMA": 0.0, "CONTROLADA": 30.0, "ATESTADOS": 70.0, "AFASTAMENTO": 90.0}
MORADIA = {"ESTAVEL": 0.0, "ALUGUEL_COMPROMETIDO": 35.0, "MUDOU_SEM_REDE": 55.0,
           "MUDANCA_NO_PERIODO": 60.0, "PRECARIA": 100.0}
DESCRICAO_CATEGORIA = {
    "NENHUMA": "nenhuma dificuldade declarada", "COM_ACOMPANHAMENTO": "dificuldade declarada, com acompanhamento",
    "SEM_ACOMPANHAMENTO": "dificuldade declarada sem acompanhamento ou pedido de apoio não atendido",
    "AFASTAMENTO": "afastamento formal no período", "CONTROLADA": "condição controlada, com acompanhamento",
    "ATESTADOS": "condição que gerou 3 ou mais atestados no período", "ESTAVEL": "moradia estável",
    "ALUGUEL_COMPROMETIDO": "aluguel com comprometimento da renda", "MUDOU_SEM_REDE": "mudou de cidade sem rede de apoio",
    "MUDANCA_NO_PERIODO": "mudança de residência no período", "PRECARIA": "moradia precária ou insegura",
}


def risco_por_categoria(tabela: dict, categoria):
    return tabela.get(categoria) if isinstance(categoria, str) else None


def risco_por_dependentes(quantidade, cuidado_continuo: bool = False):
    q = _valido(quantidade, 0.0, 50.0)
    if q is None:
        return None
    if q <= 0:
        return 0.0
    if cuidado_continuo:
        return 100.0
    return 40.0 if q < 2 else 70.0


@dataclass
class Fator:
    fator: str
    valor_bruto: float | None
    unidade: str
    pontuacao: float
    peso: float
    explicacao: str


def _fatores(d: dict, p: Parametros) -> dict[str, Fator]:
    fatores: dict[str, Fator] = {}

    def add(nome, bruto, unidade, pontos, frase):
        if pontos is not None:
            fatores[nome] = Fator(nome, bruto, unidade, round(pontos, 2), p.peso(nome), frase)

    media = _valido(d.get("media_ponderada"), 0, 10)
    pontos = risco_por_nota(media, p)
    if pontos is not None:
        minima = p["NOTA_MINIMA"]
        if media < minima:
            frase = (f"A média ponderada de {_num(media, fixo=True)} está {_num(minima - media, fixo=True)} "
                     f"ponto(s) abaixo da nota mínima ({_num(minima, fixo=True)}).")
        elif media < p["NOTA_CONFORTAVEL"]:
            frase = (f"A média ponderada de {_num(media, fixo=True)} está acima da nota mínima "
                     f"({_num(minima, fixo=True)}), mas abaixo de {_num(p['NOTA_CONFORTAVEL'], fixo=True)}.")
        else:
            frase = f"A média ponderada de {_num(media, fixo=True)} não indica risco."
        variacao = _valido(d.get("variacao_media"), -10, 10)
        if variacao is not None and variacao < 0:
            frase = frase[:-1] + f", com queda de {_num(-variacao, fixo=True)} ponto(s) em relação ao período anterior."
        add("notas", media, "média 0-10", pontos, frase)

    freq = _valido(d.get("percentual_frequencia"), 0, 100)
    pontos = risco_por_frequencia(freq, p)
    if pontos is not None:
        minima = p["FREQUENCIA_MINIMA"]
        if freq < minima:
            frase = f"A frequência de {_num(freq)}% está abaixo do mínimo de {_num(minima, 0)}%."
        elif freq < p["FREQUENCIA_CONFORTAVEL"]:
            frase = (f"A frequência de {_num(freq)}% está acima do mínimo de {_num(minima, 0)}%, mas abaixo "
                     f"de {_num(p['FREQUENCIA_CONFORTAVEL'], 0)}%.")
        else:
            frase = f"A frequência de {_num(freq)}% não indica risco."
        add("frequencia", freq, "%", pontos, frase)

    tr = _valido(d.get("taxa_reprovacao_pct"), 0, 100)
    pontos = risco_por_reprovacao(tr, bool(d.get("reprovou_pre_requisito")), bool(d.get("terceira_tentativa")))
    if pontos is not None:
        cursadas, reprovadas = d.get("disciplinas_cursadas"), d.get("disciplinas_reprovadas")
        detalhe = f" ({reprovadas} de {cursadas} disciplinas cursadas)" if cursadas and reprovadas is not None else ""
        add("reprovacao", tr, "%", pontos, f"Taxa de reprovação de {_num(tr)}%{detalhe}.")

    pontos = risco_por_engajamento_ava(d.get("engajamento_ava"), d.get("taxa_entrega_ava"),
                                       d.get("dias_sem_acesso_ava"), p)
    if pontos is not None:
        dias = _valido(d.get("dias_sem_acesso_ava"), 0, 10_000)
        if dias is not None and dias > p["AVA_DIAS_SEM_ACESSO"]:
            frase = f"Sem acesso ao ambiente virtual há {int(dias)} dias."
        elif pontos:
            frase = "Participação no ambiente virtual abaixo do esperado."
        else:
            frase = "Participação no ambiente virtual dentro do esperado."
        add("engajamento_ava", d.get("engajamento_ava"), "acessos por dia letivo", pontos, frase)

    renda = _valido(d.get("renda_per_capita_sm"), 0, 1000)
    pontos = risco_por_renda_per_capita(renda, bool(d.get("auxilio_ativo")), d.get("mensalidades_atraso") or 0,
                                        bool(d.get("cadunico_sem_renda")), p)
    if pontos is not None:
        frase = (f"Renda de {_num(renda, 2)} salário mínimo por pessoa" if renda is not None
                 else "Inscrição no CadÚnico sem renda informada")
        frase += "; há auxílio de permanência ativo." if d.get("auxilio_ativo") else "."
        add("financeiro", renda, "salário mínimo por pessoa", pontos, frase)

    horas = _valido(d.get("horas_trabalho_semana"), 0, 168)
    pontos = risco_por_trabalho(horas, bool(d.get("trabalho_mesmo_turno")), bool(d.get("estagio_na_area")),
                                bool(d.get("trabalho_informal")), p)
    if pontos is not None:
        limite = p["JORNADA_LIMITE"]
        if horas == 0:
            frase = "Não trabalha."
        elif d.get("trabalho_mesmo_turno"):
            frase = f"Jornada de {_num(horas, 0)} horas semanais no mesmo turno das aulas."
        elif horas > limite:
            frase = (f"Jornada de {_num(horas, 0)} horas semanais, acima do limite de {_num(limite, 0)} horas "
                     "considerado compatível com a rotina de estudos.")
        else:
            frase = f"Jornada de {_num(horas, 0)} horas semanais, dentro do limite de {_num(limite, 0)} horas."
        add("trabalho", horas, "h/semana", pontos, frase)

    minutos = _valido(d.get("minutos_deslocamento"), 0, 1440)
    pontos = risco_por_deslocamento(minutos, bool(d.get("dois_ou_mais_onibus")), p)
    if pontos is not None:
        limite = p["DESLOCAMENTO_LIMITE"]
        comparacao = "acima" if minutos > limite else "dentro"
        add("deslocamento", minutos, "minutos por trajeto", pontos,
            f"Deslocamento de {_num(minutos, 0)} minutos por trajeto, {comparacao} do limite de "
            f"{_num(limite, 0)} minutos.")

    for nome, tabela, rotulo in (("saude_mental", SAUDE_MENTAL, "Saúde mental"),
                                 ("saude_fisica", SAUDE_FISICA, "Saúde física"),
                                 ("moradia", MORADIA, "Moradia")):
        categoria = d.get(nome)
        add(nome, None, "categoria declarada", risco_por_categoria(tabela, categoria),
            f"{rotulo}: {DESCRICAO_CATEGORIA.get(categoria, '')}.")

    deps = _valido(d.get("qtd_dependentes"), 0, 50)
    pontos = risco_por_dependentes(deps, bool(d.get("dependente_cuidado_continuo")))
    if pontos is not None:
        add("dependentes", deps, "dependentes", pontos,
            "Nenhum dependente sob cuidado." if deps == 0 else f"{_num(deps, 0)} dependente(s) sob cuidado.")

    return fatores


def _modificadores(d: dict, fatores: dict[str, Fator]) -> list[dict]:
    mods = []
    variacao = _valido(d.get("variacao_media"), -10, 10)
    financeiro = fatores.get("financeiro")
    if financeiro and financeiro.pontuacao >= 60 and variacao is not None and variacao <= -1.5:
        mods.append({"id": "M1", "descricao": f"Situação financeira com pontuação {_num(financeiro.pontuacao, 0)} "
                     f"e queda de {_num(-variacao)} ponto(s) na média", "delta": 10})
    periodo = _valido(d.get("periodo_atual"), 1, 30)
    if periodo is not None and periodo <= 2:
        mods.append({"id": "M2", "descricao": f"Aluno no {int(periodo)}º período", "delta": 8})
    deslocamento = fatores.get("deslocamento")
    if d.get("turno_noturno") and deslocamento and deslocamento.pontuacao >= 75:
        mods.append({"id": "M3", "descricao": "Turno noturno com deslocamento de "
                     f"{_num(deslocamento.valor_bruto, 0)} minutos por trajeto", "delta": 7})
    medias = [float(m) for m in (d.get("medias_ultimos_periodos") or []) if _valido(m, 0, 10) is not None]
    if len(medias) >= 3:
        a, b, c = medias[-3:]
        if a > b > c:
            mods.append({"id": "M4", "descricao": "Média em queda por dois períodos seguidos", "delta": 10})
        freq = _valido(d.get("percentual_frequencia"), 0, 100)
        if a < b < c and freq is not None and freq >= 85:
            mods.append({"id": "M5", "descricao": "Média em melhora por dois períodos seguidos, com frequência "
                         f"de {_num(freq)}%", "delta": -8})
    return mods


def _sobreposicoes(d: dict, p: Parametros) -> list[dict]:
    regras = []
    minima = p["FREQUENCIA_MINIMA"]
    if d.get("periodo_em_andamento", True):
        disciplinas = d.get("disciplinas") or []
        abaixo = [x for x in disciplinas
                  if _valido(x.get("frequencia_pct"), 0, 100) is not None and float(x["frequencia_pct"]) < minima]
        if abaixo:
            pior = min(abaixo, key=lambda x: float(x["frequencia_pct"]))
            extra = f" e em mais {len(abaixo) - 1} disciplina(s)" if len(abaixo) > 1 else ""
            regras.append({"id": "S1", "nivel": "ALTO", "motivo": (
                f"S1: frequência de {_num(float(pior['frequencia_pct']), 0)}% em "
                f"{pior.get('nome') or 'uma disciplina'}{extra}, abaixo do mínimo de {_num(minima, 0)}%")})
        elif not disciplinas:
            freq = _valido(d.get("percentual_frequencia"), 0, 100)
            if freq is not None and freq < minima:
                regras.append({"id": "S1", "nivel": "ALTO", "motivo": (
                    f"S1: frequência de {_num(freq, 0)}%, abaixo do mínimo de {_num(minima, 0)}%")})
    dias = _valido(d.get("dias_sem_presenca"), 0, 10_000)
    if dias is not None and dias >= 15:
        regras.append({"id": "S2", "nivel": "CRITICO", "motivo": (
            f"S2: {int(dias)} dias corridos sem presença em todas as disciplinas")})
    if d.get("sem_lancamento_30_dias"):
        regras.append({"id": "S3", "nivel": "CRITICO", "motivo": (
            "S3: período iniciado há mais de 30 dias sem nenhuma nota ou frequência lançada")})
    if d.get("trancamento_solicitado"):
        regras.append({"id": "S4", "nivel": "CRITICO", "motivo": "S4: solicitação de trancamento registrada"})
    return regras


def _ordenar(fatores) -> list[Fator]:
    return sorted(fatores, key=lambda f: (-(f.peso * f.pontuacao), FATORES.index(f.fator)))


def _fator_json(f: Fator, peso_disponivel: float, soma_pontos: float) -> dict:
    pontos = f.peso * f.pontuacao / peso_disponivel if peso_disponivel else 0.0
    return {
        "id": ID_FATOR[f.fator], "fator": f.fator, "nome": ROTULOS[f.fator],
        "valor_bruto": f.valor_bruto, "unidade": f.unidade, "pontuacao": f.pontuacao,
        "peso": f.peso, "contribuicao_pontos": round(pontos, 1),
        "contribuicao_pct": round(100 * pontos / soma_pontos, 1) if soma_pontos else 0.0,
        "acionavel": ACIONAVEL[f.fator], "explicacao": f.explicacao,
    }


def calcular_score_aluno(dados_aluno: dict, parametros: Parametros = PADRAO) -> dict:
    p = parametros
    fatores = _fatores(dados_aluno, p)
    peso_disponivel = sum(f.peso for f in fatores.values())
    completude = round(peso_disponivel, 4)
    sobreposicoes = _sobreposicoes(dados_aluno, p)
    ordenados = _ordenar(fatores.values())
    soma = sum(f.peso * f.pontuacao for f in ordenados) / peso_disponivel if peso_disponivel else 0.0

    resultado = {
        "matricula": dados_aluno.get("matricula"),
        "completude": completude,
        "parcial": False,
        "versao_modelo": VERSAO_MODELO,
        "versao_parametros": p.rotulo_versao,
        "aviso_pesos": AVISO_PESOS,
        "fatores": [_fator_json(f, peso_disponivel, soma) for f in ordenados],
        "detalhamento": {f.fator: f.pontuacao for f in ordenados},
        "sobreposicao_frequencia": any(s["id"] == "S1" for s in sobreposicoes),
        "motivo_sobreposicao": "; ".join(s["motivo"] for s in sobreposicoes) or None,
    }

    if completude * 100 < p["COMPLETUDE_MINIMA"] - 1e-9:
        nivel, origem = "INDETERMINADO", "COMPLETUDE"
        if sobreposicoes:
            nivel, origem = max((s["nivel"] for s in sobreposicoes), key=ORDEM_NIVEL.get), "SOBREPOSICAO"
        return {**resultado, "score": None, "nivel": nivel, "nivel_origem": origem, "fatores_principais": [],
                "modificadores": [], "contribuicoes": {}, "recomendacao": RECOMENDACAO_NIVEL[nivel]}

    modificadores = _modificadores(dados_aluno, fatores)
    score = arredondar(max(0.0, min(100.0, soma + sum(m["delta"] for m in modificadores))))

    nivel = classificar_nivel_risco(score, p)
    parcial = completude * 100 < p["COMPLETUDE_PLENA"] - 1e-9
    origem = "FAIXA"
    if parcial and nivel == "CRITICO":
        nivel, origem = "ALTO", "FAIXA_PARCIAL"
    for regra in sobreposicoes:
        if ORDEM_NIVEL[regra["nivel"]] > ORDEM_NIVEL[nivel]:
            nivel, origem = regra["nivel"], "SOBREPOSICAO"

    principais = [f.fator for i, f in enumerate(ordenados) if (i < 3 and f.pontuacao > 0) or f.pontuacao >= 50]

    return {
        **resultado,
        "score": score,
        "nivel": nivel,
        "nivel_origem": origem,
        "parcial": parcial,
        "fatores_principais": principais,
        "modificadores": modificadores,
        "contribuicoes": {f.fator: round(f.peso * f.pontuacao / peso_disponivel, 1) for f in ordenados},
        "recomendacao": RECOMENDACAO_NIVEL[nivel],
    }


def calcular_tendencia(scores: list) -> str | None:
    serie = [s for s in scores if s is not None]
    if len(serie) < 2:
        return None
    if len(serie) >= 3 and serie[-3] < serie[-2] < serie[-1]:
        return "PIORA_SUSTENTADA"
    if serie[-1] > serie[-2]:
        return "PIORA"
    if serie[-1] < serie[-2]:
        return "MELHORA"
    return "ESTAVEL"


def explicar_score(resultado: dict) -> str:
    nivel = resultado.get("nivel")
    if resultado.get("score") is None:
        if nivel == "INDETERMINADO":
            return (f"Não foi possível calcular: só {arredondar(resultado.get('completude', 0) * 100)}% dos dados "
                    "necessários estão disponíveis, e o mínimo é 40%. Foi aberta uma tarefa de correção de dados.")
        return (f"Nível {NOMES_NIVEL.get(nivel, nivel)} por regra de sobreposição "
                f"({resultado.get('motivo_sobreposicao')}). Os dados disponíveis não bastam para o score.")

    nomes = [ROTULOS.get(f, f) for f in resultado.get("fatores_principais", [])]
    texto = f"Pontuação de risco: {resultado['score']} de 100, nível {NOMES_NIVEL.get(nivel, nivel)}."
    if resultado.get("parcial"):
        texto += f" Score parcial: {arredondar(resultado['completude'] * 100)}% dos dados disponíveis."
    if nomes:
        lista = ", ".join(nomes[:-1]) + " e " + nomes[-1] if len(nomes) > 1 else nomes[0]
        texto += f" Os fatores que mais pesaram foram: {lista}."
    else:
        texto += " Nenhum fator apresentou risco relevante."
    if resultado.get("nivel_origem") == "SOBREPOSICAO":
        texto += f" O nível foi elevado por regra de sobreposição: {resultado['motivo_sobreposicao']}."
    elif resultado.get("nivel_origem") == "FAIXA_PARCIAL":
        texto += " Com dados parciais, o nível Crítico só é atribuído por regra de sobreposição."
    return texto
