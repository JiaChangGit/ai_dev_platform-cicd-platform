#!/usr/bin/env python3
"""驗證各 CI 轉接器的路徑、佔位符與發行證據契約。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TOKEN = re.compile(r"<[A-Z][A-Z0-9_]*>")
KNOWN = {
    "<BUILD_COMMAND>", "<TEST_COMMAND>", "<LINT_AND_SECURITY_COMMAND>",
    "<PACKAGE_COMMAND>", "<WRITE_RELEASE_EVIDENCE_JSON_COMMAND>",
    "<EVIDENCE_AND_ARTIFACT_PATHS>", "<ARTIFACT_PATH>", "<RELEASE_EVIDENCE_PATH>",
}
REQUIRED = {
    "github-actions": {"<BUILD_COMMAND>", "<TEST_COMMAND>", "<PACKAGE_COMMAND>", "<WRITE_RELEASE_EVIDENCE_JSON_COMMAND>"},
    "gitlab-ci": {"<BUILD_COMMAND>", "<TEST_COMMAND>", "<PACKAGE_COMMAND>", "<WRITE_RELEASE_EVIDENCE_JSON_COMMAND>"},
    "jenkins": {"<BUILD_COMMAND>", "<TEST_COMMAND>", "<PACKAGE_COMMAND>", "<WRITE_RELEASE_EVIDENCE_JSON_COMMAND>"},
}
INTERNAL_INPUTS = {
    "sourceRepository", "sourceCommit", "sourceRef", "artifactUri", "artifactSha256",
    "artifactSignatureUri", "artifactSignatureSha256", "checks", "sbomUri", "sbomSha256",
    "provenanceUri", "provenanceSha256", "approval", "publisher",
}


def validate_ci_adapters(root: Path) -> list[str]:
    errors: list[str] = []
    paths = {
        "github-actions": root / "adapters/ci/github-actions/release-evidence.yml.template",
        "gitlab-ci": root / "adapters/ci/gitlab-ci/release-evidence.gitlab-ci.yml.template",
        "jenkins": root / "adapters/ci/jenkins/Jenkinsfile.template",
    }
    for adapter, path in paths.items():
        if not path.is_file():
            errors.append(f"{adapter}: 缺少 template")
            continue
        text = path.read_text(encoding="utf-8")
        tokens = set(TOKEN.findall(text))
        if unknown := sorted(tokens - KNOWN):
            errors.append(f"{adapter}: 不明佔位符 {', '.join(unknown)}")
        if missing := sorted(REQUIRED[adapter] - tokens):
            errors.append(f"{adapter}: 缺少佔位符 {', '.join(missing)}")
        rendered = TOKEN.sub("echo-ok", text)
        if adapter in {"github-actions", "gitlab-ci"}:
            try:
                import yaml

                parsed = yaml.safe_load(rendered)
                if not isinstance(parsed, dict):
                    errors.append(f"{adapter}: template 不是 YAML object")
            except ImportError:
                pass
            except Exception as error:
                errors.append(f"{adapter}: YAML 無法解析：{error}")
        if adapter == "jenkins":
            if rendered.count("{") != rendered.count("}"):
                errors.append("jenkins: 大括號不平衡")
            for stage in ("Verify", "Package", "Evidence"):
                if f"stage('{stage}')" not in rendered:
                    errors.append(f"jenkins: 缺少 {stage} stage")

    contract_path = root / "adapters/ci/internal/release-evidence.contract.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        inputs = set(contract.get("requiredInputs", []))
        if inputs != INTERNAL_INPUTS:
            errors.append("internal-ci: requiredInputs 與嚴格發行證據契約不一致")
        if contract.get("output") != "release-evidence.json":
            errors.append("internal-ci: output 必須是 release-evidence.json")
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"internal-ci: contract 無法解析：{error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_ci_adapters(args.root.resolve())
    if errors:
        for error in errors:
            print(f"[FAIL] CI adapter: {error}", file=sys.stderr)
        return 1
    print("[OK] CI adapter contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
