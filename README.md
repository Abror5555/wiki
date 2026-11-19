# uzwiki

**Wikipedia va Wikidata'dan o'zbek tilida ma'lumot olish uchun Python kutubxonasi va buyruq qatori (CLI).**

> **English:** `uzwiki` looks up Wikipedia articles and Wikidata facts with Uzbek as the default
> language, falls back to English automatically, and can optionally translate queries and answers
> with Google Gemini — handy for Uzbek-speaking voice assistants and chat bots.

- 📖 **Wikipedia** — qidiruv, maqola mazmuni, to'liq matn, bo'limlar, tasodifiy maqola
- 📊 **Wikidata** — aniq faktlar: tug'ilgan sana, aholi, poytaxt, koordinata va boshqalar
- 🔁 **Avtomatik fallback** — o'zbekcha maqola topilmasa, inglizchasi olinadi
- 🤖 **Gemini qatlami (ixtiyoriy)** — so'rovni tozalaydi/tarjima qiladi, javobni o'zbekchaga o'giradi
- 🛡️ **Wikimedia qoidalariga mos** — to'g'ri User-Agent, so'rovlar orasida tanaffus, 429 da qayta urinish
- 🎙️ **Ovozli yordamchilar uchun tayyor** — `(parameters, player=None)` imzosi tool-calling'ga mos

## O'rnatish

```bash
pip install uzwiki
```

Gemini tarjima qatlami bilan:

```bash
pip install "uzwiki[gemini]"
```

Python 3.10 yoki undan yangi versiya kerak.

## Buyruq qatori (CLI)

```bash
uzwiki summary "Amir Temur"                 # qisqacha mazmun
uzwiki search "sun'iy intellekt"            # maqolalarni qidirish
uzwiki full "Python (dasturlash tili)"      # to'liq matn (4000 belgigacha)
uzwiki sections "O'zbekiston"               # bo'limlar ro'yxati
uzwiki random --lang en                     # tasodifiy maqola
uzwiki facts "O'zbekiston"                  # Wikidata: asosiy faktlar
uzwiki wd-search "Amir Temur"               # Wikidata: elementlarni qidirish
uzwiki property "Toshkent" aholisi          # Wikidata: bitta xususiyat
uzwiki smart "amir temur kim edi"           # Gemini qatlami bilan, javob doim o'zbekcha
```

Har bir buyruqda `--lang uz|en|ru|...` bilan tilni tanlash mumkin (standart: `uz`).
Yordam: `uzwiki --help` yoki `uzwiki property --help`.

## Python'da ishlatish

```python
from uzwiki import wikipedia_action, wikidata_action

# Hikoya/tushuntirish kerak bo'lsa:
print(wikipedia_action({"action": "summary", "query": "Amir Temur", "lang": "uz"}))

# Aniq fakt kerak bo'lsa:
print(wikidata_action({"action": "property", "query": "Amir Temur",
                        "lang": "uz", "prop": "tug'ilgan_sana"}))

# Barcha muhim faktlarni birdan olish:
print(wikidata_action({"action": "facts", "query": "O'zbekiston", "lang": "uz"}))
```

| | Wikipedia (`wikipedia_action`) | Wikidata (`wikidata_action`) |
|---|---|---|
| Nima qaytaradi | O'qiladigan matn, paragraf | Aniq faktlar (sana, raqam, koordinata) |
| Qachon ishlatiladi | "X kim edi?", "Y haqida gapir" | "Qachon tug'ilgan?", "Aholisi qancha?" |
| `action` qiymatlari | `search`, `summary`, `full`, `random`, `sections` | `search`, `facts`, `property` |

`wikidata_action`dagi `prop` uchun tayyor nomlar: `tug'ilgan_sana`, `vafot_sana`, `tug'ilgan_joy`,
`fuqaroligi`, `kasbi`, `poytaxti`, `aholisi`, `maydoni`, `koordinata`, `rasmiy_til`, `valyuta`,
`davlati` va boshqalar (to'liq ro'yxat: `uzwiki.PROPERTY_MAP`). Xom Wikidata P-kodini ham
(`"P569"` kabi) to'g'ridan-to'g'ri berish mumkin.

## Gemini tarjima qatlami (`wiki_lookup`)

