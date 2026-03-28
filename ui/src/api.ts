/**
 * NanoFoxy UI - API Client
 */

const API_BASE = '/api';

export async function fetchStatus() {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function fetchSession(key: string) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(key)}`);
  if (!res.ok) throw new Error('Failed to fetch session');
  return res.json();
}

export async function clearSession(key: string) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(key)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to clear session');
  return res.json();
}

export async function fetchCronJobs() {
  const res = await fetch(`${API_BASE}/cron/jobs`);
  if (!res.ok) throw new Error('Failed to fetch cron jobs');
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error('Failed to fetch config');
  return res.json();
}

export function connectWebSocket(onMessage: (data: unknown) => void) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/ws/events`);

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onMessage(data);
    } catch {
      onMessage(e.data);
    }
  };

  ws.onerror = () => {
    console.error('WebSocket error');
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };

  return ws;
}
