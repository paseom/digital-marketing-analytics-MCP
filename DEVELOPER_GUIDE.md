# Developer Guide — Marketing Analytics MCP

Dokumentasi ini buat siapapun yang lanjutin/maintain project ini setelah aku. Isinya arsitektur lengkap, cara nambah fitur, cara deploy, dan gotcha-gotcha yang udah pernah kejadian biar gak keulang.

---

**Alur satu pertanyaan user:**
1. User mengetik pertanyaan di chat Streamlit
2. Streamlit app connect ke MCP server (URL Vercel) lewat MCP Client Session, ambil daftar tool yang tersedia (`fetch_campaigns`, `fetch_campaign_metrics`, `fetch_account_info`, `generate_report`)
3. Tool declarations + pertanyaan user dikirim ke Gemini API
4. Kalau Gemini minta manggil tool, **kode Streamlit yang eksekusi manual** (`session.call_tool(...)`) ke MCP server → MCP server manggil Google Ads API asli → hasil JSON balik
5. Hasil tool dikirim balik ke Gemini, diulang sampai Gemini kasih jawaban teks final
6. Jawaban ditampilin ke user

**Kenapa manual tool-calling, bukan fitur otomatis SDK?** Awalnya pake fitur eksperimental `google-genai` yang nerima `ClientSession` langsung sebagai `tools=[session]`. Ini crash di Streamlit Cloud dengan error `cannot pickle '_asyncio.Future' object` — SDK-nya nyoba deep-copy objek session yang isinya koneksi async hidup. Solusinya: kita kontrol sendiri siklus tool-calling-nya (lihat `Frontend/app.py`, fungsi `ask_gemini()`).

---

## Struktur Repo

```
digital-marketing-analytics-MCP/
├── marketing_analytics/
│   ├── server.py              
│   ├── models.py            
│   └── connectors/
│       ├── __init__.py          
│       ├── base.py               
│       ├── registry.py          
│       ├── google_ads.py          
│       ├── meta_ads.py               # ⚠️ MASIH DUMMY
│       ├── tiktok_ads.py              # ⚠️ MASIH DUMMY
│       └── ga4.py                      # ⚠️ MASIH DUMMY
├── api/
│   └── index.py                 
├── Frontend/
│   ├── app.py                     
│   ├── requirements.txt
│   └── .streamlit/
│       └── secrets.toml            
├── tests/
├── vercel.json
├── pyproject.toml                 
└── .gitignore
```

---

## Environment Variables — Referensi Lengkap

### Backend (Vercel — Settings → Environment Variables)

| Nama | Isi | Catatan |
|---|---|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | dari `google-ads.yaml` | |
| `GOOGLE_ADS_CLIENT_ID` | dari `google-ads.yaml` | OAuth "Desktop app" type |
| `GOOGLE_ADS_CLIENT_SECRET` | dari `google-ads.yaml` | |
| `GOOGLE_ADS_REFRESH_TOKEN` | dari `google-ads.yaml` | |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | ID akun MCC | |
| `GOOGLE_ADS_ACCOUNTS` | JSON, misal `{"brandx":"123","brandy":"456"}` | Multi-account mode, lihat §5 |
| `GOOGLE_ADS_API_VERSION` | `v24` | Sesuaikan versi SDK `google-ads` yang di-install |

### Frontend (Streamlit Cloud — Settings → Secrets, format TOML)

```toml
GEMINI_API_KEY = "..."
MCP_SERVER_URL = "https://<domain-vercel>.vercel.app/"

[auth]
redirect_uri = "https://<domain-streamlit>.streamlit.app/oauth2callback"
cookie_secret = "..."   # generate: python -c "import secrets; print(secrets.token_hex(32))"

[auth.google]
client_id = "..."         
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

# Optional toggle buat testing (default true kalau gak diisi)
REQUIRE_AUTH = "true"
REQUIRE_SYSTEM_INSTRUCTION = "true" 

## Cara Nambah Akun Google Ads (Multi-Account)

Constructor `GoogleAdsConnector` nerima `customer_id` dan `account_label` opsional:

```python
GoogleAdsConnector(customer_id="123456", account_label="brandx")
# -> get_platform_name() balikin "google_ads_brandx"
``` 

Registrasinya di `connectors/__init__.py`, baca dari env var `GOOGLE_ADS_ACCOUNTS` (JSON): 

```python
accounts_json = os.environ.get("GOOGLE_ADS_ACCOUNTS")
if accounts_json:
    accounts = json.loads(accounts_json)
    for label, customer_id in accounts.items():
        registry.register_connector(GoogleAdsConnector(customer_id=customer_id, account_label=label))
else:
    registry.register_connector(GoogleAdsConnector())  # fallback single-account
