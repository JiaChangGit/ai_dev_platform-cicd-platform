#!/usr/bin/env python3
"""確認規格、閱讀筆記與靜態手冊的需求識別字一致。"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIREMENT = re.compile(r"\bREQ-[0-9]{3}\b")


def requirement_ids(path: Path) -> set[str]:
    return set(REQUIREMENT.findall(path.read_text(encoding="utf-8")))


def main() -> int:
    spec_ids = requirement_ids(ROOT / "sample-spec.md")
    if not spec_ids:
        print("[FAIL] sample-spec.md 沒有需求識別字")
        return 1

    failed = False
    for name in ("reading-notes.md", "index.html"):
        missing = sorted(spec_ids - requirement_ids(ROOT / name))
        if missing:
            print(f"[FAIL] {name} 缺少：{', '.join(missing)}")
            failed = True

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if re.search(r"<(script|link)[^>]+(?:src|href)=[\"']https?://", html, re.IGNORECASE):
        print("[FAIL] index.html 不得載入外部 script 或 stylesheet")
        failed = True

    if failed:
        return 1
    print(f"[OK] {len(spec_ids)} 個需求識別字已出現在筆記與手冊")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
