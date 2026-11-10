"""Loads knowledge markdown files and splits them into (section, text) pairs by `##` heading.

A "section" is the unit citations point to — everything under one `##` heading, up to the next
`##` (or end of file). Content before the first `##` heading is the "Overview" section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class DocumentSection:
    document_id: str
    title: str
    section: str
    text: str


def load_document_sections(knowledge_dir: Path) -> list[DocumentSection]:
    sections: list[DocumentSection] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        sections.extend(_split_sections(path))
    return sections


def _split_sections(path: Path) -> list[DocumentSection]:
    raw = path.read_text(encoding="utf-8")
    title = _first_h1(raw) or path.stem

    matches = list(_SECTION_PATTERN.finditer(raw))
    out: list[DocumentSection] = []

    if not matches:
        text = raw.strip()
        if text:
            out.append(DocumentSection(document_id=path.name, title=title, section="Overview", text=text))
        return out

    preamble = raw[: matches[0].start()].strip()
    # Drop the H1 title line from the preamble so it isn't duplicated as chunk content.
    preamble = re.sub(r"^#\s+.+?\n", "", preamble).strip()
    if preamble:
        out.append(DocumentSection(document_id=path.name, title=title, section="Overview", text=preamble))

    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()
        if body:
            out.append(DocumentSection(document_id=path.name, title=title, section=section_title, text=body))

    return out


def _first_h1(raw: str) -> str | None:
    match = re.search(r"^#\s+(.+?)\s*$", raw, re.MULTILINE)
    return match.group(1).strip() if match else None