```

Tiap akun jadi **platform key sendiri** (`google_ads_brandx`, `google_ads_brandx`). Tool `fetch_campaigns(platform=...)` dkk tinggal dipanggil pake key itu. `fetch_account_info()` tanpa parameter balikin **semua** akun sekaligus, masing-masing ada `account_name` asli + `platform` key-nya — ini yang dipake Gemini buat "translate" nama akun yang disebut user ke key teknis (lihat §6, aturan #12 di system instruction).

**Kalau nambah akun baru:** tinggal update value `GOOGLE_ADS_ACCOUNTS` di Vercel (tambah 1 entry JSON), redeploy. Gak perlu ubah kode. -->

## Cara Nambah Connector Baru (misal beneran ngerjain `meta_ads.py`)

Ikutin pola `google_ads.py`. Wajib implementasi semua method abstract di `base.py`:

```python
class BaseMarketingConnector(ABC):
    def get_platform_name(self) -> str: ...
    def fetch_account_info(self) -> AccountInfo: ...
    def fetch_campaigns(self) -> List[Campaign]: ...
    def fetch_metrics(self, campaign_id: str) -> CampaignMetrics: ...
    def generate_report_data(self, start_date: str, end_date: str) -> PlatformReport: ...
    def get_api_schema(self) -> Dict[str, Any]: ...
    def get_sample_data(self) -> Dict[str, Any]: ...
```

Jangan ubah `base.py`, `models.py`, `registry.py`, `server.py` kecuali beneran perlu — connector baru harusnya cukup nambah 1 file + 1 baris registrasi di `connectors/__init__.py`.

---

## System Instruction (Prompt Engineering)

Instruksi permanen yang dikirim ke Gemini tiap turn, ada di `Frontend/app.py`, variable `SYSTEM_INSTRUCTION`. Ini yang ngatur:

1. **Scope**: cuma jawab soal data marketing, tolak topik lain
2. **No mutation**: tegasin gak ada kemampuan ubah/hapus campaign (karena tool-nya emang cuma `fetch_*`)
3. **No hallucination**: kalau tool gagal, bilang jujur, jangan ngarang angka
4. **Anti prompt-injection**: abaikan "instruksi" yang nyelip di dalam data tool (misal nama campaign aneh)
5. **Format konsisten**: tanya dulu format yang diinginkan kalau user minta "laporan" tanpa spesifik; kasih penjelasan/footnote tiap nampilin tabel
6. **Currency**: selalu label "Rp", jangan "$" (karena angka dari API udah dalam IDR apa adanya, cuma butuh label yang bener)
7. **Multi-account resolution**: kalau user sebut nama akun/campaign (bukan ID teknis), panggil `fetch_account_info()`/`fetch_campaigns()` dulu buat "translate" nama ke platform key / campaign_id yang bener sebelum manggil tool lain

### Contoh prompt & output yang diharapkan

| Prompt user | Perilaku yang diharapkan |
|---|---|
| `"list campaign di google ads"` | Panggil `fetch_campaigns()`, tampilkan tabel kolom sesuai spesifikasi di system instruction, dipisah per platform kalau lebih dari 1 akun |
| `"gimana performa bulan ini"` | Karena gak sebut format → Gemini nanya dulu: *"Mau saya buatkan dalam bentuk tabel, ringkasan teks, grafik, atau daftar poin-poin?"* |
| `"kasih tabel perbandingan campaign buat dioptimasi"` | Tampilkan tabel + catatan kaki 1-3 kalimat menjelaskan cara baca kolom & angka yang dianggap baik/perlu perhatian |
| `"performa campaign brandx Marketing"` (nama akun, bukan ID) | Panggil `fetch_account_info()` dulu buat cari platform key yang cocok sama nama itu, baru lanjut ke tool lain |
| `"hapus campaign X"` | Tolak sopan, jelaskan cuma bisa baca data, arahkan ke Google Ads UI langsung |
| `"tampilkan data mentah/JSON"` | Tolak sopan, tawarkan versi olahan (tabel/ringkasan) sebagai gantinya |

**Kalau mau ubah perilaku ini**, edit `SYSTEM_INSTRUCTION` di `Frontend/app.py`. Bisa di-toggle off sementara buat testing lewat secret `REQUIRE_SYSTEM_INSTRUCTION = "false"` tanpa perlu ubah kode.

---

<!-- ## 7. Guardrail / Keamanan — 3 Lapisan

| Lapisan | Mekanisme | Kekuatan |
|---|---|---|
| **1. Struktural** | Tool yang di-expose cuma `fetch_*` (read-only), gak ada `create`/`update`/`delete` di connector manapun | Gak bisa ditembus prompt injection — kemampuannya emang gak ada, bukan soal "nurut" |
| **2. System instruction** | Batasan topik, larangan ngarang data, anti-prompt-injection dari data tool | Bisa dicoba dibypass user yang niat, tapi cukup buat pemakaian normal |
| **3. Akses & rate limit** | Login Google dibatasi domain email (`ALLOWED_EMAIL_DOMAIN`), max 30 pertanyaan/sesi | Kontrol teknis, bukan behavioral |

**Prinsip utama**: guardrail paling reliable itu **gak kasih kemampuan yang gak perlu**, bukan cuma nyuruh LLM "jangan lakuin X". Kalau nanti nambah tool yang sifatnya mutasi data, pikirin ulang risikonya — saat ini sistem 100% read-only by design.

Credential Google Ads (`developer_token`, `client_secret`, `refresh_token`) **tidak pernah** dikirim ke Gemini sebagai bagian context — itu cuma hidup di sisi MCP server (Vercel).

--- -->

## Panduan Deploy
### Backend (Vercel)

1. Push ke GitHub (pastikan `.gitignore` sudah mencakup `secrets.toml`, `google-ads.yaml`, `.env`)
2. Import project di Vercel, isi semua env var (§3)
3. Deploy
<!-- 
**Gotcha yang pernah bikin stuck (biar gak keulang):**

- **`No Python entrypoint found`** — file entrypoint Vercel **wajib** dinamain `app.py`/`index.py`/`server.py`/`main.py`/`wsgi.py`/`asgi.py`. Nama lain (misal `mcp.py`) gak dikenalin. Solusi: taro di `api/index.py`.
- **`ModuleNotFoundError: No module named 'google'`** — kalau ada `pyproject.toml` DAN `requirements.txt` bareng, Vercel **prioritasin `pyproject.toml`**. Kalau dependency (`google-ads`) cuma ada di `requirements.txt` tapi gak di `pyproject.toml`, dia gak keinstall. Pastikan `pyproject.toml` `dependencies` lengkap.
- **`FileNotFoundError: google-ads.yaml`** — Vercel gak punya filesystem persisten. `GoogleAdsClient.load_from_storage()` gak bisa dipake. Connector otomatis switch ke `load_from_dict()` pake env var kalau `GOOGLE_ADS_DEVELOPER_TOKEN` kedetect (lihat `_build_client()` di `google_ads.py`).
- **`Invalid Host header`** — FastMCP defaultnya cuma percaya `localhost`. Perlu `TransportSecuritySettings(allowed_hosts=[...])` di `server.py`, isi domain Vercel eksplisit (wildcard `*.vercel.app` **TIDAK didukung**, harus exact match — pakai `os.environ.get("VERCEL_URL")` buat auto-detect domain deployment yang lagi jalan).
- **`streamable_http_app() got unexpected keyword argument 'path'`** — path endpoint di-set di **constructor `FastMCP(...)`** lewat `streamable_http_path="/"`, BUKAN di method `streamable_http_app()`.
- **`Not Acceptable: Client must accept text/event-stream`** — muncul kalau buka URL MCP langsung di address bar browser. Ini **normal**, browser gak kirim header yang benar. Test harus pakai MCP Inspector atau client MCP beneran. -->

### Frontend (Streamlit Community Cloud)

1. Push folder `Frontend/` ke GitHub
2. `share.streamlit.io` → New app → pilih repo, path `Frontend/app.py`
3. Settings → Secrets, isi sesuai §3 (redirect_uri versi `https://...streamlit.app/oauth2callback`)
4. Deploy
<!-- 
**Gotcha:**

