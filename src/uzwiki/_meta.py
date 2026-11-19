"""Paket versiyasi va Wikimedia uchun User-Agent sozlamasi."""

from __future__ import annotations

import os

__version__ = "0.1.0"

PROJECT_URL = "https://github.com/Abror5555/wiki"

# Wikimedia siyosati: har bir so'rovda ilova nomi va aloqa manzili (repo yoki
# email) bo'lgan User-Agent yuborilishi kerak. O'z ilovangiz uchun
# UZWIKI_USER_AGENT muhit o'zgaruvchisi yoki uzwiki.set_user_agent() bilan
# o'zgartiring, masalan: "MyBot/1.0 (https://github.com/me/mybot; me@example.com)".
DEFAULT_USER_AGENT = f"uzwiki/{__version__} ({PROJECT_URL})"


def initial_user_agent() -> str:
    return os.getenv("UZWIKI_USER_AGENT", "").strip() or DEFAULT_USER_AGENT
