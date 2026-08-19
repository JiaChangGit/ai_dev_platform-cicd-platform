#!/usr/bin/env python3
"""稽核預設離線 skill 的結構、資源引用、觸發邊界與重疊路由。"""

from __future__ import annotations

import argparse
import hashlib
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


def parse_unique_yaml(text: str, source: str) -> object:
    """解析 YAML，拒絕會被預設 parser 靜默覆蓋的重複 key。"""
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("維護環境需要 PyYAML 才能稽核 skill 路由") from error

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader: UniqueKeyLoader, node: object, deep: bool = False) -> dict:
        if not isinstance(node, yaml.MappingNode):
            raise ValueError(f"YAML mapping 格式無效：{source}")
        mapping: dict = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"YAML 含重複 key：{source}: {key}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    return yaml.load(text, Loader=UniqueKeyLoader)


def load_yaml(path: Path) -> dict:
    try:
        data = parse_unique_yaml(path.read_text(encoding="utf-8"), str(path))
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
        metadata = parse_unique_yaml(text[4:end], str(path)) or {}
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


def local_reference_is_packaged(
    root: Path,
    source: Path,
    link: str,
    payload: set[str],
) -> bool:
    """確認 Markdown 本機參照的檔案，或所指目錄內至少一項內容，會進入發行包。"""
    target = (source.parent / link).resolve()
    try:
        relative = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        return False
    if target.is_file():
        return relative in payload
    if target.is_dir():
        prefix = f"{relative.rstrip('/')}/"
        return any(item.startswith(prefix) for item in payload)
    return False


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


def explicitly_names_manual_skill(prompt: str, name: str) -> bool:
    """手動 skill 只接受指令或明確的 skill 點名。"""
    lowered = prompt.lower()
    escaped = re.escape(name.lower())
    patterns = (
        rf"/{escaped}(?![a-z0-9-])",
        rf"skill:{escaped}(?![a-z0-9-])",
        rf"\buse\s+{escaped}\s+skill\b",
        rf"使用\s*`?{escaped}`?\s*skill",
    )
    return any(re.search(pattern, lowered) for pattern in patterns)


