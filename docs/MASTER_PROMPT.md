# RUSSIANMORPH — MASTER DEVELOPMENT PROMPT

## 1. SENING ROLING

Sen Senior Software Architect, Full-Stack Developer, AI Engineer, Database Architect va UI/UX Designer sifatida ishlaysan.

Mening maqsadim — **RussianMorph** nomli professional rus tili o‘rganish platformasini yaratish.

Bu oddiy lug‘at yoki grammatika ilovasi emas. Bu foydalanuvchiga rus tilini bosqichma-bosqich o‘rgatadigan, uning xatolarini tahlil qiladigan, talaffuzini tekshiradigan, shaxsiy o‘quv materiallarini boshqaradigan va rivojlanishini kuzatadigan kompleks o‘quv ekotizimi bo‘lishi kerak.

Loyiha Windows va Android qurilmalarida ishlashi, internet bilan ham, internetsiz ham imkon qadar ko‘p funksiyalarni taqdim etishi kerak.

**Eng muhim talab:** mavjud ArabMorph AI loyihasining arxitekturasi va foydali modullaridan asos sifatida foydalan. Uni diqqat bilan o‘rgan, so‘ng rus tilining grammatikasi va morfologiyasiga moslashtir. Arab tiliga xos grammatik qoidalarni ko‘chirib o‘tma.

---

# 2. ISHNI BOSHLASHDAN OLDINGI MAJBURIY TALABLAR

Dastlab kod yozishga shoshilma.

1. Mavjud loyiha papkalarini va fayllarini tekshir.
2. ArabMorph loyihasining arxitekturasini, modullarini, ma'lumotlar bazasini va ishlash mexanizmini o‘rgan.
3. Qaysi modullarni qayta ishlatish mumkinligini aniqlab chiq.
4. Qaysi qismlarni rus tiliga moslashtirish kerakligini belgilab ol.
5. Qaysi qismlarni noldan yaratish kerakligini aniqlagin.
6. Texnologiyalar o‘rtasidagi moslikni tekshir.
7. Loyihaning umumiy arxitekturasini ishlab chiq.
8. Bosqichma-bosqich Development Roadmap tayyorla.

Dastlab menga:
- ArabMorph tahlili;
- RussianMorph arxitekturasi;
- loyiha papkalari tuzilishi;
- asosiy modullar;
- texnologiyalar;
- ishlab chiqish bosqichlari

bo‘yicha aniq hisobot taqdim et.

Men tasdiqlaganimdan keyin ishlab chiqishni boshlash mumkin.

**Muhim:** mavjud ArabMorph kodini o‘zboshimchalik bilan o‘zgartirma. RussianMorph uchun alohida loyiha yarat. ArabMorph loyihasiga zarar yetkazma.

---

# 3. LOYIHANING TEXNOLOGIK ARXITEKTURASI

Quyidagi texnologiyalar asosiy tanlov hisoblanadi:

### Frontend
- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Zamonaviy komponentlar arxitekturasi

### Desktop va Mobile
- Tauri 2
- Windows desktop
- Android mobile

Tauri 2 ning Windows va Android uchun joriy imkoniyatlarini, pluginlar mosligini va platforma cheklovlarini oldindan tekshir. Agar biror funksiya ikkala platformada bir xil ishlamasa, mos alternativani taklif qil.

### Backend
- Cloudflare Workers
- REST API
- Zarur joylarda background processing
- API orqali frontend va markaziy ma'lumotlar bazasi o‘rtasidagi aloqa

### Markaziy ma'lumotlar bazasi
- PostgreSQL

PostgreSQL loyihaning asosiy markaziy bazasi bo‘ladi.

Cloudflare D1 ishlatilmasin.

Cloudflare Workers va PostgreSQL o‘rtasidagi ulanish uchun joriy texnik imkoniyatlarni tekshir. Serverless muhitga mos ulanish usuli, connection pooling yoki Cloudflare Hyperdrive kabi mexanizmlardan foydalanish imkoniyatini bahola.

### Lokal ma'lumotlar bazasi
- SQLite

Har bir qurilmada lokal SQLite bazasi bo‘ladi.

