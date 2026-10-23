# Falcon AI Model Providers & Speech Setup

## 1. Provider Architecture

Falcon AI uses an adapter-based AI pipeline allowing hot-swappable providers for LLM, ASR (Automated Speech Recognition), and TTS (Text-to-Speech) without server restarts.

```
+-------------------------------------------------------------------------+
|                              FALCON AI SERVER                           |
|                                                                         |
|  [ ASR Pipeline ]          [ LLM Engine ]             [ TTS Engine ]    |
|   - OpenAI Whisper          - Google Gemini 1.5        - Edge-TTS       |
|   - Faster-Whisper          - OpenAI (GPT-4o, Mini)    - OpenAI Speech  |
|   - SenseVoice              - Ollama (Local Llama 3)   - Piper          |
|   - Mock Simulator          - OpenAI-Compatible        - Mock Audio     |
+-------------------------------------------------------------------------+
```

---

## 2. Supported LLM Providers

### A. Google Gemini (Recommended Default)
- **Models**: `gemini-1.5-flash`, `gemini-1.5-pro`
- **Features**: Ultra-low first-token latency (< 350 ms), excellent Bengali and English bilingual reasoning, high rate limits.
- **Configuration**:
  - Web Console: Navigate to **AI Models** -> Enter `GEMINI_API_KEY` -> Select `Gemini 1.5 Flash` -> Click **Save**.
  - Environment: `GEMINI_API_KEY=AIzaSy...`

### B. OpenAI
- **Models**: `gpt-4o-mini`, `gpt-4o`
- **Configuration**:
  - Web Console: Enter `OPENAI_API_KEY` -> Select `gpt-4o-mini` -> Click **Save**.
  - Environment: `OPENAI_API_KEY=sk-...`

### C. Local Ollama (Zero Cloud Dependency)
- **Base URL**: `http://localhost:11434`
- **Models**: `llama3.2`, `mistral`, `qwen2.5`
- **Configuration**:
  - Pull model on server: `ollama run llama3.2`
  - In Web Console: Select provider `Ollama` -> Base URL: `http://localhost:11434` -> Model: `llama3.2`.

---

## 3. Bilingual Speech Synthesis (TTS)

### A. Microsoft Edge Neural TTS (Free & Built-In)
Falcon AI integrates high-fidelity Edge Neural speech synthesis with streaming chunk decoding.

#### Bengali Neural Voices (First-Class Support):
- `bn-BD-NabanitaNeural` (Female, natural Bangladeshi Bengali)
- `bn-BD-PradeepNeural` (Male, clear Bangladeshi Bengali)

#### English Neural Voices:
- `en-US-AriaNeural` (Female, conversational standard US)
- `en-US-GuyNeural` (Male, crisp US)
- `en-US-JennyNeural` (Female, natural assistant tone)

---

## 4. Multi-Agent Persona Customization

In Falcon AI Console, navigate to **AI Agents**:
- You can create distinct agents with different languages and models:
  - **Falcon Primary**: English assistant using `gemini-1.5-flash` and `en-US-AriaNeural`.
  - **Falcon Bangla**: Bengali assistant using `gemini-1.5-flash` and `bn-BD-NabanitaNeural`.
  - **Falcon Local**: Private assistant using local `Ollama llama3.2` and `Piper`.
- Assign any agent to your ESP32 device with one click; settings sync to the active hardware in real time over WebSocket!
