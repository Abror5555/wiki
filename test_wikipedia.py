"""
test_wikipedia.py
──────────────────
Wikipedia va Wikidata modullarini Avelia'siz, mustaqil sinash uchun skript.

Ishga tushirish:
    python test_wikipedia.py

Internet aloqasi kerak (wikipedia.org / wikidata.org ga chiqish).
"""

from actions.wikipedia_action import wikipedia_action
from actions.wikidata_action import wikidata_action

try:
    from actions.wiki_smart import wiki_lookup
    _SMART_AVAILABLE = True
except Exception as e:
    _SMART_AVAILABLE = False
    _SMART_IMPORT_ERROR = e


def run_case(title: str, func, params: dict) -> None:
    print("=" * 70)
    print(f"[{title}]  params = {params}")
    print("-" * 70)
    result = func(params)
    print(result)
    print()


def main() -> None:
    # ── WIKIPEDIA: hikoya/tushuntirish uchun ────────────────────────────
    run_case("WIKI SUMMARY", wikipedia_action, {"action": "summary", "query": "Amir Temur", "lang": "uz"})
    run_case("WIKI SEARCH", wikipedia_action, {"action": "search", "query": "sun'iy intellekt", "lang": "uz"})
    run_case("WIKI FULL", wikipedia_action, {"action": "full", "query": "Python (dasturlash tili)", "lang": "uz"})
    run_case("WIKI SECTIONS", wikipedia_action, {"action": "sections", "query": "O'zbekiston", "lang": "uz"})
    run_case("WIKI RANDOM", wikipedia_action, {"action": "random", "lang": "en"})
    run_case("WIKI FALLBACK", wikipedia_action, {"action": "summary", "query": "Quantum computing", "lang": "uz"})

    # ── WIKIDATA: aniq faktlar uchun ─────────────────────────────────────
    run_case("WD SEARCH", wikidata_action, {"action": "search", "query": "Amir Temur", "lang": "uz"})
    run_case("WD FACTS (odam)", wikidata_action, {"action": "facts", "query": "Amir Temur", "lang": "uz"})
    run_case("WD FACTS (davlat)", wikidata_action, {"action": "facts", "query": "O'zbekiston", "lang": "uz"})
    run_case("WD PROPERTY (sana)", wikidata_action, {
        "action": "property", "query": "Amir Temur", "lang": "uz", "prop": "tug'ilgan_sana",
    })
    run_case("WD PROPERTY (aholi)", wikidata_action, {
        "action": "property", "query": "Toshkent", "lang": "uz", "prop": "aholisi",
    })

    # ── WIKI_SMART: Gemini tarjima qatlami bilan to'liq oqim ────────────
    # E'TIBOR: bu qism uchun config/api_keys.json ichida haqiqiy
    # gemini_api_key kerak (config/api_keys.json.example'ga qarang).
    if _SMART_AVAILABLE:
        run_case("SMART auto (o'zbekcha so'rov -> inglizcha qidiruv -> o'zbekcha javob)",
                  wiki_lookup, {"query": "amir temur", "source": "wikipedia"})
        run_case("SMART uz (imlo xato bilan)",
                  wiki_lookup, {"query": "ozbekistn aholisi qancha", "source": "wikidata",
                                "mode": "property", "prop": "aholisi", "lang_hint": "uz"})
        run_case("SMART auto (inglizcha so'rov)",
                  wiki_lookup, {"query": "black holes", "source": "wikipedia", "mode": "summary"})
    else:
        print("=" * 70)
        print(f"[SMART testlar o'tkazib yuborildi] Sabab: {_SMART_IMPORT_ERROR}")
        print("config/api_keys.json faylini yarating (namuna: config/api_keys.json.example)")
        print()

    # ── Interaktiv rejim ──────────────────────────────────────────────────
    print("=" * 70)
    print("Interaktiv rejim. Chiqish uchun bo'sh Enter bosing.")
    while True:
        q = input("\nMavzu kiriting: ").strip()
        if not q:
            break
        source = input("Manba (wiki/wikidata) [wiki]: ").strip().lower() or "wiki"
        lang = input("Til kodi (uz/en/ru...) [uz]: ").strip() or "uz"

        if source == "wikidata":
            action = input("Action (search/facts/property) [facts]: ").strip() or "facts"
            params = {"action": action, "query": q, "lang": lang}
            if action == "property":
                params["prop"] = input("Xususiyat nomi (masalan tug'ilgan_sana, aholisi): ").strip()
            print()
            print(wikidata_action(params))
        else:
            action = input("Action (search/summary/full/random/sections) [summary]: ").strip() or "summary"
            print()
            print(wikipedia_action({"action": action, "query": q, "lang": lang}))


if __name__ == "__main__":
    main()
