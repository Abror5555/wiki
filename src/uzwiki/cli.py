"""
uzwiki buyruq qatori (CLI).

Misollar:
    uzwiki summary "Amir Temur"
    uzwiki search "sun'iy intellekt"
    uzwiki full "Python (dasturlash tili)"
    uzwiki sections "O'zbekiston"
    uzwiki random --lang en
    uzwiki facts "O'zbekiston"
    uzwiki property "Toshkent" aholisi
    uzwiki smart "amir temur kim edi"        # Gemini qatlami bilan
"""

from __future__ import annotations

import argparse
import sys

from uzwiki._meta import __version__
from uzwiki.smart import wiki_lookup
from uzwiki.wikidata import PROPERTY_MAP, wikidata_action
from uzwiki.wikipedia import DEFAULT_LANG, wikipedia_action

_WIKIPEDIA_ACTIONS = {
    "summary": "maqolaning qisqacha mazmuni (kirish qismi)",
    "full": "maqolaning to'liq matni (4000 belgigacha)",
    "search": "Wikipedia'da maqola nomlarini qidirish",
    "sections": "maqoladagi bo'limlar ro'yxati",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uzwiki",
        description="Wikipedia va Wikidata'dan o'zbek tilida ma'lumot olish.",
    )
    parser.add_argument("--version", action="version", version=f"uzwiki {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="BUYRUQ")
    sub.required = True

    def add_lang(p: argparse.ArgumentParser) -> None:
        p.add_argument("--lang", default=DEFAULT_LANG, help=f"til kodi: uz, en, ru... (standart: {DEFAULT_LANG})")

    for name, help_text in _WIKIPEDIA_ACTIONS.items():
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("query", help="maqola nomi yoki mavzu")
        add_lang(p)

    p = sub.add_parser("random", help="tasodifiy maqola", description="Tasodifiy Wikipedia maqolasi.")
    add_lang(p)

    p = sub.add_parser("facts", help="Wikidata: eng muhim faktlar", description="Wikidata'dan eng muhim faktlar.")
    p.add_argument("query", help="element nomi, masalan \"Amir Temur\"")
    add_lang(p)

    p = sub.add_parser("wd-search", help="Wikidata: elementlarni qidirish", description="Wikidata'da element qidirish.")
    p.add_argument("query", help="element nomi")
    add_lang(p)

    p = sub.add_parser(
        "property",
        help="Wikidata: bitta aniq xususiyat",
        description="Wikidata'dan bitta xususiyat. Tayyor nomlar: " + ", ".join(sorted(PROPERTY_MAP)),
    )
    p.add_argument("query", help="element nomi, masalan \"Toshkent\"")
    p.add_argument("prop", help="xususiyat nomi (aholisi, tug'ilgan_sana...) yoki P-kod (P569)")
    add_lang(p)

    p = sub.add_parser(
        "smart",
        help="Gemini tarjima qatlami bilan (javob doim o'zbekcha)",
        description=(
            "So'rovni Gemini orqali tayyorlab, Wikipedia/Wikidata'dan qidiradi va javobni o'zbekchaga "
            "o'giradi. GEMINI_API_KEY kerak; o'rnatish: pip install \"uzwiki[gemini]\"."
        ),
    )
    p.add_argument("query", help="erkin savol yoki mavzu")
    p.add_argument("--source", choices=["wikipedia", "wikidata"], default="wikipedia")
    p.add_argument("--mode", help="wikipedia: search|summary|full|random|sections; wikidata: search|facts|property")
    p.add_argument("--prop", help="mode=property uchun xususiyat nomi")
    p.add_argument("--uz", action="store_true", help="o'zbek tilidagi manbalardan qidirish")

    return parser


def run(argv: list[str] | None = None) -> str:
    args = _build_parser().parse_args(argv)
    cmd = args.command

    if cmd in _WIKIPEDIA_ACTIONS:
        return wikipedia_action({"action": cmd, "query": args.query, "lang": args.lang})
    if cmd == "random":
        return wikipedia_action({"action": "random", "lang": args.lang})
    if cmd == "facts":
        return wikidata_action({"action": "facts", "query": args.query, "lang": args.lang})
    if cmd == "wd-search":
        return wikidata_action({"action": "search", "query": args.query, "lang": args.lang})
    if cmd == "property":
        return wikidata_action({"action": "property", "query": args.query, "lang": args.lang, "prop": args.prop})

    params = {"query": args.query, "source": args.source, "lang_hint": "uz" if args.uz else "auto"}
    if args.mode:
        params["mode"] = args.mode
    if args.prop:
        params["prop"] = args.prop
    return wiki_lookup(params)


def main(argv: list[str] | None = None) -> int:
    # Windows konsolida o'zbekcha harflar (ʻ, ʼ) chiqarishda xato bermasligi uchun
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    print(run(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
