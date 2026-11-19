"""
uzwiki.wikipedia
────────────────
Wikipedia integratsiyasi — MediaWiki Action API orqali (api.php).

Wikipedia API to'liq BEPUL va API kalit talab qilmaydi, lekin Wikimedia
foydalanish shartlariga ko'ra HAR BIR so'rovda tanib bo'ladigan User-Agent
yuborish shart (aks holda IP vaqtincha bloklanishi mumkin).

Qo'llab-quvvatlanadigan action'lar:
    search   -> sahifalarni qidirish (nomlar ro'yxati)
    summary  -> sahifaning qisqacha mazmuni (intro paragraf)
    full     -> sahifaning to'liq (oddiy matn) tarkibi
    random   -> tasodifiy sahifa
    sections -> sahifadagi bo'limlar ro'yxati

Bir nechta tilni qo'llab-quvvatlaydi (lang parametri, masalan: "uz", "en", "ru").
Agar so'ralgan tilda maqola topilmasa, avtomatik inglizcha (en) ga fallback qiladi.
"""

from __future__ import annotations

import time
import requests

from uzwiki._meta import initial_user_agent

# ── Sozlamalar ─────────────────────────────────────────────────────────────

DEFAULT_LANG = "uz"
FALLBACK_LANG = "en"

# Wikimedia siyosati: User-Agent'da ilova nomi + aloqa (email yoki repo link) bo'lishi kerak.
# Umumiy/generic User-Agent'lar qattiqroq cheklanadi (429 xatosi ko'proq chiqadi).
# O'zgartirish: UZWIKI_USER_AGENT muhit o'zgaruvchisi yoki uzwiki.set_user_agent().
USER_AGENT = initial_user_agent()

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

_REQUEST_TIMEOUT = 8      # soniya
_MAX_RETRIES = 4          # 429/5xx xatolarida qayta urinishlar soni
_MIN_INTERVAL = 0.4       # ketma-ket so'rovlar orasidagi minimal tanaffus (soniya)

_last_request_at = {"t": 0.0}


def _throttle() -> None:
    """So'rovlar orasida minimal tanaffus qo'yadi — Wikimedia'ni "bot" deb
    hisoblab tezroq cheklab qo'yishining oldini oladi."""
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _last_request_at["t"])
    if wait > 0:
        time.sleep(wait)
    _last_request_at["t"] = time.monotonic()


