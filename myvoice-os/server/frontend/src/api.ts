import {
  Device,
  DeviceSettingsPayload,
  AIProvidersConfig,
  ConversationItem,
  ConversationMessage,
  LiveSession
} from './types';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    const message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    throw new Error(message || `Request failed with status ${res.status}`);
  }
  return data as T;
}

export async function getDevices(): Promise<{ devices: Device[] }> {
  return request<{ devices: Device[] }>('/api/admin/devices');
}

export async function claimDevice(code: string, name: string): Promise<{ paired: boolean; device_id: string; name: string }> {
  return request('/api/admin/claim', {
    method: 'POST',
    body: JSON.stringify({ code, name }),
  });
}

export async function saveSettings(deviceId: string, payload: DeviceSettingsPayload): Promise<{ ok: boolean; config_version: number }> {
  return request(`/api/admin/devices/${encodeURIComponent(deviceId)}/settings`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function rotateDeviceToken(deviceId: string): Promise<{ ok: boolean; device_id: string; new_token: string }> {
  return request(`/api/admin/devices/${encodeURIComponent(deviceId)}/rotate-token`, {
    method: 'POST',
  });
}

export async function revokeDevice(deviceId: string): Promise<{ ok: boolean; revoked: boolean; device_id: string }> {
  return request(`/api/admin/devices/${encodeURIComponent(deviceId)}/revoke`, {
    method: 'POST',
  });
}

export async function askAssistant(text: string, deviceId: string | null): Promise<{ answer: string }> {
  return request('/api/admin/ask', {
    method: 'POST',
    body: JSON.stringify({ text, device_id: deviceId || null }),
  });
}

export async function getAIProviders(): Promise<AIProvidersConfig> {
  return request<AIProvidersConfig>('/api/admin/providers');
}

export async function saveAIProviders(payload: Record<string, string>): Promise<{ ok: boolean; message: string }> {
  return request('/api/admin/providers', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function testAIProvider(provider_type: string, provider_name: string, options: Record<string, any> = {}): Promise<{ ok: boolean; error?: string; [key: string]: any }> {
  return request('/api/admin/providers/test', {
    method: 'POST',
    body: JSON.stringify({ provider_type, provider_name, ...options }),
  });
}

export async function getConversations(q = '', deviceId = ''): Promise<{ conversations: ConversationItem[] }> {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (deviceId) params.set('device_id', deviceId);
  return request(`/api/admin/conversations?${params.toString()}`);
}

export async function getConversationMessages(convId: string): Promise<{ messages: ConversationMessage[] }> {
  return request(`/api/admin/conversations/${encodeURIComponent(convId)}/messages`);
}

export async function deleteConversation(convId: string): Promise<{ ok: boolean; id: string }> {
  return request(`/api/admin/conversations/${encodeURIComponent(convId)}`, {
    method: 'DELETE',
  });
}

export async function getActiveSessions(): Promise<{ sessions: LiveSession[] }> {
  return request<{ sessions: LiveSession[] }>('/api/admin/sessions');
}

// Phase 3 Tool & Skill APIs
export async function getTools(): Promise<{ tools: any[] }> {
  return request('/api/admin/tools');
}

export async function testTool(tool_name: string, args: Record<string, any> = {}, device_id = 'SIMULATOR'): Promise<any> {
  return request('/api/admin/tools/test', {
    method: 'POST',
    body: JSON.stringify({ tool_name, arguments: args, device_id }),
  });
}

export async function updateDeviceTools(device_id: string, tools: string[]): Promise<any> {
  return request(`/api/admin/devices/${encodeURIComponent(device_id)}/tools`, {
    method: 'POST',
    body: JSON.stringify({ tools }),
  });
}

// Phase 3 Timers & Alarms APIs
export async function getTimers(): Promise<{ timers: any[] }> {
  return request('/api/admin/timers');
}

export async function deleteTimer(timer_id: string): Promise<any> {
  return request(`/api/admin/timers/${encodeURIComponent(timer_id)}`, {
    method: 'DELETE',
  });
}

export async function getAlarms(): Promise<{ alarms: any[] }> {
  return request('/api/admin/alarms');
}

export async function createAlarm(payload: { device_id: string; time_str: string; label: string; repeat_days?: string }): Promise<any> {
  return request('/api/admin/alarms', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteAlarm(alarm_id: string): Promise<any> {
  return request(`/api/admin/alarms/${encodeURIComponent(alarm_id)}`, {
    method: 'DELETE',
  });
}

// Phase 3 OTA Firmware APIs
export async function getOTAReleases(): Promise<{ releases: any[] }> {
  return request('/api/admin/ota/releases');
}

export async function uploadFirmware(formData: FormData): Promise<any> {
  const res = await fetch('/api/admin/ota/upload', {
    method: 'POST',
    credentials: 'same-origin',
    body: formData,
  });
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    throw new Error(data.detail || `Upload failed with status ${res.status}`);
  }
  return data;
}

export async function deployFirmware(version: string, target_device = 'ALL'): Promise<any> {
  return request('/api/admin/ota/deploy', {
    method: 'POST',
    body: JSON.stringify({ version, target_device }),
  });
}

// Phase 3 Remote Device Actions & Telemetry
export async function rebootDevice(device_id: string): Promise<any> {
  return request(`/api/admin/devices/${encodeURIComponent(device_id)}/reboot`, {
    method: 'POST',
  });
}

export async function resetWifiDevice(device_id: string): Promise<any> {
  return request(`/api/admin/devices/${encodeURIComponent(device_id)}/reset_wifi`, {
    method: 'POST',
  });
}

export async function getDeviceTelemetry(device_id: string): Promise<{ telemetry: any[] }> {
  return request(`/api/admin/devices/${encodeURIComponent(device_id)}/telemetry`);
}

export async function getAuditLogs(): Promise<{ audit_logs: any[] }> {
  return request('/api/admin/audit_logs');
}

