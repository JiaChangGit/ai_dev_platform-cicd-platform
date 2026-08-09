#!/usr/bin/env bash
#
# scripts/check.sh
# 驗證 ai-dev-platform 倉庫本身的完整性：
#   1. 必要檔案是否存在（含頂層檔案與 product-entrypoint 模板）
#   2. 必要的目錄是否存在
#   3. YAML 檔案語法是否正確（若環境有 python3+yaml 就檢查，沒有就跳過並警告）
#   4. registry/workflow.yaml 內參照的 doc/governance/templates 是否都存在
#   5. 每份 markdown 是否以一級標題 (# ) 開頭
#   6. handoff_required: true 的 workflow 項目，templates 是否有包含 task-handoff.md
#   7. workflow/governance/templates/docs 底下是否有完全沒被引用的孤兒檔案（WARN）
#   8. CHANGELOG.md 是否存在且至少有一個版本條目
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
         templates/product-entrypoint/AGENTS.md.template \
         templates/product-entrypoint/CLAUDE.md.template \
         templates/product-entrypoint/opencode.json.template; do
  if [ -f "$f" ]; then pass "$f 存在"; else fail "$f 缺少"; fi
done

echo "== 2. 目錄存在性 =="
for d in workflow governance registry templates docs scripts external; do
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
  refs="$(grep -Eo '[A-Za-z0-9_-]+/[A-Za-z0-9_-]+\.md' registry/workflow.yaml | sort -u)"
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
done < <(find workflow governance templates docs -name '*.md' -print0 2>/dev/null)

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

echo "=================================="
if [ "$FAIL" -eq 0 ]; then
  echo "檢查完成：全部通過（可能有 WARN，請自行評估）"
  exit 0
else
  echo "檢查完成：有項目 FAIL，請修正後再送出"
  exit 1
fi
