from datetime import date, datetime
from enum import Enum
from typing import Annotated

from fastapi import Path, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

PADRAO_MATRICULA = r"^(?:\d{7}|ALU\d{4})$"

Matricula = Annotated[str, Path(pattern=PADRAO_MATRICULA, description="Matricula do aluno (7 digitos)")]


class Fechado(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Perfil(str, Enum):
    ALUNO = "ALUNO"
    DOCENTE = "DOCENTE"
    COORDENACAO = "COORDENACAO"
    NUCLEO_APOIO = "NUCLEO_APOIO"
    FINANCEIRO = "FINANCEIRO"
    DIRECAO = "DIRECAO"
    ADMIN = "ADMIN"
    ENCARREGADO_DADOS = "ENCARREGADO_DADOS"


class PedidoLogin(Fechado):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._@-]+$",
                       description="Matricula, para aluno; login institucional, para os demais perfis")
    senha: str = Field(min_length=1, max_length=72)
    perfil: Perfil = Field(description="Perfil escolhido na tela de login; precisa ser o da conta")

    @field_validator("senha")
    @classmethod
    def _limite_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("senha acima do limite de 72 bytes")
        return v


class RespostaToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em_segundos: int
    perfil: str
    deve_trocar_senha: bool = False
    termo_pendente: bool = False


class Ordem(str, Enum):
    nome = "nome"
    semestre = "semestre"
    matricula = "matricula"
    risco = "risco"


class Nivel(str, Enum):
    BAIXO = "BAIXO"
    MODERADO = "MODERADO"
    ALTO = "ALTO"
    CRITICO = "CRITICO"
    INDETERMINADO = "INDETERMINADO"


class FiltrosLista(Fechado):
    semestre: int | None = Field(default=None, ge=1, le=12)
    nivel: Nivel | None = None
    busca: str | None = Field(default=None, max_length=60)
    ordem: Ordem = Ordem.nome
    limite: int = Field(default=25, ge=1, le=200)
    pagina: int = Field(default=1, ge=1, le=10_000)


def filtros_lista(
    semestre: Annotated[int | None, Query(ge=1, le=12)] = None,
    nivel: Nivel | None = None,
    busca: Annotated[str | None, Query(max_length=60, pattern=r"^[\w .'-]*$")] = None,
    ordem: Ordem = Ordem.nome,
    limite: Annotated[int, Query(ge=1, le=200)] = 25,
    pagina: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> FiltrosLista:
    return FiltrosLista(semestre=semestre, nivel=nivel, busca=busca, ordem=ordem, limite=limite, pagina=pagina)


class AlunoResumo(BaseModel):
    matricula: str
    nome: str
    semestre: int | None
    nivel_risco: str | None
    score: int | None = None


class PaginaAlunos(BaseModel):
    pagina: int
    limite: int
    total: int | None = None
    itens: list[AlunoResumo]


AVISO_METODOLOGICO = (
    "O nível de risco indica que o padrão de indicadores deste estudante se assemelha a padrões que "
    "costumam anteceder a evasão. Não é previsão sobre a pessoa, não é julgamento de esforço ou "
    "capacidade e não pode ser usado em decisão de avaliação, seleção ou concessão de benefício."
)


class AvaliacaoHistorica(BaseModel):
    periodo_letivo: str | None
    tipo: str | None
    data_avaliacao: str | None
    risco_evasao_pct: float | None
    nivel_risco: str | None


class GrupoAgregado(BaseModel):
    semestre: int | None
    nivel_risco: str | None
    total: int


class RespostaAgregados(BaseModel):
    minimo_por_grupo: int
    grupos: list[GrupoAgregado]
    observacao: str = "Grupos com menos alunos que o mínimo foram suprimidos para impedir reidentificação."


class Finalidade(str, Enum):
    DADOS_SAUDE = "DADOS_SAUDE"


class PedidoConsentimento(Fechado):
    finalidade: Finalidade
    concedido: bool
    versao_termo: str = Field(pattern=r"^\d+\.\d+$", max_length=10)


class Consentimento(BaseModel):
    finalidade: str
    concedido: bool
    concedido_por: str
    versao_termo: str
    registrado_em: datetime | str


class TipoSolicitacao(str, Enum):
    CONFIRMACAO_ACESSO = "CONFIRMACAO_ACESSO"
    CORRECAO = "CORRECAO"
    ANONIMIZACAO_ELIMINACAO = "ANONIMIZACAO_ELIMINACAO"
    PORTABILIDADE = "PORTABILIDADE"
    INFORMACAO_COMPARTILHAMENTO = "INFORMACAO_COMPARTILHAMENTO"
    REVOGACAO_CONSENTIMENTO = "REVOGACAO_CONSENTIMENTO"
    REVISAO_DECISAO_AUTOMATIZADA = "REVISAO_DECISAO_AUTOMATIZADA"
    OPOSICAO = "OPOSICAO"


class PedidoSolicitacao(Fechado):
    tipo: TipoSolicitacao
    descricao: str = Field(default="", max_length=1000)


class SolicitacaoRegistrada(BaseModel):
    protocolo_registrado: bool = True
    prazo: str = "Resposta em até 15 dias (LGPD, art. 19, II)."


class Solicitacao(BaseModel):
    id_solicitacao: int
    id_aluno: str
    tipo: str
    situacao: str
    registrada_em: datetime | str


class RegistroAuditoria(BaseModel):
    momento: datetime | str
    id_requisicao: str | None
    id_usuario: int | None
    perfil: str | None
    operacao: str
    recurso: str
    id_aluno_alvo: str | None
    resultado: str


class ResultadoAuditoria(str, Enum):
    PERMITIDO = "PERMITIDO"
    NEGADO = "NEGADO"
    BLOQUEADO = "BLOQUEADO"


class FiltroAuditoria(Fechado):
    matricula: str | None = Field(default=None, pattern=PADRAO_MATRICULA)
    perfil: Perfil | None = None
    resultado: ResultadoAuditoria | None = None
    operacao: str | None = Field(default=None, pattern=r"^[A-Z_]{3,40}$")
    de: datetime | None = None
    ate: datetime | None = None
    limite: int = Field(default=50, ge=1, le=500)
    pagina: int = Field(default=1, ge=1, le=10_000)


def filtro_auditoria(
    matricula: Annotated[str | None, Query(pattern=PADRAO_MATRICULA)] = None,
    perfil: Perfil | None = None,
    resultado: ResultadoAuditoria | None = None,
    operacao: Annotated[str | None, Query(pattern=r"^[A-Z_]{3,40}$")] = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
    pagina: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> FiltroAuditoria:
    return FiltroAuditoria(matricula=matricula, perfil=perfil, resultado=resultado, operacao=operacao,
                           de=de, ate=ate, limite=limite, pagina=pagina)


class FiltroPagina(Fechado):
    limite: int = Field(default=25, ge=1, le=200)
    pagina: int = Field(default=1, ge=1, le=10_000)


def filtro_pagina(
    limite: Annotated[int, Query(ge=1, le=200)] = 25,
    pagina: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> FiltroPagina:
    return FiltroPagina(limite=limite, pagina=pagina)


def converter_data(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)
