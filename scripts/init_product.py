#!/usr/bin/env python3
"""建立產品開發與發行儲存庫骨架，並連接共用 ai-dev-platform。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


PRODUCT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class ProductConfig:
    name: str
    display_name: str
    domain: str
    ci: str
    product_type: str
    target_platform: str
    language_framework: str
    build_command: str
    test_command: str
    lint_command: str
    package_command: str
    artifact_path: str


DOMAIN_DEFAULTS = {
    "android": {
        "product_type": "Android App",
        "target_platform": "Android 23 以上",
        "language_framework": "Kotlin、Gradle、Android SDK",
        "build_command": "gradle --no-daemon :app:assembleDebug",
        "test_command": "gradle --no-daemon :app:testDebugUnitTest",
        "lint_command": "gradle --no-daemon :app:lintDebug",
        "package_command": "gradle --no-daemon :app:assembleRelease",
        "artifact_path": "app/build/outputs/apk/release/app-release-unsigned.apk",
    },
    "ssd-pcie-fw": {
        "product_type": "SSD PCIe 韌體",
        "target_platform": "產品定義的 SSD 控制器與 PCIe 平台",
        "language_framework": "C11、Make",
        "build_command": "make all",
        "test_command": "make test",
        "lint_command": "make lint",
        "package_command": "make package",
        "artifact_path": "dist/ssd-pcie-fw-sample.elf",
    },
}

CI_CHOICES = ("github-actions", "gitlab-ci", "jenkins", "internal-ci")


def validate_product_name(value: str) -> str:
    if not PRODUCT_NAME.fullmatch(value):
        raise ValueError("產品名稱只能使用小寫英文字母、數字與連字號，且須以英文字母或數字開頭")
    return value


def validate_single_line(label: str, value: str) -> str:
    if not value.strip() or "\n" in value or "\r" in value or "\0" in value:
        raise ValueError(f"{label} 必須是單行非空字串")
    return value.strip()


def validate_relative_path(value: str) -> str:
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or not parsed.parts:
        raise ValueError("artifact path 必須是產品儲存庫內的安全相對路徑")
    return parsed.as_posix()


def build_config(args: argparse.Namespace) -> ProductConfig:
    name = validate_product_name(args.name)
    display_name = validate_single_line("display name", args.display_name or name)
    defaults = DOMAIN_DEFAULTS.get(args.domain)

    if defaults is None:
        required = {
            "product type": args.product_type,
            "target platform": args.target_platform,
            "language/framework": args.language_framework,
            "build command": args.build_command,
            "test command": args.test_command,
            "lint command": args.lint_command,
            "package command": args.package_command,
            "artifact path": args.artifact_path,
        }
        missing = [label for label, value in required.items() if not value]
        if missing:
            raise ValueError(f"generic domain 缺少必要參數：{', '.join(missing)}")
        defaults = {
            "product_type": args.product_type,
            "target_platform": args.target_platform,
            "language_framework": args.language_framework,
            "build_command": args.build_command,
            "test_command": args.test_command,
            "lint_command": args.lint_command,
            "package_command": args.package_command,
            "artifact_path": args.artifact_path,
        }

    values = dict(defaults)
    for key in (
        "product_type",
        "target_platform",
        "language_framework",
        "build_command",
        "test_command",
        "lint_command",
        "package_command",
        "artifact_path",
    ):
        override = getattr(args, key)
        if override:
            values[key] = override

    for key in (
        "product_type",
        "target_platform",
        "language_framework",
        "build_command",
        "test_command",
        "lint_command",
        "package_command",
    ):
        values[key] = validate_single_line(key.replace("_", " "), values[key])
    values["artifact_path"] = validate_relative_path(values["artifact_path"])

    return ProductConfig(
        name=name,
        display_name=display_name,
        domain=args.domain,
        ci=args.ci,
        **values,
    )


def render(text: str, config: ProductConfig) -> str:
    replacements = {
        "<PRODUCT_NAME>": config.display_name,
        "<PRODUCT_SLUG>": config.name,
        "<PRODUCT_TYPE>": config.product_type,
        "<PLATFORM>": config.target_platform,
        "<LANGUAGE_FRAMEWORK>": config.language_framework,
        "<BUILD_COMMAND>": config.build_command,
        "<TEST_COMMAND>": config.test_command,
        "<LINT_COMMAND>": config.lint_command,
        "<PACKAGE_COMMAND>": config.package_command,
        "<ARTIFACT_PATH>": config.artifact_path,
        "<CI_SYSTEM>": config.ci,
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_entrypoints(platform_root: Path, target: Path, config: ProductConfig) -> None:
    source = platform_root / "templates" / "product-entrypoint"
    for source_path, target_name in (
        (source / "AGENTS.md.template", "AGENTS.md"),
        (source / "CLAUDE.md.template", "CLAUDE.md"),
        (source / "opencode.json.template", "opencode.json"),
    ):
        write_text(target / target_name, render(source_path.read_text(encoding="utf-8"), config))


def product_readme(config: ProductConfig, includes_example: bool) -> str:
    example_line = (
        "本儲存庫已包含平台提供的最小驗收範例，可直接執行下列指令。"
        if includes_example
        else "本儲存庫只有開發骨架；加入產品程式碼後，再執行下列指令。"
    )
    return f"""# {config.display_name}

