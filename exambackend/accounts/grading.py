"""Auto-grading helpers for identification and enumeration questions."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

_WS_RE = re.compile(r'\s+')
_NUM_PREFIX = re.compile(r'^[\(\s]*(?:\d+|[a-zA-Z])[.)]\s*')
_EDGE_PUNCT = re.compile(r'^[\s\"\'“”‘’`]+|[\s\"\'“”‘’`.;:]+$')


def _normalize_grade_text(text: str, case_sensitive: bool = False) -> str:
    t = unicodedata.normalize('NFKC', text or '')
    t = t.replace('\u2019', "'").replace('\u2018', "'")
    t = t.replace('\u201c', '"').replace('\u201d', '"')
    t = _WS_RE.sub(' ', t).strip()
    t = _EDGE_PUNCT.sub('', t).strip()
    if not case_sensitive:
        t = t.casefold()
    return t


def _split_enumeration_items(text: str) -> list[str]:
    raw = text or ''
    if '\n' in raw:
        parts = raw.split('\n')
    else:
        parts = re.split(r'\s*[;,]\s*', raw)
    items = []
    for part in parts:
        cleaned = _NUM_PREFIX.sub('', part.strip()).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _identification_expected_answers(correct_answer: str) -> list[str]:
    """Instructor may list alternatives with ' | ' (not '/', which appears in terms like TCP/IP)."""
    raw = (correct_answer or '').strip()
    if not raw:
        return []
    if '|' in raw:
        return [p.strip() for p in raw.split('|') if p.strip()]
    return [raw]


def grade_question(question: Any, answer_text: str) -> tuple[bool | None, float]:
    """
    Return (is_correct, credit) for one question.

    credit is 0.0, 1.0, or a fraction for partially matched enumeration.
    is_correct is None when the question must be graded manually.
    """
    qtype = getattr(question, 'question_type', '')
    expected = (getattr(question, 'correct_answer', None) or '').strip()
    case_sensitive = bool(getattr(question, 'case_sensitive', False))
    given = (answer_text or '').strip()

    if qtype == 'multiple_choice':
        if not given:
            return False, 0.0
        ok = given.casefold() == expected.casefold()
        return ok, 1.0 if ok else 0.0

    if qtype == 'identification':
        if not expected:
            return None, 0.0
        if not given:
            return False, 0.0
        given_n = _normalize_grade_text(given, case_sensitive)
        for alt in _identification_expected_answers(expected):
            if given_n == _normalize_grade_text(alt, case_sensitive):
                return True, 1.0
        return False, 0.0

    if qtype == 'enumeration':
        if not expected:
            return None, 0.0
        expected_items = _split_enumeration_items(expected)
        if not expected_items:
            return None, 0.0
        given_items = _split_enumeration_items(given)
        expected_n = [_normalize_grade_text(i, case_sensitive) for i in expected_items]
        given_n = [_normalize_grade_text(i, case_sensitive) for i in given_items]
        given_set = set(given_n)
        matched = sum(1 for e in expected_n if e and e in given_set)
        credit = matched / len(expected_n)
        return (matched == len(expected_n), credit)

    # essay / unknown
    return None, 0.0
