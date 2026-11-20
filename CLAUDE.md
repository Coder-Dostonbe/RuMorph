# Tilsim (RuMorph) — AI uchun ish qoidalari

Bu fayl loyiha ustida ishlaydigan har qanday AI sessiyasi (Claude Code va boshqalar) uchun.
Asosiy topshiriq: [`docs/MASTER_PROMPT.md`](docs/MASTER_PROMPT.md). Unga qo'shimcha qarorlar:
[`docs/DECISIONS.md`](docs/DECISIONS.md). Ikkalasini ham ish boshlashdan oldin o'qi.

## Muloqot

- Foydalanuvchi bilan o'zbek tilida gaplash. Texnik terminlar inglizcha bo'lishi mumkin.
- Javoblar qisqa va aniq bo'lsin.

## Git

- **Har bir yangilanish `git@github.com:Coder-Dostonbe/RuMorph.git` ga push qilinadi** (branch `main`).
- Har bir tugallangan qadam alohida commit: `feat: …`, `fix: …`, `docs: …`, `chore: …`, `test: …`.
- Push'dan oldin barcha testlar o'tishi shart.
- Commit muallifi: `Coder-Dostonbe <yusupovdostonbek21@gmail.com>` (GitHub activity shu email bo'yicha hisoblanadi). AI yozgan commit'larda izoh oxirida `Co-Authored-By` qatori bo'ladi.
- Faqat oddiy push. `force push` va tarixni qayta yozish qilinmaydi.
- Secrets hech qachon commit qilinmaydi: `.env`, API kalitlar, Tauri updater private key, Android keystore, sertifikatlar.
- Kompyuterdagi ishchi nusxa: `Desktop/RuMorph`. Push'dan keyin u ham yangilanadi.

## Arxitektura qisqacha

- Domen logikasi (grammar engine, SRS, gamification, importlar) Python'da: `core/` (`tilsim_core`), faqat standart kutubxona. Qurilmada Pyodide, serverda Cloudflare Python Workers.
- Backend: Cloudflare Python Worker (`apps/api`).
- Interfeys va ma'lumot qatlami (SQLite, sync, API klienti): Vue 3 + TypeScript (`apps/client`).
- Batafsil: `docs/01-ARABMORPH-TAHLIL-VA-ARXITEKTURA.md`, 5-bo'lim.

## Bosqichlar

- Ish `docs/01-ARABMORPH-TAHLIL-VA-ARXITEKTURA.md` dagi roadmap bo'yicha, bosqichma-bosqich boradi.
- Har bosqich oxirida: nima qilindi, qaysi fayllar, testlar natijasi, nima qoldi — hisobot.
- **Keyingi bosqichga faqat foydalanuvchi tasdiqlagandan keyin o'tiladi.**

## Qat'iy qoidalar

1. ArabMorph (`Desktop/arabmorph-ai`) faqat o'qiladi. Unga hech narsa yozilmaydi.
2. Claude API kaliti faqat serverda (Cloudflare Worker secrets). Ilovada hech qachon.
3. Ilova AI'ga faqat backend'dagi AI Gateway orqali murojaat qiladi.
4. Grammar engine noto'g'ri natijani hech qachon `ok` deb qaytarmaydi. Ishonch yetmasa: `ambiguous` yoki `error`, sababi bilan.
5. Ishlamaydigan funksiyani ishlayotgandek ko'rsatma. Soxta statistika, demo ma'lumot, bo'sh tugma yo'q.
6. Offline ishlamaydigan funksiya offline holatda aniq "internet kerak" deb ko'rsatiladi.
7. Tashqi lug'at yoki ma'lumot bazasini import qilishdan oldin litsenziyani foydalanuvchi tasdiqlaydi.
8. Katta yangi kutubxona qo'shishdan oldin foydalanuvchidan so'ra.
9. Har bir yangi UI matni uchala tilda bo'ladi: `uz`, `ru`, `en`.
10. Emoji ishlatilmaydi.
