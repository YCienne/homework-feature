"""
LLM Client — supports DeepSeek, Gemini, and Anthropic Claude.
Switch providers by setting LLM_PROVIDER in .env:
LLM_PROVIDER=gemini
"""
import logging
import asyncio
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_anthropic_client = None
_gemini_client = None  # Updated to track the modern unified GenAI client instance
_deepseek_client = None

def _get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is None:
        from openai import AsyncOpenAI
        settings = get_settings()
        _deepseek_client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
    return _deepseek_client

def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        settings = get_settings()
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client

def _get_gemini_client():
    """Initializes the modern Google GenAI Client with explicit API key access."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        settings = get_settings()
        # Passing the key explicitly prevents the SDK from pulling restricted gcloud scopes
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client

async def call_llm(messages: list[dict]) -> str:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "deepseek":
        return await _call_deepseek(messages)
    elif provider == "anthropic":
        return await _call_anthropic(messages)
    elif provider == "gemini":
        return await _call_gemini(messages)
    else:
        raise LLMProviderError(f"Unknown LLM_PROVIDER: '{provider}'. Must be deepseek, anthropic, or gemini.")

async def _call_deepseek(messages: list[dict]) -> str:
    try:
        settings = get_settings()
        client = _get_deepseek_client()
        response = await client.chat.completions.create(
            model=settings.llm_model_deepseek,
            messages=messages,
            max_tokens=1000,
            temperature=0.3,
        )
        content = response.choices[0].message.content
        logger.debug(f"DeepSeek response ({len(content)} chars)")
        return content
    except Exception as e:
        if "timeout" in str(e).lower():
            raise LLMTimeoutError(str(e))
        raise LLMProviderError(f"DeepSeek error: {e}")

async def _call_anthropic(messages: list[dict]) -> str:
    try:
        settings = get_settings()
        client = _get_anthropic_client()
        response = await client.messages.create(
            model=settings.llm_model_anthropic,
            max_tokens=1000,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        raise LLMProviderError(str(e))

async def _call_gemini(messages: list[dict]) -> str:
    """Executes a structured text completion via the updated google-genai client."""
    try:
        from google.genai import types
        settings = get_settings()
        client = _get_gemini_client()
        
        # Format list arrays into a simple sequential prompt block string
        prompt = "\n\n".join(m["content"] for m in messages if m.get("content"))
        
        # Execute the call in an external asynchronous worker thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: client.models.generate_content(
                model=settings.llm_model_gemini, # Reads gemini-1.5-flash from settings
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                    response_mime_type="application/json" # Forces structured output format
                )
            )
        )
        return response.text
    except Exception as e:
        raise LLMProviderError(f"Gemini error: {e}")

async def call_vision(image_bytes: bytes, content_type: str, prompt: str) -> str:
    settings = get_settings()
    provider = settings.image_extraction_provider.lower()
    if provider == "anthropic":
        return await _vision_anthropic(image_bytes, content_type, prompt)
    else:
        return await _vision_gemini(image_bytes, content_type, prompt)

async def _vision_gemini(image_bytes: bytes, content_type: str, prompt: str) -> str:
    """Executes an OCR image text extraction process via the updated google-genai client."""
    try:
        from google.genai import types
        client = _get_gemini_client()
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2000
                )
            )
        )
        return response.text
    except Exception as e:
        raise LLMProviderError(f"Gemini vision error: {e}")

async def _vision_anthropic(image_bytes: bytes, content_type: str, prompt: str) -> str:
    try:
        import base64
        client = _get_anthropic_client()
        settings = get_settings()
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = await client.messages.create(
            model=settings.llm_model_anthropic,
            max_tokens=2000,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": b64}},
                {"type": "text", "text": prompt},
            ]}]
        )
        return response.content[0].text
    except Exception as e:
        raise LLMProviderError(f"Anthropic vision error: {e}")

class LLMTimeoutError(Exception):
    pass

class LLMProviderError(Exception):
    pass
