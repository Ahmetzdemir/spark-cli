"""Model registry ve profilleri. Her 4B model için optimize edilmiş ayarlar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelProfile:
    """Bir modelin optimize edilmiş profili."""
    id: str
    display_name: str
    context_window: int
    recommended_max_tokens: int
    temperature: float
    supports_tool_calling: bool
    tool_call_format: str  # "openai" veya "native"
    system_prompt_style: str  # "concise" veya "structured"
    strengths: list[str]


# Desteklenen 4B model profilleri
MODEL_PROFILES: dict[str, ModelProfile] = {
    "qwen3-4b": ModelProfile(
        id="qwen3-4b",
        display_name="Qwen3 4B Instruct",
        context_window=32768,
        recommended_max_tokens=4096,
        temperature=0.15,
        supports_tool_calling=True,
        tool_call_format="openai",
        system_prompt_style="concise",
        strengths=["function_calling", "turkish", "coding"],
    ),
    "phi-4-mini": ModelProfile(
        id="phi-4-mini",
        display_name="Phi-4 Mini (3.8B)",
        context_window=16384,
        recommended_max_tokens=2048,
        temperature=0.1,
        supports_tool_calling=True,
        tool_call_format="openai",
        system_prompt_style="structured",
        strengths=["reasoning", "math", "coding"],
    ),
    "gemma-4-4b": ModelProfile(
        id="gemma-4-4b",
        display_name="Gemma 4 (4B)",
        context_window=32768,
        recommended_max_tokens=4096,
        temperature=0.15,
        supports_tool_calling=True,
        tool_call_format="openai",
        system_prompt_style="concise",
        strengths=["function_calling", "general"],
    ),
}

# Varsayılan profil (model tanınmadığında kullanılır)
DEFAULT_PROFILE = ModelProfile(
    id="unknown",
    display_name="Bilinmeyen Model",
    context_window=8192,
    recommended_max_tokens=2048,
    temperature=0.15,
    supports_tool_calling=True,
    tool_call_format="openai",
    system_prompt_style="concise",
    strengths=[],
)


def get_model_profile(model_name: str) -> ModelProfile:
    """Model adına göre profil döndür. Bulunamazsa varsayılan profil döner."""
    # Tam eşleşme
    if model_name in MODEL_PROFILES:
        return MODEL_PROFILES[model_name]

    # Kısmi eşleşme (örn. "qwen3-4b-instruct" → "qwen3-4b")
    model_lower = model_name.lower()
    for key, profile in MODEL_PROFILES.items():
        if key in model_lower or model_lower in key:
            return profile

    # Akıllı eşleşme: bilinen model ailelerine bak
    family_map = {
        "qwen": "qwen3-4b",
        "phi": "phi-4-mini",
        "gemma": "gemma-4-4b",
    }
    for family, profile_key in family_map.items():
        if family in model_lower:
            profile = MODEL_PROFILES[profile_key]
            # id'yi güncelle ama diğer ayarları koru
            return ModelProfile(
                id=model_name,
                display_name=f"{profile.display_name} ({model_name})",
                context_window=profile.context_window,
                recommended_max_tokens=profile.recommended_max_tokens,
                temperature=profile.temperature,
                supports_tool_calling=profile.supports_tool_calling,
                tool_call_format=profile.tool_call_format,
                system_prompt_style=profile.system_prompt_style,
                strengths=profile.strengths,
            )

    return DEFAULT_PROFILE


def list_known_models() -> list[ModelProfile]:
    """Bilinen tüm model profillerini döndür."""
    return list(MODEL_PROFILES.values())