### Fayllarni saqlash
- Cloudflare R2

PDF, DOCX, TXT, XLSX, CSV, audio va boshqa katta hajmdagi fayllar R2 orqali saqlanishi mumkin.

### AI
- Dastlab Claude API.
- Kelajakda n8n orqali boshqariladigan o‘zimizning AI agentimiz.
- Keyinchalik boshqa AI provayderlari yoki local AI modellarini ulash imkoniyati.

Claude API kalitini hech qachon frontend, mobil ilova yoki desktop dastur ichiga joylashtirma. API kalitlari faqat server tomonida saqlansin.

### Muhim arxitektura qoidasi

Ilova hech qachon to‘g‘ridan-to‘g‘ri Claude API bilan bog‘lanmasin.

Barcha AI so‘rovlari yagona **AI Gateway** orqali boshqarilsin.

AI Gateway keyinchalik Claude, n8n agenti yoki boshqa AI provayderiga yo‘naltira oladigan mustaqil modul bo‘lishi kerak.

---

# 4. ARABMORPH GRAMMAR ENGINE'INI RUS TILIGA MOSLASHTIRISH

Bu loyihaning eng muhim qismlaridan biri.

ArabMorph'dagi asosiy engine arxitekturasi o‘rganilib, RussianMorph uchun qayta ishlatilishi va moslashtirilishi kerak.

Lekin rus tili grammatikasi alohida tizim sifatida ishlab chiqiladi.

Dastlabki versiyada quyidagi rus tili grammatik imkoniyatlarini qo‘llab-quvvatlashni rejalashtir:

### Otlar (Существительные)
- Род: мужской, женский, средний.
- Единственное и множественное число.
- Шесть падежей.
- Склонение существительных.
- Jonli va jonsiz otlar.
- Istisno va noto‘g‘ri shakllar.

### Sifatlar (Прилагательные)
- Rod bilan moslashish.
- Son bilan moslashish.
- Kelishik bilan moslashish.
- Qisqa va to‘liq shakllar.
- Sifatlarning turlari.

### Fe'llar (Глаголы)
- Инфинитив.
- Спряжение.
- Вид: совершенный / несовершенный.
- Время: настоящее, прошедшее, будущее.
- Лицо и число.
- Наклонение.
- Возвратные глаголы.
- Fe'l boshqaruvi.

### Olmoshlar (Местоимения)
- Личные.
- Притяжательные.
- Указательные.
- Вопросительные.
- Отрицательные.
- Возвратные.

### Sonlar (Числительные)
- Количественные.
- Порядковые.
- Sonlarning otlar bilan moslashuvi.

### Boshqa grammatik mavzular
- Предлоги.
- Союзы.
- Наречия.
- Причастия.
- Деепричастия.
- Sintaksis va gap tuzilishi.
- So‘z tartibi.

### Grammar Engine vazifalari

Foydalanuvchi ruscha so‘z kiritganda tizim imkon qadar quyidagilarni aniqlasin:

- Boshlang‘ich shakli.
- So‘z turkumi.
- Grammatik jinsi.
- Son.
- Kelishik.
- Fe'l bo‘lsa, zamon va aspekt.
- Morfologik tahlil.
- Mumkin bo‘lgan grammatik shakllar.
- Istisnolar.
- Ishonchlilik darajasi.

Engine natijani tushunarli o‘zbekcha izoh bilan ko‘rsata olsin.

**Muhim:** barcha ruscha so‘zlarni oddiy qo‘shimcha qoidalari bilan aniqlash mumkin emas. Istisnolar, o‘zak almashinuvi, urg‘u o‘zgarishi, suppletiv shakllar va noaniqliklar hisobga olinsin.

Noto‘g‘ri natijani ishonchli deb ko‘rsatish taqiqlanadi.

Dastlab engine'ning ishlaydigan MVP versiyasini yarat. Keyinchalik lug‘at va grammatik qoidalar bazasini boyitish imkoniyatini saqla.

---

# 5. ASOSIY MODULLAR

## 5.1. Dashboard

Bosh sahifada quyidagilar ko‘rinsin:

