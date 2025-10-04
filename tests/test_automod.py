from __future__ import annotations

from bot.database.repositories import AutomodRule
from bot.services.automod import AutomodEngine


def test_link_filter_allows_whitelisted_domain():
    engine = AutomodEngine()
    rules = [AutomodRule(guild_id=1, rule_type="link_filter", payload={"allow_domains": ["example.com"]}, is_active=True)]
    violations = engine.evaluate(content="kunjungi https://example.com/page", mention_count=0, rules=rules)
    assert not violations


def test_link_filter_blocks_other_domains():
    engine = AutomodEngine()
    rules = [AutomodRule(guild_id=1, rule_type="link_filter", payload={"allow_domains": ["example.com"]}, is_active=True)]
    violations = engine.evaluate(content="http://malicious.test", mention_count=0, rules=rules)
    assert violations
    assert violations[0].rule_type == "link_filter"


def test_caps_rule_detects_uppercase():
    engine = AutomodEngine()
    rules = [AutomodRule(guild_id=1, rule_type="caps", payload={"threshold": 0.6, "min_length": 5}, is_active=True)]
    violations = engine.evaluate(content="INI PENGUMUMAN PENTING!!!", mention_count=0, rules=rules)
    assert violations


def test_mention_limit_violation():
    engine = AutomodEngine()
    rules = [AutomodRule(guild_id=1, rule_type="mention_limit", payload={"max_mentions": 2}, is_active=True)]
    violations = engine.evaluate(content="halo", mention_count=5, rules=rules)
    assert violations