`wiki_lookup` so'rovni Gemini orqali tayyorlaydi (inglizchaga tarjima qiladi yoki o'zbekcha imloni
tuzatadi), Wikipedia/Wikidata'dan qidiradi va natijani **har doim o'zbek tilida** qaytaradi.

```python
import uzwiki

uzwiki.set_api_key("AIzaSy...")   # yoki GEMINI_API_KEY muhit o'zgaruvchisi
print(uzwiki.wiki_lookup({"query": "amir temur kim edi"}))
print(uzwiki.wiki_lookup({"query": "ozbekistn aholisi qancha", "source": "wikidata",
                          "mode": "property", "prop": "aholisi", "lang_hint": "uz"}))
```

API kalit quyidagi tartibda qidiriladi:

1. `uzwiki.set_api_key("...")`
2. `GEMINI_API_KEY` muhit o'zgaruvchisi
3. Joriy papkadagi `config/api_keys.json` (namuna: [`config/api_keys.json.example`](config/api_keys.json.example))

Kalit topilmasa yoki `google-genai` o'rnatilmagan bo'lsa, dastur qulab tushmaydi —
`wiki_lookup` shunchaki tarjima qilinmagan natijani qaytaradi. Modelni o'zgartirish:
`uzwiki.gemini_tools.TEXT_MODEL = "models/..."`.

## User-Agent (muhim)

Wikimedia siyosati bo'yicha har bir ilova o'zini tanitadigan User-Agent yuborishi kerak.
Standart qiymat: `uzwiki/<versiya> (https://github.com/Abror5555/wiki)`. O'z ilovangiz uchun
o'zgartiring:

```python
uzwiki.set_user_agent("MyBot/1.0 (https://github.com/me/mybot; me@example.com)")
```

yoki `UZWIKI_USER_AGENT` muhit o'zgaruvchisi orqali.

## Ovozli yordamchiga ulash (masalan, Avelia)

1. O'rnating: `pip install "uzwiki[gemini]"`
2. Import qiling:

   ```python
   from uzwiki import wiki_lookup
   ```

3. `TOOL_DECLARATIONS` ro'yxatiga qo'shing:

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

4. `_execute_tool` ichidagi dispatch'ga qo'shing:

   ```python
               elif name == "wiki_lookup":
                   r = await loop.run_in_executor(None, lambda: wiki_lookup(args, player=self.ui))
                   result = r or "Ma'lumot topilmadi."
                   self.ui.show_content(f"WIKI — {args.get('query', '')[:38]}", result)
   ```

Avelia'ning `config/api_keys.json` fayli bo'lsa, `uzwiki` kalitni o'sha yerdan o'zi o'qiydi
(dastur loyiha papkasidan ishga tushirilganda). `wiki_lookup` odatda 2 ta Gemini va 1-2 ta
Wikipedia/Wikidata so'rovini ketma-ket bajaradi (taxminan 2-5 soniya), shuning uchun uni
`run_in_executor` orqali chaqirish tavsiya etiladi.

## Ishlab chiqish

```bash
git clone https://github.com/Abror5555/wiki
cd wiki
pip install -e ".[dev,gemini]"
pytest                      # internetsiz testlar
python examples/demo.py     # haqiqiy so'rovlar bilan namoyish + interaktiv rejim
```

## PyPI'ga chiqarish (muallif uchun)

Yangi versiya chiqarish GitHub Actions orqali avtomatlashtirilgan
([`.github/workflows/publish.yml`](.github/workflows/publish.yml)):

1. **Bir martalik sozlash:** pypi.org'da akkaunt oching → *Your projects* → *Publishing* →
   *Add a new pending publisher* → GitHub tab: Owner `Abror5555`, Repository `wiki`,
   Workflow `publish.yml`, Environment `pypi`, PyPI project name `uzwiki`.
2. `src/uzwiki/_meta.py` dagi `__version__` ni yangilang (masalan `0.1.1`).
3. GitHub'da *Releases* → *Draft a new release* → teg `v0.1.1` → *Publish release*.
   Workflow testlarni o'tkazadi, paketni yig'adi va PyPI'ga yuklaydi.

## Litsenziya

[MIT](LICENSE) © 2026 Abror Kushshiyev
