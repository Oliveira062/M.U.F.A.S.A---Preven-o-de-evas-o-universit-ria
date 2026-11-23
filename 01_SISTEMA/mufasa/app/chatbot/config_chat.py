from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracaoChat(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    chat_database_url: SecretStr | None = None

    groq_api_key: SecretStr | None = None
    groq_modelo: str = "openai/gpt-oss-20b"
    chat_ia_classificar: bool = False
    chat_ia_conversa: bool = True
    groq_timeout_segundos: float = Field(default=4.0, ge=1.0, le=10.0)
    groq_temperatura: float = Field(default=0.7, ge=0.0, le=1.2)

    chat_limite_minuto: int = Field(default=20, ge=1, le=120)
    chat_inatividade_minutos: int = Field(default=120, ge=1, le=1440)
    chat_tamanho_maximo: int = Field(default=500, ge=50, le=2000)

    chat_janela_atendimento: str = "no horário de funcionamento da secretaria acadêmica"

    @property
    def ia_habilitada(self) -> bool:
        return self.groq_api_key is not None and bool(self.groq_api_key.get_secret_value().strip())


@lru_cache
def obter_configuracao_chat() -> ConfiguracaoChat:
    return ConfiguracaoChat()
