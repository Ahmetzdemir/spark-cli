"""Tool registry — araç tanımlama, kayıt ve OpenAI schema üretimi.

4B modeller için schema'lar kasıtlı olarak basit tutulmuştur:
- Maksimum 5 parametre
- Basit tipler (string, integer, boolean)
- Net, kısa açıklamalar
- İç içe nesne yok
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class ToolParameter:
    """Bir tool parametresi."""
    name: str
    type: str  # "string", "integer", "boolean"
    description: str
    required: bool = True
    enum: list[str] | None = None


@dataclass
class ToolDefinition:
    """Bir tool tanımı."""
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    handler: Callable[..., str] | None = None

    def to_openai_schema(self) -> dict[str, Any]:
        """OpenAI function calling formatına dönüştür."""
        properties: dict[str, Any] = {}
        required_list: list[str] = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required_list.append(param.name)

        schema: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                },
            },
        }

        if required_list:
            schema["function"]["parameters"]["required"] = required_list

        return schema


class ToolRegistry:
    """Araç kayıt ve yönetim sistemi."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Tool kaydet."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """İsme göre tool döndür."""
        return self._tools.get(name)

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Tüm tool'ların OpenAI schema'larını döndür."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Tool'u çalıştır ve sonucu döndür."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"

        if not tool.handler:
            return f"Error: Tool '{name}' has no handler"

        try:
            return tool.handler(**args)
        except TypeError as e:
            return f"Error: Invalid arguments for '{name}': {e}"
        except Exception as e:
            return f"Error: Tool '{name}' failed: {type(e).__name__}: {e}"

    def list_tools(self) -> list[str]:
        """Kayıtlı tool adlarını döndür."""
        return list(self._tools.keys())

    @property
    def count(self) -> int:
        return len(self._tools)
