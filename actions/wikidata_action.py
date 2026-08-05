"""
actions/wikidata_action.py
────────────────────────────
Wikidata integratsiyasi — strukturaviy (fact-based) ma'lumotlar uchun.

Wikipedia matn/hikoya beradi, Wikidata esa aniq FAKTLARNI beradi:
tug'ilgan sana, aholi soni, koordinata, poytaxt va h.k. — har biri alohida
"xususiyat" (property, P-kod) sifatida saqlangan.

Ishlatiladigan endpoint: https://www.wikidata.org/w/api.php  (MediaWiki Action API,
xuddi Wikipedia'dagi kabi — faqat "wb" prefiksli action'lar bilan)

    wbsearchentities -> nom bo'yicha element (Q-ID) topish
    wbgetentities    -> element haqida to'liq ma'lumot (label, description, claims)

Qo'llab-quvvatlanadigan action'lar:
    search   -> nomga mos elementlarni topish (Q-ID + qisqa tavsif)
    facts    -> eng muhim faktlarni o'qiladigan ko'rinishda qaytaradi
    property -> bitta aniq xususiyatni so'rash ("tug'ilgan_sana", "aholisi" va h.k.)

Til: label/description so'ralgan tilda (lang) qidiriladi, topilmasa
avtomatik inglizchaga (en) tushadi — MediaWiki'ning languagefallback
mexanizmi orqali.
"""

from __future__ import annotations

import time
import re
import requests

# ── Sozlamalar ─────────────────────────────────────────────────────────────

DEFAULT_LANG = "uz"
FALLBACK_LANG = "en"

# MUHIM: shablon holida qoldirmang — o'zingizning haqiqiy GitHub repo
# linkingiz yoki email'ingizni yozing (Wikimedia buni talab qiladi va
# umumiy/generic User-Agent'larni qattiqroq cheklaydi).
USER_AGENT = "AveliaAssistant/1.0 (https://github.com/your-repo; contact@example.com)"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

_API_URL = "https://www.wikidata.org/w/api.php"
_REQUEST_TIMEOUT = 8
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

# Inson o'qiydigan nom -> Wikidata property kodi.
# "property" action'ida shu lug'atdan foydalaniladi, xohlasa xom P-kod ham beriladi.
PROPERTY_MAP = {
    "tug'ilgan_sana":  "P569",
    "tugilgan_sana":   "P569",
    "vafot_sana":      "P570",
    "tug'ilgan_joy":   "P19",
    "tugilgan_joy":    "P19",
    "vafot_joy":       "P20",
    "fuqaroligi":      "P27",
    "millati":         "P172",
    "kasbi":           "P106",
    "jinsi":           "P21",
    "poytaxti":        "P36",
    "aholisi":         "P1082",
    "maydoni":         "P2046",
    "koordinata":      "P625",
    "rasmiy_til":      "P37",
    "valyuta":         "P38",
    "qitasi":          "P30",
    "davlati":         "P17",
    "tashkil_topgan":  "P571",
    "sanoat":          "P452",
    "veb_sayt":        "P856",
}

# "facts" action'i uchun ustuvorlik tartibida ko'rib chiqiladigan xususiyatlar
_PRIORITY_PROPS = [
    "P31", "P569", "P570", "P19", "P20", "P27", "P106", "P21",
    "P36", "P1082", "P2046", "P625", "P37", "P38", "P17", "P571",
]

_MAX_FACTS = 10


def _get(params: dict) -> dict:
    params = {**params, "format": "json"}

    for attempt in range(_MAX_RETRIES):
        _throttle()
        resp = _session.get(_API_URL, params=params, timeout=_REQUEST_TIMEOUT)

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if (retry_after and retry_after.isdigit()) else (2 ** attempt)
            wait = min(wait, 20)
            time.sleep(wait)
            continue

        resp.raise_for_status()
        return resp.json()

    resp.raise_for_status()


# ── Ichki yordamchi funksiyalar ─────────────────────────────────────────────

def _search_entity(query: str, lang: str, entity_type: str = "item") -> list[dict]:
    data = _get({
        "action": "wbsearchentities",
        "search": query,
        "language": lang,
        "uselang": lang,
        "type": entity_type,
        "limit": 5,
    })
    return data.get("search", [])


