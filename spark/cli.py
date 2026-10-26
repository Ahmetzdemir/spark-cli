"""Spark CLI giriş noktası — argparse ile komut satırı arayüzü."""

from __future__ import annotations

import argparse
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from spark import __version__, __app_name__


def create_parser() -> argparse.ArgumentParser:
    """CLI argument parser oluştur."""
    parser = argparse.ArgumentParser(
        prog="spark",
        description="Spark - Yerel AI Kodlama Asistani",
        epilog="Örnekler:\n"
               "  spark                    Etkileşimli REPL başlat\n"
               '  spark "bu hatayı düzelt" Tek seferlik komut\n'
               "  spark --model qwen3-4b   Belirli modelle başlat\n"
               "  spark init               Proje config oluştur\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Kullanılacak model adı (örn: qwen3-4b, phi-4-mini)",
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="LM Studio sunucu portu (varsayılan: 1234)",
    )

    parser.add_argument(
        "--url",
        default=None,
        help="LM Studio API URL'i (varsayılan: http://localhost:1234/v1)",
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"{__app_name__} v{__version__}",
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        default=True,
        help="Tüm araç çağrılarını otomatik onayla (varsayılan: aktif)",
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        default=[],
        help="Tek seferlik istek (opsiyonel). Belirtilmezse REPL başlar.",
    )

    return parser


def main() -> None:
    """Ana giriş noktası."""
    # Subcommand kontrolü
    raw_args = sys.argv[1:]

    # Config yükle
    from spark.config import SparkConfig
    config = SparkConfig.load()

    # Hızlı alt komut kontrolleri
    if raw_args and raw_args[0] == "init":
        _cmd_init(config)
        return
    if raw_args and raw_args[0] == "test":
        _cmd_test(config)
        return

    parser = create_parser()
    args = parser.parse_args()

    # Port/URL override
    if args.port:
        config.llm.base_url = f"http://localhost:{args.port}/v1"
    if args.url:
        config.llm.base_url = args.url

    # Prompt birleştir
    prompt_str = " ".join(args.prompt).strip() if args.prompt else None

    # Ana uygulama başlat
    from spark.app import SparkApp
    app = SparkApp(
        config=config,
        model_override=args.model,
    )
    app.run(one_shot=prompt_str)


def _cmd_init(config) -> None:
    """Proje config oluştur."""
    from pathlib import Path
    from spark.ui.console import print_success, print_info

    project_dir = Path.cwd()
    config.save_project_config(project_dir)
    print_success(f".spark/settings.toml oluşturuldu: {project_dir}")
    print_info("Ayarları düzenlemek için .spark/settings.toml dosyasını açın.")


def _cmd_test(config) -> None:
    """LM Studio bağlantısını test et."""
    from spark.llm.client import LMStudioClient
    from spark.ui.console import print_success, print_error, print_info

    print_info(f"Bağlantı test ediliyor: {config.llm.base_url}")

    client = LMStudioClient(config.llm)
    success, message = client.test_connection()

    if success:
        print_success(message)

        # Model bilgisi
        from spark.llm.models import get_model_profile
        model_name = client.model_name
        profile = get_model_profile(model_name)
        print_info(f"Model profili: {profile.display_name}")
        print_info(f"Context window: {profile.context_window:,} token")
        print_info(f"Tool calling: {'✓ Destekli' if profile.supports_tool_calling else '✗ Desteklenmiyor'}")
    else:
        print_error(message)
        sys.exit(1)


if __name__ == "__main__":
    main()
