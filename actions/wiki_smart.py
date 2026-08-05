"""
actions/wiki_smart.py
────────────────────────
Wikipedia + Wikidata'ni Gemini tarjima/imlo-tekshiruv qatlami bilan
birlashtiruvchi YAGONA tool — Avelia funksiya-chaqiruvi shu birini ishlatadi.

Oqim:
  1. So'rov tili:
       - lang_hint == "uz"   -> so'rov o'zbekcha deb hisoblanadi, FAQAT imlo
         tuzatiladi (fix_uzbek_spelling), qidiruv o'zbek Wikipedia/Wikidata'da
         ('uz') bajariladi.
       - lang_hint == "auto" (DEFAULT) -> so'rov ingliz tiliga tarjima
         qilinadi (translate_to_english), qidiruv ingliz Wikipedia/Wikidata'da
         ('en') bajariladi — bu har doim eng to'liq/tozaroq manba.
  2. Wikipedia yoki Wikidata'dan xom natija olinadi (allaqachon mavjud
     wikipedia_action / wikidata_action orqali, ularning ichki uz→en
     fallback mexanizmi ham xavfsizlik-to'ri sifatida ishlab turadi).
  3. Xom natija ensure_uzbek() orqali o'tkaziladi — til aniqlanadi, agar
     o'zbekcha bo'lmasa tarjima qilinadi.
  4. Yakuniy (har doim o'zbekcha) matn qaytariladi — Avelia buni to'g'ridan-
     to'g'ri ovoz orqali aytadi.
"""

from __future__ import annotations

from actions.wikipedia_action import wikipedia_action
from actions.wikidata_action import wikidata_action
from actions.gemini_text_tools import (
    translate_to_english,
    fix_uzbek_spelling,
    ensure_uzbek,
)

# Ovozli javob uchun mos uzunlik. Bundan tashqari, bu Gemini'ning tarjima
# chiqish-token chegarasidan (ensure_uzbek) chiqib ketishining ham oldini
# oladi — juda uzun inglizcha maqolalar (masalan "Timur", "Black hole")
# tarjima qilinayotganda matn o'rtasida kesilib qolmasligi uchun.
_MAX_VOICE_CHARS = 1500


def _trim_for_voice(text: str) -> str:
    """Matnni ovozli javob uchun mos uzunlikkacha, jumla chegarasida qisqartiradi."""
    if len(text) <= _MAX_VOICE_CHARS:
        return text
    cut = text[:_MAX_VOICE_CHARS]
    for stop in (". ", ".\n", "! ", "? "):
        idx = cut.rfind(stop)
        if idx != -1 and idx > len(cut) * 0.4:
            return cut[: idx + 1]
    return cut.rstrip() + "..."


def wiki_lookup(parameters: dict, player=None) -> str:
    """
    parameters:
        query     : foydalanuvchi so'ragan mavzu — o'zi aytgan xom tilda/shaklda
        source    : "wikipedia" (tushuntirish/hikoya) | "wikidata" (aniq fakt)
                    (default: "wikipedia")
        mode      : wikipedia uchun -> search | summary | full | random | sections
                                        (default: "summary")
                    wikidata uchun  -> search | facts | property
                                        (default: "facts")
        lang_hint : "uz"   — foydalanuvchi ANIQ "o'zbek tilida qidir" desa
                    "auto" — (default) qolgan barcha holatlarda
        prop      : wikidata "property" mode'i uchun xususiyat nomi
                    (masalan "tug'ilgan_sana", "aholisi")
    """
    query     = (parameters.get("query") or "").strip()
    source    = (parameters.get("source") or "wikipedia").strip().lower()
    lang_hint = (parameters.get("lang_hint") or "auto").strip().lower()
    prop      = (parameters.get("prop") or "").strip()

    if not query:
        return "Nima haqida qidirishni aytmadingiz."

    # 1) So'rovni Gemini orqali tayyorlash
    if lang_hint == "uz":
        search_query = fix_uzbek_spelling(query)
        search_lang = "uz"
    else:
        search_query = translate_to_english(query)
        search_lang = "en"

    # 2) Wikipedia yoki Wikidata'dan xom natija
    if source == "wikidata":
        mode = (parameters.get("mode") or "facts").strip().lower()
        wd_params = {"action": mode, "query": search_query, "lang": search_lang}
        if mode == "property":
            wd_params["prop"] = prop
        raw_result = wikidata_action(wd_params, player=player)
    else:
        mode = (parameters.get("mode") or "summary").strip().lower()
        raw_result = wikipedia_action(
            {"action": mode, "query": search_query, "lang": search_lang}, player=player
        )

    # 3) Yakuniy javobni o'zbek tiliga keltirish
    #    (avval ovoz uchun mos uzunlikka qisqartiramiz — bu tarjimaning
    #    token chegarasidan chiqib, matn o'rtasida kesilib qolishini oldini oladi)
    raw_result = _trim_for_voice(raw_result)
    return ensure_uzbek(raw_result)