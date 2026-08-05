# Wikipedia + Wikidata Module (mustaqil loyiha)

Bu papka Avelia'ga hech qanday bog'liq emas — mustaqil sinash uchun.
Tayyor bo'lgach, `actions/wikipedia_action.py` va `actions/wikidata_action.py`
fayllarini Avelia loyihasidagi `actions/` papkasiga ko'chirib qo'yasiz.

## 1. Kerakli kutubxonani o'rnatish

Faqat bitta tashqi kutubxona kerak — `requests` (ikkala modul ham shuni ishlatadi).

```bash
pip install -r requirements.txt
```

yoki to'g'ridan-to'g'ri:

```bash
pip install requests
```

(Agar Linux/Mac'da "externally-managed-environment" xatosi chiqsa:
`pip install requests --break-system-packages`)

## 2. Papka tuzilishi

```
wikipedia_project/
├── actions/
│   ├── wikipedia_action.py   ← matn/hikoya uchun (Wikipedia)
│   └── wikidata_action.py    ← aniq faktlar uchun (Wikidata)
├── test_wikipedia.py         ← ikkalasini ham sinaydigan skript
├── requirements.txt
└── README.md
```

## 3. Ikkisining farqi (qisqacha)

| | Wikipedia (`wikipedia_action`) | Wikidata (`wikidata_action`) |
|---|---|---|
| Nima qaytaradi | O'qiladigan matn, paragraf | Aniq faktlar (sana, raqam, koordinata) |
| Qachon ishlatiladi | "X kim edi?", "Y haqida gapir" | "Qachon tug'ilgan?", "Aholisi qancha?" |
| Formati | Erkin matn | `xususiyat: qiymat` juftliklari |

## 4. Sinab ko'rish

```bash
cd wikipedia_project
python test_wikipedia.py
```

Skript avval Wikipedia bo'yicha 6 ta, keyin Wikidata bo'yicha 5 ta test
holatini avtomatik bajaradi, so'ng interaktiv rejimga o'tadi — manba
(wiki/wikidata), action va tilni o'zingiz tanlab sinaysiz.

## 5. Modullarni to'g'ridan-to'g'ri ishlatish

```python
from actions.wikipedia_action import wikipedia_action
from actions.wikidata_action import wikidata_action

# Hikoya/tushuntirish kerak bo'lsa:
print(wikipedia_action({"action": "summary", "query": "Amir Temur", "lang": "uz"}))

# Aniq fakt kerak bo'lsa:
print(wikidata_action({"action": "property", "query": "Amir Temur",
                        "lang": "uz", "prop": "tug'ilgan_sana"}))

# Barcha muhim faktlarni birdan olish:
print(wikidata_action({"action": "facts", "query": "O'zbekiston", "lang": "uz"}))
```

`wikidata_action`dagi `prop` uchun tayyor nomlar: `tug'ilgan_sana`,
`vafot_sana`, `tug'ilgan_joy`, `fuqaroligi`, `kasbi`, `poytaxti`,
`aholisi`, `maydoni`, `koordinata`, `rasmiy_til`, `valyuta`, `davlati`
va boshqalar (to'liq ro'yxat faylning `PROPERTY_MAP` qismida). Xohlagan
xom Wikidata P-kodini ham (`"P569"` kabi) to'g'ridan-to'g'ri berish mumkin.

## 6. USER_AGENT'ni o'zgartirish (muhim)

Wikimedia siyosati bo'yicha har bir ilova o'zini tanitadigan User-Agent
yuborishi kerak. Har ikkala faylda ham:

```python
USER_AGENT = "AveliaAssistant/1.0 (https://github.com/your-repo; contact@example.com)"
```

qatorini o'zingizning haqiqiy ma'lumotingizga almashtiring.

---

## 7. Gemini tarjima qatlami (`wiki_smart.py`)

Sizning talabingizga ko'ra qo'shildi: **Wikipedia/Wikidata'ga har doim
ingliz tilida murojaat qilinadi (foydalanuvchi aniq "o'zbekcha qidir"
demasa), natija esa har doim Gemini orqali o'zbek tiliga tarjima qilinib
qaytariladi.**

Fayllar:
- `actions/gemini_text_tools.py` — Gemini bilan uchta vazifa: `translate_to_english`,
  `fix_uzbek_spelling`, `ensure_uzbek` (til aniqlash + kerak bo'lsa tarjima).
- `actions/wiki_smart.py` — yuqoridagilarni `wikipedia_action`/`wikidata_action`
  bilan birlashtiruvchi yagona `wiki_lookup()` funksiyasi.

**Standalone sinash uchun** (`test_wikipedia.py` ichidagi SMART testlar):

```bash
cp config/api_keys.json.example config/api_keys.json
```

va faylga haqiqiy Gemini API kalitingizni yozing:

```json
{"gemini_api_key": "AIzaSy...."}
```

Keyin `python test_wikipedia.py` — endi WIKI/WIKIDATA testlaridan keyin 3 ta
SMART test ham ishga tushadi. **Eslatma:** `config/api_keys.json` bo'lmasa
ham dastur qulab tushmaydi — Gemini chaqiruvi xato bersa, `gemini_text_tools.py`
shunchaki asl (tarjima qilinmagan) matnni qaytaradi.

`TEXT_MODEL` qatorini (`actions/gemini_text_tools.py` ichida) o'zingizdagi
google-genai SDK versiyasida mavjud bo'lgan model nomiga moslang.

## 8. Avelia'ga ulash — to'liq tayyor kod

Sinovdan o'tgach, quyidagi o'zgarishlarni Avelia'ning `main.py`siga kiritasiz.
**Diqqat:** endi Avelia'ga faqat BITTA yangi tool qo'shiladi — `wiki_lookup`,
chunki til mantig'i (ingliz/o'zbek, tarjima) endi shu tool ichida avtomatik
hal qilinadi.

