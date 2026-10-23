export interface Device {
  id: string;
  name: string;
  paired: boolean;
  created_at: string;
  last_seen: string | null;
  firmware: string;
  city: string;
  latitude: number;
  longitude: number;
  timezone: string;
  config_version: number;
  language: string;
  oled_brightness: number;
  idle_display_mode: 'clock' | 'weather' | 'blank';
  clock_format: '12h' | '24h';
  speaker_volume: number;
  mic_gain: number;
  wake_mode: 'button' | 'wakeword';
  weather_enabled: boolean;
  search_enabled: boolean;
  timers_enabled: boolean;
  system_prompt?: string | null;
  assistant_name: string;
  personality?: string | null;
  history_length: number;
  asr_provider?: string | null;
  llm_provider?: string | null;
  llm_model?: string | null;
  tts_provider?: string | null;
  tts_voice?: string | null;
  vad_mode: 'manual' | 'vad';
  revoked: boolean;
  online: boolean;
  tools_enabled?: string;
  agent_id?: string | null;
}

export interface DeviceSettingsPayload {
  name: string;
  city: string;
  latitude: number;
  longitude: number;
  timezone: string;
  language: string;
  oled_brightness: number;
  idle_display_mode: 'clock' | 'weather' | 'blank';
  clock_format: '12h' | '24h';
  speaker_volume: number;
  mic_gain: number;
  wake_mode: 'button' | 'wakeword';
  weather_enabled: boolean;
  search_enabled: boolean;
  timers_enabled: boolean;
  system_prompt?: string | null;
  assistant_name?: string;
  personality?: string | null;
  history_length: number;
  asr_provider?: string | null;
  llm_provider?: string | null;
  llm_model?: string | null;
  tts_provider?: string | null;
  tts_voice?: string | null;
  vad_mode: 'manual' | 'vad';
  tools_enabled?: string;
  agent_id?: string | null;
}

export interface AIAgent {
  id: string;
  name: string;
  avatar: string;
  description?: string;
  personality: string;
  system_prompt?: string;
  language: string;
  model_provider: string;
  model_name: string;
  tts_provider: string;
  tts_voice: string;
  response_style: string;
  temperature: number;
  tools_enabled: string;
  created_at: string;
  updated_at: string;
  assigned_devices_count?: number;
  assigned_devices?: Array<{ id: string; name: string; online: boolean }>;
}

export interface AgentCreatePayload {
  name: string;
  avatar: string;
  description?: string;
  personality: string;
  system_prompt?: string;
  language: string;
  model_provider: string;
  model_name: string;
  tts_provider: string;
  tts_voice: string;
  response_style: string;
  temperature: number;
  tools_enabled: string;
}


export interface ProviderItem {
  id: string;
  name: string;
  description?: string;
  models?: string[];
  voices?: string[];
}

export interface AIProvidersConfig {
  available_asr: ProviderItem[];
  available_llm: ProviderItem[];
  available_tts: ProviderItem[];
  defaults: {
    default_asr_provider: string;
    default_llm_provider: string;
    default_llm_model: string;
    default_tts_provider: string;
    default_tts_voice: string;
    ollama_base_url: string;
    openai_compatible_base_url: string;
    openai_api_key_masked: string;
    gemini_api_key_masked: string;
    openai_compatible_api_key_masked: string;
    has_openai_key: boolean;
    has_gemini_key: boolean;
    has_compat_key: boolean;
  };
}

export interface ConversationItem {
  id: string;
  device_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  device_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  latency_ms?: number | null;
  provider_info?: string | null;
  created_at: string;
}

export interface LiveSession {
  session_id: string;
  device_id: string;
  state: 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';
  connected_at: number;
  last_interaction: number;
  dropped_frames: number;
  last_metrics?: {
    upload_duration_ms?: number;
    stt_latency_ms?: number;
    llm_first_token_ms?: number;
    tts_first_audio_ms?: number;
    total_turnaround_ms?: number;
    asr_provider?: string;
    tts_provider?: string;
  };
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  timeout_seconds: number;
}

export interface TimerItem {
  id: string;
  device_id: string;
  label: string;
  duration_seconds: number;
  created_at: string;
  expires_at: string;
  status: 'active' | 'completed' | 'cancelled';
  alert_acknowledged: boolean;
}

export interface AlarmItem {
  id: string;
  device_id: string;
  time_str: string;
  label: string;
  timezone: string;
  repeat_days: string;
  created_at: string;
  next_trigger_at: string;
  status: 'active' | 'dismissed' | 'cancelled';
}

export interface FirmwareReleaseItem {
  id: string;
  version: string;
  target_hardware: string;
  file_size: number;
  sha256: string;
  release_notes?: string;
  created_at: string;
  is_active: boolean;
}

export interface DeviceTelemetryItem {
  id: string;
  device_id: string;
  rssi?: number;
  free_heap?: number;
  min_free_heap?: number;
  uptime_s?: number;
  dropped_frames: number;
  error_count: number;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  user: string;
  action: string;
  target?: string;
  details?: string;
  ip_address?: string;
  created_at: string;
}

