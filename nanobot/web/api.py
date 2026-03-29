"""FastAPI web server for nanobot dashboard."""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel


class StatusResponse(BaseModel):
    model: str
    provider: str
    workspace: str
    channels_enabled: list[str]
    cron_jobs: int
    uptime_seconds: float


class SessionInfo(BaseModel):
    key: str
    created_at: str
    updated_at: str


class MessageInfo(BaseModel):
    role: str
    content: str
    timestamp: str


class SessionDetail(BaseModel):
    key: str
    messages: list[dict[str, Any]]
    created_at: str
    updated_at: str


def create_app(
    config: Any,
    session_manager: Any,
    cron_service: Any,
    channels: Any,
    start_time: float | None = None,
) -> FastAPI:
    app = FastAPI(
        title="NanoFoxy Dashboard",
        description="Web UI for NanoFoxy AI Assistant",
        version="0.1.0",
    )

    app.state.config = config
    app.state.session_manager = session_manager
    app.state.cron = cron_service
    app.state.channels = channels
    app.state.start_time = start_time or time.time()
    app.state.websockets: list[WebSocket] = []

    from nanobot.web.routes import router, register_paperclip_routes
    app.include_router(router)
    register_paperclip_routes(app)

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return _DASHBOARD_HTML

    return app


async def run_server(
    config: Any,
    session_manager: Any,
    cron_service: Any,
    channels: Any,
    host: str = "127.0.0.1",
    port: int = 18791,
):
    """Run the web server."""
    import uvicorn

    app = create_app(
        config, session_manager, cron_service, channels,
        start_time=time.time()
    )

    config_uvicorn = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()


def get_uptime_seconds(start_time: float) -> float:
    return time.time() - start_time


