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
- `Tilsim-android.apk` — Android uchun APK (release build, arm64 + armv7).

## 3. Android'da sinash (1-bosqich spike)

1. Telefondan <https://github.com/Coder-Dostonbe/RuMorph/releases/tag/dev> ni oching va `Tilsim-android.apk` ni yuklab oling.
2. Telefonda "Noma'lum manbalardan o'rnatish"ga ruxsat bering va o'rnating.
3. Ilovani oching, **Ilova haqida** sahifasiga o'ting va **"Python muhitining ishga tushishi → Jami"** raqamini menga yuboring.
   Ilovani 2–3 marta yopib-ochib o'lchang: birinchi ochilish odatda sekinroq bo'ladi.

## 4. PostgreSQL — Neon

1. <https://neon.tech> da hisob oching va `tilsim` nomli loyiha yarating.
2. **Connection string** ni nusxalang: **Direct** (pooled emas) ulanish kerak. Ichida parol bor:
   uni hech qayerga yozmang, faqat quyidagi ikki joyga qo'yasiz.

Migratsiyalarni GitHub o'zi qo'llaydi (5-bo'lim).

## 5. Cloudflare Worker (API) — GitHub orqali avtomatik

Bir marta sozlanadi. Keyin har bir push'da, barcha testlar o'tgach, GitHub Actions o'zi:
Neon'ga migratsiyalarni qo'llaydi, Worker'ni deploy qiladi va `/health` ni tekshiradi.

1. **Hyperdrive** (Cloudflare dashboard): **Storage & Databases → Hyperdrive → Create configuration**.
   Nomi `tilsim-db`, ulanish: Neon'ning Direct connection string'i. Chiqqan **ID** ni nusxalang.
2. **API token**: o'ng yuqoridagi profil → **My Profile → API Tokens → Create Token** →
   **Edit Cloudflare Workers** shabloni. **Permissions** ga yana bitta qator qo'shing:
   **Account → Hyperdrive → Edit**. Yarating va tokenni nusxalang (bir marta ko'rsatiladi).
3. **Account ID**: dashboard → **Workers & Pages**, o'ng tomonda.
4. **JWT kaliti** (kamida 32 belgi): `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
5. GitHub: **repo → Settings → Secrets and variables → Actions → New repository secret**:

| Nomi | Qiymati |
|---|---|
| `CLOUDFLARE_API_TOKEN` | 2-qadamdagi token |
| `CLOUDFLARE_ACCOUNT_ID` | 3-qadamdagi ID |
| `HYPERDRIVE_ID` | 1-qadamdagi ID |
| `DATABASE_URL` | Neon'ning Direct connection string'i |
| `JWT_SECRET` | 4-qadamdagi matn |

6. Cloudflare dashboard'da Worker'ning o'z GitHub ulanishi (Workers Builds) bo'lsa, uzing:
   deploy'ni GitHub Actions qiladi.
7. Secrets qo'yilgach, istalgan push (yoki **Actions → CI → Re-run**) deploy qiladi. Manzil
   (`https://tilsim-api.<akkaunt>.workers.dev`) "Deploy API" job'ining logida chiqadi.
8. Manzilni ilovada kiriting: "Ilova haqida" sahifasida versiyaga 7 marta bosing →
   **Admin panel → Server va hisob → Server manzili**. Keyin o'sha yerdagi "Hisob bo'limini ochish"
   → ro'yxatdan o'ting. Birinchi hisob avtomatik `admin` bo'ladi.
9. Shundan keyin ro'yxatdan o'tishni yopamiz (`wrangler.jsonc` da `"ALLOW_REGISTRATION": "false"`):
   menga ayting, o'zgartirib push qilaman.

Kompyuterdan qo'lda deploy ham mumkin (zarur bo'lsa): `apps\api` da `npx wrangler login`,
`wrangler.jsonc` ga Hyperdrive ID, `npx wrangler secret put JWT_SECRET`, `uv sync`,
`uv run pywrangler deploy`.

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

## 7. Avtomatik yangilanish (bir marta)

Ikkita kalit kerak. Ikkalasini ham **zaxira qilib saqlang** (repo papkasidan tashqarida, masalan
fleshka yoki parol menejerida): kalit yo'qolsa, o'rnatilgan ilovalar keyingi versiyalarni qabul
qilmaydi. Kalitlar va parollar repoga ham, chatga ham yozilmaydi.

GitHub'da: **repo → Settings → Secrets and variables → Actions → New repository secret**.

### Windows: updater kaliti

```powershell
npx tauri signer generate -w "$HOME\.tauri\tilsim-updater.key"
```

Parol so'raydi (o'ylab toping va saqlang). Ikkita fayl chiqadi: `tilsim-updater.key` (yopiq) va
`tilsim-updater.key.pub` (ochiq). Secrets:

| Nomi | Qiymati |
|---|---|
| `TAURI_SIGNING_PRIVATE_KEY` | `tilsim-updater.key` faylining butun matni |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | o'sha parol |
| `TAURI_UPDATER_PUBKEY` | `tilsim-updater.key.pub` faylining butun matni |

Fayl matnini nusxalash: `Get-Content "$HOME\.tauri\tilsim-updater.key" -Raw | Set-Clipboard`.

### Android: imzo kaliti (keystore)

`keytool` Java bilan keladi (Android Studio'da: `C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe`).

```powershell
keytool -genkeypair -v -keystore "$HOME\tilsim-release.jks" -alias tilsim -keyalg RSA -keysize 2048 -validity 10000
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$HOME\tilsim-release.jks")) | Set-Clipboard
```

Parol so'raydi (kalit uchun ham xuddi shu parolni ishlating). Secrets:

| Nomi | Qiymati |
|---|---|
| `ANDROID_KEYSTORE_B64` | yuqoridagi buyruq nusxalagan matn |
| `ANDROID_KEYSTORE_PASSWORD` | keystore paroli |
| `ANDROID_KEY_ALIAS` | `tilsim` |

### Keyin

Secrets qo'yilgach, keyingi push'dan chiqqan versiyani **bir marta qo'lda** o'rnating (Android'da
eski ilovani avval o'chirib). Undan keyingi versiyalarni ilovaning o'zi taklif qiladi:
Windows'da yuklab olib o'rnatadi va qayta ochadi, Android'da yuklab olib o'rnatish oynasini ochadi.
Holatini admin panelda ko'rasiz: **Ilova va qurilma → Avtomatik yangilanish**.

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
