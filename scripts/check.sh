#!/usr/bin/env bash
#
# scripts/check.sh
# 驗證 ai-dev-platform 儲存庫本身的完整性：
#   1. 必要檔案是否存在（含頂層檔案與 product-entrypoint 模板）
#   2. 必要的目錄是否存在
#   3. YAML 檔案語法是否正確（若環境有 python3+yaml 就檢查，沒有就跳過並警告）
#   4. registry/workflow.yaml 內參照的 doc/governance/templates 是否都存在
#   5. 每份 markdown 是否以一級標題 (# ) 開頭
#   6. handoff_required: true 的 workflow 項目，templates 是否有包含 task-handoff.md
#   7. workflow/governance/templates/docs 底下是否有完全沒被引用的孤兒檔案（WARN）
#   8. CHANGELOG.md 是否存在且至少有一個版本條目
#   9. 發行包、第三方授權、CI 轉接器與領域設定檔是否有效
#  10. CI 轉接器與領域設定檔參照是否有效
#  11. 專案自有內容是否誤用非台灣繁體術語
#  12. 共用平台、發行邊界與跨領域範例是否符合架構決策
#
# 用法: scripts/check.sh

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FAIL=0
pass() { echo "  [OK]   $1"; }
fail() { echo "  [FAIL] $1"; FAIL=1; }
warn() { echo "  [WARN] $1"; }

echo "== 1. 必要檔案 =="
for f in README.md AGENTS.md CLAUDE.md opencode.json CHANGELOG.md \
         scripts/init_product.py scripts/install_platform.py scripts/audit_workspace.py \
         scripts/audit_skills.py scripts/pre_push_audit.py \
         scripts/package_optional_pack.py scripts/verify_package.py \
         scripts/verify_release_evidence.py scripts/verify_release_layout.py \
         scripts/verify_release_readiness.py scripts/validate_ci_adapters.py \
         scripts/manage_collaborators.py \
         templates/product-entrypoint/AGENTS.md.template \
         templates/product-entrypoint/CLAUDE.md.template \
         templates/product-entrypoint/opencode.json.template; do
  if [ -f "$f" ]; then pass "$f 存在"; else fail "$f 缺少"; fi
done

echo "== 2. 目錄存在性 =="
for d in workflow governance registry templates docs scripts external adapters distribution profiles examples tests; do
  if [ -d "$d" ]; then pass "$d/ 存在"; else fail "$d/ 缺少"; fi
done

