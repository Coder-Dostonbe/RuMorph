# Qarorlar jurnali

`MASTER_PROMPT.md` ga qo'shimcha yoki uni aniqlashtiruvchi qarorlar. Yangisi pastga qo'shiladi.

| Sana | Qaror | Kim |
| ---- | ----- | --- |
| 2026-11-19 | Admin panel hozircha faqat Windows ilovasi ichida bo'ladi. Keyinchalik alohida loyiha qilib chiqariladi. | Doston |
| 2026-11-19 | Ilova shaxsiy sinov uchun. Ommaga chiqarilmaydi. Android APK to'g'ridan-to'g'ri o'rnatiladi (Play Store'siz), Windows o'rnatuvchisi imzolanmaydi. | Doston |
| 2026-11-19 | Backend uchun vaqtincha Cloudflare bepul tarifi (Workers, Hyperdrive, R2) ishlatiladi. PostgreSQL tashqi hostingda turadi. | Doston |
| 2026-11-19 | Ilova nomi vaqtincha **Tilsim**. Logo konsepsiyasi: sakkiz qirrali girih yulduzi va kirill "Я" harfi; firuza, indigo, oltin ranglar. | Doston |
| 2026-11-19 | Repozitoriy: `git@github.com:Coder-Dostonbe/RuMorph.git`. Har bir yangilanish shu repoga push qilinadi. | Doston |
| 2026-11-19 | **B variant:** grammar engine va boshqa domen logikasi (SRS, gamification, importlar) Python'da (`core/`, faqat standart kutubxona). Qurilmada Pyodide orqali, serverda Cloudflare Python Workers orqali ishlaydi. Backend ham Python. Interfeys va ma'lumot qatlami Vue 3 + TypeScript. 1-bosqich boshida Pyodide (telefonda) va Python Worker (bepul tarif CPU cheklovi) sinab ko'riladi. Natija yomon bo'lsa, A variantga (TypeScript) qaytish siz bilan birga hal qilinadi. | Doston |
| 2026-11-19 | Kod yozish hali boshlanmaydi. Qolgan savollar (PostgreSQL hosting, lug'at manbalari, roadmap o'zgarishlari, logo) bo'yicha javob kutilmoqda. | Doston |
| 2026-11-20 | PostgreSQL hosting: **Neon** (bepul tarif, pgvector). | Doston |
| 2026-11-20 | Lug'at manbalari: **OpenCorpora** (morfologiya) va **Wiktionary** (urg'u, paradigmalar), ikkalasi CC BY-SA. Doston o'zi ham lug'at kiritadi (admin panel va import orqali). | Doston |
| 2026-11-20 | Roadmap o'zgarishlari qabul qilindi: Android sinov build'i 1-bosqichda; Dashboard 3-bosqichda XP / streak'siz boshlanadi. | Doston |
| 2026-11-20 | Logo: **B variant** (`brand/tilsim-b.svg`). Kichik o'lchamlar (16–32 px) uchun soddalashtirilgan versiya 8-bosqichda kerak bo'lishi mumkin. | Doston |
| 2026-11-20 | 1-bosqich (kod) boshlandi. | Doston |
| 2026-11-20 | Parol xeshlash: PBKDF2-SHA256, 100 000 iteratsiya, Worker'da Web Crypto orqali. Sabab: Pyodide'da `hashlib.pbkdf2_hmac` yo'q, Cloudflare Web Crypto 100 000 dan ko'p iteratsiyani qabul qilmaydi. | Claude (texnik cheklov) |
| 2026-11-20 | **B variant tasdiqlandi.** Telefonda Pyodide noldan 8–10 s edi; xotira snapshot'i qo'shilgach keyingi ochilishlar ~1.7 s (Python 1.38 s + snapshot o'qish 0.31 s). Birinchi ochilish (snapshot yaratish) ~14 s, faqat o'rnatish yoki grammatika moduli yangilanganda. | Doston |
| 2026-11-20 | 2-bosqich boshlandi. Engine lug'atga asoslanadi: OpenCorpora paradigmalari `pymorphy3-dicts-ru` (PyPI) nusxasidan eksport qilinadi, chunki opencorpora.org build mashinasidan ochilmaydi. pymorphy3 faqat eksport vositasi, ilova ichida yo'q. Boshlang'ich lug'at: ~320 ta A1–A2 lemma (`tools/lexicon/seed_lemmas.txt`). | Claude (texnik cheklov) |
| 2026-11-20 | Olmoshlar yopiq so'z turkumi, shuning uchun ularning turi (kishilik, egalik, ko'rsatish, …) qo'shimchadan taxmin qilinmaydi, ro'yxatdan olinadi (`classify.PRONOUN_CLASSES`). Qiyosiy darajasi boshqa o'zakdan yasaladigan sifatlar ham yopiq ro'yxat: хороший, плохой, большой, маленький. Lug'atda yo'q shakl haqida (masalan, высокий → выше OpenCorpora'da yo'q) engine hech narsa demaydi, o'zi yasab ham bermaydi. | Claude (texnik qaror) |