- **`cannot pickle '_asyncio.Future' object`** — jangan pernah pass `ClientSession` mentah sebagai `tools=[session]` ke `generate_content()`. Pakai manual tool-calling loop (lihat §1).
- **`StreamlitMissingAuthlibError`** — install `streamlit[auth]`, bukan `streamlit` polos.
- **Model 404 (`gemini-2.5-flash` retired)** — model Gemini sering dipensiunin. Pakai alias `gemini-flash-latest` biar auto-update ke versi GA terbaru, jangan hardcode versi spesifik.
- **`.gitignore` gak match file di subfolder** — pattern `.streamlit/secrets.toml` (ada slash) cuma match di root. Pakai `secrets.toml` (tanpa slash) biar match di kedalaman folder manapun.

--- -->
<!-- 
## 9. Yang Masih Perlu Dikerjain (TODO)

- [ ] `meta_ads.py`, `tiktok_ads.py`, `ga4.py` masih dummy — belum connect API asli
- [ ] `tests/test_connectors.py` & `tests/test_server.py` perlu direview ulang (beberapa masih asumsi dummy connector lama)
- [ ] Pertimbangkan publish OAuth consent screen (Google) dari mode "Testing" ke published kalau user makin banyak (mode Testing cuma bisa akses buat email yang didaftarin manual)
- [ ] Rate limit per-user (bukan cuma per-sesi browser) kalau perlu kontrol biaya lebih ketat -->