"""
uzwiki.gemini_tools
───────────────────
Wikipedia/Wikidata natijalarini tarjima qilish va foydalanuvchi so'rovini
tozalash uchun yordamchi qatlam — Gemini matn modelidan foydalanadi.

Bu qatlam ixtiyoriy: `pip install "uzwiki[gemini]"` bilan o'rnatiladi.
google-genai o'rnatilmagan yoki API kalit topilmasa, funksiyalar xato
bermaydi — shunchaki asl (tarjima qilinmagan) matnni qaytaradi.

Oddiy, bir martalik (non-streaming) `generate_content` chaqiruvlari
ishlatiladi, shuning uchun ovozli (Live) Gemini sessiyasi band bo'lsa ham
alohida ishlayveradi.

Uch vazifa:
    translate_to_english(text)  -> so'rovni (istalgan tildan) ingliz tiliga tarjima qiladi
    fix_uzbek_spelling(text)    -> o'zbekcha so'rovdagi imlo xatolarini tuzatadi
    ensure_uzbek(text)          -> tilni aniqlaydi, kerak bo'lsa o'zbekchaga tarjima qiladi
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ── API kalitini yuklash ────────────────────────────────────────────────────
# Kalit quyidagi tartibda qidiriladi:
#   1) set_api_key("...") bilan berilgan kalit
#   2) GEMINI_API_KEY muhit o'zgaruvchisi
#   3) joriy papkadagi config/api_keys.json  ({"gemini_api_key": "..."})
#   4) (PyInstaller exe uchun) exe yonidagi config/api_keys.json

_api_key: str | None = None


def set_api_key(key: str) -> None:
    """Gemini API kalitini dastur ichidan beradi."""
    global _api_key, _client
    _api_key = (key or "").strip() or None
    _client = None  # keyingi chaqiruvda yangi kalit bilan klient yaratiladi


def _config_paths() -> list[Path]:
    paths = [Path.cwd() / "config" / "api_keys.json"]
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).parent / "config" / "api_keys.json")
    return paths


def _get_api_key() -> str:
    if _api_key:
        return _api_key
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    for path in _config_paths():
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                key = (json.load(f).get("gemini_api_key") or "").strip()
            if key:
                return key
    raise RuntimeError(
        "Gemini API kaliti topilmadi: GEMINI_API_KEY muhit o'zgaruvchisini o'rnating, "
        "uzwiki.set_api_key() ni chaqiring yoki config/api_keys.json yarating."
    )


# Tezkor, faqat-matn vazifalar uchun model. Kerak bo'lsa dastur ichidan
# o'zgartiring: uzwiki.gemini_tools.TEXT_MODEL = "models/..."
TEXT_MODEL = "models/gemini-2.5-flash"

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai  # ixtiyoriy bog'liqlik: pip install "uzwiki[gemini]"

        _client = genai.Client(api_key=_get_api_key(), http_options={"api_version": "v1beta"})
    return _client


def _generate(prompt: str, temperature: float = 0.1, max_output_tokens: int = 512) -> str | None:
    """
    Gemini'ga bitta oddiy matn so'rovi yuboradi va toza javobni qaytaradi.
    Xato yuz bersa None qaytaradi — chaqiruvchi funksiyalar bunda asl matnni
    ishlatib qoladi (tarjima ishlamasa ham, dastur to'xtab qolmasligi uchun).
    """
    try:
        from google.genai import types

        client = _get_client()
        resp = client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:
        logger.warning("Gemini chaqiruvi muvaffaqiyatsiz, asl matn qaytariladi: %s", e)
        return None


# ── Tashqi funksiyalar ──────────────────────────────────────────────────────

def translate_to_english(text: str) -> str:
    """
    Foydalanuvchi so'rovidan (bu to'liq savol bo'lishi mumkin, masalan
    "O'zbekiston aholisi qancha?") ASOSIY MAVZU/NOMNI ajratib oladi va uni
    ingliz tiliga tarjima qiladi — Wikipedia/Wikidata qidiruvi entity nomi
    bilan ishlaganda eng aniq natija berishi uchun.
    """
    text = text.strip()
    if not text:
        return text
    prompt = (
        "The user said this (it may be a full question or casual phrase). "
        "Extract the CORE topic/entity/subject only (a short name or noun "
        "phrase, NOT a full sentence or question), and translate it into "
        "English.\n"
        "Examples:\n"
        '  "ozbekistn aholisi qancha" -> "Uzbekistan"\n'
        '  "amir temur kim edi" -> "Amir Temur"\n'
        '  "gapirib ber python haqida" -> "Python programming language"\n'
        "Output ONLY the resulting short topic/name — no quotes, no explanation, "
        "no full sentence.\n\n"
        f"User said: {text}"
    )
    result = _generate(prompt, temperature=0.1, max_output_tokens=64)
    return result if result else text


def fix_uzbek_spelling(text: str) -> str:
    """
    Foydalanuvchi so'rovidan (bu to'liq savol bo'lishi mumkin, masalan
    "ozbekistn aholisi qancha") ASOSIY MAVZU/NOMNI ajratib oladi va imlo
    xatolarini tuzatadi — Wikipedia/Wikidata qidiruvi entity nomi bilan
    ishlaganda eng aniq natija berishi uchun.
    """
    text = text.strip()
    if not text:
        return text
    prompt = (
        "Foydalanuvchi shuni aytdi (bu to'liq savol yoki erkin gap bo'lishi "
        "mumkin). Undan FAQAT asosiy mavzu/nom/predmetni ajratib ol (qisqa "
        "nom yoki so'z birikmasi, TO'LIQ GAP EMAS) va imlo xatolarini tuzat.\n"
        "Misollar:\n"
        '  "ozbekistn aholisi qancha" -> "Oʻzbekiston"\n'
        '  "amir temur kim edi" -> "Amir Temur"\n'
        '  "gapirib ber pyton dasturlash tili haqida" -> "Python dasturlash tili"\n'
        "Faqat natijaviy qisqa mavzu/nomni qaytar — izoh, tirnoq belgisi yoki "
        "to'liq gap yozma.\n\n"
        f"Foydalanuvchi aytdi: {text}"
    )
    result = _generate(prompt, temperature=0.1, max_output_tokens=128)
    return result if result else text


def ensure_uzbek(text: str) -> str:
    """
    Berilgan matn qaysi tilda ekanini aniqlaydi. Agar allaqachon oʻzbekcha
    boʻlsa — oʻzgarishsiz qaytaradi. Aks holda tabiiy, ravon oʻzbek tiliga
    tarjima qiladi (barcha fakt/sana/raqamlarni saqlab qolgan holda).
    Aniqlash + tarjima bitta chaqiruvda — ikkita alohida so'rovdan tezroq
    va arzonroq.
    """
    text = text.strip()
    if not text:
        return text
    prompt = (
        "Determine the language of the TEXT below.\n"
        "If it is already Uzbek, output the TEXT unchanged, verbatim.\n"
        "If it is in any other language, translate it into natural, fluent Uzbek, "
        "preserving all facts, names, dates, and numbers exactly.\n"
        "Output ONLY the resulting Uzbek text — no language name, no explanation, no quotes.\n\n"
        f"TEXT:\n{text}"
    )
    # Wikipedia'ning "full" javobi 4000 belgigacha bo'lishi mumkin — shuning
    # uchun bu yerda chiqish tokenlari chegarasi kattaroq.
    result = _generate(prompt, temperature=0.2, max_output_tokens=4096)
    return result if result else text