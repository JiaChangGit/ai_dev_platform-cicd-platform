#!/usr/bin/env python3
"""確認規格、閱讀筆記與靜態手冊的需求識別字一致。"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIREMENT = re.compile(r"\bREQ-[0-9]{3}\b")
SOURCE_MARKER = "SAMPLE-EVENT-EXPORT 1.0"


class OfflineHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts = 0
        self.external_resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script":
            self.scripts += 1
        resource_attribute = {
            "script": "src",
            "link": "href",
            "img": "src",
            "iframe": "src",
            "object": "data",
        }.get(tag)
        value = values.get(resource_attribute, "") if resource_attribute else ""
        if value and re.match(r"^(?:https?:)?//", value):
            self.external_resources.append(value)


def requirement_ids(path: Path) -> set[str]:
    return set(REQUIREMENT.findall(path.read_text(encoding="utf-8")))


def main() -> int:
    spec_ids = requirement_ids(ROOT / "sample-spec.md")
    if not spec_ids:
        print("[FAIL] sample-spec.md 沒有需求識別字")
        return 1

    failed = False
    for name in ("reading-notes.md", "index.html"):
        actual_ids = requirement_ids(ROOT / name)
        missing = sorted(spec_ids - actual_ids)
        extra = sorted(actual_ids - spec_ids)
        if missing:
            print(f"[FAIL] {name} 缺少：{', '.join(missing)}")
            failed = True
        if extra:
            print(f"[FAIL] {name} 出現規格未定義的識別字：{', '.join(extra)}")
            failed = True

    for name in ("source-register.md", "sample-spec.md", "reading-notes.md", "index.html"):
        if SOURCE_MARKER not in (ROOT / name).read_text(encoding="utf-8"):
            print(f"[FAIL] {name} 缺少來源版本標記：{SOURCE_MARKER}")
            failed = True

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    parser = OfflineHTMLParser()
    parser.feed(html)
    if parser.scripts:
        print("[FAIL] index.html 不得包含 script")
        failed = True
    if parser.external_resources:
        print("[FAIL] index.html 不得載入外部資源")
        failed = True

    if failed:
        return 1
    print(f"[OK] {len(spec_ids)} 個需求識別字已出現在筆記與手冊")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
