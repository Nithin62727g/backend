from openai import OpenAI
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Default model priority: try these in order when model=None
# Confirmed working (tested 2026-03-04): google/gemma-3-4b-it:free
QUBRID_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"
OPENROUTER_MODELS_FALLBACK = [
    "google/gemma-3-4b-it:free",          # ✅ Confirmed working
    "meta-llama/llama-3.2-3b-instruct:free",  # Fallback
    "meta-llama/llama-3.3-70b-instruct:free", # Fallback
    "google/gemma-3-12b-it:free",            # Fallback
]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
QUBRID_BASE_URL = "https://platform.qubrid.com/v1"

_openrouter_client: OpenAI = None
_openai_client: OpenAI = None
_qubrid_client: OpenAI = None
_groq_client: OpenAI = None
_groq_fallback_client: OpenAI = None

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


def init_ai_client():
    global _openrouter_client, _openai_client, _qubrid_client, _groq_client

    # Initialise OpenRouter client
    if settings.OPENROUTER_API_KEY:
        _openrouter_client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://masterai.app",
                "X-Title": "MasterAI Backend",
            }
        )
        logger.info("✅ Initialized OpenRouter AI Client")
    else:
        logger.warning("⚠️  OPENROUTER_API_KEY not set — OpenRouter endpoints disabled")

    # Initialise native OpenAI client
    if settings.OPENAI_API_KEY:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("✅ Initialized OpenAI Direct Client (GPT-4o, etc.)")
    else:
        logger.warning("⚠️  OPENAI_API_KEY not set — direct OpenAI endpoints disabled")

    # Initialize Qubrid AI client
    if settings.QUBRID_API_KEY:
        _qubrid_client = OpenAI(
            api_key=settings.QUBRID_API_KEY,
            base_url=QUBRID_BASE_URL
        )
        logger.info("✅ Initialized Qubrid AI Client")
    else:
        logger.warning("⚠️  QUBRID_API_KEY not set — Qubrid AI endpoints disabled")

    # Initialize Groq AI client
    if settings.GROQ_API_KEY:
        _groq_client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=GROQ_BASE_URL
        )
        logger.info("✅ Initialized Groq AI Client")
    else:
        logger.warning("⚠️  GROQ_API_KEY not set — Groq AI endpoints disabled")

    # Initialize Groq Fallback AI client
    if settings.GROQ_API_KEY_FALLBACK:
        _groq_fallback_client = OpenAI(
            api_key=settings.GROQ_API_KEY_FALLBACK,
            base_url=GROQ_BASE_URL
        )
        logger.info("✅ Initialized Groq Fallback AI Client")


def get_ai_client() -> OpenAI:
    """Returns whichever client is available (Groq → Qubrid → OpenRouter → OpenAI)."""
    return _groq_client or _qubrid_client or _openrouter_client or _openai_client


def _openai_client_available() -> bool:
    """Returns True only if the native OpenAI client is initialised."""
    return _openai_client is not None


def chat_complete(messages: list, temperature: float = 0.7, max_tokens: int = 1024, model: str = None) -> str:
    """
    Unified AI completion wrapper with automatic fallback chain:
      1. If model starts with 'gpt-' / 'o1-' → OpenAI direct
      2. If model starts with 'qubrid/' → Qubrid AI
      3. If model=None → try Qubrid first, then OpenRouter models in order
      4. Otherwise route through OpenRouter

    Raises RuntimeError if no client can handle the request.
    """
    # Explicit model routing
    if model is not None:
        target_model = model
        is_openai_model = any(target_model.startswith(p) for p in ("gpt-", "o1-", "o3-", "text-"))
        if is_openai_model:
            if _openai_client:
                try:
                    return _call_client(_openai_client, target_model, messages, temperature, max_tokens)
                except Exception as e:
                    logger.warning(f"OpenAI explicit target {target_model} failed: {e}. Falling back to other providers...")
        elif target_model.startswith("qubrid/"):
            if _qubrid_client:
                clean_model = target_model.replace("qubrid/", "")
                try:
                    return _call_client(_qubrid_client, clean_model, messages, temperature, max_tokens)
                except Exception as e:
                    logger.warning(f"Qubrid explicit target {clean_model} failed: {e}. Falling back to other providers...")
        else:
            if _openrouter_client:
                try:
                    return _call_client(_openrouter_client, target_model, messages, temperature, max_tokens)
                except Exception as e:
                    logger.warning(f"OpenRouter explicit target {target_model} failed: {e}. Falling back to other providers...")

    # Auto fallback when model=None:
    # 1. Try Groq (Fastest)
    if _groq_client:
        try:
            logger.debug(f"Trying Groq: {GROQ_DEFAULT_MODEL}")
            return _call_client(_groq_client, GROQ_DEFAULT_MODEL, messages, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Groq primary failed ({e}), trying fallback key...")
            if _groq_fallback_client:
                try:
                    logger.debug(f"Trying Groq Fallback: {GROQ_DEFAULT_MODEL}")
                    return _call_client(_groq_fallback_client, GROQ_DEFAULT_MODEL, messages, temperature, max_tokens)
                except Exception as ef:
                    logger.warning(f"Groq fallback also failed ({ef}), falling back to Qubrid...")
            else:
                logger.warning("Groq fallback key not available, falling back to Qubrid...")

    # 2. Try Qubrid (reliable paid key)
    if _qubrid_client:
        try:
            logger.debug(f"Trying Qubrid: {QUBRID_DEFAULT_MODEL}")
            return _call_client(_qubrid_client, QUBRID_DEFAULT_MODEL, messages, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Qubrid failed ({e}), falling back to OpenRouter...")

    # 2. Try OpenRouter models in order
    if _openrouter_client:
        for fallback_model in OPENROUTER_MODELS_FALLBACK:
            try:
                logger.debug(f"Trying OpenRouter model: {fallback_model}")
                return _call_client(_openrouter_client, fallback_model, messages, temperature, max_tokens)
            except Exception as e:
                logger.warning(f"OpenRouter model {fallback_model} failed ({e}), trying next...")

    # 3. Last resort: OpenAI direct
    if _openai_client:
        try:
            return _call_client(_openai_client, "gpt-3.5-turbo", messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"OpenAI fallback also failed: {e}")

    raise RuntimeError("All AI providers failed or are unavailable. Check your API keys and quotas.")


def _call_client(client: OpenAI, model: str, messages: list, temperature: float, max_tokens: int) -> str:
    """Internal helper — calls a single client and returns the response content.
    If the model rejects system messages (e.g. Gemma via Google AI Studio),
    automatically retries by folding the system prompt into the first user message.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        err_str = str(e)
        # Gemma / some Google AI Studio models don't support system role
        if "Developer instruction is not enabled" in err_str or "system" in err_str.lower() and "400" in err_str:
            # Merge system content into first user message
            merged = []
            system_text = ""
            for msg in messages:
                if msg.get("role") == "system":
                    system_text += msg["content"] + "\n\n"
                else:
                    if system_text and msg.get("role") == "user":
                        merged.append({"role": "user", "content": system_text + msg["content"]})
                        system_text = ""
                    else:
                        merged.append(msg)
            if not merged:
                merged = messages  # fallback
            response = client.chat.completions.create(
                model=model,
                messages=merged,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        raise  # re-raise if it's a different error
