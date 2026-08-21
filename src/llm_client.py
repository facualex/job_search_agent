"""
Capa de abstracción sobre el proveedor de LLM. Expone una única función,
`complete`, que devuelve texto plano sin importar qué proveedor esté detrás.

Proveedor se elige con la variable de entorno LLM_PROVIDER (default: "anthropic").
Cada proveedor usa su SDK nativo (no una capa de compatibilidad OpenAI de terceros),
para mayor confiabilidad en un cron desatendido.
"""
import os

PROVIDERS = {
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-5",
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
}


def _get_provider():
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    if provider not in PROVIDERS:
        raise ValueError(
            f"LLM_PROVIDER desconocido: '{provider}'. Opciones válidas: {', '.join(PROVIDERS)}"
        )
    return provider


def _get_model(provider: str) -> str:
    return os.environ.get("LLM_MODEL", PROVIDERS[provider]["default_model"])


def _complete_anthropic(prompt: str, max_tokens: int, model: str) -> str:
    import anthropic

    api_key = os.environ[PROVIDERS["anthropic"]["api_key_env"]]
    client = anthropic.Anthropic(api_key=api_key)

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )

    if os.environ.get("CURATE_DEBUG"):
        print(f"[llm_client] anthropic stop_reason={resp.stop_reason} | bloques={len(resp.content)}")

    return "".join(block.text for block in resp.content if hasattr(block, "text")).strip()


def _complete_deepseek(prompt: str, max_tokens: int, model: str) -> str:
    import openai

    api_key = os.environ[PROVIDERS["deepseek"]["api_key_env"]]
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    if os.environ.get("CURATE_DEBUG"):
        print(f"[llm_client] deepseek finish_reason={resp.choices[0].finish_reason}")

    return (resp.choices[0].message.content or "").strip()


_HANDLERS = {
    "anthropic": _complete_anthropic,
    "deepseek": _complete_deepseek,
}


def complete(prompt: str, max_tokens: int = 4000) -> str:
    """Envía `prompt` al proveedor configurado y devuelve la respuesta como texto plano."""
    provider = _get_provider()
    model = _get_model(provider)

    if os.environ.get("CURATE_DEBUG"):
        print(f"[llm_client] usando proveedor={provider} modelo={model}")

    return _HANDLERS[provider](prompt, max_tokens, model)