def _normalize_for_match(text: str) -> str:
    """
    Taqqoslash uchun matnni soddalashtiradi: turli apostrof variantlarini
    (', ʻ, ʼ, ‘, ’) bitta shaklga keltiradi va kichik harflarga o'tkazadi.
    Bu, masalan, "Oʻzbekiston" (imlo tuzatilgan, ʻ belgisi bilan) va
    Wikidata'dagi "Oʻzbekiston" yozuvi turli apostrof belgilar tufayli
    "mos kelmadi" deb hisoblanib qolishining oldini oladi.
    """
    text = text.lower().strip()
    for ch in ("'", "ʻ", "ʼ", "‘", "’", "`"):
        text = text.replace(ch, "")
    return re.sub(r"\s+", " ", text)


def _resolve_entity_id(query: str, lang: str) -> tuple[str | None, str]:
    """
    Element ID'sini topadi. Agar qidiruv natijalari orasida so'ralgan nomga
    ANIQ mos keladigan element bo'lsa — o'shani tanlaydi (apostrof/registr
    farqlariga qaramay). Aks holda Wikidata'ning birinchi (eng yaqin) natijasi
    olinadi. Bu, masalan, "Oʻzbekiston" so'ralganda tasodifan "Oʻzbeklar"
    (boshqa, aloqasi yo'q element) tanlanib qolishining oldini oladi.
    Kerak bo'lsa FALLBACK_LANG bilan qayta qidiradi.
    """
    hits = _search_entity(query, lang)
    used_lang = lang
    if not hits and lang != FALLBACK_LANG:
        used_lang = FALLBACK_LANG
        hits = _search_entity(query, FALLBACK_LANG)
    if not hits:
        return None, used_lang

    target = _normalize_for_match(query)
    for h in hits:
        if _normalize_for_match(h.get("label", "")) == target:
            return h["id"], used_lang

    return hits[0]["id"], used_lang


def _get_entity(entity_id: str, lang: str) -> dict:
    data = _get({
        "action": "wbgetentities",
        "ids": entity_id,
        "props": "labels|descriptions|claims",
        "languages": f"{lang}|{FALLBACK_LANG}",
        "languagefallback": 1,
    })
    return data.get("entities", {}).get(entity_id, {})


def _label_of(entity: dict, lang: str) -> str:
    labels = entity.get("labels", {})
    return (labels.get(lang) or labels.get(FALLBACK_LANG) or {}).get("value", entity.get("id", "?"))


def _description_of(entity: dict, lang: str) -> str:
    desc = entity.get("descriptions", {})
    return (desc.get(lang) or desc.get(FALLBACK_LANG) or {}).get("value", "")


def _labels_for_ids(ids: list[str], lang: str) -> dict[str, str]:
    """Bir nechta Q-ID uchun label'larni bitta so'rovda oladi (API limiti — 50 tagacha)."""
    ids = list(dict.fromkeys(ids))[:50]  # dublikatlarsiz, 50 tagacha
    if not ids:
        return {}
    data = _get({
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "labels",
        "languages": f"{lang}|{FALLBACK_LANG}",
        "languagefallback": 1,
    })
    result = {}
    for qid, ent in data.get("entities", {}).items():
        result[qid] = _label_of(ent, lang)
    return result


def _format_wikidata_time(val: dict) -> str:
    """
    Wikidata sanani "precision" (aniqlik darajasi) bilan birga saqlaydi:
    9=yil, 10=oy, 11=kun, 8=o'n yillik, 7=asr va h.k.
    Buni hisobga olmasak, faqat yil aniqligidagi sanalar "1991-00-00"
    kabi noto'g'ri ko'rinishda chiqadi.
    """
    raw = val.get("time", "").lstrip("+")   # masalan "+1336-04-08T00:00:00Z"
    date_part = raw.split("T")[0]
    year, month, day = (date_part.split("-") + ["00", "00"])[:3]
    precision = val.get("precision", 11)

    if precision >= 11 and month != "00" and day != "00":
        return f"{year}-{month}-{day}"
    if precision == 10 and month != "00":
        return f"{year}-{month}"
    if precision == 9:
        return year
    if precision == 8:
        return f"{year[:-1]}0-yillar"
    if precision == 7:
        century = int(year) // 100 + 1
        return f"{century}-asr"
    return year