- Bugungi o‘quv maqsadi.
- Bugungi o‘rganilgan so‘zlar.
- Kunlik streak.
- XP va daraja.
- O‘zlashtirish statistikasi.
- Davom ettirilayotgan dars.
- Bugungi o‘qish matni.
- Takrorlash kerak bo‘lgan so‘zlar.
- Oxirgi faoliyatlar.

Dashboard foydalanuvchining real o‘quv holatiga qarab dinamik yangilansin.

## 5.2. Dictionary — Lug‘at

Ruscha–o‘zbekcha va o‘zbekcha–ruscha lug‘at.

Har bir so‘z uchun imkon qadar:

- Ruscha so‘z.
- O‘zbekcha tarjima.
- Transkripsiya.
- Urg‘u belgisi.
- Audio talaffuz.
- So‘z turkumi.
- Grammatik jinsi.
- Boshlang‘ich shakli.
- Grammatik shakllari.
- Misollar.
- Sinonimlar.
- Antonimlar.
- Kontekst.
- So‘zning ishlatilish holatlari.

Qo‘shimcha imkoniyatlar:
- Shaxsiy lug‘atga saqlash.
- Sevimlilarga qo‘shish.
- O‘z so‘zlarini qo‘lda kiritish.
- So‘zlarni mavzular bo‘yicha guruhlash.
- Takrorlash jadvali.

## 5.3. Reading & Speaking — O‘qish va talaffuz

Foydalanuvchiga ruscha matn ko‘rsatiladi.

Foydalanuvchi matnni ovoz chiqarib o‘qiydi.

Tizim:
- Ovoz yozib oladi.
- Nutqni matnga aylantiradi.
- O‘qilgan matn bilan asl matnni solishtiradi.
- Tushirib qoldirilgan so‘zlarni aniqlaydi.
- Noto‘g‘ri o‘qilgan so‘zlarni belgilaydi.
- Urg‘u va talaffuz muammolarini aniqlash imkoniyatini taqdim etadi.
- To‘g‘ri talaffuz namunasini eshittiradi.
- Sekinlashtirilgan audio taqdim etadi.

Talaffuzni baholashda quyidagi darajalarni ajrat:

1. Matnni to‘g‘ri o‘qish.
2. So‘zlarni to‘g‘ri talaffuz qilish.
3. Urg‘uni to‘g‘ri qo‘yish.
4. Fonema darajasida talaffuz tahlili.

Speech-to-text natijasini haqiqiy fonetik baholash deb ko‘rsatma. Fonema darajasidagi baholash uchun mos model yoki maxsus texnologiya zarur bo‘lsa, uni alohida modul sifatida ishlab chiq.

Dastlab mavjud texnik imkoniyatlar asosida MVP yarat, keyinchalik chuqur fonetik tahlilga kengaytir.

## 5.4. Daily Reading — Kunlik o‘qish

Har kuni foydalanuvchiga rus tilida o‘qish uchun matn taqdim etilsin.

Darajalar:
- A1
- A2
- B1
- B2
- C1
- C2

Har bir matnda:
- Sarlavha.
- Matn.
- Audio.
- O‘zbekcha tarjima.
- Yangi so‘zlar.
- Muhim grammatik konstruksiyalar.
- Tushunishni tekshiruvchi savollar.
- Matnni o‘qish vaqti.
- O‘zlashtirish holati.

Foydalanuvchi matnni o‘qigan, yodlagan yoki tugatgan deb belgilashi mumkin.

O‘qish tarixi saqlansin.

Matnlar markaziy bazadan kelishi, foydalanuvchi esa o‘ziga kerakli daraja va paketlarni yuklab olishi mumkin bo‘lsin.

## 5.5. Grammar — Grammatika

Rus tili grammatikasi bosqichma-bosqich o‘rgatiladi.

Har bir darsda:
- Mavzu.
- O‘zbekcha tushuntirish.
- Ruscha misollar.
- Qoidalar.
- Istisnolar.
- Jadval va sxemalar.
- Mashqlar.
- Test.
- Natija.

AI murakkab mavzularni tushuntirishda yordam beradi.

Oddiy grammatik tahlil imkon qadar o‘zimizning Grammar Engine orqali bajarilsin.

