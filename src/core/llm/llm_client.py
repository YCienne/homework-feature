"""
LLM Client — supports DeepSeek, Gemini, Anthropic (direct API), Claude Platform
on AWS, and Amazon Bedrock.
Switch providers by setting LLM_PROVIDER in .env:
LLM_PROVIDER=gemini | deepseek | anthropic | anthropic_aws | bedrock

anthropic_aws authenticates via AWS IAM/SigV4 (the default AWS credential chain)
rather than an API key, and requires CLAUDE_AWS_REGION. The workspace's AWS
region only scopes IAM/billing — it does not pin where inference runs, so it
is not on its own a data-residency guarantee (confirm with Anthropic if a
requirement like POPIA applies before relying on region choice alone).

bedrock also authenticates via the default AWS credential chain, calling
bedrock-runtime's Converse API. Requires BEDROCK_REGION and BEDROCK_MODEL_ID;
the model must be enabled for that region in the account's Bedrock console —
access is granted per-region, not account-wide.
"""
import logging
import asyncio
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_anthropic_client = None
_anthropic_aws_client = None
_bedrock_client = None
_gemini_client = None  # Updated to track the modern unified GenAI client instance
_deepseek_client = None


def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Separates system-role messages (native system prompt) from the rest."""
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    system = "\n\n".join(system_parts) if system_parts else None
    return system, rest

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

def _get_anthropic_aws_client():
    """Claude Platform on AWS — IAM/SigV4 auth via the AWS default credential
    chain, not an API key. Beta SDK surface; requires anthropic>=0.117.1."""
    global _anthropic_aws_client
    if _anthropic_aws_client is None:
        from anthropic import AsyncAnthropicAWS
        settings = get_settings()
        if not settings.claude_aws_region:
            raise LLMProviderError("claude_aws_region is not configured for the anthropic_aws provider")
        _anthropic_aws_client = AsyncAnthropicAWS(
            aws_region=settings.claude_aws_region,
            workspace_id=settings.claude_aws_workspace_id or None,
        )
    return _anthropic_aws_client

def _get_bedrock_client():
    """Amazon Bedrock — IAM/SigV4 auth via the AWS default credential chain
    (the EC2 instance's attached role in production), not an API key."""
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        settings = get_settings()
        if not settings.bedrock_region:
            raise LLMProviderError("bedrock_region is not configured for the bedrock provider")
        _bedrock_client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)
    return _bedrock_client

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
    elif provider == "anthropic_aws":
        return await _call_anthropic_aws(messages)
    elif provider == "bedrock":
        return await _call_bedrock(messages)
    elif provider == "gemini":
        return await _call_gemini(messages)
    else:
        raise LLMProviderError(f"Unknown LLM_PROVIDER: '{provider}'. Must be deepseek, anthropic, anthropic_aws, bedrock, or gemini.")

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
        system, rest = _split_system(messages)
        kwargs = {"model": settings.llm_model_anthropic, "max_tokens": 1000, "messages": rest}
        if system:
            kwargs["system"] = system
        response = await client.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        raise LLMProviderError(str(e))

async def _call_anthropic_aws(messages: list[dict]) -> str:
    try:
        settings = get_settings()
        client = _get_anthropic_aws_client()
        system, rest = _split_system(messages)
        kwargs = {"model": settings.llm_model_anthropic, "max_tokens": 1000, "messages": rest}
        if system:
            kwargs["system"] = system
        response = await client.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        raise LLMProviderError(f"Claude Platform on AWS error: {e}")

async def _call_bedrock(messages: list[dict]) -> str:
    try:
        settings = get_settings()
        if not settings.bedrock_model_id:
            raise LLMProviderError("bedrock_model_id is not configured for the bedrock provider")
        client = _get_bedrock_client()
        system, rest = _split_system(messages)
        converse_messages = [
            {"role": m["role"], "content": [{"text": m["content"]}]}
            for m in rest
        ]
        kwargs = {
            "modelId": settings.bedrock_model_id,
            "messages": converse_messages,
            "inferenceConfig": {"maxTokens": 1000, "temperature": 0.3},
        }
        if system:
            kwargs["system"] = [{"text": system}]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.converse(**kwargs))
        return response["output"]["message"]["content"][0]["text"]
    except LLMProviderError:
        raise
    except Exception as e:
        raise LLMProviderError(f"Bedrock error: {e}")

async def _call_gemini(messages: list[dict]) -> str:
    """Executes a structured text completion via the updated google-genai client."""
    try:
        from google.genai import types
        settings = get_settings()
        client = _get_gemini_client()
        system, rest = _split_system(messages)

        # Format remaining (non-system) turns into a simple sequential prompt block string
        prompt = "\n\n".join(m["content"] for m in rest if m.get("content"))
        
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
                    response_mime_type="application/json", # Forces structured output format
                    system_instruction=system,
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