def audit_skills(root: Path) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_json(root / "distribution/manifest.json")
    routing = load_yaml(root / "registry/skill-routing.yaml")
    catalog = load_yaml(root / "registry/skills.yaml")
    payload = expected_payload_names(root, manifest)
    skill_paths = sorted(path for path in payload if path.endswith("/SKILL.md"))
    validation = routing.get("validation", {})
    for path in validation.get("disallowedPackagedPaths", []):
        if path in payload:
            errors.append(f"發行包含第三方開發紀錄或非必要索引：{path}")
    expected_count = validation.get("expectedPackagedSkillCount")
    if len(skill_paths) != expected_count:
        errors.append(f"預設包 skill 數量應為 {expected_count}，實際為 {len(skill_paths)}")

    included_roots = routing.get("discovery", {}).get("includedRoots", [])
    excluded_roots = routing.get("discovery", {}).get("excludedRoots", [])
    catalog_entries = catalog.get("skills")
    if not isinstance(catalog_entries, list):
        errors.append("registry/skills.yaml 的 skills 必須是清單")
        catalog_entries = []
    catalog_ids: set[str] = set()
    catalog_sources: set[str] = set()
    for item in catalog_entries:
        if not isinstance(item, dict):
            errors.append("registry/skills.yaml 含無效項目")
            continue
        item_id = item.get("id")
        source = item.get("source")
        if not isinstance(item_id, str) or not item_id or item_id in catalog_ids:
            errors.append(f"skill 來源 id 缺少或重複：{item_id}")
        else:
            catalog_ids.add(item_id)
        if not isinstance(source, str) or not source or source in catalog_sources:
            errors.append(f"skill 來源路徑缺少或重複：{source}")
        else:
            catalog_sources.add(source)
        if "trigger_keywords" in item:
            errors.append(f"skill 來源索引不得定義第二份觸發條件：{item_id}")
    if catalog_sources != set(included_roots):
        errors.append("registry/skills.yaml 與 skill-routing discovery.includedRoots 不一致")
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
    descriptions: dict[str, list[str]] = defaultdict(list)
    bodies: dict[str, list[str]] = defaultdict(list)
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
        else:
            normalized_description = " ".join(description.split()).casefold()
            descriptions[normalized_description].append(relative)
            maximum = validation.get("maxDescriptionCharacters", 1200)
            if len(description) > maximum:
                errors.append(f"{relative}: description 超過 {maximum} 個字元，應保留功能與分流邊界")
        if not body.strip():
            errors.append(f"{relative}: SKILL.md 缺少可執行的內容")
        else:
            digest = hashlib.sha256(body.strip().encode("utf-8")).hexdigest()
            bodies[digest].append(relative)
        fields = set(metadata)
        if unknown := sorted(fields - allowed_fields):
            errors.append(f"{relative}: 未登記的上游 frontmatter 欄位：{', '.join(unknown)}")
        if metadata.get("disable-model-invocation") is True and relative not in manual:
            errors.append(f"{relative}: 上游標記手動呼叫，但 manualOnly 未登記")
        if "disable-model-invocation" in metadata and not isinstance(
            metadata.get("disable-model-invocation"), bool
        ):
            errors.append(f"{relative}: disable-model-invocation 必須是 boolean")
        if "argument-hint" in metadata and relative not in manual:
            errors.append(f"{relative}: argument-hint 只能用於 manualOnly skill")
        line_count = len((root / relative).read_text(encoding="utf-8", errors="replace").splitlines())
        if line_count > validation.get("maxSkillLines", 500) and not length_exceptions.get(relative):
            errors.append(f"{relative}: {line_count} 行超過 progressive disclosure 建議上限")
        for link in local_links(body):
            target = path.parent / link
            if not target.exists():
                errors.append(f"{relative}: 本機參照不存在：{link}")
            elif not local_reference_is_packaged(root, path, link, payload):
                errors.append(f"{relative}: 發行包未包含本機參照：{link}")
        lowered = str(description).lower()
        if any(phrase in lowered for phrase in BROAD_TRIGGER_PHRASES) and relative not in guarded:
            errors.append(f"{relative}: 觸發描述過廣，但沒有路由護欄")

    for name, paths in names.items():
        if len(paths) > 1:
            errors.append(f"skill name 重複：{name}: {', '.join(paths)}")
    for paths in descriptions.values():
        if len(paths) > 1:
            errors.append(f"skill description 完全相同：{', '.join(paths)}")
    for paths in bodies.values():
        if len(paths) > 1:
            errors.append(f"SKILL.md 主體完全相同：{', '.join(paths)}")

    all_known = set(skill_paths) | {"templates/task-handoff.md"}
    for configured in sorted(guarded):
        if configured not in all_known:
            errors.append(f"路由設定指向未打包的 skill：{configured}")
    for excluded in excluded_roots:
        if not (root / excluded).exists():
            warnings.append(f"排除路徑不存在：{excluded}")

    for path, reason in length_exceptions.items():
        if path not in skill_paths:
            errors.append(f"長度例外指向未打包的 skill：{path}")
        elif not isinstance(reason, str) or not reason.strip():
            errors.append(f"長度例外缺少原因：{path}")
        elif len((root / path).read_text(encoding="utf-8", errors="replace").splitlines()) <= validation.get(
            "maxSkillLines", 500
        ):
            errors.append(f"長度例外已不需要：{path}")

    restricted_items = routing.get("restrictedAutomatic", [])
    restricted_paths: set[str] = set()
    for item in restricted_items:
        path = item.get("path") if isinstance(item, dict) else None
        required = item.get("requireAny") if isinstance(item, dict) else None
        excluded = item.get("excludeAny") if isinstance(item, dict) else None
        if not isinstance(path, str) or path in restricted_paths:
            errors.append(f"restrictedAutomatic 路徑缺少或重複：{path}")
            continue
        restricted_paths.add(path)
        if not isinstance(required, list) or not required or not all(isinstance(term, str) and term for term in required):
            errors.append(f"restrictedAutomatic.requireAny 必須是非空字串清單：{path}")
        if not isinstance(excluded, list) or not all(isinstance(term, str) and term for term in excluded):
            errors.append(f"restrictedAutomatic.excludeAny 必須是字串清單：{path}")
        if isinstance(required, list) and isinstance(excluded, list):
            overlap = {str(term).casefold() for term in required} & {str(term).casefold() for term in excluded}
            if overlap:
                errors.append(f"restrictedAutomatic requireAny 與 excludeAny 重複：{path}")

    collision_paths: set[str] = set()
    collision_membership: dict[str, str] = {}
    collision_ids: set[str] = set()
    for group in routing.get("collisionGroups", []):
        group_id = group.get("id")
        paths = [group.get("primary"), *group.get("alternatives", [])]
        collision_paths.update(path for path in paths if isinstance(path, str) and path.endswith("SKILL.md"))
        if not isinstance(group_id, str) or not group_id or group_id in collision_ids:
            errors.append(f"collision group id 缺少或重複：{group_id}")
        else:
            collision_ids.add(group_id)
        if len(paths) != len(set(paths)) or len(paths) < 2 or not group.get("selection"):
            errors.append(f"collision group {group_id or '?'} 缺少唯一路由或選擇規則")
        for path in paths:
            if not isinstance(path, str) or path not in all_known:
                errors.append(f"collision group {group_id or '?'} 指向未打包內容：{path}")
                continue
            if previous := collision_membership.get(path):
                errors.append(f"同一路徑同時屬於 collision group {previous} 與 {group_id}：{path}")
            else:
                collision_membership[path] = str(group_id)
    if manual & bootstrap:
        errors.append("manualOnly 與 bootstrapOnly 不得重疊")
    if manual & restricted_paths:
        errors.append("manualOnly 與 restrictedAutomatic 不得重疊")

    positive_coverage: set[str] = set()
    negative_coverage: set[str] = set()
    prompts: set[str] = set()
    for index, case in enumerate(routing.get("triggerTests", []), start=1):
        prompt_text = case.get("prompt")
        if not isinstance(prompt_text, str) or not prompt_text.strip():
            errors.append(f"routing case {index}: prompt 必須是非空字串")
            prompt_text = ""
        normalized_prompt = " ".join(prompt_text.split()).casefold()
        if normalized_prompt in prompts:
            errors.append(f"routing case {index}: prompt 重複")
        prompts.add(normalized_prompt)
        expected_items = case.get("expect")
        forbidden_items = case.get("forbid")
        if not isinstance(expected_items, list) or not isinstance(forbidden_items, list):
            errors.append(f"routing case {index}: expect 與 forbid 必須是清單")
            continue
        if not all(isinstance(path, str) for path in expected_items + forbidden_items):
            errors.append(f"routing case {index}: expect 與 forbid 只能包含路徑字串")
            continue
        if len(expected_items) != len(set(expected_items)):
            errors.append(f"routing case {index}: expect 含重複路徑")
        if len(forbidden_items) != len(set(forbidden_items)):
            errors.append(f"routing case {index}: forbid 含重複路徑")
        expected = set(expected_items)
        forbidden = set(forbidden_items)
        positive_coverage.update(expected)
        negative_coverage.update(forbidden)
        if expected & forbidden:
            errors.append(f"routing case {index}: expect 與 forbid 重疊")
        for path in expected | forbidden:
            if path not in all_known:
                errors.append(f"routing case {index}: 指向未打包的 skill：{path}")
        for path in expected & manual:
            name = metadata_by_path.get(path, {}).get("name", "")
            if name and not explicitly_names_manual_skill(prompt_text, name):
                errors.append(f"routing case {index}: manualOnly skill 必須用指令或 skill 名稱明確點名：{name}")
        for item in restricted_items:
            path = item.get("path")
            prompt = prompt_text.lower()
            required = [str(term).lower() for term in item.get("requireAny", [])]
            excluded = [str(term).lower() for term in item.get("excludeAny", [])]
            if path in expected and required and not any(term in prompt for term in required):
                errors.append(f"routing case {index}: 未命中 {path} 的 requireAny")
            if path in expected and any(term in prompt for term in excluded):
                errors.append(f"routing case {index}: {path} 命中 excludeAny")
            if path in forbidden and required and any(term in prompt for term in required) and not any(
                term in prompt for term in excluded
            ):
                errors.append(
                    f"routing case {index}: {path} 已命中 requireAny，"
                    "但 forbid 沒有對應 excludeAny"
                )
        for group in routing.get("collisionGroups", []):
            group_paths = {group.get("primary"), *group.get("alternatives", [])}
            if selected := expected & group_paths:
                missing_forbid = group_paths - selected - forbidden
                if missing_forbid:
                    errors.append(
                        f"routing case {index}: collision group {group.get('id')} 未禁止其他候選："
                        + ", ".join(sorted(str(path) for path in missing_forbid))
                    )

    required_positive = guarded
    for path in sorted(required_positive - positive_coverage):
        errors.append(f"高風險路由缺少正向案例：{path}")
    for path in sorted(restricted_paths - negative_coverage):
        errors.append(f"限制自動觸發缺少負向案例：{path}")

    return {
        "schemaVersion": 1,
        "packagedSkillCount": len(skill_paths),
        "descriptionAuditCount": len(metadata_by_path),
        "catalogSourceCount": len(catalog_sources),
        "manualOnlyCount": len(manual),
        "collisionGroupCount": len(routing.get("collisionGroups", [])),
        "triggerTestCount": len(routing.get("triggerTests", [])),
        "guardedRouteCount": len(guarded),
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
                f"{result['triggerTestCount']} routing cases"
            )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
