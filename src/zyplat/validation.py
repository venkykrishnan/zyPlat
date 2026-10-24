"""Identifier and classification shape rules shared by the API and services."""

from __future__ import annotations

import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,127}$")
CLASSIFICATION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
RESERVED_CLASSIFICATIONS = frozenset({"base"})


def normalize_identifier(value: str) -> str:
    cleaned = value.strip()
    if not IDENTIFIER_RE.match(cleaned):
        raise ValueError(
            "must start with a letter and contain only letters, digits, underscores, or hyphens"
        )
    return cleaned


def normalize_display_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 256 or any(ord(char) < 32 for char in cleaned):
        raise ValueError("name must be 1..256 characters without control characters")
    return cleaned


def normalize_description(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) > 4000:
        raise ValueError("description must be at most 4000 characters")
    if any(ord(char) < 32 and char not in "\n\t" for char in cleaned):
        raise ValueError("description must not contain control characters")
    return cleaned


def normalize_classification_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in values:
        token = raw.strip()
        if token.lower() in RESERVED_CLASSIFICATIONS:
            raise ValueError("'base' is reserved for entities with no classification")
        if not CLASSIFICATION_RE.match(token):
            raise ValueError(
                "classifications must start with a letter and contain only letters, digits, "
                "underscores, or hyphens"
            )
        if token in cleaned:
            raise ValueError(f"duplicate classification '{token}'")
        cleaned.append(token)
    return cleaned
