"""Configuration schema using Pydantic."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings


class Base(BaseModel):
    """Base model that accepts both camelCase and snake_case keys."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ACPConfig(Base):
    """ACP (Agent Client Protocol) configuration."""

    enabled: bool = False
    default_agent: str = "codex"
    allowed_agents: list[str] = Field(default_factory=lambda: ["codex", "claude", "opencode"])
    max_concurrent_sessions: int = 8


class ACPThreadBindingsConfig(Base):
    """ACP thread binding configuration."""

    enabled: bool = False
    spawn_acp_sessions: bool = False  # Allow spawning ACP sessions in threads
    idle_hours: int = 24
    max_age_hours: int = 0


class ChannelsConfig(Base):
    """Configuration for chat channels.

    Built-in and plugin channel configs are stored as extra fields (dicts).
    Each channel parses its own config in __init__.
    Per-channel "streaming": true enables streaming output (requires send_delta impl).
    """

    model_config = ConfigDict(extra="allow")

    send_progress: bool = True  # stream agent's text progress to the channel
    send_tool_hints: bool = False  # stream tool-call hints (e.g. read_file("…"))
    send_max_retries: int = Field(default=3, ge=0, le=10)  # Max delivery attempts (initial send included)


class AgentDefaults(Base):
    """Default agent configuration optimized for Qwen2.5-8B via LM Studio."""

    workspace: str = "~/.nanobot/workspace"
    model: str = "qwen2.5-8b-instruct"  # Optimized for local 8B model
    provider: str = (
        "auto"  # Provider name (e.g. "anthropic", "openrouter") or "auto" for auto-detection
    )
    max_tokens: int = 4096  # Reduced for 8B efficiency
    context_window_tokens: int = 128_000  # Full context for Qwen2.5
    temperature: float = 0.7  # Slightly higher for creativity
    max_tool_iterations: int = 30  # Reduced - 8B is faster
    reasoning_effort: str | None = None  # low / medium / high - enables LLM thinking mode
    timezone: str = "UTC"  # IANA timezone, e.g. "Asia/Shanghai", "America/New_York"


class AgentsConfig(Base):
    """Agent configuration."""

    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class LMStudioSettings(BaseModel):
    """LM Studio-specific configuration."""

    context_length: int = 32768
    flash_attention: bool = True
    eval_batch_size: int = 512
    offload_kv_cache_to_gpu: bool = True
    auto_load: bool = True
    use_stateful_chat: bool = True
    llama_k_cache_quantization_type: str = "Q8_0"
    llama_v_cache_quantization_type: str = "Q4_0"


class OllamaSettings(BaseModel):
    """Ollama-specific configuration."""

    use_native_api: bool = True  # Use native /api/chat instead of OpenAI compat
    think: str | None = None  # "high", "medium", "low" - enable thinking mode
    keep_alive: str = "5m"  # Model keep-alive duration


class ProviderConfig(Base):
    """LLM provider configuration."""

    api_key: str = ""
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None  # Custom headers (e.g. APP-Code for AiHubMix)