## 5.6. Tests & Word Games — Testlar va o‘yinlar

Quyidagi mashqlarni qo‘llab-quvvatla:

- Multiple choice.
- So‘z va tarjimani moslashtirish.
- Gapni to‘g‘ri tartibga keltirish.
- Yetishmayotgan so‘zni topish.
- To‘g‘ri grammatik shaklni tanlash.
- Tinglab so‘zni aniqlash.
- Tarjima mashqlari.
- So‘zlardan gap tuzish.
- Kelishik va fe'l shakllarini aniqlash.

Natijalar, xatolar va vaqt saqlansin.

## 5.7. Spell Checker — Imlo va grammatika tekshiruvi

Foydalanuvchi so‘z yoki matn kiritadi.

Tizim:
- Imlo xatolarini topadi.
- Grammatik xatolarni aniqlaydi.
- Punktuatsiyani tekshiradi.
- Xatolarni belgilaydi.
- To‘g‘ri variantni taklif qiladi.
- Xatoning sababini o‘zbek tilida tushuntiradi.

Imkon qadar oddiy tekshiruvlar lokal engine orqali bajarilsin.

Murakkab kontekstual tekshiruvlar AI Gateway orqali amalga oshirilishi mumkin.

## 5.8. Knowledge Base — Bilimlar bazasi

Foydalanuvchi o‘z o‘quv manbalarini yuklay olsin.

Qo‘llab-quvvatlanadigan formatlar:
- PDF
- DOCX
- TXT
- XLSX
- CSV
- Audio fayllar

Manbalar:
- Darsliklar.
- Lug‘atlar.
- Grammatika kitoblari.
- O‘qish materiallari.
- Mashqlar.
- Audio darslar.

Imkoniyatlar:
- Fayl yuklash.
- Fayllarni guruhlash.
- Qidirish.
- Fayl tarkibini ko‘rish.
- Materiallarni tahlil qilish.
- Kerakli ma'lumotlarni ajratib olish.
- Manbaga tayangan AI javoblari.

AI bilimlar bazasidan javob berganda imkon qadar manba nomi va sahifasini ko‘rsatsin.

Foydalanuvchining shaxsiy materiallari boshqa foydalanuvchilarga avtomatik ko‘rinmasin.

## 5.9. Learning Calendar — O‘quv kalendari

- Kunlik darslar.
- O‘rganilgan mavzular.
- Takrorlash kunlari.
- Test natijalari.
- O‘qish tarixi.
- Kunlik maqsadlar.

Kalendar orqali foydalanuvchi o‘z rivojlanishini kuzata olsin.

## 5.10. Smart Flashcards — Aqlli kartochkalar

Spaced Repetition algoritmi asosida ishlasin.

So‘zlarni quyidagi intervallarda takrorlashni boshlang‘ich mexanizm sifatida qo‘llash mumkin:

- 1 kun.
- 3 kun.
- 7 kun.
- 14 kun.
- 30 kun.

Keyinchalik foydalanuvchining javoblariga qarab interval avtomatik moslashtirilsin.

Har bir kartochkada:
- Ruscha so‘z.
- Tarjima.
- Audio.
- Misol.
- Grammatik ma'lumot.
- Bilish darajasi.

Foydalanuvchi so‘zni bilish darajasini belgilaydi.

---

# 6. GAMIFICATION — MOTIVATSIYA TIZIMI

Dastlab quyidagi funksiyalar kiritilsin:

### XP va darajalar
- Har bir bajarilgan mashq uchun XP.
- Dars tugatish uchun XP.
- Kunlik maqsad uchun bonus.
- Darajalar tizimi.

### Daily Streak
- Ketma-ket o‘qilgan kunlar.
- Streak tarixi.
- Kunlik faollik.

### Daily Goals
- Kunlik so‘zlar soni.
- Kunlik o‘qish vaqti.
- Kunlik grammatik mashqlar.
- Kunlik testlar.

### Achievements & Medals
- Birinchi dars.
- Birinchi 100 ta so‘z.
- 7 kunlik streak.
- 30 kunlik streak.
- Grammatika bosqichini tugatish.
- Testlarda yuqori natija.

