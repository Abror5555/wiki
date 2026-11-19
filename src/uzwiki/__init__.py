"""
uzwiki — Wikipedia va Wikidata'dan o'zbek tilida ma'lumot olish.

    from uzwiki import wikipedia_action, wikidata_action, wiki_lookup

    wikipedia_action({"action": "summary", "query": "Amir Temur", "lang": "uz"})
    wikidata_action({"action": "property", "query": "Toshkent", "prop": "aholisi"})
    wiki_lookup({"query": "amir temur kim edi"})   # Gemini qatlami bilan (ixtiyoriy)
"""

from __future__ import annotations

from uzwiki import wikidata as _wikidata
from uzwiki import wikipedia as _wikipedia
from uzwiki._meta import __version__
from uzwiki.gemini_tools import ensure_uzbek, fix_uzbek_spelling, set_api_key, translate_to_english
from uzwiki.smart import wiki_lookup
from uzwiki.wikidata import PROPERTY_MAP, wikidata_action
from uzwiki.wikipedia import wikipedia_action

# Eslatma: uzwiki.wikipedia va uzwiki.wikidata — bu modullar nomi. Funksiyalarning qisqa
# nomlari (wikipedia(), wikidata()) o'sha modullar ichida: from uzwiki.wikipedia import wikipedia


def set_user_agent(user_agent: str) -> None:
    """Wikipedia va Wikidata so'rovlari uchun User-Agent'ni o'zgartiradi.

    Wikimedia ilova nomi va aloqa manzilini so'raydi, masalan:
    "MyBot/1.0 (https://github.com/me/mybot; me@example.com)".
    """
    user_agent = (user_agent or "").strip()
    if not user_agent:
        raise ValueError("User-Agent bo'sh bo'lmasligi kerak")
    for module in (_wikipedia, _wikidata):
        module.USER_AGENT = user_agent
        module._session.headers["User-Agent"] = user_agent


__all__ = [
    "__version__",
    "PROPERTY_MAP",
    "ensure_uzbek",
    "fix_uzbek_spelling",
    "set_api_key",
    "set_user_agent",
    "translate_to_english",
    "wiki_lookup",
    "wikidata_action",
    "wikipedia_action",
]
