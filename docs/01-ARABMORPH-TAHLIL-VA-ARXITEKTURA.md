# Tilsim (RuMorph): ArabMorph tahlili va taklif etilgan arxitektura

*Sana: 2026-11-19. Holat: tasdiq kutilmoqda. Bu hujjatda kod yo'q, faqat tahlil va reja.*

*Yangilanish (2026-11-19): **B variant** tanlandi. Engine va backend Python'da, interfeys Vue 3 + TypeScript'da. Python qurilmada Pyodide orqali, serverda Cloudflare Python Workers orqali ishlaydi. Qarang: `DECISIONS.md`.*

Tahlil qilingan manba: `Desktop/arabmorph-ai`, oxirgi commit `eafa0bf`, desktop ilova v0.5.1, engine v0.3.0.
ArabMorph'ga hech narsa yozilmadi. Testlar uning nusxasida ishga tushirildi.

---

## 1. ArabMorph arxitekturasi qanday ishlaydi

### 1.1. Umumiy tuzilma

ArabMorph uchta qatlamdan iborat:

```
┌───────────────────────────── Windows ilova (Tauri 2) ─────────────────────────────┐
│                                                                                    │
│  Vue 3 + TS + Pinia + Vue Router (webview)                                         │
│   views: Activity, Test, Sets, Analysis, Results, Lexicon, Rules, About            │
│   i18n: uz / ar / ru / en          theme: kunduz / tun / avto                      │
│        │ invoke()                                                                  │
│        ▼                                                                           │
│  Rust shell (src-tauri)                                                            │
│   lib.rs   — engine servisini ishga tushiradi, timeout, qayta ishga tushirish     │
│   store.rs — JSON fayllarni atomik saqlaydi + 5 ta backup                          │
│   log.rs   — log, 1 MB da rotatsiya                                                │
│   claude.rs— API kalit (Windows Credential Manager) + Claude so'rovi               │
│        │ stdin/stdout, qatorma-qator JSON (tarmoq porti yo'q)                     │
│        ▼                                                                           │
│  Python sidecar (PyInstaller --onedir, arabmorph-service.exe)                      │
│   arabmorph_service.py — operatsiyalar: generate, analyze, import_file, ...       │
│   importers.py, vocab.py, activity.py, verify.py, user_lexicon.py                  │
│        │ import                                                                    │
│        ▼                                                                           │
│  engine/ — sof Python morfologiya engine'i (faqat standart kutubxona)              │
└────────────────────────────────────────────────────────────────────────────────────┘
```

Server, ma'lumotlar bazasi, autentifikatsiya, sinxronizatsiya va Android versiyasi yo'q.
Ilova to'liq offline ishlaydi, faqat ixtiyoriy Claude yordamchisi internet talab qiladi.

### 1.2. Engine (`engine/src/arabmorph`, ~3 000 qator)

Engine'ning eng qimmatli tomoni kodi emas, **dizayn tamoyillari**:

| Tamoyil | Qanday amalga oshirilgan |
| ------- | ------------------------ |
| Mustaqil engine | Faqat standart kutubxona. `test_architecture.py` Django, AI SDK va boshqalar import qilinmasligini tekshiradi. |
| Yagona pipeline | `pipeline.py`: parse → validate → interpret → assemble. Barcha generatorlar shundan o'tadi. |
| Natija turi | `GenerationResult`: `status` (`ok` / `ambiguous` / `error`), `forms`, `warnings`, `errors`, `assumptions`, `suggestions`. |
| Har bir shakl o'z dalili bilan | `GeneratedForm`: qo'llangan qoidalar (`rule_ids`), manba (`rule` / `lexicon` / `heuristic` / `asserted`), `confidence`, `condition`. |
| Noaniqlik — natija, taxmin emas | Dalil yetmasa `ambiguous` va har bir o'qilish sharti bilan. Noto'g'ri shakl hech qachon `ok` bo'lmaydi. |
| Avval lug'at, keyin qoida | Imlodan aniqlab bo'lmaydigan faktlar lug'atdan olinadi, qoidalar keyin qo'llanadi. |
| Qoidalar — ma'lumot | `rules.py`: har bir qoidaning izohi, misoli, manbasi, ishonchliligi va `review_status`i. |
| Teskari tahlil tekshiriladi | `analyze()` har bir variantni qaytadan generatsiya qilib tasdiqlaydi. |
| "Siz buni nazarda tutdingizmi?" | Takliflar beriladi, lekin hech qachon avtomatik qo'llanmaydi. |
| Asl kiritma saqlanadi | Normalizatsiya asl matnni ham qaytaradi. Ma'lumot yo'qotadigan normalizatsiya o'chiq. |
| Kontekst bo'yicha kelishik | `context.py`: oldingi so'z (predlog va boshqalar) ot kelishigini belgilaydi. |
| Lug'at bir nechta fayldan | Seed + import + foydalanuvchi lug'ati. Tasdiqlanmagan yozuvlar `verified: false`. |

Testlar: **365 ta engine testi o'tdi** (Python 3.12). Har bir qoida kamida bitta corpus testi bilan qoplangan, buni test o'zi tekshiradi.

### 1.3. Desktop ilova (`desktop/`)