### Statistics
- O‘rganilgan so‘zlar.
- O‘zlashtirilgan grammatika mavzulari.
- Testlar natijasi.
- O‘qish vaqti.
- Talaffuz rivojlanishi.
- Umumiy o‘sish.

Gamification tizimi alohida modul bo‘lsin. Keyinchalik o‘zgartirish va yangi yutuqlar qo‘shish oson bo‘lishi kerak.

---

# 7. AI GATEWAY VA KELAJAKDAGI MUSTAQIL AGENT

Bu arxitektura boshidan to‘g‘ri ishlab chiqilishi kerak.

Dastlab Claude API ishlatiladi.

Lekin butun loyiha Claude API'ga qattiq bog‘lanib qolmasin.

AI Gateway quyidagi vazifalarni bajaradi:
- AI so‘rovlarini qabul qilish.
- So‘rov turini aniqlash.
- Tegishli AI provider'ni tanlash.
- Natijani yagona formatga keltirish.
- Xatolarni boshqarish.
- Token va xarajatlarni nazorat qilish.
- So‘rovlarni log qilish.
- Foydalanuvchi huquqlarini tekshirish.

AI Provider interfeysi mustaqil bo‘lsin.

Kelajakda quyidagilarni ulash mumkin bo‘lsin:

1. Claude API.
2. n8n orqali boshqariladigan RussianMorph Agent.
3. Boshqa AI API'lar.
4. Local AI model.

### n8n integratsiyasi

Keyinchalik o‘zimiz n8n'da agent yaratamiz.

U quyidagi vazifalarni bajarishi mumkin:
- Rus tilidagi savollarga javob berish.
- Grammatikani tushuntirish.
- Xatolarni tahlil qilish.
- O‘quv rejasini taklif qilish.
- Bilimlar bazasidan foydalanish.
- Shaxsiy o‘quv tavsiyalarini yaratish.

n8n o‘z-o‘zidan til modeli emasligini hisobga ol. Uni kerakli AI model va vositalar bilan integratsiya qil.

Ilovaning frontend qismi n8n'ning ichki tuzilishini bilmasin. U faqat RussianMorph backend bilan ishlasin.

AI provayderini almashtirish uchun frontendni qayta yozish talab qilinmasin.

AI Conversation Partner hozircha ishlab chiqilmaydi. Keyinchalik alohida modul sifatida qo‘shiladi.

---

# 8. OFFLINE VA ONLINE REJIM

Loyihaning eng muhim talablaridan biri — internet bo‘lmaganda ham o‘rganishni davom ettirish.

### Online rejim

- PostgreSQL markaziy baza.
- Cloudflare Workers API.
- Cloudflare R2 fayllari.
- Claude API orqali AI.
- Markaziy kontent yangilanishlari.
- Sinxronizatsiya.

### Offline rejim

- Lokal SQLite.
- Oldindan yuklab olingan o‘quv paketlari.
- Lokal lug‘at.
- Lokal grammatika engine.
- Lokal testlar.
- Lokal Flashcards.
- Lokal foydalanuvchi statistikasi.
- Lokal o‘quv tarixi.

Internet talab qiladigan AI funksiyalari offline holatda ishlamasligi mumkin. Bunday holat foydalanuvchiga aniq ko‘rsatilsin.

Speech recognition va TTS imkoniyatlari qurilma hamda mavjud lokal modellarga qarab bosqichma-bosqich qo‘shilsin.

Offline rejimda ishlamaydigan funksiyalarni ishlayotgandek ko‘rsatma.

---

# 9. MA'LUMOTLARNI SINXRONIZATSIYA QILISH

Windows va Android qurilmalarida foydalanuvchining o‘quv jarayoni bir xil hisob bilan ishlashi kerak.

Masalan, foydalanuvchi Windows'da 50 ta so‘z o‘rgansa, internetga ulangandan so‘ng bu ma'lumot Android qurilmasiga ham yetib borishi kerak.

### Kontent paketlari

Dastlabki o‘rnatishda foydalanuvchi o‘ziga kerakli paketlarni tanlaydi:

