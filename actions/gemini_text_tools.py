"""
actions/gemini_text_tools.py
──────────────────────────────
Wikipedia/Wikidata natijalarini tarjima qilish va foydalanuvchi so'rovini
tozalash uchun yordamchi qatlam — Gemini matn modelidan foydalanadi.

MUHIM: bu Avelia'ning ovozli (Live) Gemini sessiyasidan MUSTAQIL — bu yerda
oddiy, bir martalik (non-streaming) `generate_content` chaqiruvlari
ishlatiladi. Ovozli session band bo'lsa ham, bu alohida ishlayveradi.

Uch vazifa:
    translate_to_english(text)  -> so'rovni (istalgan tildan) ingliz tiliga tarjima qiladi
    fix_uzbek_spelling(text)    -> o'zbekcha so'rovdagi imlo xatolarini tuzatadi
    ensure_uzbek(text)          -> tilni aniqlaydi, kerak bo'lsa o'zbekchaga tarjima qiladi
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from google import genai
from google.genai import types

# ── API kalitini yuklash ────────────────────────────────────────────────────
# Avelia'ning o'zidagi bilan bir xil joydan o'qiydi: config/api_keys.json
# Bu modul Avelia'ning actions/ papkasiga ko'chirilgach, BASE_DIR avtomatik
# to'g'ri aniqlanadi (loyihaning ildiz papkasi).

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # actions/gemini_text_tools.py -> ota papka (loyiha ildizi)
    return Path(__file__).resolve().parent.parent


def _get_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


# Tezkor, faqat-matn vazifalar uchun model (ovozli LIVE_MODEL'dan farqli).
# O'zingizdagi google-genai SDK versiyasida mavjud bo'lgan model nomiga
# moslab, kerak bo'lsa shu qatorni o'zgartiring (masalan main.py'dagi
# LIVE_MODEL bilan bir oilaga tegishli, lekin "flash" / matnli variant).
TEXT_MODEL = "models/gemini-2.5-flash"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=_get_api_key(), http_options={"api_version": "v1beta"})
    return _client


def _generate(prompt: str, temperature: float = 0.1, max_output_tokens: int = 512) -> str | None:
    """
    Gemini'ga bitta oddiy matn so'rovi yuboradi va toza javobni qaytaradi.
    Xato yuz bersa None qaytaradi — chaqiruvchi funksiyalar bunda asl matnni
    ishlatib qoladi (tarjima ishlamasa ham, dastur to'xtab qolmasligi uchun).
    """
    try:
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
        print(f"[gemini_text_tools] ⚠️ Gemini chaqiruvi muvaffaqiyatsiz: {e}")
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