- **Frontend:** Vue 3, TypeScript, Vite, Pinia, Vue Router. Har bir bo'lim alohida view. Tarjimalar `i18n/` papkasida, `uz.ts` asosiy shakl bo'lib xizmat qiladi va `vue-tsc` to'rtala tilni tekshiradi. Mavzu CSS o'zgaruvchilari orqali (kunduz / tun / avto).
- **Rust shell:** sidecar'ni yashirin jarayon sifatida ishga tushiradi. Har bir so'rovda timeout bor (15 s, fayl importida 60 s). Servis o'lsa, bir marta qayta ishga tushiradi. Ma'lumotlar `%APPDATA%` dagi JSON fayllarda: atomik yozish va oxirgi 5 ta backup. API kalit Windows Credential Manager'da, webview'ga hech qachon qaytmaydi. Claude so'rovini Rust yuboradi, webview CSP'si tashqi hostlarga ruxsat bermaydi.
- **Sidecar:** `.docx`, `.xlsx`, `.txt`, `.csv` ni standart kutubxona bilan o'qiydi (hajm cheklangan, DOCTYPE rad etiladi). Arabcha va o'zbekcha matnni ustunlarga ajratadi. Engine yordamida mashq va distraktorlar yasaydi. Claude yaratgan elementlarni engine bilan qayta tekshiradi.
- **Testlar:** 135 ta sidecar testi o'tdi. Bittasi (`test_shipped_samples_import_unchanged`) faqat mening sinov muhitimda modul yo'qligi sababli o'tmadi, ArabMorph'dagi xato emas. Yana Rust testlari va CI (Windows): engine, sidecar, frontend build, `cargo check`.
- **O'rnatuvchi:** NSIS, administrator huquqisiz. Updater tayyorlangan, lekin o'chiq.

### 1.4. RuMorph uchun eng muhim xulosa

> **ArabMorph'ning Python sidecar usuli Android'da ishlamaydi.**

Tauri sidecar (tashqi `.exe` ni ishga tushirish) Android'da qo'llab-quvvatlanmaydi. Tauri Android'ga o'tgan
loyihalar Python sidecar'ga bog'liq funksiyalarni mobil versiyada yashirishga majbur bo'lmoqda.

**Tanlangan yechim (B variant):** engine Python'da qoladi, lekin alohida `.exe` sifatida emas, **Pyodide** orqali ishlaydi.
Pyodide Python'ni WebAssembly'ga o'girib, ilovaning webview'i ichida ishlatadi. Shunda bitta Python kodi Windows'da,
Android'da va serverda (Cloudflare Python Workers ham Pyodide asosida) ishlaydi. ArabMorph engine'i faqat standart
kutubxonadan foydalanadi, Pyodide uchun bu ideal holat. Uning tuzilmasi, natija turlari va pytest testlari uslubi
to'g'ridan-to'g'ri ko'chiriladi (5-bo'limga qarang).

---

## 2. RuMorph'da qayta ishlatiladigan qismlar

Bular tilga bog'liq emas. Ozgina o'zgartirish bilan olinadi:

