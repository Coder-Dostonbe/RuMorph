# 1-bosqich hisoboti — Architecture & Foundation

*Sana: 2026-11-20. Holat: kod tayyor, CI yashil. Ikkita o'lchov sizning qurilmangiz va hisobingizda kutilmoqda.*

## Nima qilindi

| Qism | Natija |
| ---- | ------ |
| `core/` (tilsim_core) | Python paketi, faqat standart kutubxona. JSON ko'prik (`version`, `echo`), xatolar kod bilan qaytadi, traceback tashqariga chiqmaydi. Arxitektura testi stdlib'dan tashqari importni taqiqlaydi. |
| Pyodide ko'prigi | Ilova tilsim_core'ni Web Worker ichida Pyodide orqali ishga tushiradi (offline, internetsiz). Ishga tushish vaqti o'lchanadi va **Ilova haqida** sahifasida ko'rsatiladi. |
| Interfeys | Vue 3 + TS + Pinia + Router. Windows'da chap sidebar, Android / tor ekranda pastki menyu. Kunduzgi / tungi / tizim mavzusi, uz / ru / en (uchala til `vue-tsc` bilan tekshiriladi). Faqat ishlaydigan bo'limlar bor: Bosh sahifa (haqiqiy holatlar), Hisob, Sozlamalar, Ilova haqida. |
| Tauri shell | Windows + Android. SQLite (`tauri-plugin-sql`, migratsiyalar `db/sqlite/migrations`). Refresh token: Windows Credential Manager, Android'da ilovaning yopiq papkasi. CSP: Pyodide uchun faqat `wasm-unsafe-eval`. Ikonlar logo B dan. |
| API (Python Worker) | Framework'siz `handle(Request) → Response`. `/health`, `/v1/auth/register`, `login`, `refresh`, `logout`, `/v1/me`. CORS faqat ilova manbalari uchun. |
| Auth | JWT HS256 (15 daqiqa), refresh token (30 kun, faqat SHA-256 xeshi saqlanadi, har refresh'da almashadi, qayta ishlatilsa butun sessiya bekor qilinadi). PBKDF2-SHA256 100 000 iteratsiya. 15 daqiqada 5 ta xato urinishdan keyin blok. Birinchi hisob — admin. Audit log (parol / token yozilmaydi). |
| PostgreSQL | Migratsiya `0001`: users, devices, refresh_tokens, user_settings, auth_attempts, audit_log. `scripts/migrate.py` (har fayl bir marta, o'zgartirilgan faylni rad etadi). |
| CI | 6 ta job: core, API + PostgreSQL, **API haqiqiy Workers runtime'da** (register / login / refresh / me), client (typecheck, build, Pyodide testlari), **Windows NSIS o'rnatuvchi**, **Android debug APK**. |

## Testlar

| To'plam | Natija |
| ------- | ------ |
| `core` pytest | 20 / 20 |
| `apps/api` pytest (haqiqiy PostgreSQL) | 66 / 66 |
| Web Crypto PBKDF2 Pyodide ichida (`node --test`) | 4 / 4 |
| `apps/client` vitest (tilsim_core haqiqiy Pyodide'da) | 6 / 6 |
| `cargo test` (Tauri shell) | 2 / 2 |
| Workers runtime smoke test (CI) | o'tdi |
| Ilova Linux'da (WebKitGTK) ishga tushirildi | Pyodide ishladi, SQLite migratsiyasi qo'llandi |

## O'lchovlar (shu paytgacha)

| Nima | Qayerda | Natija |
| ---- | ------- | ------ |
| Pyodide ishga tushishi | Server (2 yadro), Node | ~1.6 s |
| Pyodide ishga tushishi | Chrome (headless), shu server | ~1.8 s |
| tilsim_core chaqiruvi (ishga tushgandan keyin) | Node | 0.02 ms |
| PBKDF2 100 000 iteratsiya, Web Crypto | Node (Pyodide ichidan) | ~15 ms |

## Topilgan va tuzatilgan muammo

CI'dagi Workers runtime testi ro'yxatdan o'tishda `internal` xato topdi. Sababi: Python Workers Pyodide'da
ishlaydi, `hashlib.pbkdf2_hmac` esa u yerda yo'q. Yechim: Worker parolni Web Crypto (`crypto.subtle`) bilan
xeshlaydi. Cloudflare Web Crypto 100 000 iteratsiyadan ko'pini qabul qilmaydi, shuning uchun 100 000 tanlandi.
Ikkala yo'l bir xil xesh beradi, buni test tekshiradi.

## Sizdan kerak bo'ladigan narsalar (spike)

1. **Android:** GitHub → Actions → oxirgi "CI" → `tilsim-android-debug-apk` ni yuklab, telefonga o'rnating.
   **Ilova haqida → Jami** raqamini 2–3 marta ochib yuboring.
2. **Neon + Cloudflare:** `docs/SETUP.md` 4–5-bo'limlari. Deploy'dan keyin login va refresh'ning
   CPU vaqtini yuboring (6-bo'lim).

Bu ikki raqam B variant (Pyodide + Python Worker) uzil-kesil tasdiqlanishi uchun kerak.

## Hali qilinmagan (ataylab)

- Android'da refresh token Keystore'da emas, ilovaning yopiq papkasida turadi. Shaxsiy foydalanish uchun yetarli, keyinroq kuchaytiriladi.
- `user_settings` sinxronizatsiyasi 6-bosqichda.
- Android APK faqat `arm64` va debug kalit bilan imzolangan (sinov uchun).
- Admin panel keyingi bosqichlarda (Windows'da, `admin` roli bilan).
- Pydantic va JSON Schema → TS tiplar hali yo'q. API tiplari (`apps/client/src/api/types.ts`) hozircha qo'lda yozilgan, server tomoni testlar bilan tekshiriladi. Avtomatik yaratish endpointlar ko'paygach (3–5-bosqich) qo'shiladi.

## Keyingi bosqich

2-bosqich — rus grammar engine (Python, `core/`): tiplar, normalizatsiya, otlar, sifatlar, fe'llar,
olmoshlar, sonlar, teskari tahlil. Lug'at manbalari (OpenCorpora, Wiktionary) importi bilan.
