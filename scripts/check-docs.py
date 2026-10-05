#!/usr/bin/env python3
"""Check bilingual structure, local links and English technical instructions.

This detects missing translations and drift in section/release structure. It
cannot establish that translated prose has the same meaning; reviewers still
compare content. Working data and private review reports are outside this scan.
"""
from __future__ import annotations

import ast
import io
import pathlib
import re
import sys
import tokenize
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parent.parent
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
PAIRS = ("README", "CONTRIBUTING", "BACKLOG", "CHANGELOG",
         "docs/INSTALL", "docs/CONCEPTS", "docs/CLEANUP", "docs/RELEASE", "SPEC/FORMAT")


def headings(text: str) -> list[str]:
    """Ignore fenced examples when comparing heading levels."""
    result, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced:
            match = re.match(r"^(#{2,6}) ", line)
            if match:
                result.append(match.group(1))
    return result


def main() -> int:
    errors = []
    for stem in PAIRS:
        en, ru = ROOT / f"{stem}.md", ROOT / f"{stem}.ru.md"
        if not en.is_file() or not ru.is_file():
            errors.append(f"Нет обеих языковых версий: {stem}")
            continue
        if headings(en.read_text()) != headings(ru.read_text()):
            errors.append(f"Структура разделов разошлась: {stem}")
        if stem == "CHANGELOG":
            versions = lambda p: re.findall(r"^## (\d+\.\d+\.\d+)\b", p.read_text(), re.M)
            if versions(en) != versions(ru):
                errors.append("Список релизов разошёлся в CHANGELOG")

    docs = list(ROOT.glob("*.md"))
    for folder in ("docs", "SPEC", "commands"):
        docs.extend((ROOT / folder).glob("*.md"))
    docs.extend((ROOT / "skills").glob("*/SKILL.md"))
    for path in docs:
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", path.read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            if not (path.parent / unquote(url.path)).exists():
                errors.append(f"Ссылка не разрешается: {path.relative_to(ROOT)} → {target}")

    code = list((ROOT / "scripts").glob("*.py")) + list((ROOT / "hooks").glob("*.py")) + list((ROOT / "tests").glob("*.py"))
    for path in code:
        source = path.read_text()
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and CYRILLIC.search(token.string):
                errors.append(f"Комментарий кода не английский: {path.relative_to(ROOT)}:{token.start[0]}")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if doc and CYRILLIC.search(doc):
                    errors.append(f"Docstring не английский: {path.relative_to(ROOT)}")

    for path in list((ROOT / "commands").glob("*.md")) + list((ROOT / "skills").glob("*/SKILL.md")):
        # Descriptions can quote Russian user input; instruction bodies are English.
        body = re.sub(r"\A---\n.*?\n---\n", "", path.read_text(), count=1, flags=re.S)
        if CYRILLIC.search(body):
            errors.append(f"Инструкции агенту не английские: {path.relative_to(ROOT)}")
    for message in errors:
        print(f"Ошибка: {message}")
    if not errors:
        print("Документация: пары, разделы и ссылки согласованы; технические инструкции английские.")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