- A1–A2 Grammar.
- B1–B2 Grammar.
- Russian-Uzbek Dictionary.
- Daily Reading.
- Pronunciation Audio.
- Tests & Games.
- Boshqa materiallar.

Barcha ma'lumotlar majburiy yuklanmasin.

### Kontent yangilanishi

Kontent yangilanishlari avtomatik amalga oshirilsin.

Agar markaziy bazada foydalanuvchi yuklab olgan paket o‘zgarsa:
- Tizim yangilanishni aniqlaydi.
- Faqat o‘zgargan ma'lumotlarni yuklaydi.
- Keraksiz katta hajmdagi ma'lumotlar qayta yuklanmaydi.
- Tekshiruvdan keyin lokal baza yangilanadi.

Package Manifest quyidagilarni o‘z ichiga olsin:
- Package ID.
- Version.
- File size.
- Last updated.
- SHA-256 checksum.
- Engine compatibility.
- Update type.

Yangilanish vaqtida xatolik yuz bersa, eski ishlaydigan paket saqlanib qolsin.

### Ilova yangilanishi

Ilovaning yangi versiyasi chiqqanda:
- Foydalanuvchiga bildirishnoma ko‘rsatilsin.
- Versiya va o‘zgarishlar ko‘rsatilsin.
- Foydalanuvchi yuklab olish va o‘rnatishni o‘zi tasdiqlasin.

**Kontent yangilanishi avtomatik, ilova versiyasi yangilanishi esa foydalanuvchi roziligi bilan bo‘ladi.**

### Foydalanuvchi ma'lumotlari

Quyidagi ma'lumotlar offline holatda ham saqlansin:
- O‘rganilgan so‘zlar.
- Test natijalari.
- XP.
- Streak.
- Shaxsiy lug‘at.
- O‘qish tarixi.
- Sozlamalar.

Internet qaytganda ushbu ma'lumotlar markaziy bazaga xavfsiz sinxronlashtirilsin.

---

# 10. FOYDALANUVCHI VA ACCOUNT TIZIMI

Dastlab ilova shaxsiy foydalanish uchun yaratiladi.

Lekin arxitektura kelajakda ko‘p foydalanuvchiga kengayishga tayyor bo‘lsin.

Shu sababli:
- User ID.
- Device ID.
- Authentication.
- Access token.
- Refresh token.
- User progress.
- Personal vocabulary.
- Personal materials.
- User settings

kabi tizimlar boshidan to‘g‘ri rejalashtirilsin.

Har bir foydalanuvchining ma'lumotlari alohida himoyalansin.

Boshqa foydalanuvchi shaxsiy materiallarini ko‘ra olmasin.

---

# 11. DIZAYN VA UI/UX

Dizayn konsepsiyasi: **Modern Dark + Light Mode**.

Professional, premium, zamonaviy va texnologik ko‘rinish.

### Ranglar

Asosiy ranglar uchun o‘zing professional palitra tanla.

Dizayn faqat qora yoki to‘q ranglardan iborat bo‘lib qolmasin.

Light Mode ham to‘liq ishlab chiqilsin.

Ranglar kontrasti, matn o‘qilishi va accessibility talablariga rioya qil.

### Animatsiyalar

O‘rtacha va yuqori sifatli silliq animatsiyalar aralashmasi.

Kerakli joylarda:
- Page transitions.
- Hover effects.
- Progress animations.
- Loading animations.
- Micro interactions.
- Modal transitions.

Oddiy funksional elementlarga keraksiz animatsiyalar qo‘shma.

### Windows navigatsiya

- Chap tomonda Sidebar.
- Markazda asosiy kontent.
- Zarur joylarda o‘ng panel.
- Responsive dashboard.

### Android navigatsiya

- Pastki Bottom Navigation.
- Mobil qurilmaga mos kartochkalar.
- Katta va qulay tugmalar.
- Gesture va touch-friendly interfeys.

### Interfeys tillari

- O‘zbekcha.
- Ruscha.
- Inglizcha.

Foydalanuvchi interfeys tilini almashtira olsin.

Rus tilini o‘rganish kontenti interfeys tilidan mustaqil bo‘lsin.

