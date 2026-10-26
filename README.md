# ⚡ Spark CLI

**Yerel AI Kodlama Asistanı** — Claude Code benzeri, 4B parametreli küçük modellerle optimize çalışan, LM Studio üzerinden yerel bir AI kodlama CLI aracı.

## ✨ Özellikler

- 🤖 **Akıllı Agent Döngüsü** — Dosya okuma, düzenleme, arama ve komut çalıştırma tool'ları
- ⚡ **4B Model Optimizasyonu** — Qwen3-4B, Phi-4-Mini, Gemma-4-4B için özel profiller
- 🔒 **Yapılandırılabilir İzinler** — Dosya yazma ve komut çalıştırma için otomatik veya manuel onay seçenekleri
- 📝 **Akıllı Düzenleme** — Search-replace ile hassas kod düzenleme
- 🔍 **Hızlı Arama** — ripgrep entegrasyonu (Python fallback)
- 🌐 **Web Arama** — DuckDuckGo ile gizlilik dostu web araması
- 🔀 **Git Entegrasyonu** — Status, diff, AI commit mesajları
- 💾 **Undo Sistemi** — Her dosya değişikliğini geri alabilme
- 📊 **Token Yönetimi** — Agresif context bütçeleme, otomatik sıkıştırma
- 🎨 **Zengin Terminal UI** — Renkli çıktı, markdown render, streaming

## 🚀 Kurulum

### Gereksinimler

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) (yerel LLM sunucusu)
- Desteklenen bir 4B model (Qwen3-4B, Phi-4-Mini veya Gemma-4-4B)

### Yükleme

```bash
# Projeyi klonla
git clone https://github.com/Ahmetzdemir/spark-cli.git
cd spark-cli

# Sanal ortam oluştur
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Yükle
pip install -e .
```

## 📖 Kullanım

### LM Studio Hazırlığı

1. LM Studio'yu açın
2. Bir 4B model yükleyin (önerilen: **Qwen3-4B-Instruct**)
3. **Developer** sekmesinden sunucuyu başlatın (varsayılan port: 1234)

### Spark'ı Başlatma

```bash
# Etkileşimli REPL
spark

# Tek seferlik komut
spark "bu projedeki hataları bul"

# Belirli modelle
spark --model qwen3-4b

# Farklı port
spark --port 8080

# Bağlantı testi
spark test

# Proje config oluştur
spark init
```

### Slash Komutları

| Komut | Açıklama |
|:---|:---|
| `/help` | Tüm komutları listele |
| `/add <dosya>` | Dosyayı bağlama ekle |
| `/drop <dosya>` | Dosyayı bağlamdan çıkar |
| `/files` | Bağlamdaki dosyaları listele |
| `/diff` | Git değişikliklerini göster |
| `/commit [mesaj]` | AI mesajıyla git commit |
| `/undo` | Son değişikliği geri al |
| `/compact` | Geçmişi sıkıştır |
| `/clear` | Sohbet geçmişini temizle |
| `/model [ad]` | Model değiştir |
| `/status` | Oturum bilgisi |
| `/config` | Ayarları göster |
| `/exit` | Çıkış |

### Araçlar (Tool'lar)

Spark aşağıdaki araçları otomatik olarak kullanır:

| Araç | Açıklama | İzin |
|:---|:---|:---|
| `read_file` | Dosya okuma | ✅ Otomatik |
| `write_file` | Dosya oluşturma | ⚠️ Onay |
| `edit_file` | Search-replace düzenleme | ⚠️ Onay |
| `search_code` | Kod arama (grep) | ✅ Otomatik |
| `list_dir` | Dizin listeleme | ✅ Otomatik |
| `run_command` | Shell komutu | 🔴 Onay |
| `git_status/diff` | Git durumu | ✅ Otomatik |
| `git_commit` | Git commit | ⚠️ Onay |
| `web_search` | Web araması | ✅ Otomatik |

## ⚙️ Konfigürasyon

CLI'nin okuduğu genel ayarları `~/.spark/settings.toml` dosyasında düzenleyin
(Windows: `%USERPROFILE%\.spark\settings.toml`). `spark init` proje klasöründe
bir `.spark/settings.toml` şablonu oluşturur; mevcut CLI sürümü bu proje dosyasını
otomatik yüklemez. Şablonu genel ayar dosyasına aktarabilir veya aşağıdaki örneği kullanabilirsiniz:

```toml
[llm]
base_url = "http://localhost:1234/v1"
model = "auto"
temperature = 0.15
max_tokens = 4096

[permissions]
auto_approve_all = false
auto_approve_write = false
auto_approve_execute = false
whitelisted_commands = ["npm test", "python -m pytest"]

[agent]
max_iterations = 15
max_tool_retries = 3

[ui]
theme = "spark"
show_token_usage = true
show_tool_calls = true
```

Kodda varsayılan olarak otomatik onay açıktır. Yukarıdaki örnek ayarlar dosya
yazma ve komut çalıştırma işlemleri için manuel onayı etkinleştirir; izin
listesindeki komutlar otomatik çalışır. Araçlar işletim sistemi kullanıcı
hesabınızın yetkileriyle çalışır; ayrı bir sandbox sağlamaz.

Yerel `.spark/` ayarları, oturum geçmişi ve `.env` dosyaları Git deposuna dahil edilmez.

## Testler

```bash
python -m pip install pytest
python -m pytest -q
```

## 🧠 Desteklenen Modeller

| Model | Context | Güçlü Yanları |
|:---|:---|:---|
| **Qwen3-4B-Instruct** | 32K | Function calling, Türkçe, kodlama |
| **Phi-4-Mini (3.8B)** | 16K | Reasoning, matematik, kodlama |
| **Gemma-4-4B** | 32K | Function calling, genel |

## 📄 Lisans

MIT
