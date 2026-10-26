"""Spark CLI konfigürasyon yönetimi."""

from __future__ import annotations

import os
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONFIG_DIR_NAME = ".spark"
CONFIG_FILE_NAME = "settings.toml"
HISTORY_DIR_NAME = "history"


@dataclass
class PermissionsConfig:
    """İzin sistemi ayarları."""
    auto_approve_read: bool = True
    auto_approve_write: bool = True
    auto_approve_execute: bool = True
    auto_approve_all: bool = True
    whitelisted_commands: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /", "del /s /q C:\\", "format", "mkfs",
        ":(){ :|:& };:", "shutdown", "reboot",
    ])


@dataclass
class LLMConfig:
    """LLM bağlantı ayarları."""
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lmstudio"
    model: str = "auto"
    temperature: float = 0.15
    max_tokens: int = 4096
    timeout: int = 120


@dataclass
class UIConfig:
    """Arayüz ayarları."""
    theme: str = "spark"
    show_token_usage: bool = True
    show_tool_calls: bool = True
    markdown_rendering: bool = True
    max_diff_lines: int = 50


@dataclass
class AgentConfig:
    """Agent döngüsü ayarları."""
    max_iterations: int = 15
    max_tool_retries: int = 3
    loop_detection_threshold: int = 3
    max_file_read_chars: int = 10000
    max_tool_result_chars: int = 5000


@dataclass
class SparkConfig:
    """Ana konfigürasyon sınıfı."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def load(cls, project_dir: Path | None = None) -> "SparkConfig":
        """Konfigürasyonu yükle. Önce proje dizininden, yoksa varsayılanları kullan."""
        config = cls()

        # Proje dizini config
        if project_dir:
            project_config_path = project_dir / CONFIG_DIR_NAME / CONFIG_FILE_NAME
            if project_config_path.exists():
                config._merge_from_file(project_config_path)

        # Global config (~/.spark/settings.toml)
        global_config_path = Path.home() / CONFIG_DIR_NAME / CONFIG_FILE_NAME
        if global_config_path.exists():
            config._merge_from_file(global_config_path)

        # Çevre değişkenleri override
        config._apply_env_overrides()

        return config

    def _merge_from_file(self, path: Path) -> None:
        """TOML dosyasından config yükle ve mevcut config'e birleştir."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            self._merge_dict(data)
        except Exception:
            pass  # Config dosyası okunamazsa sessizce devam et

    def _merge_dict(self, data: dict[str, Any]) -> None:
        """Dict'i config'e birleştir."""
        if "llm" in data:
            for key, value in data["llm"].items():
                if hasattr(self.llm, key):
                    setattr(self.llm, key, value)

        if "permissions" in data:
            for key, value in data["permissions"].items():
                if hasattr(self.permissions, key):
                    setattr(self.permissions, key, value)

        if "ui" in data:
            for key, value in data["ui"].items():
                if hasattr(self.ui, key):
                    setattr(self.ui, key, value)

        if "agent" in data:
            for key, value in data["agent"].items():
                if hasattr(self.agent, key):
                    setattr(self.agent, key, value)

    def _apply_env_overrides(self) -> None:
        """Çevre değişkenlerinden override."""
        if url := os.environ.get("SPARK_LLM_URL"):
            self.llm.base_url = url
        if key := os.environ.get("SPARK_API_KEY"):
            self.llm.api_key = key
        if model := os.environ.get("SPARK_MODEL"):
            self.llm.model = model

    def get_project_config_dir(self, project_dir: Path) -> Path:
        """Proje config dizinini döndür."""
        return project_dir / CONFIG_DIR_NAME

    def save_project_config(self, project_dir: Path) -> None:
        """Proje config'ini kaydet."""
        config_dir = self.get_project_config_dir(project_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / CONFIG_FILE_NAME

        content = f"""# Spark CLI Proje Ayarları
# Daha fazla bilgi: spark --help

[llm]
base_url = "{self.llm.base_url}"
model = "{self.llm.model}"
temperature = {self.llm.temperature}
max_tokens = {self.llm.max_tokens}

[permissions]
auto_approve_write = {str(self.permissions.auto_approve_write).lower()}
whitelisted_commands = {self.permissions.whitelisted_commands}
blocked_commands = {self.permissions.blocked_commands}

[ui]
theme = "{self.ui.theme}"
show_token_usage = {str(self.ui.show_token_usage).lower()}
show_tool_calls = {str(self.ui.show_tool_calls).lower()}

[agent]
max_iterations = {self.agent.max_iterations}
max_tool_retries = {self.agent.max_tool_retries}
"""
        config_path.write_text(content, encoding="utf-8")
