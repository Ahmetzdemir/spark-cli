"""Streaming yanıt işleme."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamedToolCall:
    """Streaming sırasında biriken tool call verisi."""
    id: str = ""
    name: str = ""
    arguments: str = ""

    @property
    def is_complete(self) -> bool:
        return bool(self.id and self.name and self.arguments)

    def parse_arguments(self) -> dict[str, Any]:
        """Arguments JSON'ını parse et."""
        try:
            return json.loads(self.arguments)
        except json.JSONDecodeError:
            # 4B modeller bazen hatalı JSON üretir, basit düzeltme dene
            return self._try_fix_json(self.arguments)

    @staticmethod
    def _try_fix_json(raw: str) -> dict[str, Any]:
        """Hatalı JSON'ı düzeltmeye çalış."""
        cleaned = raw.strip()

        # Sondaki virgülü kaldır
        if cleaned.endswith(",}"):
            cleaned = cleaned[:-2] + "}"
        elif cleaned.endswith(","):
            cleaned = cleaned[:-1] + "}"

        # Başlangıç/bitiş süslü parantez eksikse ekle
        if not cleaned.startswith("{"):
            cleaned = "{" + cleaned
        if not cleaned.endswith("}"):
            cleaned = cleaned + "}"

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"_raw": raw, "_parse_error": True}


@dataclass
class StreamAccumulator:
    """Streaming yanıt biriktiricisi."""
    content: str = ""
    reasoning_content: str = ""
    tool_calls: list[StreamedToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    _current_tool_calls: dict[int, StreamedToolCall] = field(default_factory=dict)

    def process_chunk(self, chunk: Any) -> str | None:
        """Bir stream chunk'ını işle. Yeni metin içeriği varsa döndür."""
        if not chunk.choices:
            # Usage chunk (bazı modeller sonunda gönderir)
            if hasattr(chunk, "usage") and chunk.usage:
                self.usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens or 0,
                    "completion_tokens": chunk.usage.completion_tokens or 0,
                    "total_tokens": chunk.usage.total_tokens or 0,
                }
            return None

        choice = chunk.choices[0]
        delta = choice.delta

        # Finish reason
        if choice.finish_reason:
            self.finish_reason = choice.finish_reason

        # Metin içeriği
        new_text = None
        if delta and delta.content:
            self.content += delta.content
            new_text = delta.content

        # Düşünme içeriği (Thinking / reasoning modelleri için)
        if delta and hasattr(delta, "reasoning_content") and delta.reasoning_content:
            self.reasoning_content += delta.reasoning_content

        # Tool calls
        if delta and delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in self._current_tool_calls:
                    self._current_tool_calls[idx] = StreamedToolCall()

                tc = self._current_tool_calls[idx]

                if tc_delta.id:
                    tc.id = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tc.name = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tc.arguments += tc_delta.function.arguments

        return new_text

    def finalize(self) -> None:
        """Stream tamamlandığında tool call'ları sonlandır."""
        self.tool_calls = [
            self._current_tool_calls[idx]
            for idx in sorted(self._current_tool_calls.keys())
        ]

    @property
    def has_tool_calls(self) -> bool:
        return bool(self._current_tool_calls)

    @property
    def is_tool_call(self) -> bool:
        return self.finish_reason == "tool_calls" or bool(self._current_tool_calls)