本儲存庫保存 {config.product_type} 的產品原始碼與 CI/CD 設定。AI 開發工具一律讀取相鄰的 `../ai-dev-platform/AGENTS.md`，不複製平台規則或第三方 skill。

{example_line}

## 開發指令

```bash
{config.build_command}
{config.test_command}
{config.lint_command}
```

## 發行邊界

建置成品保存於 CI／成品平台。`../{config.name}-release/` 只保存發行證據、Release Note、Git tag，以及成品 URI／SHA-256；不得複製原始碼、建置成品或 `external/`。
"""


def product_gitignore(config: ProductConfig) -> str:
    common = [".idea/", ".vscode/", "__pycache__/", "*.pyc", "dist/", "build/"]
    if config.domain == "android":
        common.extend([".gradle/", "local.properties", "**/build/"])
    elif config.domain == "ssd-pcie-fw":
        common.extend(["*.o", "*.elf", "*.bin", "*.map"])
    return "\n".join(dict.fromkeys(common))


def architecture_doc(config: ProductConfig) -> str:
    return f"""# {config.display_name} 架構

本文件記錄 {config.product_type} 的目前架構。產品細節應隨實作持續補充。

## 系統邊界

```mermaid
flowchart LR
    A["ai-dev-platform<br/>共用目前版本"] -.->|"規則、流程、skill"| B["{config.name}-cicd-platform<br/>產品原始碼與 CI/CD"]
    B -->|"build、test、lint、scan"| C["CI／成品平台"]
    C -->|"release evidence<br/>artifact URI／SHA-256"| D["{config.name}-release<br/>發行中繼資料"]
```

## 元件

| 元件 | 職責 | 相依項目 |
|---|---|---|
| 待補 | 待補 | 待補 |

## 已知限制

- 平台路徑固定為 `../ai-dev-platform/`，不支援內嵌或產品端版本鎖定。
- 產品領域規範以 `docs/domain-standards.md` 為準。
"""


def adr_doc(config: ProductConfig) -> str:
    return f"""# 0001. 使用共用 ai-dev-platform 目前版本

## 狀態

Accepted

## 背景（Context）

{config.display_name} 需要與其他產品共用相同的 AI 開發規則，且產品 CI/CD 與發行儲存庫不得保存第三方 skill。

## 決策（Decision）

產品入口檔固定讀取 `../ai-dev-platform/AGENTS.md`。平台更新後，產品下一次任務直接使用目前版本，不建立平台 lock file，也不使用 subtree 內嵌平台內容。

## 後果（Consequences）

