import logging

import httpx

from app.chatbot.config_chat import obter_configuracao_chat

log = logging.getLogger("mufasa.chat.ia")

URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"


def completar(mensagens: list[dict], max_tokens: int = 350, temperatura: float = 0.4) -> str | None:
    cfg = obter_configuracao_chat()
    if not cfg.ia_habilitada:
        return None
    try:
        resposta = httpx.post(
            URL_GROQ,
            headers={"Authorization": f"Bearer {cfg.groq_api_key.get_secret_value()}"},
            json={"model": cfg.groq_modelo, "messages": mensagens, "temperature": temperatura,
                  "max_tokens": max_tokens},
            timeout=cfg.groq_timeout_segundos,
        )
        resposta.raise_for_status()
        conteudo = resposta.json()["choices"][0]["message"]["content"]
        return conteudo if isinstance(conteudo, str) else None
    except Exception as exc:
        log.warning("IA indisponivel (%s); usando texto pronto", type(exc).__name__)
        return None
