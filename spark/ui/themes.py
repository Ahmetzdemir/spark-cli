"""Spark Claude Code Stili Renk Teması ve İkonlar."""

from __future__ import annotations

from rich.theme import Theme


CLAUDE_STYLE_COLORS = {
    # Ana renkler (Claude Code Minimalist Paleti)
    "spark.accent": "#D97706",        # Sıcak Amber / Terracotta
    "spark.accent_bright": "#F59E0B", # Parlak Amber
    "spark.accent_dim": "#78350F",    # Koyu Amber
    "spark.success": "#10B981",       # Zümrüt Yeşili
    "spark.warning": "#F59E0B",       # Uyarı Sarısı
    "spark.error": "#EF4444",         # Hata Kırmızısı
    "spark.info": "#0EA5E9",          # Gökyüzü Mavisi

    # UI elementleri
    "spark.border": "#334155",        # İnce Slate Çizgiler
    "spark.border_active": "#64748B", # Vurgulu Çizgi
    "spark.muted": "#64748B",         # Soluk Yazı / Çizgi
    "spark.bg_highlight": "#0F172A",  # Koyu Zemin

    # Metin
    "spark.text": "#F8FAFC",          # Parlak Beyaz
    "spark.text_dim": "#94A3B8",      # Açık Gri
    "spark.thinking": "italic #64748B",# Düşünce Süreci (Soluk Gri)

    # Roller
    "spark.user": "bold #F8FAFC",
    "spark.assistant": "bold #D97706",
    "spark.system": "italic #64748B",
    "spark.tool_name": "bold #38BDF8",
    "spark.tool_result": "#94A3B8",

    # Diff (Claude Code Stili)
    "spark.diff_add": "#10B981",
    "spark.diff_remove": "#EF4444",
    "spark.diff_header": "bold #38BDF8",
}


def get_spark_theme() -> Theme:
    """Claude Code minimalist temasını döndür."""
    return Theme(CLAUDE_STYLE_COLORS)


# Sabit Minimalist UI İkonları
ICONS = {
    "spark": "⚡",
    "user": "›",
    "thinking": "◆",
    "tool": "●",
    "success": "✓",
    "error": "✗",
    "warning": "▲",
    "info": "ℹ",
    "file": "📄",
    "folder": "📁",
    "search": "🔍",
    "edit": "✏️",
    "shell": "💻",
    "git": "🔀",
    "web": "🌐",
    "lock": "🔒",
    "arrow_right": "→",
    "arrow_down": "↓",
    "dot": "·",
    "bar": "│",
    "corner": "└",
    "tee": "├",
    "card_tl": "╭",
    "card_tr": "╮",
    "card_bl": "╰",
    "card_br": "╯",
}