### Dizayn qoidalari

- Professional typography.
- Yaxshi spacing.
- Consistent design system.
- Reusable components.
- Dark/Light theme.
- Responsive layout.
- Skeleton loading.
- Empty states.
- Error states.
- Success notifications.

Emoji va ortiqcha dekorativ elementlardan foydalanma.

---

# 12. MA'LUMOTLAR BAZASI ARXITEKTURASI

PostgreSQL uchun modulli va kengaytiriladigan schema ishlab chiq.

Dastlab quyidagi asosiy entity'larni rejalashtir:

- Users.
- Devices.
- UserSettings.
- Packages.
- PackageVersions.
- DictionaryEntries.
- WordForms.
- GrammarTopics.
- GrammarRules.
- GrammarExamples.
- Lessons.
- ReadingTexts.
- ReadingHistory.
- Exercises.
- Tests.
- TestResults.
- UserVocabulary.
- Flashcards.
- ReviewHistory.
- UserProgress.
- XPTransactions.
- Achievements.
- UserAchievements.
- DailyGoals.
- StreakHistory.
- UserMaterials.
- MaterialFiles.
- AIRequests.
- SyncHistory.

Barcha entity'lar uchun to‘g‘ri relationship, index, unique constraint va foreign key'lar rejalashtirilsin.

Lokal SQLite schema ham markaziy ma'lumotlar tuzilmasiga mos bo‘lsin, ammo faqat offline ishlashi kerak bo‘lgan ma'lumotlar lokalga yuklansin.

---

# 13. XAVFSIZLIK

Quyidagi xavfsizlik talablariga rioya qil:

- API key'larni frontendda saqlama.
- Secrets faqat server muhitida bo‘lsin.
- Authentication xavfsiz ishlasin.
- Authorization tekshirilsin.
- API rate limiting.
- Input validation.
- SQL injection himoyasi.
- Xavfsiz file upload.
- Fayl hajmi va formatini tekshirish.
- Shaxsiy ma'lumotlarni himoyalash.
- HTTPS.
- Audit log.
- Backup va restore.

AI'ga yuboriladigan foydalanuvchi fayllari va matnlarini ham xavfsizlik nuqtayi nazaridan tekshir.

---

# 14. KOD SIFATI VA DEVELOPMENT QOIDALARI

Quyidagi qoidalarga qat'iy rioya qil:

1. Kod modulli bo‘lsin.
2. Har bir modul o‘z vazifasiga ega bo‘lsin.
3. Bir faylda haddan tashqari ko‘p funksiyalar jamlanmasin.
4. Reusable components ishlat.
5. TypeScript type'larini to‘g‘ri yoz.
6. API va database qatlamlarini ajrat.
7. Error handling to‘liq bo‘lsin.
8. Logging tizimi bo‘lsin.
9. Testlar yozilsin.
10. Muhim funksiyalar hujjatlashtirilsin.
11. Kod takrorlanishi kamaytirilsin.
12. Keraksiz kutubxonalar o‘rnatilmasin.
13. Deprecated texnologiyalardan foydalanma.
14. Platformaga mos kelmaydigan funksiyalarni majburan ishlatma.

Mavjud kodni o‘zgartirishdan oldin uning vazifasini tushun.

Ishlayotgan funksiyalarni sababsiz buzma.

---

# 15. ISHLAB CHIQISH BOSQICHLARI

Loyihani birdaniga to‘liq yaratishga urinma.

Quyidagi bosqichlarda ishlab chiq:

### PHASE 1 — Architecture & Foundation
- ArabMorph arxitekturasini o‘rganish.
- RussianMorph arxitekturasini yaratish.
- Repository structure.
- Frontend foundation.
- Backend foundation.
- PostgreSQL schema.
- SQLite foundation.
- API architecture.
- Authentication.

### PHASE 2 — Core Russian Grammar Engine
- Rus tili grammatikasi uchun model.
- So‘z turkumlari.
- Otlar morfologiyasi.
- Kelishiklar.
- Sifatlar.
- Fe'llar.
- Olmoshlar.
- Sonlar.
- Grammatik tahlil.
- Istisnolar bazasi.