| ArabMorph | RuMorph'da | Izoh |
| --------- | ---------- | ---- |
| Natija turlari (`GenerationResult`, `GeneratedForm`, `Status`, `Source`) | `core/src/tilsim_core/engine/types.py` | Xuddi shu dataclass'lar. Grammatik belgilar ruschaga almashadi. |
| Pipeline: parse → validate → interpret → assemble (`pipeline.py`) | Engine yadrosi | Bosqichlar o'sha, kod tuzilmasi ham o'sha. |
| Qoidalar registri (`rules.py`) | `rules.py` + keyin PostgreSQL `grammar_rules` | Izohlar uz / ru / en. `review_status` saqlanadi. |
| Lug'at interfeysi va bir nechta manbadan yuklash | `lexicon.py` | Seed + paketlar + foydalanuvchi lug'ati. |
| Foydalanuvchi lug'ati va AI takliflari uchun ko'rib chiqish navbati | Shaxsiy lug'at + admin panel | AI taklifi avval navbatga tushadi, tasdiqlangandan keyin lug'atga o'tadi. |
| AI natijasini engine bilan qayta tekshirish (`verify.py`) | AI Gateway javobini tekshirish | AI yaratgan mashqlar engine'dan o'tadi. Mos kelmasa belgilanadi. |
| Corpus testlari + "har bir qoida testlangan" testi + arxitektura testi | `core/tests` | pytest, xuddi ArabMorph'dagidek. |
| `store.rs` (atomik yozish, backup) | Rust shell | Eksport va backup fayllar uchun. Asosiy ma'lumot SQLite'ga o'tadi. |
| `log.rs` (rotatsiya) | Rust shell | O'zgarishsiz. |
| Mavzu tizimi (CSS o'zgaruvchilar, kunduz / tun / avto) | `apps/client/src/theme` | Ranglar Tilsim palitrasiga almashadi. |
| i18n tuzilmasi (tiplangan asosiy til, `vue-tsc` tekshiruvi) | `apps/client/src/i18n` | `uz` / `ru` / `en`. Arab tili va RTL olib tashlanadi. |
| `countdown.ts` (to'xtatib turiladigan taymer) | Test va o'yinlar | O'zgarishsiz. |
| Mashg'ulot va test logikasi (Activity / Test), distraktorlar | Tests & Word Games | Distraktorlar: boshqa kelishik, boshqa rod, qoida xatosi. |
| Natijalar tarixi va `.xlsx` eksport | Statistika | Ma'lumot SQLite'dan olinadi. |
| CI (Windows), NSIS sozlamalari, updater tayyorgarligi, `.gitignore` | Repozitoriy asosi | Android build qo'shiladi. |
| Xavfsizlik amaliyotlari: CSP, kirish ma'lumotini servisda tekshirish, fayl hajmi va qator cheklovi | Hammasi | Saqlanadi va kengaytiriladi. |

---

## 3. Rus tiliga moslashtiriladigan qismlar

| ArabMorph | Nima o'zgaradi |
| --------- | -------------- |
| `types.py` (3 kelishik, 3 son, ikki rod) | 6 kelishik (+ 2-predlojniy va 2-roditelniy uchun joy), 2 son, 3 rod + umumiy rod, jonli / jonsiz, vid, zamon, shaxs, mayl, nisbat, qisqa / to'liq shakl, qiyoslash darajasi. |
| `normalize.py` (arab Unicode) | Rus normalizatsiyasi: `ё` / `е`, urg'u belgisi (U+0301) saqlanadi yoki olib tashlanadi, kirill so'z ichidagi lotin "o'xshash" harflar (a, o, e, c, p, x) aniqlanadi va ogohlantiriladi, defis va katta harf. |
| `clusters.py` (harf + harakat) | Harf + urg'u. Ichki shaklda urg'u alohida maydonda saqlanadi, matnga qo'shilmaydi. |
| `classify.py` (oxirgi harf bo'yicha tasnif) | Turlanish va tuslanish turlari (Zaliznyak indeksi asosida), urg'u sxemasi, unli va undosh almashinuvi. |
| `declension.py`, `dual.py`, `plural.py` | Otlarning turlanishi (3 ta asosiy tur + noodatiy otlar), sifatlarning moslashuvi, olmosh va sonlarning turlanishi. |
| Fe'l bo'limi yo'q | Noldan (4-bo'lim). |
| `context.py` (oldingi so'z → kelishik) | **To'g'ridan-to'g'ri o'xshashi bor:** rus predloglari kelishikni boshqaradi (`без` → roditelniy, `в` → vinitelniy yoki predlojniy). Ikki kelishikli predloglar `ambiguous` qaytaradi. Keyinroq fe'l boshqaruvi (`ждать` + rod./vin.). |
| `function_words.py` | Predloglar, bog'lovchilar, yuklamalar. |
| `analyze.py` | Teskari tahlil o'sha usulda: har bir variant qayta generatsiya bilan tasdiqlanadi. Ruschada omonimiya ko'p (`стали` = `стать` fe'li yoki `сталь` oti), shuning uchun bir nechta tahlil ehtimollik bilan qaytariladi. |
| `vocab.py` (arab / o'zbek ajratish) | Rus / o'zbek ajratish. O'zbek kirillchasi ham bor, shuning uchun bu murakkabroq: `ў қ ғ ҳ` harflari o'zbekcha ekanini ko'rsatadi, ularsiz matn noaniq deb belgilanadi. |
| `importers.py` (Python) | Deyarli o'zgarishsiz ko'chadi (`.docx` / `.xlsx` = zip + XML, standart kutubxona). Pyodide'da ishlaydi. |
| JSON fayllarda saqlash | SQLite'ga o'tadi. |
| Claude ilovadan, o'qituvchi kaliti bilan | Claude faqat serverdagi AI Gateway orqali. Ilovada kalit yo'q. |
| Windows Credential Manager (`keyring`) | Faqat Windows'da ishlaydi. Android uchun boshqa yechim kerak (8-bo'lim). |
| Sinf rejimi (o'qituvchi proyektorda ko'rsatadi) | Shaxsiy o'quvchi rejimi. Navigatsiya: Windows'da chap sidebar, Android'da pastki menyu. |
| Lug'at sxemasi | Lemma (urg'u bilan), so'z turkumi, rod, jonlilik, turlanish turi, urg'u sxemasi, vid jufti, tuslanish turi, noodatiy shakllar, o'zbekcha tarjimalar, misollar. |

---

## 4. Noldan yaratiladigan qismlar

**Rus tili grammatikasi (engine):**
- otlar: rod, son, 6 kelishik, turlanish, jonlilik, noodatiy shakllar (`путь`, `время`, `мать`), qochuvchi unli (`день` → `дня`), urg'u ko'chishi;
- sifatlar: qattiq / yumshoq / aralash asos, moslashuv, qisqa shakl, qiyoslash darajasi;
- fe'llar: infinitiv, tuslanish (I / II va noodatiy), vid, zamonlar, buyruq mayli, shart mayli, `-ся`, undosh almashinuvi (`писать` → `пишу`), suppletiv shakllar (`идти` → `шёл`);
- olmoshlar, sonlar (`два` + roditelniy birlik qoidasi), sifatdosh, ravishdosh;
- teskari tahlil va ishonchlilik darajasi.

**Backend:** Cloudflare Worker REST API, autentifikatsiya (access va refresh token), PostgreSQL sxemasi va migratsiyalar, Hyperdrive ulanishi, R2 ga fayl yuklash, rate limiting, audit log.

**Offline va sinxronizatsiya:** lokal SQLite, o'zgarishlar navbati (outbox), sinxronizatsiya protokoli, kontent paketlari, manifest, delta yangilanish, SHA-256 tekshiruvi, xatoda eski paketga qaytish.

**O'quv modullari:** Dashboard, Dictionary, Daily Reading, Grammar darslari, Tests & Games, Spell Checker, Knowledge Base, Learning Calendar, Smart Flashcards (spaced repetition).

**Boshqalar:** gamification moduli, nutq tizimi (yozib olish, STT, TTS, matnni solishtirish), AI Gateway, Android ilova, Windows'dagi admin panel (kontent kiritish va tasdiqlash).

---

## 5. Taklif etilgan RuMorph arxitekturasi

### 5.1. Umumiy sxema

```
┌────────────── Windows / Android (Tauri 2, bitta kod bazasi) ──────────────┐
│ Vue 3 + TS + Pinia + Router                                               │
│   modullar: dashboard, dictionary, reading, grammar, tests, spell,        │
│             knowledge, calendar, flashcards, speech, admin (faqat Win)    │
│   Pyodide (Web Worker) → tilsim_core (Python):                           │
│      engine, srs, gamification, importers — sof funksiyalar              │
│      TS ↔ Python: JSON so'rov / javob (ArabMorph sidecar protokoli kabi) │
│   data qatlami: repository'lar → SQLite (tauri-plugin-sql)                │
│   sync: outbox + pull cursor                                              │
│ Rust shell: SQLite, fayllar, log, platform pluginlar (mikrofon, TTS)      │
└──────────────────────────────┬────────────────────────────────────────────┘
                               │ HTTPS, Bearer token
┌──────────────────────────────▼────────────────────────────────────────────┐
│ Cloudflare Python Worker (apps/api)                                        │
│   /v1/auth   /v1/sync   /v1/packages   /v1/materials   /v1/ai   /v1/admin │
│   AI Gateway modul → provider: Claude | n8n | boshqa | local              │
│   tilsim_core ← server tomonda ham (AI natijasini tekshirish uchun)        │
└───────┬───────────────────────┬──────────────────────────┬────────────────┘
        │ Hyperdrive            │ R2 binding               │ HTTPS
   PostgreSQL (Neon)       R2: paketlar, audio,       Claude API / n8n
                           foydalanuvchi fayllari
```

### 5.2. Asosiy arxitektura qarorlari

1. **Domen logikasi Python'da, bitta paketda** (`core/`, `tilsim_core`): grammar engine, spaced repetition, gamification qoidalari, fayl importi. Hammasi sof funksiyalar, faqat standart kutubxona.
   - **Qurilmada** Pyodide orqali, alohida Web Worker ichida ishlaydi, shuning uchun interfeys qotib qolmaydi. Pyodide fayllari ilova bilan birga keladi, internet kerak emas.
   - **Serverda** o'sha paket Cloudflare Python Worker'da ishlaydi.
   - ArabMorph'dagi "engine hech qanday framework'ni import qilmaydi" qoidasi test bilan saqlanadi.
   - **Chegara:** Python ma'lumotni o'zi saqlamaydi va tarmoqqa chiqmaydi. Kerakli ma'lumotni TypeScript qatlami beradi va natijani qaytarib oladi.

   **Interfeys va ma'lumot qatlami TypeScript'da** (Vue 3, prompt talabi): ekranlar, SQLite, sinxronizatsiya, API klienti.

   **1-bosqich boshidagi sinov (spike):** Pyodide'ning telefoningizda ishga tushish vaqti va Python Worker'ning bepul tarifdagi 10 ms CPU cheklovi ichida ishlashi o'lchanadi. Natija yomon bo'lsa, engine TypeScript'ga o'tkaziladi (A variant). Bu qaror siz bilan birga qabul qilinadi.

2. **Monorepo.** JavaScript qismi uchun npm workspaces, Python qismi uchun `uv` va `pyproject.toml`. ArabMorph ham npm va `pyproject.toml` ishlatadi.

3. **Offline-first.** Ilova har doim lokal SQLite bilan ishlaydi. Server faqat sinxronizatsiya, kontent paketlari va AI uchun kerak. UI hech qachon to'g'ridan-to'g'ri serverga bog'liq bo'lmaydi.

4. **Lug'at ma'lumoti va qoidalar alohida.** Rus tilida 390 mingdan ortiq lemma bor. Telefon uchun barcha shakllarni saqlash juda katta hajm. Yechim: lemma + paradigma (qo'shimchalar jadvali) formatida saqlash. Shakllar shundan generatsiya qilinadi. MVP'da qo'lda tekshirilgan asosiy lug'at (A1–B1, 3–5 ming lemma) bo'ladi. Katta lug'at alohida yuklab olinadigan paket sifatida keyinroq qo'shiladi.

5. **Lug'atda yo'q so'zlar** qo'shimchasiga qarab taxmin qilinadi (`source: heuristic`, past ishonch, `ambiguous`). Hech qachon `ok` bo'lmaydi.

6. **Backend: Cloudflare Python Worker.** Framework 1-bosqichdagi sinovdan keyin tanlanadi: FastAPI (ASGI orqali qo'llab-quvvatlanadi) yoki CPU cheklovi uchun yengilroq router. **DB drayveri:** Hyperdrive orqali `asyncpg`. **Validatsiya:** pydantic modellari. Ulardan JSON Schema chiqariladi va TypeScript tiplari shundan avtomatik yaratiladi, shuning uchun ikki tomondagi API tiplari bir-biridan ajralib ketmaydi.

7. **Admin panel** client ilova ichidagi alohida bo'lim. Faqat Windows'da va `admin` roli bo'lsa ko'rinadi. Keyinroq alohida loyihaga chiqarish oson bo'lishi uchun o'z papkasida va o'z API yo'llarida (`/v1/admin/*`) turadi.

### 5.3. Papkalar tuzilishi

```
RuMorph/
├── apps/
│   ├── client/                    # Vue 3 + TS + Vite + Pinia (Windows + Android)
│   │   ├── src/
│   │   │   ├── app/               # router, layout (sidebar / bottom nav), platform aniqlash
│   │   │   ├── modules/           # har bir modul o'z papkasida
│   │   │   │   ├── dashboard/  dictionary/  reading/  grammar/  tests/
│   │   │   │   ├── spell/  knowledge/  calendar/  flashcards/  speech/
│   │   │   │   └── admin/         # faqat Windows + admin roli
│   │   │   ├── data/              # SQLite repository'lar, migratsiyalar, sync
│   │   │   ├── api/               # backend klienti (tiplar JSON Schema'dan yaratiladi)
│   │   │   ├── core/              # Pyodide yuklovchi, Web Worker, tilsim_core chaqiruvlari
│   │   │   ├── ui/                # umumiy komponentlar, dizayn tizimi, theme
│   │   │   └── i18n/              # uz / ru / en
│   │   └── src-tauri/             # Rust shell + Android loyiha (gen/android)
│   └── api/                       # Cloudflare Python Worker
│       ├── pyproject.toml
│       └── src/tilsim_api/
│           ├── routes/            # auth, sync, packages, materials, ai, admin
│           ├── ai/                # AI Gateway: router, provider'lar, promptlar
│           ├── db/                # so'rovlar (SQL qatlami alohida)
│           ├── schemas/           # pydantic modellari → JSON Schema → TS tiplar
│           └── lib/               # auth, rate limit, log, xatolar
├── core/                          # tilsim_core — Python domen logikasi (faqat stdlib)
│   ├── pyproject.toml
│   ├── src/tilsim_core/
│   │   ├── engine/                # rus morfologiyasi (ArabMorph tuzilmasi asosida)
│   │   ├── srs/                   # spaced repetition algoritmi
│   │   ├── gamification/          # XP, daraja, streak, yutuq qoidalari
│   │   ├── importers/             # .docx / .xlsx / .txt / .csv
│   │   └── bridge.py              # TS ↔ Python JSON so'rovlar (Pyodide uchun)
│   └── tests/                     # pytest + corpus
├── db/
│   ├── postgres/migrations/       # 0001_init.sql, ...
│   └── sqlite/migrations/
├── content/                       # kontent manbalari → paket build
├── tools/                         # Python: lug'at import, paket yig'ish, checksum
├── brand/                         # logo
└── docs/
```

---

## 6. PostgreSQL va SQLite ma'lumotlar bazasi tuzilishi

### 6.1. Umumiy qoidalar

- **ID:** UUID v7. Mijoz offline holatda ham ID yarata oladi va vaqt bo'yicha tartiblanadi.
- **Sinxronlanadigan jadvallarda:** `user_id`, `created_at`, `updated_at`, `deleted_at` (o'chirish yozuvi, sinxronizatsiya uchun), `version`, `server_seq` (server tartib raqami, pull uchun kursor).
- **Foydalanuvchi ma'lumotlari** har bir so'rovda `user_id` bo'yicha cheklanadi. Bundan tashqari PostgreSQL Row Level Security qo'shimcha himoya sifatida yoqiladi.
- Barcha FK, unique va indekslar migratsiyalarda yoziladi.

### 6.2. PostgreSQL (markaziy baza)

| Guruh | Jadvallar | Asosiy maydonlar va cheklovlar |
| ----- | --------- | ------------------------------ |
| **Hisob** | `users`, `devices`, `refresh_tokens`, `user_settings` | `users.email` UNIQUE, `role` (`user` / `admin`). `devices(user_id, platform, name, last_seen_at)`. Refresh token xeshlangan holda saqlanadi, aylanib turadi (rotation), bekor qilinishi mumkin. |
| **Kontent paketlari** | `packages`, `package_versions` | `packages.code` UNIQUE (`dict-ru-uz`, `grammar-a1a2`...). `package_versions(package_id, version, sha256, size, engine_min, update_type, r2_key, published_at)`, UNIQUE(`package_id`, `version`). |
| **Lug'at** | `dictionary_entries`, `word_forms`, `translations`, `examples`, `topics`, `entry_topics` | `dictionary_entries(lemma, lemma_stressed, pos, gender, animacy, inflection_class, stress_pattern, aspect, aspect_pair_id, cefr_level, verified, source)`. `word_forms(entry_id, form, form_stressed, tags)`, indeks `form` bo'yicha. Teskari qidiruv uchun `translations(entry_id, lang, text)`. |
| **Grammatika** | `grammar_topics`, `grammar_rules`, `grammar_examples`, `lessons`, `lesson_items` | Qoida `id` engine'dagi qoida ID'si bilan bir xil (`noun.decl.1.gen_sg`). `review_status`. Dars mavzuga va CEFR darajasiga bog'langan. |
| **O'qish** | `reading_texts`, `reading_vocab`, `reading_questions` | Daraja, matn, tarjima, audio `r2_key`, taxminiy o'qish vaqti. |
| **Mashqlar** | `exercises`, `tests`, `test_items` | Mashq turi (`multiple_choice`, `order_words`, `fill_gap`, `pick_form`...), `payload jsonb`, `answer jsonb`. |
| **Foydalanuvchi progressi** | `user_vocabulary`, `flashcards`, `review_history`, `reading_history`, `test_results`, `user_progress` | `flashcards(user_id, entry_id, due_at, interval_days, ease, reps, lapses)`, UNIQUE(`user_id`, `entry_id`). `review_history` faqat qo'shiladi (append-only). |
| **Gamification** | `xp_transactions`, `achievements`, `user_achievements`, `daily_goals`, `streak_history` | XP faqat tranzaksiya sifatida yoziladi. Jami summa hisoblanadi. `user_achievements` UNIQUE(`user_id`, `achievement_id`). Bir qurilmada ikki marta hisoblanmasligi uchun `idempotency_key`. |
| **Shaxsiy materiallar** | `user_materials`, `material_files`, `material_chunks` | `material_files(r2_key, mime, size, sha256, status)`. `material_chunks(material_id, page, text, embedding vector)` (pgvector). Faqat egasi ko'radi. |
| **AI** | `ai_requests` | `user_id, task, provider, model, input_tokens, output_tokens, cost_usd, latency_ms, status, error`. Matnning o'zi emas, faqat qisqa xesh va meta saqlanadi. |
| **Tizim** | `sync_history`, `audit_log` | Kim, qachon, qaysi qurilmadan, nima o'zgardi. |

### 6.3. SQLite (har bir qurilmada)

Ikkiga bo'linadi:

1. **Kontent bazalari:** har bir paket uchun alohida fayl (`dict-ru-uz.db`, `grammar-a1a2.db`...). Faqat o'qiladi. Yangilanish yangi faylga yoziladi, tekshiriladi (SHA-256 va sxema versiyasi), keyin eski fayl bilan almashtiriladi. Xato bo'lsa, eski fayl joyida qoladi. Prompt talab qilgan "eski ishlaydigan paket saqlanib qolsin" sharti shu bilan bajariladi.
2. **`user.db`:** foydalanuvchi ma'lumotlari (lug'at, kartochkalar, tarix, XP, streak, sozlamalar) va `outbox` (serverga hali yuborilmagan o'zgarishlar), `sync_state` (oxirgi kursor).

SQLite sxemasi PostgreSQL bilan bir xil nomlar va maydonlarda bo'ladi. Faqat offline kerak bo'lgan jadvallar olinadi. `users`, `refresh_tokens`, `ai_requests`, `audit_log` kabi jadvallar lokal bazada bo'lmaydi.

### 6.4. Sinxronizatsiya

- **Push:** `outbox` dagi o'zgarishlar paket-paket yuboriladi. Har birida `id` va `version` bor. Server qabul qilganini tasdiqlaydi.
- **Pull:** `GET /v1/sync?since=<server_seq>`. Qurilmalar soatiga ishonilmaydi, server o'z tartib raqamini beradi.
- **Konflikt:** oddiy maydonlarda oxirgi yozuv yutadi (`version` bo'yicha). Hisoblagichlar (XP, sharhlar tarixi) faqat qo'shiladigan yozuvlar bo'lgani uchun to'qnashmaydi.
- **Kontent paketlari:** `GET /v1/packages/manifest`. Manifestda ID, versiya, hajm, sana, SHA-256, engine mosligi, yangilanish turi (`full` / `delta`). Delta: versiya N → N+1 o'zgarishlar ro'yxati. Zanjir uzun bo'lsa, butun fayl yuklanadi.
- **Ilova yangilanishi:** Windows'da Tauri updater (foydalanuvchi tasdiqlaydi). Android'da ilova yangi APK haqida xabar beradi va havolani ochadi, o'rnatishni foydalanuvchi tasdiqlaydi.

---

## 7. AI Gateway va kelajakdagi n8n integratsiyasi

### 7.1. Tuzilma

```
client ──► POST /v1/ai/{task} ──► AI Gateway (Worker)
                                   1. auth + huquq + rate limit + kunlik byudjet
                                   2. kirishni tekshirish (hajm, format, tozalash)
                                   3. task → provider tanlash (sozlama jadvali)
                                   4. prompt shabloni (serverda, versiyalangan)
                                   5. provider.complete()
                                   6. javobni yagona formatga keltirish + sxema tekshiruvi
                                   7. kerak bo'lsa engine bilan tekshirish
                                   8. ai_requests ga log
```

- **Provider interfeysi:** `id`, `capabilities`, `complete(request) → AIResult`. Implementatsiyalar: `ClaudeProvider` (hozir), `N8nProvider`, `OpenAICompatibleProvider`, `LocalProvider` (keyin).
- **Task turlari:** `explain_grammar`, `analyze_text`, `spell_check_deep`, `kb_answer`, `generate_exercises`, `study_plan`. Har bir task uchun javob sxemasi (JSON) aniq belgilanadi.
- **Yagona javob:** `{ ok, task, content, sources[], warnings[], usage: { input_tokens, output_tokens, cost_usd }, provider, model, latency_ms }`.
- **Model:** sukut bo'yicha eng arzon Claude modeli. Murakkab tasklar uchun sozlamada kuchliroq model.
- **Xavfsizlik:** API kalit faqat Worker secret'larida. Foydalanuvchi fayllari va matni AI'ga "ma'lumot" sifatida beriladi, ko'rsatma sifatida emas (prompt injection'dan himoya). Kunlik token va xarajat limiti bor.
- **Offline:** AI tugmalari "internet kerak" holatini ko'rsatadi. Offline ishlayotgandek ko'rsatilmaydi.

### 7.2. n8n agenti (9-bosqich)

- n8n o'zi til modeli emas. U workflow orqali LLM'ni (masalan, Claude) va vositalarni chaqiradi.
- `N8nProvider` n8n webhook'iga HMAC imzo bilan so'rov yuboradi va javobni xuddi shu yagona formatda kutadi.
- n8n agentiga RuMorph API'ning maxsus vositalari beriladi: bilimlar bazasidan qidirish, foydalanuvchi progressini o'qish, engine tahlili.
- Frontend n8n haqida hech narsa bilmaydi. Provider almashganda faqat Worker'dagi sozlama o'zgaradi.

### 7.3. Knowledge Base (RAG)

- Fayl R2 ga yuklanadi, matni ajratiladi, sahifa va bo'laklarga bo'linadi, embedding hisoblanadi, `material_chunks` ga yoziladi (pgvector).
- Javobda manba: fayl nomi va sahifa.
- Embedding provayderi 5-bosqichda tanlanadi. Anthropic'ning o'z embedding modeli yo'q, shuning uchun boshqa provayder kerak bo'ladi.
- PDF matnini ajratish qayerda bo'lishi (qurilmada yoki serverda) ham 5-bosqichda hal qilinadi. Worker bepul tarifida CPU vaqti 10 ms, katta PDF'ga yetmaydi.

### 7.4. Nom haqida eslatma

Cloudflare'ning ham "AI Gateway" degan mahsuloti bor (AI so'rovlarini log va keshlash uchun). Bizning AI Gateway — Worker ichidagi o'z modulimiz. Kerak bo'lsa, Cloudflare'nikini uning orqasiga qo'shimcha qatlam qilib qo'yish mumkin. Ular bir-birining o'rnini bosmaydi.

---

## 8. Windows va Android uchun texnik imkoniyatlar

| Imkoniyat | Windows (WebView2) | Android (WebView) | Yechim |
| --------- | ------------------ | ----------------- | ------ |
| Grammar engine | Python, Pyodide orqali webview'da | Python, Pyodide orqali webview'da | Bir xil kod. Telefonda ishga tushish vaqti 1-bosqichda o'lchanadi. |
| SQLite | `tauri-plugin-sql` | `tauri-plugin-sql` (Android rasman qo'llab-quvvatlanadi) | Bir xil. Android'da SQLite kutubxonaga birga qo'shib qurilishi kerak. |
| Python sidecar (`.exe`) | Ishlaydi | **Ishlamaydi** | Ishlatilmaydi. O'rniga Pyodide. |
| Mikrofon (yozib olish) | `getUserMedia` | Manifestda `RECORD_AUDIO` va WebView ruxsati kerak | 1-bosqichda Android'da sinab ko'riladi. Ishlamasa, kichik native plugin yoziladi. |
| Nutqni matnga (STT) | Web Speech API WebView2'da ishonchli emas | Android WebView'da **yo'q** | Online: server orqali STT provayderi. Offline: keyinroq qurilmadagi model (Vosk yoki whisper.cpp). 4-bosqichda tanlanadi. |
| Matnni nutqqa (TTS) | `speechSynthesis` ishlaydi (Windows'da rus ovozi o'rnatilgan bo'lishi kerak) | Android WebView'da `speechSynthesis` **yo'q** | Android: Android TextToSpeech asosida kichik Kotlin plugin. Lug'at so'zlari uchun tayyor audio paketlari (R2) eng sifatli va offline ishlaydi. |
| Fonema darajasidagi baholash | — | — | Alohida modul, 9-bosqich. STT natijasi talaffuz bahosi deb ko'rsatilmaydi. |
| Fayl tanlash | dialog plugin | dialog plugin | Bir xil. |
| Token saqlash | Windows Credential Manager (`keyring`) | `keyring` Android'da ishlamaydi | Android: ilovaning yopiq papkasi (shaxsiy foydalanish uchun yetarli). Keyinroq Android Keystore. |
| Ilova yangilanishi | Tauri updater | Updater plugin desktop uchun | Android: yangi APK haqida xabar + havola. |
| Fon sinxronizatsiyasi | Ilova ochiq paytda taymer | Faqat ilova ochiq paytda | MVP'da fon servisi yo'q. |
| Navigatsiya | Chap sidebar + o'ng panel | Pastki menyu | Bitta Vue kodi, platformaga qarab layout. |
| Build | Windows'da `tauri build` (NSIS) | Android Studio, SDK, NDK, JDK kerak | Kompyuterda Android tooling borligi 1-bosqichda tekshiriladi. |
| O'rnatish | Imzosiz, SmartScreen ogohlantiradi | APK baribir imzolanishi kerak | Shaxsiy keystore. U hech qachon repoga tushmaydi. |

---

## 9. Bosqichma-bosqich roadmap

Prompt'dagi 9 bosqich saqlanadi. Ikkita kichik o'zgarish taklif qilaman:

- **Android tekshiruvi 1-bosqichga qo'shiladi.** Platforma xavflarini (mikrofon, SQLite, build) 8-bosqichgacha kutish xavfli. Shuning uchun 1-bosqichda Android'da oddiy APK yig'ilib, telefoningizda sinab ko'riladi.
- **Dashboard 3-bosqichda XP va streak'siz quriladi.** Bo'sh yoki soxta raqam ko'rsatilmaydi. XP va streak 7-bosqichdan keyin qo'shiladi. Yoki XP va streak hisobini 3-bosqichga olish mumkin. Bu qaror sizda.

| # | Bosqich | Natija | Tugash mezoni |
| - | ------- | ------ | ------------- |
| 1 | Architecture & Foundation | Avval sinov: Pyodide telefonda va Python Worker bepul tarifda. Keyin monorepo, Vue + Tauri skeleti (sidebar / bottom nav, theme, i18n), Pyodide ko'prigi, Python Worker skeleti (`/health`), PostgreSQL migratsiya `0001`, Hyperdrive ulanishi, SQLite + migratsiyalar, auth (ro'yxatdan o'tish, kirish, refresh, logout), CI. | Windows'da ilova ishga tushadi, Android'da APK ochiladi, login ishlaydi, testlar o'tadi. |
| 2 | Rus grammar engine (Python) | Tiplar, normalizatsiya, otlar (rod, son, 6 kelishik), sifatlar, fe'llar (hozirgi, o'tgan, kelasi zamon, vid), olmoshlar, sonlar, predlog → kelishik, teskari tahlil, istisnolar bazasi, seed lug'at. | Har bir qoida corpus testi bilan qoplangan. Noto'g'ri `ok` yo'q. |
| 3 | Learning Modules | Dictionary, Grammar, Daily Reading, Tests & Games, Spell Checker (lokal), Learning Calendar, Flashcards (SRS), Dashboard. | Har bir modul real ma'lumot bilan ishlaydi. |
| 4 | Speech System | Yozib olish, STT, matnni solishtirish (tushib qolgan va noto'g'ri o'qilgan so'zlar), TTS, sekinlashtirilgan audio. | Windows va Android'da ishlaydi. Cheklovlar ochiq ko'rsatiladi. |
| 5 | AI Integration | AI Gateway, Claude provider, grammatika tushuntirish, matn tahlili, Knowledge Base (yuklash, RAG, manba ko'rsatish). | Provider almashtirish faqat sozlama orqali. Xarajat limiti ishlaydi. |
| 6 | Offline System | Kontent paketlari, manifest, delta, SHA-256, rollback, to'liq sinxronizatsiya. | Internetni o'chirib-yoqish sinovi. Windows ↔ Android bir xil holat. |
| 7 | Gamification | XP, darajalar, streak, kunlik maqsadlar, yutuqlar, statistika. | Qoidalar alohida modulda, testlangan. |
| 8 | Windows & Android | Ikonkalar, ruxsatlar, audio, o'rnatuvchilar, updater, platforma sinovlari. | Ikkala o'rnatuvchi tayyor. |
| 9 | Future | n8n agent, boshqa provayderlar, local AI, chuqur talaffuz tahlili, ko'p foydalanuvchi. | Alohida rejalashtiriladi. |

---

## 10. Aniqlangan xavflar va texnik cheklovlar

| # | Xavf | Ta'siri | Chora |
| - | ---- | ------- | ----- |
| 1 | **Rus morfologik lug'ati litsenziyasi.** Eng to'liq ochiq manba OpenCorpora (390 mingdan ortiq so'z). Uning ma'lumotlari Creative Commons Attribution-ShareAlike litsenziyasida. | Shaxsiy foydalanish uchun muammo yo'q. Ilova kelajakda ommaga chiqsa, lug'at ma'lumoti ham CC BY-SA bo'lishi va manba ko'rsatilishi kerak. | Importdan oldin siz tasdiqlaysiz. Manba har bir yozuvda saqlanadi. |
| 2 | **Urg'u.** OpenCorpora'da urg'u yo'q. Urg'u va to'liq paradigmalar Wiktionary'da bor (u ham CC BY-SA). | Urg'usiz lug'at talaffuz o'rganish uchun yaramaydi. | Urg'u Wiktionary'dan olinadi (litsenziyani tasdiqlaganingizdan keyin). Lug'atda yo'q so'z uchun urg'u taxmin qilinmaydi. |
| 3 | **Ruscha–o'zbekcha lug'at.** Litsenziyasi aniq, katta ochiq RU–UZ lug'at bazasini topmadim. | Tarjima kontenti asosiy ish hajmi bo'ladi. | AI tarjimani taklif qiladi, siz admin panelda tasdiqlaysiz. Tasdiqlanmagan tarjima belgilanadi. Sizda o'z lug'atlaringiz bo'lsa, ular import qilinadi. |
| 4 | **Omonimiya** (`стали`, `мой`, `три`). | Bitta so'zga bir nechta tahlil. | Hammasi ehtimollik bilan ko'rsatiladi. Kontekstdan aniqlash cheklangan. |
| 5 | **Android'da nutq imkoniyatlari.** WebView'da STT va TTS yo'q. | Native plugin yoki server kerak. | 4-bosqichda. Mikrofon 1-bosqichda sinaladi. |
| 6 | **STT talaffuzni baholamaydi.** | Noto'g'ri "talaffuzingiz yaxshi" xulosasi xavfi. | Prompt talabi bo'yicha 4 daraja alohida. Fonema bahosi alohida modul. |
| 7 | **Worker bepul tarifi:** 10 ms CPU, kuniga 100 ming so'rov. Hyperdrive bepul tarifi: kuniga 100 ming so'rov. | Og'ir hisob-kitob serverda ishlamaydi. | Engine va fayl tahlili qurilmada. Kerak bo'lsa $5 lik tarif. |
| 8 | **Neon bepul tarifi:** 1 GB joy, oyiga 100 CU-soat. Ishlatilmaganda o'zi to'xtaydi. | Embedding'lar bilan bazaning hajmi o'sadi. To'xtagan bazaning birinchi so'rovi sekinroq. | Shaxsiy foydalanish uchun yetarli. Hajm kuzatiladi. |
| 9 | **Sinxronizatsiya konfliktlari.** | Ma'lumot yo'qolishi. | Faqat qo'shiladigan jurnallar, `version`, server kursori. Sinovlar bilan. |
| 10 | **Android build tooling** (Android Studio, NDK, JDK) kompyuterda bor-yo'qligi noma'lum. | 1-bosqichni sekinlashtirishi mumkin. | 1-bosqich boshida tekshiriladi va o'rnatish yo'riqnomasi beriladi. |
| 11 | **Hajm.** Loyiha juda katta, ishlab chiquvchi bitta. | Hech qachon tugamaydigan loyiha xavfi. | MVP intizomi. Har bir bosqich alohida ishlaydigan holatda tugaydi. |
| 12 | **Pyodide qurilmada.** Runtime bir necha MB. Birinchi ishga tushish telefonda sekinroq. | Ilova hajmi kattaroq, ochilishda kutish. | Pyodide alohida Web Worker'da, fonda yuklanadi. Interfeys darhol ochiladi, engine tayyor bo'lguncha "yuklanmoqda" holati ko'rsatiladi. 1-bosqichda o'lchanadi. |
| 13 | **Python Worker va 10 ms CPU.** Python Worker'ning ishga tushishi bepul tarif cheklovidan oshishi mumkin. | Bepul tarif yetmasligi. | 1-bosqichda o'lchanadi. Yetmasa, $5 lik tarif yoki backend TypeScript'da. |
| 14 | **Ikki til (TS + Python) va ular orasidagi ko'prik.** | Tiplar ajralib ketishi, debugging qiyinlashishi. | Tiplar pydantic → JSON Schema → TS yo'li bilan avtomatik yaratiladi. Ko'prik protokoli ArabMorph sidecar'idagi kabi: so'rov va javob JSON, har bir operatsiya tekshiriladi. |
| 15 | **Git push.** Bu sessiya repoga HTTPS orqali push qiladi. Kompyuterdagi nusxa SSH (`git@github.com`) orqali ishlaydi. | — | Ikkalasi bir repo. Push'dan keyin Desktop'dagi nusxa ham yangilanadi. |

---

## Tasdiqlash uchun savollar

1. ~~Engine tili~~ — **hal qilindi:** B variant (engine va backend Python'da, interfeys TypeScript'da).
2. **PostgreSQL hosting: Neon** (bepul, pgvector bor, Job Agent'da allaqachon ishlatgansiz)? Yoki Railway / Supabase?
3. **Lug'at manbalari:** OpenCorpora (morfologiya) va Wiktionary (urg'u, paradigmalar). Ikkalasi ham CC BY-SA. Tasdiqlaysizmi?
4. **Roadmap o'zgarishlari:** Android tekshiruvini 1-bosqichga olish va Dashboard'ni XP / streak'siz boshlash ma'qulmi?
5. **Logo:** A, B yoki C variant (`brand/tilsim-variantlar.png`)?

Tasdiqlaganingizdan keyin 1-bosqich (Architecture & Foundation) boshlanadi.
