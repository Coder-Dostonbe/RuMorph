# Tilsim (RuMorph)

O'zbek tilida so'zlashuvchilar uchun rus tilini o'rganish platformasi. Windows va Android'da ishlaydi.

- **Ilova nomi:** Tilsim (vaqtinchalik; keyinroq o'zgarishi mumkin)
- **Ichki loyiha nomi:** RuMorph / RussianMorph
- **Repozitoriy:** `git@github.com:Coder-Dostonbe/RuMorph.git`
- **Foydalanish:** shaxsiy sinov uchun. Ommaga chiqarilmaydi.

## Holat

| Bosqich | Holat |
| ------- | ----- |
| 0 — ArabMorph tahlili, arxitektura, roadmap | **Tayyor, tasdiq kutilmoqda** |
| 1 — Architecture & Foundation | Boshlanmagan |
| 2–9 | Boshlanmagan |

Kod hali yozilmagan. Tahlil va taklif etilgan arxitektura:
[`docs/01-ARABMORPH-TAHLIL-VA-ARXITEKTURA.md`](docs/01-ARABMORPH-TAHLIL-VA-ARXITEKTURA.md).

## Hujjatlar

| Fayl | Mazmuni |
| ---- | ------- |
| [`docs/MASTER_PROMPT.md`](docs/MASTER_PROMPT.md) | Loyihaning asosiy texnik topshirig'i (o'zgartirilmagan asl matn) |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Qabul qilingan qarorlar jurnali (topshiriqqa qo'shimchalar) |
| [`docs/01-ARABMORPH-TAHLIL-VA-ARXITEKTURA.md`](docs/01-ARABMORPH-TAHLIL-VA-ARXITEKTURA.md) | ArabMorph tahlili, arxitektura, bazalar, AI Gateway, platformalar, roadmap, xavflar |
| [`brand/`](brand/) | Tilsim logosi (SVG manba fayllar) |
| [`CLAUDE.md`](CLAUDE.md) | Loyiha ustida ishlaydigan AI uchun ish qoidalari |

## Git qoidasi

**Har bir yangilanish shu repozitoriyga push qilinadi:**

```
git@github.com:Coder-Dostonbe/RuMorph.git
```

- Asosiy branch: `main`.
- Har bir tugallangan qadam alohida commit bo'ladi (`feat: …`, `fix: …`, `docs: …`, `chore: …`).
- Push qilishdan oldin testlar o'tishi kerak (kod paydo bo'lgandan keyin).
- Secrets (API kalitlar, `.env`, signing kalitlari, keystore) hech qachon commit qilinmaydi.

Kompyuterdagi nusxa: `Desktop/RuMorph`.
