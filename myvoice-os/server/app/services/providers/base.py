"""Abstract base interfaces for multi-provider AI audio pipeline."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional

class ASRProvider(ABC):
    """Abstract interface for Automated Speech Recognition."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """Transcribe 16 kHz PCM16 or WAV audio bytes to text string."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify API connectivity and credentials."""
        pass


class LLMProvider(ABC):
    """Abstract interface for Language Model completions and token streaming."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream incremental text token deltas."""
        pass

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Accumulate tokens and return full response text."""
        chunks = []
        async for chunk in self.stream_chat(messages, model=model, temperature=temperature):
            chunks.append(chunk)
        return "".join(chunks)

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify model endpoint reachability."""
        pass


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech synthesis."""

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized 16 kHz 16-bit mono PCM chunks."""
        pass

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "en"
    ) -> bytes:
        """Synthesize text and return full PCM16 audio bytes."""
        chunks = []
        async for chunk in self.synthesize_stream(text, voice=voice, language=language):
            chunks.append(chunk)
        return b"".join(chunks)

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify voice synthesis service availability."""
        pass