def _extract_snak_value(snak: dict) -> tuple[str, str | None]:
    """
    Bitta claim'ning asosiy qiymatini ajratib oladi.
    Returns: (kind, qiymat) — kind: "entity" | "time" | "quantity" | "coordinate" | "text" | None
    """
    if snak.get("snaktype") != "value":
        return "unknown", None

    dv = snak.get("datavalue", {})
    vtype = dv.get("type")
    val = dv.get("value")

    if vtype == "wikibase-entityid":
        return "entity", val.get("id")
    if vtype == "time":
        return "time", _format_wikidata_time(val)
    if vtype == "quantity":
        amount = val.get("amount", "").lstrip("+")
        return "quantity", amount
    if vtype == "globecoordinate":
        return "coordinate", f"{val.get('latitude')}, {val.get('longitude')}"
    if vtype in ("string", "monolingualtext"):
        text = val if isinstance(val, str) else val.get("text", "")
        return "text", text
    return "unknown", None


def _collect_claims(entity: dict, prop_ids: list[str], lang: str) -> list[tuple[str, str]]:
    """
    Berilgan property ID'lar ro'yxati bo'yicha (property_label, qiymat) juftliklarini yig'adi.
    Entity-turdagi qiymatlar uchun label'larni ham hal qiladi.
    """
    claims = entity.get("claims", {})
    raw_rows = []       # (prop_id, kind, raw_value)
    entity_ids_needed = []

    for pid in prop_ids:
        if pid not in claims:
            continue
        snak = claims[pid][0].get("mainsnak", {})
        kind, value = _extract_snak_value(snak)
        if value is None:
            continue
        raw_rows.append((pid, kind, value))
        if kind == "entity":
            entity_ids_needed.append(value)

    # Property'larning o'zi label'ini olish (masalan P569 -> "birth date")
    prop_labels = _labels_for_ids([pid for pid, _, _ in raw_rows], lang)
    # Entity turidagi qiymatlarning label'ini olish (masalan Q159 -> "Russia")
    value_labels = _labels_for_ids(entity_ids_needed, lang)

    rows = []
    for pid, kind, value in raw_rows:
        prop_name = prop_labels.get(pid, pid)
        if kind == "entity":
            shown = value_labels.get(value, value)
        else:
            shown = value
        rows.append((prop_name, shown))
    return rows


# ── Asosiy action funksiyalari ──────────────────────────────────────────────

def _do_search(query: str, lang: str) -> str:
    hits = _search_entity(query, lang)
    used_lang = lang
    if not hits and lang != FALLBACK_LANG:
        used_lang = FALLBACK_LANG
        hits = _search_entity(query, FALLBACK_LANG)
    if not hits:
        return f'"{query}" bo\'yicha Wikidata\'da hech narsa topilmadi.'

    lines = []
    for h in hits:
        label = h.get("label", h.get("id"))
        desc = h.get("description", "")
        lines.append(f"{label} ({h['id']}){' — ' + desc if desc else ''}")
    note = f" (inglizcha nomlar bilan, {used_lang})" if used_lang != lang else ""
    return f"Topilgan elementlar{note}:\n" + "\n".join(lines)


