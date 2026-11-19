"""Internetsiz testlar: tarmoq so'rovlari soxta javoblar bilan almashtiriladi."""

from __future__ import annotations

import pytest

import uzwiki
from uzwiki import cli, gemini_tools, smart, wikidata, wikipedia


# ── Wikipedia ──────────────────────────────────────────────────────────────

def test_summary_found_in_requested_language(monkeypatch):
    monkeypatch.setattr(
        wikipedia, "_get_extract",
        lambda title, lang, intro_only, chars_limit=None: ("Amir Temur", "Amir Temur — davlat arbobi."),
    )
    out = wikipedia.wikipedia_action({"action": "summary", "query": "Amir Temur", "lang": "uz"})
    assert out == "Amir Temur:\nAmir Temur — davlat arbobi."


def test_summary_falls_back_to_english(monkeypatch):
    def fake_extract(title, lang, intro_only, chars_limit=None):
        return ("Quantum computing", "A quantum computer...") if lang == "en" else (None, "")

    monkeypatch.setattr(wikipedia, "_get_extract", fake_extract)
    out = wikipedia.wikipedia_action({"action": "summary", "query": "Quantum computing", "lang": "uz"})
    assert out.startswith("Quantum computing (ingliz tilidagi Wikipedia'dan, en):")


def test_missing_query_message():
    assert wikipedia.wikipedia_action({"action": "summary"}) == "Wikipedia'dan nima qidirishni aytmadingiz."
    assert "aytmadingiz" in wikidata.wikidata_action({"action": "facts"})


def test_unknown_action():
    assert wikipedia.wikipedia_action({"action": "nimadir", "query": "x"}) == "Noma'lum action: nimadir"


def test_search_lists_titles(monkeypatch):
    monkeypatch.setattr(wikipedia, "_get", lambda lang, params: {
        "query": {"search": [{"title": "Sun'iy intellekt"}, {"title": "Mashinali o'rganish"}]}
    })
    out = wikipedia.wikipedia_action({"action": "search", "query": "AI"})
    assert out == "Topilgan maqolalar: Sun'iy intellekt; Mashinali o'rganish"


def test_trim_to_sentence():
    text = "Birinchi gap. Ikkinchi gap. Uchinchi gap kesil"
    assert wikipedia._trim_to_sentence(text) == "Birinchi gap. Ikkinchi gap."


# ── Wikidata ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "value, expected",
    [
        ({"time": "+1336-04-08T00:00:00Z", "precision": 11}, "1336-04-08"),
        ({"time": "+1991-09-00T00:00:00Z", "precision": 10}, "1991-09"),
        ({"time": "+1991-00-00T00:00:00Z", "precision": 9}, "1991"),
        ({"time": "+1990-00-00T00:00:00Z", "precision": 8}, "1990-yillar"),
        ({"time": "+1336-00-00T00:00:00Z", "precision": 7}, "14-asr"),
        ({"time": "+1500-00-00T00:00:00Z", "precision": 7}, "15-asr"),
    ],
)
def test_format_wikidata_time(value, expected):
    assert wikidata._format_wikidata_time(value) == expected


def test_normalize_ignores_apostrophe_variants():
    assert wikidata._normalize_for_match("Oʻzbekiston") == wikidata._normalize_for_match("O'zbekiston")


def test_property_unknown_name():
    out = wikidata.wikidata_action({"action": "property", "query": "Toshkent", "prop": "nomalum"})
    assert out.startswith('"nomalum" xususiyati tanilmadi.')


def test_property_lookup(monkeypatch):
    monkeypatch.setattr(wikidata, "_resolve_entity_id", lambda q, lang: ("Q269", lang))
    monkeypatch.setattr(wikidata, "_get_entity", lambda eid, lang: {"id": eid, "labels": {"uz": {"value": "Toshkent"}}})
    monkeypatch.setattr(wikidata, "_collect_claims", lambda entity, pids, lang: [("aholisi", "3000000")])
    out = wikidata.wikidata_action({"action": "property", "query": "Toshkent", "prop": "aholisi"})
    assert out == "Toshkent — aholisi: 3000000"


# ── Gemini qatlami ─────────────────────────────────────────────────────────

def test_smart_works_without_gemini(monkeypatch):
    """Gemini ishlamasa ham wiki_lookup qulab tushmaydi va xom natijani qaytaradi."""
    monkeypatch.setattr(gemini_tools, "_generate", lambda *a, **k: None)
    monkeypatch.setattr(smart, "wikipedia_action", lambda params, player=None: f"natija: {params['query']}")
    assert smart.wiki_lookup({"query": "amir temur"}) == "natija: amir temur"


def test_api_key_priority(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    uzwiki.set_api_key("")
    with pytest.raises(RuntimeError):
        gemini_tools._get_api_key()

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "api_keys.json").write_text('{"gemini_api_key": "from-file"}', encoding="utf-8")
    assert gemini_tools._get_api_key() == "from-file"

    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert gemini_tools._get_api_key() == "from-env"

    uzwiki.set_api_key("explicit")
    assert gemini_tools._get_api_key() == "explicit"
    uzwiki.set_api_key("")


# ── Umumiy ─────────────────────────────────────────────────────────────────

def test_set_user_agent_updates_both_sessions():
    original = wikipedia.USER_AGENT
    try:
        uzwiki.set_user_agent("TestBot/1.0 (test@example.com)")
        assert wikipedia._session.headers["User-Agent"] == "TestBot/1.0 (test@example.com)"
        assert wikidata._session.headers["User-Agent"] == "TestBot/1.0 (test@example.com)"
    finally:
        uzwiki.set_user_agent(original)


def test_default_user_agent_identifies_project():
    assert wikipedia.USER_AGENT.startswith("uzwiki/")
    assert "github.com/Abror5555/wiki" in wikipedia.USER_AGENT


def test_cli_property(monkeypatch):
    captured = {}

    def fake(params):
        captured.update(params)
        return "ok"

    monkeypatch.setattr(cli, "wikidata_action", fake)
    assert cli.run(["property", "Toshkent", "aholisi"]) == "ok"
    assert captured == {"action": "property", "query": "Toshkent", "lang": "uz", "prop": "aholisi"}


def test_cli_smart_uz_flag(monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "wiki_lookup", lambda params: captured.update(params) or "ok")
    cli.run(["smart", "ozbekistn aholisi", "--source", "wikidata", "--mode", "property", "--prop", "aholisi", "--uz"])
    assert captured == {
        "query": "ozbekistn aholisi", "source": "wikidata", "lang_hint": "uz",
        "mode": "property", "prop": "aholisi",
    }