- 所有產品立即取得平台規則與 skill 更新。
- 平台更新可能同時影響多個產品，因此平台發行前必須執行跨領域範例驗證。
- 產品儲存庫可以獨立保存原始碼，但 AI 開發環境必須維持 `Work/` 平行目錄結構。
"""


def domain_standards_doc(config: ProductConfig) -> str:
    if config.domain == "android":
        sources = """- [Android Developers](https://developer.android.com/)
- [Android Gradle Plugin 9.2 release notes](https://developer.android.com/build/releases/agp-9-2-0-release-notes)
- [Gradle compatibility matrix](https://docs.gradle.org/current/userguide/compatibility.html)"""
        notes = "- 範例以 AGP 9.2.0 內建 Kotlin、Gradle 9.4.1、JDK 17 與 compileSdk 36 驗證最小結構。"
    elif config.domain == "ssd-pcie-fw":
        sources = """- 產品核准的 PCI-SIG／NVMe 規格版本（可能需要會員權限）
- 控制器供應商提供並經核准的資料表與程式設計手冊
- 產品工具鏈與安全啟動規範"""
        notes = "- 不得由公開範例臆測控制器暫存器、管理命令、韌體格式或未公開協定。"
    else:
        sources = "- 待補：此領域的官方或一手來源"
        notes = "- 依 `../ai-dev-platform/docs/domain-adaptation.md` 補齊。"
    return f"""# {config.display_name} 領域規範

本文件只保存 {config.product_type} 專屬規範；跨產品規則由 `../ai-dev-platform/` 維護。

## 已確認來源

{sources}

## 目前限制

{notes}
"""


def github_ci(config: ProductConfig) -> str:
    setup = ""
    if config.domain == "android":
        setup = """
      - uses: actions/setup-java@v5
        with:
          distribution: temurin
          java-version: "17"
      - uses: gradle/actions/setup-gradle@v6
        with:
          gradle-version: "9.4.1"
"""
    return f"""name: product-check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
{setup.rstrip()}
      - name: Build
        run: |
          {config.build_command}
      - name: Test
        run: |
          {config.test_command}
      - name: Lint
        run: |
          {config.lint_command}
"""


def gitlab_ci(config: ProductConfig) -> str:
    return f"""stages: [verify]

verify:
  stage: verify
  script:
    - {json.dumps(config.build_command)}
    - {json.dumps(config.test_command)}
    - {json.dumps(config.lint_command)}
"""


def jenkins_ci(config: ProductConfig) -> str:
    commands = " && ".join(
        command.replace("\\", "\\\\").replace("'", "\\'")
        for command in (config.build_command, config.test_command, config.lint_command)
    )
    return f"""pipeline {{
  agent any
  stages {{
    stage('Verify') {{
      steps {{
        sh '{commands}'
      }}
    }}
  }}
}}
"""


def write_ci(product: Path, config: ProductConfig, platform_root: Path) -> None:
    if config.ci == "github-actions":
        write_text(product / ".github" / "workflows" / "check.yml", github_ci(config))
    elif config.ci == "gitlab-ci":
        write_text(product / ".gitlab-ci.yml", gitlab_ci(config))
    elif config.ci == "jenkins":
        write_text(product / "Jenkinsfile", jenkins_ci(config))
    else:
        contract = {
            "schemaVersion": 1,
            "product": config.name,
            "commands": {
                "build": config.build_command,
                "test": config.test_command,
                "lint": config.lint_command,
                "package": config.package_command,
            },
            "artifactPath": config.artifact_path,
            "releaseEvidenceContract": "../ai-dev-platform/distribution/release-evidence.schema.json",
        }
        write_text(product / ".ci" / "internal-ci.json", json.dumps(contract, ensure_ascii=False, indent=2))

    adapters = {
        "github-actions": platform_root
        / "adapters"
        / "ci"
        / "github-actions"
        / "release-evidence.yml.template",
        "gitlab-ci": platform_root
        / "adapters"
        / "ci"
        / "gitlab-ci"
        / "release-evidence.gitlab-ci.yml.template",
        "jenkins": platform_root / "adapters" / "ci" / "jenkins" / "Jenkinsfile.template",
        "internal-ci": platform_root
        / "adapters"
        / "ci"
        / "internal"
        / "release-evidence.contract.json",
    }
    adapter = adapters[config.ci]
    destination = product / ".ci" / "release" / adapter.name
    write_text(destination, render(adapter.read_text(encoding="utf-8"), config))


def release_agents(config: ProductConfig) -> str:
    return f"""# AGENTS.md — {config.display_name} 發行儲存庫

開始任務前先讀取 `../ai-dev-platform/AGENTS.md` 與 `../ai-dev-platform/workflow/release.md`。

## 儲存庫邊界

- 只保存 `release-evidence/*.json`、`release-notes/*.md`、Git tag 與必要的儲存庫管理檔。
- 建置成品只保存在 CI／成品平台；本儲存庫只記錄不可變 URI 與 SHA-256。
- 不得加入產品原始碼、`external/`、第三方 skill、APK、AAB、韌體映像檔、ELF、ZIP 或其他建置成品。
- 本儲存庫使用獨立 `.git` 與 remote，不得和產品開發儲存庫共用 Git 歷史或 origin。
- 若使用 `--no-git` 或需要重建 `.git`，只能連接同名的空白遠端；不得 force push 覆寫既有歷史。
- 變更完成後先執行 `python3 -B ../ai-dev-platform/scripts/verify_release_layout.py .`。
- 正式發布前必須執行 `verify_release_readiness.py`；建置、測試、lint、安全、封裝、簽章、SBOM、SLSA、獨立核准與 tag 均為阻擋條件。
"""


def release_readme(config: ProductConfig) -> str:
    return f"""# {config.display_name} Release

本儲存庫只保存發行中繼資料，不保存產品原始碼或建置成品。

```mermaid
flowchart LR
    A["{config.name}-cicd-platform"] -->|"build、test、scan"| B["CI／成品平台"]
    B -->|"artifact URI／SHA-256<br/>release evidence"| C["{config.name}-release"]
```

## 允許內容

| 內容 | 位置 |
|---|---|
| 發行證據（release evidence） | `release-evidence/<version>.json` |
| Release Note | `release-notes/<version>.md` |
| 發行標記 | Git tag `v<MAJOR>.<MINOR>.<PATCH>` |
| 成品位置與摘要 | 發行證據內的 `artifact.uri`、`artifact.sha256` |

## Git 初始化與 remote

初始化工具預設會建立獨立 `.git`。若使用 `--no-git` 或刻意移除舊的本機 Git 中繼資料，先在 Git 服務建立同名空白遠端，再執行：

```bash
git init -b main
git remote add origin <release-repository-url>
git remote -v
```

遠端若已有 commit，應先 clone 並搬入允許的發行檔案，不得使用 force push 覆寫。

## 驗證

```bash
python3 -B ../ai-dev-platform/scripts/verify_release_layout.py .
python3 -B ../ai-dev-platform/scripts/verify_release_evidence.py release-evidence/<version>.json
# 下載成品／簽章／SBOM／SLSA 證據後，依共用平台 docs/release-evidence.md
# 補齊參數執行 verify_release_readiness.py。
```
"""


def release_gitignore() -> str:
    return """# 發行儲存庫不得保存敏感資料、產品原始碼、skill 或建置成品。
.env
.env.*
*.pem
*.key
*.p12
*.pfx
*.jks
*.keystore
secrets/
credentials/
/.ai/handoffs/
*.log
__pycache__/
external/
src/
app/
build/
dist/
artifacts/
*.apk
*.aab
*.bin
*.elf
*.hex
*.img
*.iso
*.zip
*.tar
*.tgz
*.gz
"""


def populate_product(
    platform_root: Path,
    product: Path,
    config: ProductConfig,
    with_example: bool,
) -> None:
    product.mkdir(parents=True)
    if with_example:
        example_name = "android-app" if config.domain == "android" else "ssd-pcie-fw"
        example = platform_root / "examples" / example_name
        if not example.is_dir():
            raise ValueError(f"找不到範例來源：{example}")
        shutil.copytree(example, product, dirs_exist_ok=True)

    copy_entrypoints(platform_root, product, config)
    write_text(product / "README.md", product_readme(config, with_example))
    write_text(product / ".gitignore", product_gitignore(config))
    write_text(product / "docs" / "architecture.md", architecture_doc(config))
    write_text(product / "docs" / "adr" / "0001-use-shared-ai-dev-platform.md", adr_doc(config))
    write_text(product / "docs" / "domain-standards.md", domain_standards_doc(config))
    metadata = {
        "schemaVersion": 1,
        "product": config.name,
        "displayName": config.display_name,
        "domain": config.domain,
        "ci": config.ci,
        "platform": "../ai-dev-platform",
        "platformVersionPolicy": "always-current",
        "releaseRepository": f"../{config.name}-release",
    }
    write_text(product / ".ai" / "product.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    write_ci(product, config, platform_root)


def populate_release(release: Path, config: ProductConfig) -> None:
    release.mkdir(parents=True)
    write_text(release / "README.md", release_readme(config))
    write_text(release / "AGENTS.md", release_agents(config))
    write_text(
        release / "CLAUDE.md",
        """# CLAUDE.md

@../ai-dev-platform/AGENTS.md
@AGENTS.md
""",
    )
    write_text(
        release / "opencode.json",
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": ["../ai-dev-platform/AGENTS.md", "AGENTS.md"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    write_text(release / ".gitignore", release_gitignore())
    write_text(
        release / "release-evidence" / "README.md",
        "# 發行證據\n\n每個正式版本保存一份 `<version>.json`，格式依平行目錄 `ai-dev-platform/distribution/release-evidence.schema.json`。",
    )
    write_text(
        release / "release-notes" / "README.md",
        "# Release Note\n\n每個正式版本保存一份 `<version>.md`，內容依平行目錄 `ai-dev-platform/templates/release-note.md`。",
    )


def initialize_git_repository(path: Path) -> None:
    result = subprocess.run(
        ["git", "init", "-b", "main", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        fallback = subprocess.run(
            ["git", "init", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if fallback.returncode != 0:
            raise RuntimeError(f"無法初始化 Git 儲存庫：{fallback.stderr.strip()}")


def create_product_workspace(
    platform_root: Path,
    output_root: Path,
    config: ProductConfig,
    *,
    with_example: bool = False,
    initialize_git: bool = True,
) -> tuple[Path, Path]:
    platform_root = platform_root.resolve()
    output_root = output_root.resolve()
    expected_platform = output_root / "ai-dev-platform"
    if platform_root != expected_platform.resolve():
        raise ValueError(f"平台必須位於 {expected_platform}，產品才能固定讀取 Work/ai-dev-platform 目前版本")
    if not (platform_root / "AGENTS.md").is_file():
        raise ValueError(f"找不到平台入口：{platform_root / 'AGENTS.md'}")
    if with_example and config.domain not in DOMAIN_DEFAULTS:
        raise ValueError("generic domain 沒有內建範例")

    product_target = output_root / f"{config.name}-cicd-platform"
    release_target = output_root / f"{config.name}-release"
    existing = [str(path) for path in (product_target, release_target) if path.exists()]
    if existing:
        raise FileExistsError(f"目標已存在，不會覆寫：{', '.join(existing)}")

    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ai-dev-platform-init-", dir=output_root) as temp:
        staging = Path(temp)
        product_staging = staging / product_target.name
        release_staging = staging / release_target.name
        populate_product(platform_root, product_staging, config, with_example)
        populate_release(release_staging, config)
        if initialize_git:
            initialize_git_repository(product_staging)
            initialize_git_repository(release_staging)
        os.replace(product_staging, product_target)
        os.replace(release_staging, release_target)
    return product_target, release_target


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--name", required=True, help="產品識別字，例如 my-android-app")
    result.add_argument("--display-name", help="文件顯示名稱；預設與 --name 相同")
    result.add_argument("--domain", choices=("android", "ssd-pcie-fw", "generic"), required=True)
    result.add_argument("--ci", choices=CI_CHOICES, required=True)
    result.add_argument("--output-root", type=Path, help="Work 目錄；預設為平台目錄的上一層")
    result.add_argument("--with-example", action="store_true", help="加入所選領域的最小驗收範例")
    result.add_argument("--no-git", action="store_true", help="不要執行 git init（只供測試或預覽環境）")
    result.add_argument("--dry-run", action="store_true", help="只顯示預計建立的路徑")
    result.add_argument("--product-type")
    result.add_argument("--target-platform")
    result.add_argument("--language-framework")
    result.add_argument("--build-command")
    result.add_argument("--test-command")
    result.add_argument("--lint-command")
    result.add_argument("--package-command")
    result.add_argument("--artifact-path")
    return result


def main() -> int:
    args = parser().parse_args()
    platform_root = Path(__file__).resolve().parents[1]
    output_root = (args.output_root or platform_root.parent).resolve()
    try:
        config = build_config(args)
        expected_platform = output_root / "ai-dev-platform"
        if platform_root.resolve() != expected_platform.resolve():
            raise ValueError(
                f"目前腳本位於 {platform_root}；正式初始化請從 {expected_platform}/scripts/init_product.py 執行"
            )
        targets = (
            output_root / f"{config.name}-cicd-platform",
            output_root / f"{config.name}-release",
        )
        if args.dry_run:
            if any(path.exists() for path in targets):
                raise FileExistsError("預計建立的產品或發行儲存庫已存在")
            print(f"[OK] platform: {platform_root}")
            for target in targets:
                print(f"[OK] create: {target}")
            return 0
        product, release = create_product_workspace(
            platform_root,
            output_root,
            config,
            with_example=args.with_example,
            initialize_git=not args.no_git,
        )
    except (FileExistsError, OSError, RuntimeError, ValueError) as error:
        print(f"[FAIL] product init: {error}", file=sys.stderr)
        return 1
    print(f"[OK] product: {product}")
    print(f"[OK] release: {release}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