def _do_facts(query: str, lang: str) -> str:
    entity_id, used_lang = _resolve_entity_id(query, lang)
    if not entity_id:
        return f'"{query}" nomli element Wikidata\'da topilmadi.'

    entity = _get_entity(entity_id, lang)
    if not entity:
        return f'"{query}" elementi ma\'lumotlarini olib bo\'lmadi.'

    label = _label_of(entity, lang)
    desc = _description_of(entity, lang)

    claims = entity.get("claims", {})
    all_claim_ids = list(claims.keys())

    # Tashqi identifikatorlarni (VIAF, LCCN, ISNI va h.k.) "facts" ro'yxatidan
    # chiqarib tashlaymiz — bular inson uchun o'qiladigan fakt emas, texnik
    # ID'lar, va bo'sh joylarni band qilib, foydali maydonlarni siqib chiqaradi.
    def _is_external_id(pid: str) -> bool:
        snak = claims[pid][0].get("mainsnak", {})
        return snak.get("datatype") == "external-id"

    ordered = [p for p in _PRIORITY_PROPS if p in all_claim_ids]
    for p in all_claim_ids:
        if p not in ordered and not _is_external_id(p):
            ordered.append(p)
    ordered = ordered[:_MAX_FACTS]

    rows = _collect_claims(entity, ordered, lang)

    header = f"{label}" + (f" — {desc}" if desc else "")
    note = f" (ma'lumotlar inglizcha, {used_lang})" if used_lang != lang else ""
    if not rows:
        return f"{header}{note}\nQo'shimcha strukturaviy faktlar topilmadi."

    body = "\n".join(f"- {name}: {value}" for name, value in rows)
    return f"{header}{note}\n{body}"


def _do_property(query: str, lang: str, prop: str) -> str:
    prop_key = prop.strip().lower().replace(" ", "_")
    pid = PROPERTY_MAP.get(prop_key, prop.strip().upper() if prop.strip().upper().startswith("P") else None)
    if not pid:
        available = ", ".join(sorted(PROPERTY_MAP.keys()))
        return f'"{prop}" xususiyati tanilmadi. Mavjud nomlar: {available} (yoki to\'g\'ridan-to\'g\'ri P-kod, masalan "P569")'

    entity_id, used_lang = _resolve_entity_id(query, lang)
    if not entity_id:
        return f'"{query}" nomli element Wikidata\'da topilmadi.'

    entity = _get_entity(entity_id, lang)
    label = _label_of(entity, lang)

    rows = _collect_claims(entity, [pid], lang)
    note = f" (ma'lumot inglizcha, {used_lang})" if used_lang != lang else ""
    if not rows:
        return f"{label} uchun bu xususiyat (({pid})) topilmadi.{note}"

    prop_name, value = rows[0]
    return f"{label} — {prop_name}: {value}{note}"


# ── Tashqi interfeys (Avelia'dagi boshqa actions/*.py bilan bir xil) ───────

def wikidata_action(parameters: dict, player=None) -> str:
    """
    parameters:
        action : "search" | "facts" | "property"   (default: "facts")
        query  : element nomi (masalan "Amir Temur", "O'zbekiston")
        lang   : til kodi, masalan "uz", "en", "ru"  (default: "uz")
        prop   : "property" action'i uchun — xususiyat nomi
                 (masalan "tug'ilgan_sana", "aholisi") yoki xom P-kod ("P569")
    """
    action = (parameters.get("action") or "facts").strip().lower()
    query  = (parameters.get("query") or "").strip()
    lang   = (parameters.get("lang") or DEFAULT_LANG).strip().lower()
    prop   = (parameters.get("prop") or "").strip()

    if not query:
        return "Wikidata'dan nima haqida ma'lumot kerakligini aytmadingiz."

    try:
        if action == "search":
            return _do_search(query, lang)
        elif action == "facts":
            return _do_facts(query, lang)
        elif action == "property":
            if not prop:
                return "Qaysi xususiyat (prop) so'ralayotganini bermadingiz."
            return _do_property(query, lang, prop)
        else:
            return f"Noma'lum action: {action}"
    except requests.exceptions.Timeout:
        return "Wikidata javob berishda kechikdi (timeout). Internetni tekshiring."
    except requests.exceptions.HTTPError as e:
        if getattr(e.response, "status_code", None) == 429:
            return "Wikidata so'rovlar sonini vaqtincha cheklab qo'ydi (429). Bir necha soniyadan so'ng qayta urinib ko'ring."
        return f"Wikidata'ga ulanishda xatolik: {e}"
    except requests.exceptions.RequestException as e:
        return f"Wikidata'ga ulanishda xatolik: {e}"
    except Exception as e:
        return f"wikidata_action xatosi: {e}"


# Nomlash konvensiyasi uchun alias
wikidata = wikidata_action