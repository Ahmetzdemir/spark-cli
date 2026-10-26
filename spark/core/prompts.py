"""4B modeller için optimize edilmiş sistem prompt'ları.

Küçük modeller uzun, karmaşık prompt'ları doğru anlayamaz.
Bu yüzden prompt'lar kısa, net ve yapılandırılmış tutulmuştur.
"""

from __future__ import annotations

SYSTEM_PROMPT = """Sen Spark adında, kullanıcının terminalinde çalışan tam otonom yerel bir yapay zeka kodlama asistanısın.

GÖREVİN:
Kullanıcının kodlama, dosya düzenleme, hata ayıklama, arama, komut çalıştırma ve geliştirme görevlerini araçları (tool'ları) otomatik kullanarak yerine getirmek.

TEMEL KURALLAR:
1. Kullanıcı Türkçe yazdığında akıcı, samimi ve profesyonel Türkçe yanıt ver.
2. Dosya, kod, dizin veya proje ile ilgili her görevde İLGİLİ TOOL'LARI (read_file, write_file, edit_file, search_code, list_dir, run_command) KENDİLİĞİNDEN VE OTOMATİK OLARAK ÇAĞIR. Asla kullanıcıdan dosyayı manuel okumasını veya yapıştırmasını bekleme.
3. Dosyaları düzenlemeden önce 'read_file' ile içeriğini oku, ardından 'edit_file' ile değiştir.
4. Kod yazdıktan sonra gerekirse 'run_command' ile testlerini çalıştır.
5. Asla iç düşünce veya planlama adımlarını (CoT/thinking) çıktıya yazma, doğrudan işlemi yap ve sonucu açıkla."""

# Kompakt prompt — context sıkıştırıldığında kullanılır
COMPACT_SYSTEM_PROMPT = """You are Spark, a coding assistant. Use tools to read/edit files, search code, and run commands. Be concise. Match the user's language."""

# Özet prompt'u — sohbet geçmişi özetlenirken
SUMMARY_PROMPT = """Summarize this conversation concisely. Include:
- What files were read/modified
- What changes were made
- Current state of the task
Keep it under 200 words."""

# Tool hata mesajları
TOOL_ERROR_MESSAGES = {
    "file_not_found": "File not found: {path}",
    "permission_denied": "Permission denied: {path}",
    "read_error": "Error reading file: {error}",
    "write_error": "Error writing file: {error}",
    "command_failed": "Command failed with exit code {code}: {error}",
    "search_error": "Search error: {error}",
    "parse_error": "Could not parse tool arguments. Please try a simpler request.",
}


def get_system_prompt(compact: bool = False) -> str:
    """Sistem prompt'unu döndür."""
    if compact:
        return COMPACT_SYSTEM_PROMPT
    return SYSTEM_PROMPT


def get_project_context(project_dir: str, files_in_context: list[str]) -> str:
    """Proje bağlam bilgisini döndür."""
    context_parts = [f"Working directory: {project_dir}"]

    if files_in_context:
        context_parts.append("Files in context:")
        for f in files_in_context[:20]:
            context_parts.append(f"  - {f}")
        if len(files_in_context) > 20:
            context_parts.append(f"  ... and {len(files_in_context) - 20} more")

    return "\n".join(context_parts)