### 8.1. Fayllarni ko'chirish

To'rtala faylni Avelia'ning `actions/` papkasiga ko'chiring:
- `wikipedia_action.py`
- `wikidata_action.py`
- `gemini_text_tools.py`
- `wiki_smart.py`

(`config/api_keys.json` Avelia'da allaqachon mavjud — `gemini_api_key`
maydoni bor bo'lsa, qo'shimcha hech narsa qilish shart emas, chunki
`gemini_text_tools.py` xuddi shu faylni o'qiydi.)

### 8.2. Import qo'shish

`main.py`dagi boshqa `actions.*` importlari yoniga:

```python
from actions.wiki_smart import wiki_lookup
```

(`wikipedia_action`, `wikidata_action`, `gemini_text_tools` bevosita
`main.py`da kerak emas — ular `wiki_smart.py` ichida allaqachon import
qilingan.)

### 8.3. TOOL_DECLARATIONS ro'yxatiga qo'shish

```python
    {
        "name": "wiki_lookup",
        "description": (
            "Wikipedia (tushuntirish/hikoya) yoki Wikidata'dan (aniq fakt: sana, "
            "aholi, koordinata va h.k.) ma'lumot oladi. Til mantig'i avtomatik: "
            "agar foydalanuvchi ANIQ 'o'zbek tilida qidir' / 'o'zbekchada top' "
            "demagan bo'lsa, lang_hint='auto' qoldiring — bu holda so'rov ichki "
            "tarzda inglizchaga tarjima qilinib, ingliz Wikipedia/Wikidata'dan "
            "eng to'liq ma'lumot olinadi. Foydalanuvchi aniq o'zbek tilida "
            "qidirishni so'rasa, lang_hint='uz' qiling. Natija HAR DOIM avtomatik "
            "o'zbek tiliga tarjima qilib qaytariladi — boshqa hech narsa qilish shart emas."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Foydalanuvchi so'ragan mavzu/savol, o'zi aytgan tilda"
                },
                "source": {
                    "type": "STRING",
                    "description": "'wikipedia' — tushuntirish/hikoya kerak bo'lsa (default). 'wikidata' — aniq sana/raqam/fakt kerak bo'lsa."
                },
                "mode": {
                    "type": "STRING",
                    "description": (
                        "source='wikipedia' bo'lsa: search|summary|full|random|sections (default: summary). "
                        "source='wikidata' bo'lsa: search|facts|property (default: facts)."
                    )
                },
                "lang_hint": {
                    "type": "STRING",
                    "description": "'auto' (default, tavsiya etiladi) yoki 'uz' (foydalanuvchi aniq o'zbekcha qidirishni so'ragandagina)"
                },
                "prop": {
                    "type": "STRING",
                    "description": (
                        "mode='property' uchun majburiy: tug'ilgan_sana | vafot_sana | "
                        "tug'ilgan_joy | fuqaroligi | kasbi | poytaxti | aholisi | maydoni | "
                        "koordinata | rasmiy_til | valyuta | davlati (yoki xom P-kod, masalan 'P569')"
                    )
                },
            },
            "required": ["query"]
        }
    },
```

### 8.4. `_execute_tool` ichidagi dispatch (elif zanjiri)

`elif name == "web_search":` blokidan keyin qo'shing:

```python
            elif name == "wiki_lookup":
                r = await loop.run_in_executor(None, lambda: wiki_lookup(args, player=self.ui))
                result = r or "Ma'lumot topilmadi."
                self.ui.show_content(f"WIKI — {args.get('query', '')[:38]}", result)
```

**Muhim eslatma — ishlash tezligi:** `wiki_lookup` har bir chaqiruvda odatda
2 ta Gemini matn-so'rovi (tarjima/imlo + yakuniy o'zbekchalashtirish) va 1-2
ta Wikipedia/Wikidata so'rovini ketma-ket bajaradi. Bu ovozli javobni odatiy
`web_search`ga qaraganda biroz sekinroq qiladi (taxminan 2-5 soniya). Bu
me'yorda — `run_in_executor` orqali asosiy ovozli oqim bloklanmasligi
allaqachon ta'minlangan.

Shu bilan tayyor. Sinab ko'rib, biror joyda muammo chiqsa — ayting.