echo "== 3. YAML 語法檢查 =="
if python3 -c "import yaml" >/dev/null 2>&1; then
  for y in registry/*.yaml external/*.yaml; do
    [ -f "$y" ] || continue
    if python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$y" >/dev/null 2>&1; then
      pass "$y 語法正確"
    else
      fail "$y YAML 語法錯誤"
    fi
  done
else
  warn "找不到 python3 的 yaml 模組，跳過 YAML 語法檢查（可 pip install pyyaml 後重跑）"
fi

echo "== 4. registry/workflow.yaml 參照完整性 =="
if [ -f registry/workflow.yaml ]; then
  refs="$(grep -Eo '[A-Za-z0-9_./-]+\.(md|json\.template)' registry/workflow.yaml | sort -u)"
  while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    if [ -f "$ref" ]; then
      pass "參照存在: $ref"
    else
      fail "參照的檔案不存在: $ref"
    fi
  done <<< "$refs"
else
  fail "registry/workflow.yaml 缺少"
fi

echo "== 5. Markdown 是否以一級標題開頭 =="
while IFS= read -r -d '' md; do
  first_nonblank="$(grep -m1 -E '.' "$md" || true)"
  if [[ "$first_nonblank" == \#\ * ]]; then
    pass "$md"
  else
    warn "$md 未以 '# 標題' 開頭"
  fi
done < <(find workflow governance templates docs examples -name '*.md' -print0 2>/dev/null)

echo "== 6. handoff_required 項目是否包含 task-handoff.md =="
if python3 -c "import yaml" >/dev/null 2>&1 && [ -f registry/workflow.yaml ]; then
  py_out="$(python3 - <<'PYEOF'
import yaml, sys
d = yaml.safe_load(open("registry/workflow.yaml"))
bad = []
for wf in d.get("workflows", []):
    if wf.get("handoff_required") is True:
        templates = wf.get("templates", []) or []
        if "templates/task-handoff.md" not in templates:
            bad.append(wf.get("id", "?"))
for b in bad:
    print(b)
PYEOF
)"
  if [ -z "$py_out" ]; then
    pass "所有 handoff_required: true 的項目都有引用 templates/task-handoff.md"
  else
    while IFS= read -r id; do
      [ -z "$id" ] && continue
      fail "workflow '$id' 標記 handoff_required: true 但 templates 未包含 templates/task-handoff.md"
    done <<< "$py_out"
  fi
else
  warn "跳過 handoff_required 交叉檢查（缺 python3+yaml 或 registry/workflow.yaml）"
fi

echo "== 7. 孤兒檔案檢查（workflow / governance / templates / docs）=="
# 「孤兒」定義：完整相對路徑（例如 governance/review.md）完全沒有被其他任何
# .md/.yaml 檔案提及。這是啟發式檢查，用 WARN 而非 FAIL——ad hoc 引用（例如
# 在某段散文中提到，而不是登記進 registry/workflow.yaml）也算數，這裡不強求
# 一定要出現在 registry 裡。
#
# 用完整相對路徑比對、不是只比對檔名：workflow/、governance/、templates/、docs/
# 之間有同名檔案（例如 workflow/review.md 與 governance/review.md），只比對
# 檔名會讓其中一個被引用時，另一個也被誤判為「有被引用」。
# --include 篩選器必須放在 -- 前面，放在後面會被當成路徑參數，篩選器整個失效
# 且會誤掃 .git/ 內部二進位物件；--exclude-dir=.git 是雙重保險。
for d in workflow governance templates docs; do
  for f in "$d"/*.md; do
    [ -f "$f" ] || continue
    hits="$(grep -rl --include='*.md' --include='*.yaml' --exclude-dir=.git -- "$f" . 2>/dev/null | grep -v -- "^\./$f$" | wc -l)"
    if [ "$hits" -eq 0 ]; then
      warn "$f 沒有被任何其他檔案引用（孤兒檔案，確認是否遺漏了整合步驟）"
    else
      pass "$f 有被引用（$hits 處）"
    fi
  done
done

echo "== 8. CHANGELOG.md =="
if [ -f CHANGELOG.md ]; then
  if grep -qE '^## \[' CHANGELOG.md; then
    pass "CHANGELOG.md 至少有一個版本條目"
  else
    fail "CHANGELOG.md 存在但找不到 '## [版本]' 格式的條目"
  fi
else
  fail "CHANGELOG.md 缺少"
fi

echo "== 9. distribution / adapter JSON 與檔案參照 =="
if command -v python3 >/dev/null 2>&1; then
  py_out="$(python3 - <<'PYEOF'
import json
from pathlib import Path

errors = []
for path in [
    Path("distribution/manifest.json"),
    Path("distribution/third-party-notices.json"),
    Path("distribution/optional-packs.json"),
    Path("distribution/release-evidence.schema.json"),
    Path("adapters/ci/internal/release-evidence.contract.json"),
    Path("templates/release-evidence.json.template"),
]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON 無法解析: {path}: {exc}")

try:
    manifest = json.loads(Path("distribution/manifest.json").read_text(encoding="utf-8"))
    includes = manifest.get("include", [])
    required_offline = {
        "external/anthropic-skills/THIRD_PARTY_NOTICES.md",
        "external/anthropic-skills/skills",
        "external/mattpocock-skills/LICENSE",
        "external/mattpocock-skills/engineering",
        "external/mattpocock-skills/misc",
        "external/mattpocock-skills/productivity",
        "external/superpowers",
        "external/openai-cookbook/.codex/skills/docs-editor",
        "external/openai-cookbook/examples/evals/realtime_evals/skills/bootstrap-realtime-eval",
        "external/openai-cookbook/LICENSE",
    }
    if missing := sorted(required_offline - set(includes)):
        errors.append(f"distribution manifest 缺少預設離線 skill／授權：{', '.join(missing)}")
    if "external" in includes or "external/openai-cookbook" in includes:
        errors.append("預設發行包不得包含完整 external/ 或 OpenAI Cookbook")
    if any(item == ".git" or item.startswith(".git/") for item in includes):
        errors.append("distribution manifest 不可包含 .git")
    archive_root = manifest.get("archiveRoot")
    if not isinstance(archive_root, str) or not archive_root or "/" in archive_root or archive_root in (".", ".."):
        errors.append("distribution manifest 的 archiveRoot 必須是單一安全目錄名稱")
    for item in includes:
        if not Path(item).exists():
            errors.append(f"distribution manifest 參照不存在: {item}")
except Exception as exc:
    errors.append(f"無法驗證 distribution manifest: {exc}")

try:
    notices = json.loads(Path("distribution/third-party-notices.json").read_text(encoding="utf-8"))
    for entry in notices.get("entries", []):
        for key in ("path", "licenseEvidence", "snapshotTree"):
            if not entry.get(key):
                errors.append(f"第三方項目 {entry.get('id', '?')} 缺少 {key}")
        for key in ("path", "licenseEvidence"):
            value = entry.get(key)
            if value and not Path(value).exists():
                errors.append(f"第三方項目 {entry.get('id', '?')} 參照不存在: {value}")
        packaged_paths = entry.get("packagedPaths")
        if not isinstance(packaged_paths, list) or not packaged_paths:
            errors.append(f"第三方項目 {entry.get('id', '?')} 缺少 packagedPaths")
        else:
            for value in packaged_paths:
                if not isinstance(value, str) or not Path(value).exists():
                    errors.append(f"第三方項目 {entry.get('id', '?')} 打包參照不存在: {value}")

    if Path(".git").exists():
        import subprocess
        for entry in notices.get("entries", []):
            actual = subprocess.check_output(
                ["git", "rev-parse", f"HEAD:{entry['path']}"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if actual != entry.get("snapshotTree"):
                errors.append(f"第三方項目 {entry.get('id', '?')} snapshotTree 與 Git tree 不同步")

    try:
        import yaml
        subtree_items = yaml.safe_load(Path("external/subtrees.yaml").read_text(encoding="utf-8"))["subtrees"]
        subtree_by_name = {item["name"]: item for item in subtree_items}
        for entry in notices.get("entries", []):
            source = subtree_by_name.get(entry.get("id"))
            if not source:
                errors.append(f"第三方項目 {entry.get('id', '?')} 未登記在 external/subtrees.yaml")
                continue
            expected_fields = {"path": source["prefix"], "syncRepository": source["repo"], "branch": source["branch"]}
            for key, expected in expected_fields.items():
                if entry.get(key) != expected:
                    errors.append(f"第三方項目 {entry.get('id', '?')} 的 {key} 與 external/subtrees.yaml 不同步")
    except ImportError:
        pass
except Exception as exc:
    errors.append(f"無法驗證第三方 notices: {exc}")

for error in errors:
    print(error)
PYEOF
)"
  if [ -z "$py_out" ]; then
    pass "distribution manifest、第三方 notices 與 release evidence JSON 有效"
  else
    while IFS= read -r error; do
      [ -z "$error" ] && continue
      fail "$error"
    done <<< "$py_out"
  fi
else
  fail "找不到 python3，無法驗證 distribution 與 release evidence JSON"
fi

echo "== 10. CI 轉接器 / 領域設定檔 registry 參照完整性 =="
for registry in registry/ci-adapters.yaml registry/profiles.yaml; do
  if [ ! -f "$registry" ]; then
    fail "$registry 缺少"
    continue
  fi
  refs="$(grep -Eo '[A-Za-z0-9_./-]+\.(md|ya?ml|json|template)' "$registry" | sort -u)"
  while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    if [ -f "$ref" ]; then
      pass "參照存在: $ref"
    else
      fail "$registry 參照的檔案不存在: $ref"
    fi
  done <<< "$refs"
done

if python3 -B scripts/validate_ci_adapters.py >/dev/null; then
  pass "CI 轉接器佔位符、語法與契約一致"
else
  fail "CI 轉接器契約驗證失敗"
fi

if python3 -c "import yaml" >/dev/null 2>&1; then
  if python3 -B scripts/audit_skills.py >/dev/null; then
    pass "預設離線 skill 結構、路由、重疊與觸發測試一致"
  else
    fail "skill 稽核失敗"
  fi
else
  warn "找不到 PyYAML，跳過維護者 skill 路由稽核"
fi

echo "== 11. 台灣繁體術語 =="
# external/ 保留第三方原文；docs/terminology.md 會列出不建議用詞作為反例。
term_hits="$(grep -RInE \
  --exclude-dir=.git \
  --exclude-dir=external \
  --exclude-dir=dist \
  --exclude-dir=__pycache__ \
  --exclude='terminology.md' \
  --exclude='check.sh' \
  --exclude='*.pyc' \
  '倉庫|回滾|數據|文檔|默認|代碼|構建|插件|信息|軟件|硬件|日志|鏈接|字段|創建|源碼|配置|请|发|为|后|这|个|与|从|进|里|还|将|们' \
  . 2>/dev/null || true)"
if [ -z "$term_hits" ]; then
  pass "專案自有內容未發現列管的非台灣繁體術語"
else
  while IFS= read -r hit; do
    [ -z "$hit" ] && continue
    fail "非台灣繁體術語: $hit"
  done <<< "$term_hits"
fi

echo "== 12. 架構決策與跨領域範例 =="
for obsolete in distribution/core-files.txt scripts/export_core.py docs/how-sync-platform-core.md; do
  if [ -e "$obsolete" ]; then
    fail "舊平台內嵌功能不應存在: $obsolete"
  else
    pass "舊平台內嵌功能已移除: $obsolete"
  fi
done

for f in \
  examples/android-app/app/src/main/AndroidManifest.xml \
  examples/android-app/app/src/test/java/dev/aiplatform/sample/GreetingTest.kt \
  examples/ssd-pcie-fw/Makefile \
  examples/ssd-pcie-fw/tests/test_fw_core.c; do
  if [ -f "$f" ]; then
    pass "跨領域範例存在: $f"
  else
    fail "跨領域範例缺少: $f"
  fi
done

for f in \
  external/anthropic-skills/skills/docx/SKILL.md \
  external/openai-cookbook/.codex/skills/docs-editor/SKILL.md \
  external/openai-cookbook/examples/evals/realtime_evals/skills/bootstrap-realtime-eval/SKILL.md \
  external/mattpocock-skills/engineering/grill-with-docs/SKILL.md \
  external/mattpocock-skills/productivity/grilling/SKILL.md \
  external/mattpocock-skills/engineering/domain-modeling/SKILL.md \
  external/superpowers/using-superpowers/SKILL.md; do
  if [ -f "$f" ]; then
    pass "離線第三方 skill 存在: $f"
  else
    fail "離線第三方 skill 缺少: $f"
  fi
done

pending_skills="$(find external -name PENDING.md -print 2>/dev/null)"
if [ -z "$pending_skills" ]; then
  pass "第三方 skill 無待同步佔位檔"
else
  while IFS= read -r pending; do
    [ -z "$pending" ] && continue
    fail "第三方 skill 尚未完整同步: $pending"
  done <<< "$pending_skills"
fi

if grep -q '../ai-dev-platform/AGENTS.md' templates/product-entrypoint/AGENTS.md.template && \
   grep -q 'always-current' scripts/init_product.py; then
  pass "產品固定讀取共用 ai-dev-platform 目前版本"
else
  fail "產品入口或初始化中繼資料未落實 always-current 政策"
fi

if grep -q 'self-hosting stable policy' AGENTS.md && [ -f .ai/product.json ]; then
  pass "平台自我開發固定讀取穩定 Work/ai-dev-platform"
else
  fail "平台自我開發缺少穩定規則來源"
fi

if grep -q 'verify_release_layout.py' workflow/release.md && \
   grep -q 'verify_release_layout.py' scripts/init_product.py; then
  pass "發行儲存庫邊界已有流程與初始化入口"
else
  fail "發行儲存庫邊界缺少流程或初始化入口"
fi

if python3 -B scripts/manage_collaborators.py check >/dev/null; then
  pass "GitHub／GitLab CODEOWNERS 與 CI 政策檔一致"
else
  fail "collaborator、CODEOWNERS 或 CI 政策檔不同步"
fi

echo "=================================="
if [ "$FAIL" -eq 0 ]; then
  echo "檢查完成：全部通過（可能有 WARN，請自行評估）"
  exit 0
else
  echo "檢查完成：有項目 FAIL，請修正後再送出"
  exit 1
fi