def _api_url(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def _get(lang: str, params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = _api_url(lang)

    for attempt in range(_MAX_RETRIES):
        _throttle()
        resp = _session.get(url, params=params, timeout=_REQUEST_TIMEOUT)

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if (retry_after and retry_after.isdigit()) else (2 ** attempt)
            wait = min(wait, 20)  # 20 soniyadan ortiq kutib o'tirmaymiz
            time.sleep(wait)
            continue

        resp.raise_for_status()
        return resp.json()

    resp.raise_for_status()  # barcha urinishlar tugagach ham 429 bo'lsa — xatoni chiqaramiz


# ── Ichki yordamchi funksiyalar ─────────────────────────────────────────────

def _search_titles(query: str, lang: str, limit: int = 5) -> list[str]:
    data = _get(lang, {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
    })
    return [r["title"] for r in data.get("query", {}).get("search", [])]


def _get_extract(title: str, lang: str, intro_only: bool, chars_limit: int | None = None) -> tuple[str | None, str]:
    """
    Sahifa extract'ini (oddiy matn) qaytaradi.
    Returns: (resolved_title yoki None agar topilmasa, matn)
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "redirects": 1,
        "titles": title,
    }
    if intro_only:
        params["exintro"] = 1
    if chars_limit:
        params["exchars"] = chars_limit

    data = _get(lang, params)
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None, ""

    page = pages[0]
    return page.get("title", title), (page.get("extract") or "").strip()


def _resolve_with_fallback(title: str, lang: str, intro_only: bool, chars_limit: int | None = None):
    """
    Sarlavhani quyidagi tartibda hal qiladi (aniqdan noaniqqa):
      1) so'ralgan tilda ANIQ sarlavha
      2) FALLBACK_LANG (en) da ANIQ sarlavha — foydalanuvchi ingliz nomini
         yozgan bo'lishi mumkin, bu fuzzy qidiruvdan ko'ra ishonchliroq
      3) so'ralgan tilda FUZZY (to'liq-matn) qidiruv
      4) FALLBACK_LANG da FUZZY qidiruv
    Fuzzy qidiruv oxiriga surilgan — chunki u har doim "nimadir" topadi,
    hatto unchalik mos bo'lmasa ham, va noto'g'ri mavzuga olib ketishi mumkin.
    """
    resolved, text = _get_extract(title, lang, intro_only, chars_limit)
    used_lang = lang

    if not text and lang != FALLBACK_LANG:
        resolved, text = _get_extract(title, FALLBACK_LANG, intro_only, chars_limit)
        if text:
            used_lang = FALLBACK_LANG

    if not text:
        hits = _search_titles(title, lang, limit=1)
        if hits:
            resolved, text = _get_extract(hits[0], lang, intro_only, chars_limit)
            used_lang = lang

    if not text and lang != FALLBACK_LANG:
        hits = _search_titles(title, FALLBACK_LANG, limit=1)
        if hits:
            resolved, text = _get_extract(hits[0], FALLBACK_LANG, intro_only, chars_limit)
            used_lang = FALLBACK_LANG

    return resolved, text, used_lang


# ── Asosiy action funksiyalari ──────────────────────────────────────────────

def _do_search(query: str, lang: str) -> str:
    titles = _search_titles(query, lang, limit=5)
    if not titles:
        if lang != FALLBACK_LANG:
            titles = _search_titles(query, FALLBACK_LANG, limit=5)
        if not titles:
            return f'"{query}" bo\'yicha Wikipedia\'da hech narsa topilmadi.'
    return "Topilgan maqolalar: " + "; ".join(titles)


def _do_summary(query: str, lang: str) -> str:
    resolved, text, used_lang = _resolve_with_fallback(query, lang, intro_only=True)
    if not text:
        return f'"{query}" nomli maqola Wikipedia\'da topilmadi.'
    note = f" (ingliz tilidagi Wikipedia'dan, {used_lang})" if used_lang != lang else ""
    return f"{resolved}{note}:\n{text}"


def _trim_to_sentence(text: str) -> str:
    """Chegara tufayli jumla o'rtasida kesilgan matnni oxirgi to'liq jumlagacha qisqartiradi."""
    for stop in (". ", ".\n", "! ", "? "):
        idx = text.rfind(stop)
        if idx != -1 and idx > len(text) * 0.5:  # matnning yarmidan kamiga tushib qolmasin
            return text[: idx + 1]
    return text


def _do_full(query: str, lang: str, chars_limit: int = 4000) -> str:
    resolved, text, used_lang = _resolve_with_fallback(query, lang, intro_only=False, chars_limit=chars_limit)
    if not text:
        return f'"{query}" nomli maqola Wikipedia\'da topilmadi.'

    text = text.rstrip()
    # Wikipedia'ning o'zi ham exchars chegarasida ba'zan matnni xom "..." bilan
    # kesib qo'yadi (bu bizning chars_limit hisobimizga to'liq mos kelmasligi
    # mumkin) — shuning uchun uzunlikdan tashqari, shu belgini ham tekshiramiz.
    was_cut = text.endswith("...") or len(text) >= chars_limit - 50
    if was_cut:
        if text.endswith("..."):
            text = text[:-3].rstrip()
        text = _trim_to_sentence(text)
        text += "\n\n[...maqola davom etadi, bu faqat qisqartirilgan qism]"

    note = f" (ingliz tilidagi Wikipedia'dan, {used_lang})" if used_lang != lang else ""
    return f"{resolved}{note}:\n{text}"


def _do_random(lang: str) -> str:
    """
    Tasodifiy sahifani oladi. Agar u disambiguatsiya (ko'p ma'noli nom)
    yoki mazmunsiz qisqa "stub" sahifa bo'lib chiqsa (masalan "X may refer to:"),
    bir necha marta qayta urinadi — foydalanuvchiga mazmunli javob berish uchun.
    """
    last_title = None
    last_text = ""

    for _ in range(3):
        data = _get(lang, {
            "action": "query",
            "list": "random",
            "rnnamespace": 0,
            "rnlimit": 1,
        })
        items = data.get("query", {}).get("random", [])
        if not items:
            break
        title = items[0]["title"]
        _, text = _get_extract(title, lang, intro_only=True)
        last_title, last_text = title, text

        looks_like_disambig = "may refer to" in text.lower() or "ko'p ma'noli" in text.lower()
        if text and len(text) >= 60 and not looks_like_disambig:
            return f"{title}:\n{text}"

    if last_title:
        return f"{last_title}:\n{last_text}" if last_text else last_title
    return "Tasodifiy sahifa olishning iloji bo'lmadi."


def _do_sections(query: str, lang: str) -> str:
    resolved, _, used_lang = _resolve_with_fallback(query, lang, intro_only=True)
    if not resolved:
        return f'"{query}" nomli maqola Wikipedia\'da topilmadi.'

    data = _get(used_lang, {
        "action": "parse",
        "page": resolved,
        "prop": "sections",
    })
    sections = data.get("parse", {}).get("sections", [])
    if not sections:
        return f"{resolved} maqolasida alohida bo'limlar topilmadi."
    lines = [s["line"] for s in sections]
    return f"{resolved} bo'limlari: " + "; ".join(lines)


# ── Tashqi interfeys ────────────────────────────────────────────────────────
# (parameters, player=None) imzosi ovozli yordamchilarning tool/action
# chaqiruvlariga mos (masalan Avelia'dagi actions/*.py fayllar bilan bir xil).

def wikipedia_action(parameters: dict, player=None) -> str:
    """
    parameters:
        action : "search" | "summary" | "full" | "random" | "sections"  (default: "summary")
        query  : qidiriladigan/o'qiladigan maqola nomi yoki mavzu
        lang   : til kodi, masalan "uz", "en", "ru"  (default: "uz")
    """
    action = (parameters.get("action") or "summary").strip().lower()
    query  = (parameters.get("query") or "").strip()
    lang   = (parameters.get("lang") or DEFAULT_LANG).strip().lower()

    if action != "random" and not query:
        return "Wikipedia'dan nima qidirishni aytmadingiz."

    try:
        if action == "search":
            return _do_search(query, lang)
        elif action == "summary":
            return _do_summary(query, lang)
        elif action == "full":
            return _do_full(query, lang)
        elif action == "random":
            return _do_random(lang)
        elif action == "sections":
            return _do_sections(query, lang)
        else:
            return f"Noma'lum action: {action}"
    except requests.exceptions.Timeout:
        return "Wikipedia javob berishda kechikdi (timeout). Internetni tekshiring."
    except requests.exceptions.HTTPError as e:
        if getattr(e.response, "status_code", None) == 429:
            return "Wikipedia so'rovlar sonini vaqtincha cheklab qo'ydi (429). Bir necha soniyadan so'ng qayta urinib ko'ring."
        return f"Wikipedia'ga ulanishda xatolik: {e}"
    except requests.exceptions.RequestException as e:
        return f"Wikipedia'ga ulanishda xatolik: {e}"
    except Exception as e:
        return f"wikipedia_action xatosi: {e}"


# Qisqa nom (alias)
wikipedia = wikipedia_action
