"""LLM Provider implementations: OpenAI, Gemini, OpenAI-Compatible, Ollama, and Mock."""
import json
import os
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx
from app.services.providers.base import LLMProvider

class OpenAILLMProvider(LLMProvider):
    """OpenAI Chat Completion provider with Server-Sent Events (SSE) streaming."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Configure OPENAI_API_KEY in server settings.")

        target_model = model or self.model
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "provider": "openai", "error": "API key not configured"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if resp.status_code == 200:
                    return {"ok": True, "provider": "openai", "model": self.model}
                return {"ok": False, "provider": "openai", "error": f"HTTP {resp.status_code}: {resp.text[:120]}"}
        except Exception as exc:
            return {"ok": False, "provider": "openai", "error": str(exc)}


class GeminiLLMProvider(LLMProvider):
    """Google Gemini API provider with streaming generate content."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model

    def _convert_messages(self, messages: List[Dict[str, str]]):
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })

        return contents, system_instruction

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("Gemini API key is missing. Configure GEMINI_API_KEY in server settings.")

        target_model = model or self.model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:streamGenerateContent?key={self.api_key}&alt=sse"
        contents, system_instruction = self._convert_messages(messages)

        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 256
            }
        }
        if system_instruction:
            body["system_instruction"] = system_instruction

        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    try:
                        chunk_json = json.loads(data_str)
                        candidates = chunk_json.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "provider": "gemini", "error": "API key not configured"}
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return {"ok": True, "provider": "gemini", "model": self.model}
                return {"ok": False, "provider": "gemini", "error": f"HTTP {resp.status_code}: {resp.text[:120]}"}
        except Exception as exc:
            return {"ok": False, "provider": "gemini", "error": str(exc)}


class OpenAICompatibleProvider(LLMProvider):
    """Generic provider for OpenAI-compatible endpoints (vLLM, DeepSeek, LocalAI, etc.)."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "default"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        self.model = model

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> Dict[str, Any]:
        url = f"{self.base_url}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return {"ok": True, "provider": "openai-compatible", "endpoint": self.base_url}
                return {"ok": False, "provider": "openai-compatible", "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "provider": "openai-compatible", "error": str(exc)}


class OllamaProvider(LLMProvider):
    """Local Ollama instance provider connecting via Ollama native chat endpoint."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})
                        content = msg.get("content")
                        if content:
                            yield content
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    return {"ok": True, "provider": "ollama", "models": models}
                return {"ok": False, "provider": "ollama", "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "provider": "ollama", "error": f"Ollama not reachable: {exc}"}


class MockLLMProvider(LLMProvider):
    """Deterministic token streaming provider for testing without external API calls."""

    def __init__(self, canned_response: str = "The current weather in Dhaka is sunny and pleasant."):
        self.canned_response = canned_response

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        import asyncio
        words = self.canned_response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.01)

    async def health_check(self) -> Dict[str, Any]:
        return {"ok": True, "provider": "mock", "status": "active"}