class ProvidersConfig(Base):
    """Configuration for LLM providers."""

    custom: ProviderConfig = Field(default_factory=ProviderConfig)  # Any OpenAI-compatible endpoint
    azure_openai: ProviderConfig = Field(default_factory=ProviderConfig)  # Azure OpenAI (model = deployment name)
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    groq: ProviderConfig = Field(default_factory=ProviderConfig)
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)
    dashscope: ProviderConfig = Field(default_factory=ProviderConfig)
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)
    ollama: ProviderConfig = Field(default_factory=ProviderConfig)  # Ollama local models
    ovms: ProviderConfig = Field(default_factory=ProviderConfig)  # OpenVINO Model Server (OVMS)
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)
    minimax: ProviderConfig = Field(default_factory=ProviderConfig)
    mistral: ProviderConfig = Field(default_factory=ProviderConfig)
    stepfun: ProviderConfig = Field(default_factory=ProviderConfig)  # Step Fun (阶跃星辰)
    qianfan: ProviderConfig = Field(default_factory=ProviderConfig)  # Baidu Qianfan (百度千帆)
    mimo: ProviderConfig = Field(default_factory=ProviderConfig)  # Xiaomi MiMo
    aihubmix: ProviderConfig = Field(default_factory=ProviderConfig)  # AiHubMix API gateway
    siliconflow: ProviderConfig = Field(default_factory=ProviderConfig)  # SiliconFlow (硅基流动)
    volcengine: ProviderConfig = Field(default_factory=ProviderConfig)  # VolcEngine (火山引擎)
    volcengine_coding_plan: ProviderConfig = Field(default_factory=ProviderConfig)  # VolcEngine Coding Plan
    byteplus: ProviderConfig = Field(default_factory=ProviderConfig)  # BytePlus (VolcEngine international)
    byteplus_coding_plan: ProviderConfig = Field(default_factory=ProviderConfig)  # BytePlus Coding Plan
    openai_codex: ProviderConfig = Field(default_factory=ProviderConfig, exclude=True)  # OpenAI Codex (OAuth)
    github_copilot: ProviderConfig = Field(default_factory=ProviderConfig, exclude=True)  # Github Copilot (OAuth)
    lmstudio: ProviderConfig = Field(default_factory=ProviderConfig)  # LM Studio (local, with native API support)
    lmstudio_settings: LMStudioSettings = Field(default_factory=LMStudioSettings)
    ollama_settings: OllamaSettings = Field(default_factory=OllamaSettings)


class HeartbeatConfig(Base):
    """Heartbeat service configuration."""

    enabled: bool = True
    interval_s: int = 30 * 60  # 30 minutes
    keep_recent_messages: int = 8


class GatewayConfig(Base):
    """Gateway/server configuration."""

    host: str = "127.0.0.1"  # Bind to localhost by default for security
    port: int = 18790
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)


class WebSearchConfig(Base):
    """Web search tool configuration."""

    provider: str = "brave"  # brave, tavily, duckduckgo, searxng, jina
    api_key: str = ""
    base_url: str = ""  # SearXNG base URL
    max_results: int = 5


