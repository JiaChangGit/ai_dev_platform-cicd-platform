#!/usr/bin/env python3
"""稽核預設離線 skill 的結構、資源引用、觸發邊界與重疊路由。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True

from verify_package import expected_payload_names, load_json  # noqa: E402


NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BROAD_TRIGGER_PHRASES = (
    "starting any conversation",
    "before any creative work",
    "implementing any feature",
)


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("維護環境需要 PyYAML 才能稽核 skill 路由") from error
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise ValueError(f"YAML 無法解析：{path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"YAML root 必須是 object：{path}")
    return data


def parse_skill(path: Path) -> tuple[dict, str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, text, ["SKILL.md 缺少 YAML frontmatter"]
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text, ["SKILL.md frontmatter 未關閉"]
    try:
        import yaml

        metadata = yaml.safe_load(text[4:end]) or {}
    except Exception as error:
        return {}, text, [f"SKILL.md frontmatter 無法解析：{error}"]
    if not isinstance(metadata, dict):
        errors.append("SKILL.md frontmatter 必須是 object")
        metadata = {}
    return metadata, text[end + 5 :], errors


def local_links(body: str) -> list[str]:
    results: list[str] = []
    for raw in MARKDOWN_LINK.findall(body):
        value = raw.strip().split("#", 1)[0]
        if not value or value == "link" or value.startswith(("http://", "https://", "mailto:", "/")):
            continue
        if any(marker in value for marker in ("<", ">", "{", "}")):
            continue
        results.append(value)
    return results


def configured_paths(config: dict) -> set[str]:
    paths = set(config.get("manualOnly", []))
    for key in ("bootstrapOnly", "restrictedAutomatic"):
        paths.update(item.get("path") for item in config.get(key, []) if isinstance(item, dict))
    for group in config.get("collisionGroups", []):
        primary = group.get("primary")
        if isinstance(primary, str) and primary.endswith("SKILL.md"):
            paths.add(primary)
        paths.update(path for path in group.get("alternatives", []) if str(path).endswith("SKILL.md"))
    return paths


def audit_skills(root: Path) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_json(root / "distribution/manifest.json")
    routing = load_yaml(root / "registry/skill-routing.yaml")
    payload = expected_payload_names(root, manifest)
    skill_paths = sorted(path for path in payload if path.endswith("/SKILL.md"))
    validation = routing.get("validation", {})
    expected_count = validation.get("expectedPackagedSkillCount")
    if len(skill_paths) != expected_count:
        errors.append(f"預設包 skill 數量應為 {expected_count}，實際為 {len(skill_paths)}")

    included_roots = routing.get("discovery", {}).get("includedRoots", [])
    excluded_roots = routing.get("discovery", {}).get("excludedRoots", [])
    for path in skill_paths:
        if not any(path == prefix or path.startswith(f"{prefix.rstrip('/')}/") for prefix in included_roots):
            errors.append(f"skill 未落在 discovery.includedRoots：{path}")
        if any(path == prefix or path.startswith(f"{prefix.rstrip('/')}/") for prefix in excluded_roots):
            errors.append(f"實驗／廢棄 skill 不得進入預設包：{path}")

    allowed_fields = set(validation.get("allowedUpstreamFrontmatter", []))
    length_exceptions = {
        item.get("path"): item.get("reason") for item in validation.get("acceptedLengthExceptions", [])
    }
    manual = set(routing.get("manualOnly", []))
    bootstrap = {item.get("path") for item in routing.get("bootstrapOnly", [])}
    guarded = configured_paths(routing)
    names: dict[str, list[str]] = defaultdict(list)
    metadata_by_path: dict[str, dict] = {}

    for relative in skill_paths:
        path = root / relative
        metadata, body, skill_errors = parse_skill(path)
        errors.extend(f"{relative}: {message}" for message in skill_errors)
        metadata_by_path[relative] = metadata
        name = metadata.get("name")
        description = metadata.get("description")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            errors.append(f"{relative}: name 必須是小寫 hyphen-case")
        else:
            names[name].append(relative)
            if name != path.parent.name:
                errors.append(f"{relative}: name 與目錄名不一致")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{relative}: description 必須說明功能與觸發情境")
        elif "Replace with description" in description:
            errors.append(f"{relative}: description 仍是佔位內容")
        fields = set(metadata)
        if unknown := sorted(fields - allowed_fields):
            errors.append(f"{relative}: 未登記的上游 frontmatter 欄位：{', '.join(unknown)}")
        if metadata.get("disable-model-invocation") is True and relative not in manual:
            errors.append(f"{relative}: 上游標記手動呼叫，但 manualOnly 未登記")
        if "argument-hint" in metadata and relative not in manual:
            errors.append(f"{relative}: argument-hint 只能用於 manualOnly skill")
        line_count = len((root / relative).read_text(encoding="utf-8", errors="replace").splitlines())
        if line_count > validation.get("maxSkillLines", 500) and not length_exceptions.get(relative):
            errors.append(f"{relative}: {line_count} 行超過 progressive disclosure 建議上限")
        for link in local_links(body):
            if not (path.parent / link).exists():
                errors.append(f"{relative}: 本機參照不存在：{link}")
        lowered = str(description).lower()
        if any(phrase in lowered for phrase in BROAD_TRIGGER_PHRASES) and relative not in guarded:
            errors.append(f"{relative}: 觸發描述過廣，但沒有路由護欄")

    for name, paths in names.items():
        if len(paths) > 1:
            errors.append(f"skill name 重複：{name}: {', '.join(paths)}")

    all_known = set(skill_paths) | {"templates/task-handoff.md"}
    for configured in sorted(guarded):
        if configured not in all_known:
            errors.append(f"路由設定指向未打包的 skill：{configured}")
    for excluded in excluded_roots:
        if not (root / excluded).exists():
            warnings.append(f"排除路徑不存在：{excluded}")

    collision_paths: set[str] = set()
    for group in routing.get("collisionGroups", []):
        paths = [group.get("primary"), *group.get("alternatives", [])]
        collision_paths.update(path for path in paths if isinstance(path, str) and path.endswith("SKILL.md"))
        if len(paths) != len(set(paths)) or not group.get("selection"):
            errors.append(f"collision group {group.get('id', '?')} 缺少唯一路由或選擇規則")
    if manual & bootstrap:
        errors.append("manualOnly 與 bootstrapOnly 不得重疊")

    for index, case in enumerate(routing.get("triggerTests", []), start=1):
        expected = set(case.get("expect", []))
        forbidden = set(case.get("forbid", []))
        if expected & forbidden:
            errors.append(f"trigger test {index}: expect 與 forbid 重疊")
        for path in expected | forbidden:
            if path not in all_known:
                errors.append(f"trigger test {index}: 指向未打包的 skill：{path}")
        for path in expected & manual:
            name = metadata_by_path.get(path, {}).get("name", "")
            prompt = str(case.get("prompt", "")).lower()
            if name and name not in prompt:
                errors.append(f"trigger test {index}: manualOnly skill 必須在 prompt 明確點名：{name}")
        for item in routing.get("restrictedAutomatic", []):
            path = item.get("path")
            prompt = str(case.get("prompt", "")).lower()
            required = [str(term).lower() for term in item.get("requireAny", [])]
            excluded = [str(term).lower() for term in item.get("excludeAny", [])]
            if path in expected and required and not any(term in prompt for term in required):
                errors.append(f"trigger test {index}: 未命中 {path} 的 requireAny")
            if path in expected and any(term in prompt for term in excluded):
                errors.append(f"trigger test {index}: {path} 命中 excludeAny")
            if path in forbidden and required and any(term in prompt for term in required) and not any(
                term in prompt for term in excluded
            ):
                warnings.append(f"trigger test {index}: {path} 的 forbid 主要依賴語意邊界")

    return {
        "schemaVersion": 1,
        "packagedSkillCount": len(skill_paths),
        "manualOnlyCount": len(manual),
        "collisionGroupCount": len(routing.get("collisionGroups", [])),
        "triggerTestCount": len(routing.get("triggerTests", [])),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = audit_skills(args.root)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"[FAIL] skill audit: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in result["warnings"]:
            print(f"[WARN] skill audit: {warning}")
        for error in result["errors"]:
            print(f"[FAIL] skill audit: {error}", file=sys.stderr)
        if result["ok"]:
            print(
                f"[OK] skill audit: {result['packagedSkillCount']} skills, "
                f"{result['collisionGroupCount']} collision groups, "
                f"{result['triggerTestCount']} trigger tests"
            )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