### PHASE 3 — Learning Modules
- Dashboard.
- Dictionary.
- Grammar.
- Daily Reading.
- Tests & Games.
- Spell Checker.
- Learning Calendar.
- Smart Flashcards.

### PHASE 4 — Speech System
- Audio recording.
- Speech recognition.
- Text comparison.
- Pronunciation feedback.
- TTS.
- Talaffuz tahlilini bosqichma-bosqich chuqurlashtirish.

### PHASE 5 — AI Integration
- AI Gateway.
- Claude API.
- AI grammar explanations.
- AI text analysis.
- Knowledge Base integration.
- Provider abstraction.

### PHASE 6 — Offline System
- SQLite local storage.
- Content packages.
- Package manifest.
- Delta updates.
- Offline grammar engine.
- Local progress.
- Synchronization.

### PHASE 7 — Gamification
- XP.
- Levels.
- Streaks.
- Goals.
- Achievements.
- Statistics.

### PHASE 8 — Windows & Android
- Tauri integration.
- Windows build.
- Android build.
- Platform testing.
- Permissions.
- Audio functionality.
- Local storage testing.

### PHASE 9 — Future Integrations
- n8n agent integration.
- Alternative AI providers.
- Local AI.
- Advanced pronunciation engine.
- Multi-user expansion.

Har bir bosqichni alohida yakunla va test qil.

Bir bosqichdagi asosiy muammolar hal qilinmasdan keyingi bosqichga o‘tma.

---

# 16. NATIJA VA ISH USLUBI

Menga shunchaki ko‘p kod yozib berishing kerak emas. Sen loyihaning texnik rivojlanishini boshqaradigan tajribali hamkor sifatida ishlashing kerak.

Har bir bosqichda:

1. Nima qilinishini tushuntir.
2. Qaysi fayllar yaratilishini ko‘rsat.
3. Arxitektura qarorlarini asosla.
4. Kodni yoz.
5. Test qil.
6. Xatolarni tuzat.
7. Natijani hisobot qil.
8. Keyingi bosqichga o‘tishdan oldin zarur tasdiqni ol.

Texnik muammo yuzaga kelsa:
- Muammoning sababini aniqlagin.
- Bir nechta yechimni bahola.
- Eng to‘g‘ri variantni tanla.
- Kerak bo‘lsa mendan qaror so‘ra.

Taxminiy funksiyalarni tayyor deb ko‘rsatma.

Ishlamaydigan tugmalar, soxta statistikalar, demo ma'lumotlar bilan haqiqiy funksiyalarni almashtirma.

MVP uchun zarur bo‘lmagan murakkab funksiyalarni keyingi bosqichga qoldir.

---

# 17. BIRINCHI VAZIFA

Hozircha kod yozishni boshlama.

Birinchi navbatda mavjud ArabMorph AI loyihasini to‘liq tahlil qil.

Menga quyidagi formatda hisobot ber:

1. ArabMorph arxitekturasi qanday ishlaydi?
2. Qaysi modullarni RussianMorph'da qayta ishlatish mumkin?
3. Qaysi modullarni rus tiliga moslashtirish kerak?
4. Qaysi modullarni noldan yaratish kerak?
5. Taklif qilinayotgan RussianMorph arxitekturasi.
6. PostgreSQL va SQLite ma'lumotlar bazasi tuzilishi.
7. AI Gateway va kelajakdagi n8n integratsiyasi.
8. Windows va Android uchun texnik imkoniyatlar.
9. Loyihaning bosqichma-bosqich Roadmap'i.
10. Aniqlangan xavf va texnik cheklovlar.

Agar ArabMorph loyihasining fayllari mavjud bo‘lmasa, ularni o‘zingdan to‘qib chiqarmagin. Mendan loyiha papkasini yoki kerakli fayllarni taqdim etishimni so‘ra.

**Asosiy maqsad: ArabMorph'dan olingan foydali arxitektura asosida, rus tiliga moslashtirilgan, mustaqil rivojlantiriladigan, Windows va Android'da ishlaydigan professional RussianMorph platformasini yaratish.**