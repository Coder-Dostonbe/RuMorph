# Tilsim — o'rnatish va ishga tushirish

Bu qadamlar faqat bir marta qilinadi. Hisoblar (Neon, Cloudflare) va kalitlar sizning nomingizda bo'ladi.
Hech qanday kalit yoki parol repoga yozilmaydi.

## 0. Kompyuterda kerakli dasturlar (Windows)

| Dastur | Nima uchun | Tekshirish |
| ------ | ---------- | ---------- |
| Node.js 22 | interfeys, Tauri CLI, wrangler | `node -v` |
| Rust (MSVC) + Visual Studio C++ Build Tools | Tauri ilovasi | `cargo -V` |
| uv (0.13.4 yoki yangiroq) | Python qismlari, `pywrangler` | `uv --version` (`uv self update`) |
| WebView2 | Windows 10/11 da bor | — |

ArabMorph uchun bularning ko'pi allaqachon o'rnatilgan.

## 1. Kodni olish

```powershell
cd $HOME\Desktop\RuMorph
git pull
npm install
```

## 2. Windows ilovasini ishga tushirish

```powershell
cd apps\client
npx tauri dev          # ishlab chiqish rejimi
npx tauri build        # o'rnatuvchi: src-tauri\target\release\bundle\nsis\Tilsim_0.1.0_x64-setup.exe
```

Server sozlanmagan bo'lsa ham ilova ishlaydi: bosh sahifada "Server: sozlanmagan" deb ko'rsatadi.
"Ilova haqida" sahifasida Python muhitining ishga tushish vaqti ko'rinadi.

**Tayyor o'rnatuvchi va APK:** har bir push'dan keyin GitHub Actions ularni o'zi yig'adi.
<https://github.com/Coder-Dostonbe/RuMorph/releases/tag/dev> sahifasida (telefondan ham ochiladi):

- `Tilsim-windows-setup.exe` — Windows o'rnatuvchisi;
- `Tilsim-android-test.apk` — Android uchun APK (debug kalit bilan imzolangan, faqat sinov uchun).

## 3. Android'da sinash (1-bosqich spike)

1. Telefondan <https://github.com/Coder-Dostonbe/RuMorph/releases/tag/dev> ni oching va `Tilsim-android-test.apk` ni yuklab oling.
2. Telefonda "Noma'lum manbalardan o'rnatish"ga ruxsat bering va o'rnating.
3. Ilovani oching, **Ilova haqida** sahifasiga o'ting va **"Python muhitining ishga tushishi → Jami"** raqamini menga yuboring.
   Ilovani 2–3 marta yopib-ochib o'lchang: birinchi ochilish odatda sekinroq bo'ladi.

## 4. PostgreSQL — Neon

1. <https://neon.tech> da hisob oching va `tilsim` nomli loyiha yarating.
2. **Connection string** ni nusxalang. Migratsiya uchun **Direct** (pooled emas) ulanish kerak.
3. Migratsiyani qo'llang:

```powershell
cd apps\api
$env:DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"
uv run --no-project --with asyncpg python scripts\migrate.py
```

## 5. Cloudflare Worker (API)

```powershell
cd apps\api
npx wrangler login
npx wrangler hyperdrive create tilsim-db --connection-string="<Neon connection string>"
```

1. Chiqqan `id` ni `wrangler.jsonc` dagi `REPLACE_WITH_HYPERDRIVE_ID` o'rniga yozing.
2. JWT kalitini yarating va secret sifatida saqlang (kamida 32 belgi):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
npx wrangler secret put JWT_SECRET
```

3. Deploy:

```powershell
uv sync
uv run pywrangler deploy
```

4. Chiqqan manzilni (`https://tilsim-api.<akkaunt>.workers.dev`) ilovada **Sozlamalar → Server manzili** ga kiriting.
5. Ilovada **Hisob → Ro'yxatdan o'tish**. Birinchi hisob avtomatik `admin` bo'ladi.
6. Shundan keyin ro'yxatdan o'tishni yoping: `wrangler.jsonc` da `"ALLOW_REGISTRATION": "false"` qiling va qayta deploy qiling.

## 6. CPU o'lchovi (1-bosqich spike)

Cloudflare dashboard → **Workers & Pages → tilsim-api → Metrics → CPU time**.
`/health`, login va refresh so'rovlaridan keyin CPU vaqti (median va P99) qancha ekanini menga yuboring.

Kutilayotgan holat: oddiy so'rovlar (`/health`, refresh, `/v1/me`) bepul tarifdagi 10 ms ichida bo'ladi.
**Login** va ro'yxatdan o'tish parolni PBKDF2-SHA256 (100 000 iteratsiya, Web Crypto orqali) bilan tekshiradi.
Bu kompyuterda o'lchanganda ~15 ms bo'ldi, ya'ni 10 ms chegarasidan oshishi mumkin. Login har bir qurilmada
bir marta bo'ladi. Bepul tarifda login rad etilsa, yechim — Workers Paid ($5/oy).

100 000 — Cloudflare Web Crypto ruxsat beradigan eng ko'p iteratsiya soni. Python Workers Pyodide'da
ishlagani uchun `hashlib.pbkdf2_hmac` u yerda mavjud emas, shuning uchun Web Crypto ishlatiladi.

Qaysi biri kerakligini o'lchov natijasiga qarab birga hal qilamiz.

## Lokal ishlab chiqish (ixtiyoriy)

```powershell
# API ni lokal PostgreSQL bilan
cd apps\api
"JWT_SECRET=dev-only-secret-0123456789abcdef0123456789" | Out-File -Encoding ascii .dev.vars
uv run pywrangler dev           # http://localhost:8787
# Ilovada server manzili: http://localhost:8787
```

Testlar:

```powershell
cd core;      uv run --no-project --with pytest python -m pytest -q
cd apps\api;  $env:TEST_DATABASE_URL="postgres://postgres:...@localhost:5432/postgres"; uv run --no-project --with asyncpg --with pytest python -m pytest -q
npm test      # Pyodide ichida tilsim_core
cd apps\client\src-tauri; cargo test
```