_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NanoFoxy Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #334155;
            margin-bottom: 30px;
        }
        h1 { color: #38bdf8; font-size: 1.8rem; }
        .status-badge {
            background: #22c55e;
            color: #0f172a;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.875rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
        }
        .card h2 {
            color: #94a3b8;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 16px;
        }
        .stat { margin-bottom: 12px; }
        .stat-label { color: #64748b; font-size: 0.875rem; }
        .stat-value { color: #f1f5f9; font-size: 1.25rem; font-weight: 600; }
        .sessions-list { max-height: 300px; overflow-y: auto; }
        .session-item {
            padding: 12px;
            background: #0f172a;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .session-item:hover { background: #1e293b; }
        .session-key { font-weight: 500; margin-bottom: 4px; }
        .session-time { color: #64748b; font-size: 0.75rem; }
        .nav { display: flex; gap: 8px; }
        .nav a {
            color: #94a3b8;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 0.875rem;
            transition: all 0.2s;
        }
        .nav a:hover, .nav a.active { background: #334155; color: #f1f5f9; }
        .channel-list { display: flex; flex-wrap: wrap; gap: 8px; }
        .channel-tag {
            background: #0ea5e9;
            color: #0f172a;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .loading { color: #64748b; text-align: center; padding: 40px; }
        .error { color: #ef4444; padding: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NanoFoxy Dashboard</h1>
            <span class="status-badge">Online</span>
        </header>
        
        <nav class="nav">
            <a href="#" class="active" data-page="dashboard">Dashboard</a>
            <a href="#" data-page="sessions">Sessions</a>
            <a href="#" data-page="settings">Settings</a>
        </nav>
        
        <div id="content">
            <div class="loading">Loading...</div>
        </div>
    </div>
    
    <script type="module">
        const API_BASE = '/api';
        
        async function fetchStatus() {
            const res = await fetch(`${API_BASE}/status`);
            return res.json();
        }
        
        async function fetchSessions() {
            const res = await fetch(`${API_BASE}/sessions`);
            return res.json();
        }
        
        async function fetchConfig() {
            const res = await fetch(`${API_BASE}/config`);
            return res.json();
        }
        
        function formatUptime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            if (h > 0) return `${h}h ${m}m`;
            if (m > 0) return `${m}m ${s}s`;
            return `${s}s`;
        }
        
        function formatDate(isoString) {
            if (!isoString) return 'N/A';
            const d = new Date(isoString);
            return d.toLocaleString();
        }
        
        function renderDashboard(status, sessions) {
            return `
                <div class="grid">
                    <div class="card">
                        <h2>Agent Status</h2>
                        <div class="stat">
                            <div class="stat-label">Model</div>
                            <div class="stat-value">${status.model || 'Unknown'}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Provider</div>
                            <div class="stat-value">${status.provider || 'Unknown'}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Uptime</div>
                            <div class="stat-value">${formatUptime(status.uptime_seconds)}</div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Workspace</h2>
                        <div class="stat">
                            <div class="stat-value" style="font-size: 0.9rem; word-break: break-all;">${status.workspace || 'N/A'}</div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Channels</h2>
                        <div class="channel-list">
                            ${status.channels_enabled.length > 0 
                                ? status.channels_enabled.map(c => `<span class="channel-tag">${c}</span>`).join('')
                                : '<span class="stat-label">No channels enabled</span>'
                            }
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Cron Jobs</h2>
                        <div class="stat">
                            <div class="stat-value">${status.cron_jobs || 0}</div>
                            <div class="stat-label">scheduled tasks</div>
                        </div>
                    </div>
                </div>
                
                <div class="card" style="margin-top: 20px;">
                    <h2>Recent Sessions</h2>
                    <div class="sessions-list">
                        ${sessions.length > 0 
                            ? sessions.slice(0, 10).map(s => `
                                <div class="session-item" data-key="${s.key}">
                                    <div class="session-key">${s.key}</div>
                                    <div class="session-time">${formatDate(s.updated_at)}</div>
                                </div>
                            `).join('')
                            : '<div class="stat-label">No sessions yet</div>'
                        }
                    </div>
                </div>
            `;
        }
        
        function renderSessions(sessions) {
            if (sessions.length === 0) {
                return `
                    <div class="card">
                        <h2>All Sessions</h2>
                        <div class="stat-label" style="padding: 40px; text-align: center;">No sessions found</div>
                    </div>
                `;
            }
            return `
                <div class="card">
                    <h2>All Sessions</h2>
                    <div class="stat-label" style="margin-bottom: 16px;">${sessions.length} session(s)</div>
                    <div class="sessions-list">
                        ${sessions.map(s => `
                            <div class="session-item" data-key="${s.key}">
                                <div class="session-key">${s.key}</div>
                                <div class="session-time">Last updated: ${formatDate(s.updated_at)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        function renderSettings(config) {
            const channelsHtml = config.channels && Object.keys(config.channels).length > 0
                ? Object.entries(config.channels).map(([name, settings]) => {
                    let isEnabled = false;
                    let hasDetails = false;
                    if (typeof settings === 'boolean') {
                        isEnabled = settings;
                    } else if (typeof settings === 'object' && settings !== null) {
                        isEnabled = settings.enabled === true;
                        hasDetails = !settings.masked && Object.keys(settings).length > 1;
                    }
                    const displayName = name.charAt(0).toUpperCase() + name.slice(1).replace(/([A-Z])/g, ' $1');
                    let statusHtml = `<span style="color: ${isEnabled ? '#22c55e' : '#64748b'};">${isEnabled ? 'Enabled' : 'Disabled'}</span>`;
                    if (hasDetails) {
                        statusHtml = `<span style="color: ${isEnabled ? '#22c55e' : '#64748b'};">${isEnabled ? 'Enabled' : 'Disabled'}</span><span style="color: #64748b; margin-left: 8px; font-size: 0.75rem;">(configured)</span>`;
                    }
                    return `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #334155;">
                            <span style="color: #f1f5f9;">${displayName}</span>
                            ${statusHtml}
                        </div>
                    `;
                }).join('')
                : '<div class="stat-label">No channels configured</div>';
            
            return `
                <div class="card">
                    <h2>Agent Configuration</h2>
                    
                    <div style="margin-top: 20px;">
                        <h3 style="color: #94a3b8; font-size: 0.875rem; margin-bottom: 12px;">MODEL</h3>
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155;">
                            <span style="color: #64748b;">Model</span>
                            <span style="color: #f1f5f9;">${config.model || 'Not configured'}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155;">
                            <span style="color: #64748b;">Provider</span>
                            <span style="color: #f1f5f9;">${config.provider || 'Not configured'}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155;">
                            <span style="color: #64748b;">Timezone</span>
                            <span style="color: #f1f5f9;">${config.timezone || 'UTC'}</span>
                        </div>
                    </div>
                    
                    <div style="margin-top: 24px;">
                        <h3 style="color: #94a3b8; font-size: 0.875rem; margin-bottom: 12px;">WORKSPACE</h3>
                        <div style="padding: 12px; background: #0f172a; border-radius: 8px; word-break: break-all; color: #f1f5f9; font-size: 0.875rem;">
                            ${config.workspace || 'N/A'}
                        </div>
                    </div>
                    
                    <div style="margin-top: 24px;">
                        <h3 style="color: #94a3b8; font-size: 0.875rem; margin-bottom: 12px;">CHANNELS</h3>
                        <div style="background: #0f172a; border-radius: 8px; padding: 0 12px;">
                            ${channelsHtml}
                        </div>
                    </div>
                </div>
            `;
        }
        
        async function loadPage(page) {
            const content = document.getElementById('content');
            const navLinks = document.querySelectorAll('.nav a');
            
            navLinks.forEach(a => a.classList.remove('active'));
            document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
            
            try {
                if (page === 'dashboard') {
                    const [status, sessions] = await Promise.all([
                        fetchStatus(),
                        fetchSessions()
                    ]);
                    content.innerHTML = renderDashboard(status, sessions);
                    
                    document.querySelectorAll('.session-item').forEach(item => {
                        item.addEventListener('click', () => {
                            loadSession(item.dataset.key);
                        });
                    });
                } else if (page === 'sessions') {
                    const sessions = await fetchSessions();
                    content.innerHTML = renderSessions(sessions);
                    
                    document.querySelectorAll('.session-item').forEach(item => {
                        item.addEventListener('click', () => {
                            loadSession(item.dataset.key);
                        });
                    });
                } else if (page === 'settings') {
                    const config = await fetchConfig();
                    content.innerHTML = renderSettings(config);
                }
            } catch (e) {
                content.innerHTML = `<div class="error">Failed to load: ${e.message}</div>`;
            }
        }
        
        async function loadSession(key) {
            const content = document.getElementById('content');
            content.innerHTML = '<div class="loading">Loading session...</div>';
            
            try {
                const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(key)}`);
                const session = await res.json();
                
                content.innerHTML = `
                    <div class="card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h2 style="color: #38bdf8;">Session: ${session.key}</h2>
                            <a href="#" onclick="loadPage('dashboard')" style="color: #94a3b8;">← Back</a>
                        </div>
                        <div class="sessions-list">
                            ${session.messages.map(m => `
                                <div class="session-item" style="background: ${m.role === 'user' ? '#1e3a5f' : '#0f172a'}">
                                    <div class="session-key">${m.role}</div>
                                    <div style="white-space: pre-wrap; font-size: 0.875rem;">${m.content || ''}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } catch (e) {
                content.innerHTML = `<div class="error">Failed to load session: ${e.message}</div>`;
            }
        }
        
        window.loadPage = loadPage;
        
        document.querySelectorAll('.nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                if (page) loadPage(page);
            });
        });
        
        loadPage('dashboard');
        
        setInterval(async () => {
            try {
                const status = await fetchStatus();
                document.querySelector('.status-badge').textContent = 'Online';
            } catch {
                document.querySelector('.status-badge').textContent = 'Offline';
            }
        }, 30000);
    </script>
</body>
</html>
"""
