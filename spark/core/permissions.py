"""İzin sistemi — 3 katmanlı güvenlik modeli."""

from __future__ import annotations

from enum import Enum
from typing import Any

from spark.config import PermissionsConfig


class PermissionLevel(Enum):
    """İzin seviyeleri."""
    READ = "read"         # Otomatik onay
    WRITE = "write"       # Kullanıcı onayı gerekli
    DANGEROUS = "dangerous"  # Her seferinde onay


# Tool → izin seviyesi eşlemesi
TOOL_PERMISSIONS: dict[str, PermissionLevel] = {
    "read_file": PermissionLevel.READ,
    "list_dir": PermissionLevel.READ,
    "search_code": PermissionLevel.READ,
    "git_status": PermissionLevel.READ,
    "git_diff": PermissionLevel.READ,
    "web_search": PermissionLevel.READ,

    "write_file": PermissionLevel.WRITE,
    "edit_file": PermissionLevel.WRITE,
    "git_commit": PermissionLevel.WRITE,

    "run_command": PermissionLevel.DANGEROUS,
}


class PermissionManager:
    """İzin yöneticisi."""

    def __init__(self, config: PermissionsConfig) -> None:
        self.config = config
        # Oturum boyunca "her zaman" onaylanan tool'lar
        self._session_approved: set[str] = set()
        # Oturum boyunca "her zaman" onaylanan komutlar
        self._approved_commands: set[str] = set()

    def check_permission(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Tool çağrısı için izin kontrolü.

        Returns:
            (izin_var_mı, açıklama_mesajı)
        """
        level = TOOL_PERMISSIONS.get(tool_name, PermissionLevel.DANGEROUS)

        # READ seviyesi → her zaman izin
        if level == PermissionLevel.READ:
            return True, ""

        # Genel otomatik onay aktif mi?
        if getattr(self.config, "auto_approve_all", False):
            if tool_name == "run_command" and args:
                command = args.get("command", "")
                if self._is_blocked_command(command):
                    return False, f"🚫 Bu komut engellenmiştir: {command}"
            return True, ""

        # Oturum boyunca onaylanmış mı?
        if tool_name in self._session_approved:
            return True, ""

        # WRITE seviyesi → config'e bak
        if level == PermissionLevel.WRITE:
            if self.config.auto_approve_write or getattr(self.config, "auto_approve_all", False):
                return True, ""

            detail = self._get_write_detail(tool_name, args)
            return False, detail

        # DANGEROUS seviyesi → komut kontrolü
        if tool_name == "run_command" and args:
            command = args.get("command", "")

            # Engelli komutlar
            if self._is_blocked_command(command):
                return False, f"🚫 Bu komut engellenmiştir: {command}"

            # Otomatik çalıştırma izni var mı?
            if getattr(self.config, "auto_approve_execute", False) or getattr(self.config, "auto_approve_all", False):
                return True, ""

            # Beyaz listedeki komutlar
            if self._is_whitelisted_command(command):
                return True, ""

            # Daha önce onaylanmış komutlar
            if command in self._approved_commands:
                return True, ""

            return False, f"Bu komutu çalıştırmak istiyor: {command}"

        return False, f"Bu işlem onay gerektirir: {tool_name}"

    def approve_session(self, tool_name: str) -> None:
        """Tool'u oturum boyunca onaylı yap."""
        self._session_approved.add(tool_name)

    def approve_command(self, command: str) -> None:
        """Komutu oturum boyunca onaylı yap."""
        self._approved_commands.add(command)

    def _is_blocked_command(self, command: str) -> bool:
        """Komutun engellenmiş olup olmadığını kontrol et."""
        cmd_lower = command.lower().strip()
        return any(
            blocked.lower() in cmd_lower
            for blocked in self.config.blocked_commands
        )

    def _is_whitelisted_command(self, command: str) -> bool:
        """Komutun beyaz listede olup olmadığını kontrol et."""
        cmd_lower = command.lower().strip()
        return any(
            cmd_lower.startswith(allowed.lower())
            for allowed in self.config.whitelisted_commands
        )

    def _get_write_detail(self, tool_name: str, args: dict[str, Any] | None) -> str:
        """Yazma işlemi için detay mesajı oluştur."""
        if not args:
            return f"{tool_name} işlemi dosya değişikliği yapacak."

        if tool_name in ("write_file", "edit_file"):
            path = args.get("path", "?")
            return f"Dosyayı değiştirmek istiyor: {path}"

        if tool_name == "git_commit":
            msg = args.get("message", "")
            return f'Git commit: "{msg}"'

        return f"{tool_name} onay bekliyor."
