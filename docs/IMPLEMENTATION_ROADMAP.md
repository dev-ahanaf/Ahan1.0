# Falcon AI - Implementation Roadmap

**Project:** Falcon AI (Self-Hosted ESP32 AI Voice Assistant Ecosystem)  
**Target Board:** Regular ESP32 Dev Board (ESP32-WROOM-32, 320 KB SRAM, No PSRAM)  
**Execution Strategy:** Incremental enhancement of the operational custom core, importing advanced XiaoZhi-inspired concepts while maintaining verified performance.

---

## Roadmap Phases

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Brand Elevation & Architecture Specification                   │
│   - Create docs/ARCHITECTURE.md justifying custom core adoption        │
│   - Apply Falcon AI brand across console, server, and firmware         │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 2: First-Class Multi-Agent Entity & Management                   │
│   - Add AIAgent database model & Alembic migration                     │
│   - Build REST API for Agent CRUD and device assignment                │
│   - Connect Agent system prompt & personality to real-time LLM runtime │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Bengali & English Multilingual Voice Pipeline                 │
│   - Configure Edge-TTS Bengali voices (bn-BD-Nabanita, bn-BD-Pradeep)  │
│   - Extend intent routing & system prompts for Bengali conversations   │
│   - Validate audio streaming & tone synthesis                          │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Falcon AI Web Console Transformation                          │
│   - Restructure main navigation into SaaS 10-tab hierarchy            │
│   - Build dedicated "AI Agents" and "Voice Studio" views               │
│   - Add Bengali / English UI language localization toggle              │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 5: Firmware Branding & Boot Animation                            │
│   - Update firmware boot banner & OLED startup to "FALCON AI"          │
│   - Compile Falcon AI Firmware v1.2.0 and upload to catalog            │
│   - Verify dual button push-to-talk & LittleFS pairing persistence     │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 6: System Verification & Comprehensive Documentation             │
│   - Run full automated pytest suite & hardware simulator               │
│   - Document wiring, build, pairing, AI setup, and production deployment│
└────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Task Breakdown

### Phase 1: Brand Elevation & System Architecture
- [x] Workspace forensic audit (`docs/WORKSPACE_AUDIT.md`).
- [x] Existing features inventory (`docs/EXISTING_FEATURES.md`).
- [x] Create authoritative architecture document (`docs/ARCHITECTURE.md`).
- [ ] Rename and rebrand server headers, web console titles, and metadata to Falcon AI.

### Phase 2: AI Agent Entity & Multi-Agent Runtime
- [ ] Implement `AIAgent` database model in `myvoice-os/server/app/models.py`:
  - `id`, `name`, `avatar`, `personality`, `system_prompt`, `language`, `model_provider`, `model_name`, `tts_voice`, `response_style`, `tools_enabled`, `created_at`, `updated_at`.
- [ ] Link `Device.agent_id` &rarr; `AIAgent.id` with fallback to default agent.
- [ ] Implement REST endpoints:
  - `GET /api/admin/agents`: List all configured agents.
  - `POST /api/admin/agents`: Create new agent with custom prompt & voice.
  - `PUT /api/admin/agents/{id}`: Update agent configuration.
  - `DELETE /api/admin/agents/{id}`: Delete agent with reassignment safeguards.
- [ ] Update `ws_device.py` to resolve and apply the assigned agent's personality and prompt dynamically.

### Phase 3: Bengali & English Multilingual Pipeline
- [ ] In `app/services/providers/tts.py`, register verified Bengali voices:
  - `bn-BD-NabanitaNeural` (Female, Bangladesh)
  - `bn-BD-PradeepNeural` (Male, Bangladesh)
  - `bn-IN-TanishaaNeural` (Female, India)
- [ ] Add bilingual intent recognition patterns for Clock, Date, Weather, and Search.
- [ ] Ensure UTF-8 characters are handled properly across database, WebSocket frames, and OLED font renderers.

### Phase 4: Web Console SaaS Redesign
- [ ] Update navigation tabs:
  1. **Dashboard**: Fleet overview, active sessions, system health, and quick stats.
  2. **My Devices**: Device list, pairing modal, rename, token rotation, and remote actions.
  3. **AI Agents**: Dedicated agent creation studio, personality prompt editor, voice selection.
  4. **Voice Studio**: Voice previewer, speech rate adjustments, language catalog.
  5. **AI Models**: Provider management (OpenAI, Groq, Ollama), API key configuration, health check.
  6. **Conversations**: Full conversation session explorer and transcript audit.
  7. **Device Tools**: MCP and skill permission toggles (Clock, Weather, Search, Timers, Alarms).
  8. **Firmware & OTA**: Binary upload, SHA-256 integrity inspection, remote deploy.
  9. **Account Settings**: Theme selection, language toggle (English / Bengali), security.
  10. **Admin Panel**: Audit logs, telemetry stats, and user administration.

### Phase 5: Falcon AI Firmware Rebrand & Build
- [ ] Update `pins.h`, `display.cpp`, `main.cpp`, and `MyVoiceAssistant.ino`:
  - Brand string: `FALCON AI`
  - Boot screen: Falcon AI splash
  - Hotspot AP name: `FalconAI-Setup-XXXX`
- [ ] Compile new firmware release via PlatformIO.
- [ ] Upload binary to server catalog as `v1.2.0-falcon`.

### Phase 6: Testing & Complete Documentation
- [ ] Run backend unit & integration tests (`pytest tests`).
- [ ] Run end-to-end simulator voice cycle with Bengali and English queries.
- [ ] Generate comprehensive documentation:
  - `docs/ARCHITECTURE.md`
  - `docs/HARDWARE_WIRING.md`
  - `docs/FIRMWARE_BUILD.md`
  - `docs/DEVICE_PAIRING.md`
  - `docs/AI_PROVIDER_SETUP.md`
  - `docs/LOCAL_DEPLOYMENT.md`
  - `docs/PRODUCTION_DEPLOYMENT.md`
  - `docs/OTA_GUIDE.md`
  - `docs/API_REFERENCE.md`
  - `docs/TEST_REPORT.md`
