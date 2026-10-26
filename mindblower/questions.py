"""Loads and checks the question bank in data/questions.json."""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .models import Question

PLACEHOLDER = "{player}"


class QuestionBankError(ValueError):
    pass


def load_questions(path: str | Path) -> list[Question]:
    """Read questions.json: {"small_talk": ["What is {player}'s ...?", ...], ...}."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return parse_questions(raw)


def parse_questions(raw: dict) -> list[Question]:
    questions: list[Question] = []
    for category in config.CATEGORIES:
        texts = raw.get(category.key)
        if not texts:
            raise QuestionBankError(f"Category '{category.key}' has no questions")
        seen = set()
        for i, text in enumerate(texts, start=1):
            text = text.strip()
            if text.count(PLACEHOLDER) != 1:
                raise QuestionBankError(f"Needs exactly one {PLACEHOLDER}: {text!r}")
            if text in seen:
                raise QuestionBankError(f"Duplicate question: {text!r}")
            seen.add(text)
            questions.append(Question(id=f"{category.key}-{i}", category=category.key, text=text))
    unknown = set(raw) - set(config.CATEGORY_BY_KEY)
    if unknown:
        raise QuestionBankError(f"Unknown categories: {sorted(unknown)}")
    return questions


def fill_in(text: str, name: str) -> str:
    """The question with the person's name written in."""
    return text.replace(PLACEHOLDER, name)