class WebToolsConfig(Base):
    """Web tools configuration."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = True  # Toggle for all web tools
    proxy: str | None = (
        None  # HTTP/SOCKS5 proxy URL, e.g. "http://127.0.0.1:7890" or "socks5://127.0.0.1:1080"
    )
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(Base):
    """Shell exec tool configuration."""

    enable: bool = True
    timeout: int = 60
    path_append: str = ""

class MCPServerConfig(Base):
    """MCP server connection configuration (stdio or HTTP)."""

    type: Literal["stdio", "sse", "streamableHttp"] | None = None  # auto-detected if omitted
    command: str = ""  # Stdio: command to run (e.g. "npx")
    args: list[str] = Field(default_factory=list)  # Stdio: command arguments
    env: dict[str, str] = Field(default_factory=dict)  # Stdio: extra env vars
    url: str = ""  # HTTP/SSE: endpoint URL
    headers: dict[str, str] = Field(default_factory=dict)  # HTTP/SSE: custom headers
    tool_timeout: int = 30  # seconds before a tool call is cancelled
    enabled_tools: list[str] = Field(default_factory=lambda: ["*"])  # Only register these tools; accepts raw MCP names or wrapped mcp_<server>_<tool> names; ["*"] = all tools; [] = no tools


class PaperclipConfig(Base):
    """Paperclip task management integration configuration."""

    enabled: bool = False  # Enable Paperclip integration
    api_url: str = "http://127.0.0.1:3100"  # Paperclip API URL
    company_id: str = ""  # Company ID in Paperclip
    agent_id: str = ""  # Agent ID for task assignment
    poll_interval_seconds: int = 300  # How often to poll for new tasks (5 minutes default)
    auto_claim: bool = True  # Automatically claim tasks when found
    default_assignee: str = ""  # Default assignee for new tasks


class QMDPathConfig(Base):
    """Configuration for an extra path to index with QMD."""

    name: str = ""  # Collection name
    path: str = ""  # Directory path (supports ~ expansion)
    pattern: str = "**/*"  # Glob pattern for files to index


class QMDSessionsConfig(Base):
    """Configuration for session transcript indexing."""

    enabled: bool = True  # Enable session indexing by default


class QMDSearchScopeRule(Base):
    """Search scope rule for QMD."""

    action: Literal["allow", "deny"] = "deny"
    match: dict[str, str] = Field(default_factory=dict)  # e.g. {"chatType": "direct"}


class QMDSearchScope(Base):
    """Search scope configuration for QMD."""

    default: Literal["allow", "deny"] = "deny"
    rules: list[QMDSearchScopeRule] = Field(default_factory=list)


class QMDLimitsConfig(Base):
    """Limits for QMD operations optimized for 8B models."""

    timeout_ms: int = 2000  # Reduced for faster 8B models


class QMDConfig(Base):
    """QMD memory engine configuration."""

    paths: list[QMDPathConfig] = Field(default_factory=list)  # Extra paths to index
    sessions: QMDSessionsConfig = Field(default_factory=QMDSessionsConfig)
    scope: QMDSearchScope = Field(default_factory=QMDSearchScope)
    limits: QMDLimitsConfig = Field(default_factory=QMDLimitsConfig)
    update_interval_seconds: int = 300  # Periodic update interval (default: 5 min)


class MemoryConfig(Base):
    """Memory system configuration."""

    backend: Literal["builtin", "qmd"] = "builtin"  # Default to builtin, QMD is opt-in
    qmd: QMDConfig = Field(default_factory=QMDConfig)
    citations: Literal["auto", "on", "off"] = "auto"  # Include citations in search results
    dreaming: "DreamingConfig" = Field(default_factory=lambda: DreamingConfig())  # Dreaming configuration
    versioning: bool = True  # Enable git-versioned memory storage
    templating: bool = True  # Enable Jinja2 templating for responses


class DreamingPhaseConfig(Base):
    """Base configuration for a dreaming phase."""

    enabled: bool = True
    cron: str = ""  # Cron schedule
    limit: int = 10  # Max entries to process per run
    lookback_days: int = 2  # How many days to look back
    sources: list[str] = Field(default_factory=list)  # Data sources to scan


class DreamingLightConfig(DreamingPhaseConfig):
    """Light phase configuration - organizes and stages candidates."""

    cron: str = "0 */6 * * *"  # Every 6 hours
    lookback_days: int = 2
    limit: int = 100
    dedupe_similarity: float = 0.9  # Jaccard threshold for dedup
    sources: list[str] = Field(default_factory=lambda: ["daily", "sessions", "recall"])


class DreamingDeepConfig(DreamingPhaseConfig):
    """Deep phase configuration - promotes candidates to durable memory (optimized for 8B)."""

    cron: str = "0 3 * * *"  # Daily at 3 AM
    lookback_days: int = 30
    limit: int = 10
    min_score: float = 0.7  # Lower threshold for 8B with larger context
    min_recall_count: int = 2  # Reduced threshold
    min_unique_queries: int = 2  # Reduced threshold
    recency_half_life_days: int = 14  # Days for recency score to halve
    max_age_days: int = 30  # Max daily-note age for promotion
    sources: list[str] = Field(default_factory=lambda: ["daily", "memory", "sessions", "logs", "recall"])
    recovery: "DreamingRecoveryConfig" = Field(default_factory=lambda: DreamingRecoveryConfig())


class DreamingRecoveryConfig(Base):
    """Deep phase recovery configuration."""

    enabled: bool = True
    trigger_below_health: float = 0.35  # Health threshold to trigger recovery
    lookback_days: int = 30
    max_recovered_candidates: int = 20
    min_recovery_confidence: float = 0.9
    auto_write_min_confidence: float = 0.97


class DreamingREMConfig(DreamingPhaseConfig):
    """REM phase configuration - pattern detection and reflection."""

    cron: str = "0 5 * * 0"  # Weekly, Sunday 5 AM
    lookback_days: int = 7
    limit: int = 10
    min_pattern_strength: float = 0.75  # Minimum tag co-occurrence strength
    sources: list[str] = Field(default_factory=lambda: ["memory", "daily", "deep"])


class DreamingConfig(Base):
    """Dreaming memory consolidation configuration."""

    enabled: bool = True
    timezone: str | None = None
    verbose_logging: bool = False
    light: DreamingLightConfig = Field(default_factory=DreamingLightConfig)
    deep: DreamingDeepConfig = Field(default_factory=DreamingDeepConfig)
    rem: DreamingREMConfig = Field(default_factory=DreamingREMConfig)


class ToolsConfig(Base):
    """Tools configuration."""

    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    restrict_to_workspace: bool = False  # If true, restrict all tool access to workspace directory
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    paperclip: PaperclipConfig = Field(default_factory=PaperclipConfig)  # Paperclip integration
    memory: MemoryConfig = Field(default_factory=MemoryConfig)


class LangfuseConfig(Base):
    """Langfuse observability configuration."""

    enabled: bool = False
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"  # or self-hosted URL
    release: str | None = None  # e.g. "1.0.0" for release tracking


class Config(BaseSettings):
    """Root configuration for nanobot."""

    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    acp: ACPConfig = Field(default_factory=ACPConfig)
    ssrf_whitelist: list[str] = Field(default_factory=list)  # Additional CIDR ranges to allow (e.g. Tailscale/CGNAT)
    langfuse: "LangfuseConfig" = Field(default_factory=lambda: LangfuseConfig())  # Langfuse observability

    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()

    def _match_provider(
        self, model: str | None = None
    ) -> tuple["ProviderConfig | None", str | None]:
        """Match provider config and its registry name. Returns (config, spec_name)."""
        from nanobot.providers.registry import PROVIDERS, find_by_name

        forced = self.agents.defaults.provider
        if forced != "auto":
            spec = find_by_name(forced)
            if spec:
                p = getattr(self.providers, spec.name, None)
                return (p, spec.name) if p else (None, None)
            return None, None

        model_lower = (model or self.agents.defaults.model).lower()
        model_normalized = model_lower.replace("-", "_")
        model_prefix = model_lower.split("/", 1)[0] if "/" in model_lower else ""
        normalized_prefix = model_prefix.replace("-", "_")

        def _kw_matches(kw: str) -> bool:
            kw = kw.lower()
            return kw in model_lower or kw.replace("-", "_") in model_normalized

        # Explicit provider prefix wins — prevents `github-copilot/...codex` matching openai_codex.
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and model_prefix and normalized_prefix == spec.name:
                if spec.is_oauth or spec.is_local or p.api_key:
                    return p, spec.name

        # Match by keyword (order follows PROVIDERS registry)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(_kw_matches(kw) for kw in spec.keywords):
                if spec.is_oauth or spec.is_local or p.api_key:
                    return p, spec.name

        # Fallback: configured local providers can route models without
        # provider-specific keywords (for example plain "llama3.2" on Ollama).
        # Prefer providers whose detect_by_base_keyword matches the configured api_base
        # (e.g. Ollama's "11434" in "http://localhost:11434") over plain registry order.
        local_fallback: tuple[ProviderConfig, str] | None = None
        for spec in PROVIDERS:
            if not spec.is_local:
                continue
            p = getattr(self.providers, spec.name, None)
            if not (p and p.api_base):
                continue
            if spec.detect_by_base_keyword and spec.detect_by_base_keyword in p.api_base:
                return p, spec.name
            if local_fallback is None:
                local_fallback = (p, spec.name)
        if local_fallback:
            return local_fallback

        # Fallback: gateways first, then others (follows registry order)
        # OAuth providers are NOT valid fallbacks — they require explicit model selection
        for spec in PROVIDERS:
            if spec.is_oauth:
                continue
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key:
                return p, spec.name
        return None, None

    def get_provider(self, model: str | None = None) -> ProviderConfig | None:
        """Get matched provider config (api_key, api_base, extra_headers). Falls back to first available."""
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model: str | None = None) -> str | None:
        """Get the registry name of the matched provider (e.g. "deepseek", "openrouter")."""
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model: str | None = None) -> str | None:
        """Get API key for the given model. Falls back to first available key."""
        p = self.get_provider(model)
        return p.api_key if p else None

    def get_api_base(self, model: str | None = None) -> str | None:
        """Get API base URL for the given model. Applies default URLs for gateway/local providers."""
        from nanobot.providers.registry import find_by_name

        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        # Only gateways get a default api_base here. Standard providers
        # resolve their base URL from the registry in the provider constructor.
        if name:
            spec = find_by_name(name)
            if spec and (spec.is_gateway or spec.is_local) and spec.default_api_base:
                return spec.default_api_base
        return None

    model_config = ConfigDict(env_prefix="NANOBOT_", env_nested_delimiter="__", extra="allow")
