from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from bot.database.repositories import AutomodRule


LINK_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)


@dataclass(slots=True)
class AutomodViolation:
    rule_type: str
    reason: str


class AutomodEngine:
    def evaluate(
        self,
        *,
        content: str,
        mention_count: int,
        rules: Iterable[AutomodRule],
    ) -> list[AutomodViolation]:
        violations: list[AutomodViolation] = []
        normalized = content.strip()

        for rule in rules:
            if not rule.is_active:
                continue
            payload = rule.payload or {}
            if rule.rule_type == "link_filter":
                if self._violates_link_filter(normalized, payload):
                    violations.append(
                        AutomodViolation(
                            rule_type=rule.rule_type,
                            reason="Pesan mengandung tautan yang tidak diperbolehkan.",
                        )
                    )
            elif rule.rule_type == "mention_limit":
                if self._violates_mention_limit(mention_count, payload):
                    violations.append(
                        AutomodViolation(
                            rule_type=rule.rule_type,
                            reason="Jumlah mention melebihi batas yang diizinkan.",
                        )
                    )
            elif rule.rule_type == "caps":
                if self._violates_caps(normalized, payload):
                    violations.append(
                        AutomodViolation(
                            rule_type=rule.rule_type,
                            reason="Pesan didominasi huruf kapital.",
                        )
                    )
        return violations

    def _violates_link_filter(self, content: str, payload: dict[str, object]) -> bool:
        if not content:
            return False
        matches = LINK_REGEX.findall(content)
        if not matches:
            return False
        allow_domains = set()
        raw_allow = payload.get("allow_domains")
        if isinstance(raw_allow, list):
            allow_domains = {str(item).lower() for item in raw_allow}
        for match in matches:
            domain = self._extract_domain(match)
            if domain and domain in allow_domains:
                continue
            return True
        return False

    def _violates_mention_limit(self, mention_count: int, payload: dict[str, object]) -> bool:
        max_mentions = payload.get("max_mentions")
        if not isinstance(max_mentions, int) or max_mentions <= 0:
            return False
        return mention_count > max_mentions

    def _violates_caps(self, content: str, payload: dict[str, object]) -> bool:
        min_length = payload.get("min_length", 15)
        threshold = payload.get("threshold", 0.7)
        if not isinstance(min_length, int) or min_length <= 0:
            min_length = 15
        if not isinstance(threshold, (int, float)):
            threshold = 0.7
        if threshold <= 0:
            return False
        if len(content) < min_length:
            return False
        letters = [char for char in content if char.isalpha()]
        if not letters:
            return False
        uppercase = sum(1 for char in letters if char.isupper())
        ratio = uppercase / len(letters)
        return ratio >= threshold

    def _extract_domain(self, url: str) -> str | None:
        if "//" not in url:
            return None
        without_scheme = url.split("//", 1)[1]
        domain = without_scheme.split("/", 1)[0]
        return domain.lower()


__all__ = ["AutomodEngine", "AutomodViolation"]
