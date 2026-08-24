#!/usr/bin/env bash
#
# scripts/commit-lint.sh
# 檢查 commit message 是否符合 governance/commit.md 的 Conventional Commits 格式。
# 只檢查 subject line（第一行）；body / footer 不受此規則約束。
# 不檢查長度上限：50 字元是 governance/commit.md 提供的建議，
# 不適合當成會擋 PR 的硬性 CI 規則。
#
# 用法:
#   scripts/commit-lint.sh                  # 檢查 HEAD 的 commit message
#   scripts/commit-lint.sh <commit-sha>      # 檢查指定 commit
#   scripts/commit-lint.sh --range A..B      # 檢查範圍內每個 commit（CI 常用：檢查整個 PR）
#   scripts/commit-lint.sh --file <path>     # 檢查檔案內容作為訊息（例如 git commit-msg hook）
#   scripts/commit-lint.sh --message "..."   # 直接檢查一段文字
#
# exit 0 = 全部通過, exit 1 = 有訊息不符合格式

set -uo pipefail

TYPES="feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
TYPE_SCOPE_RE="^(${TYPES})(\([a-zA-Z0-9._/-]+\))?!?: "

FAIL=0

check_one() {
  local msg="$1" label="$2"
  local subject
  subject="$(printf '%s' "$msg" | head -n1)"

  if [ -z "$subject" ]; then
    echo "  [FAIL] $label: commit message 是空的"
    FAIL=1
    return
  fi

  if ! [[ "$subject" =~ $TYPE_SCOPE_RE ]]; then
    echo "  [FAIL] $label: \"$subject\""
    echo "         開頭需為 <type>(<scope>)?: ，type 為 ${TYPES}（見 governance/commit.md）"
    FAIL=1
    return
  fi

  local rest="${subject#*: }"
  local problems=()
  [ -z "$rest" ] && problems+=("冒號後缺少 subject 內容")
  [[ "$rest" =~ ^[A-Z] ]] && problems+=("subject 不應大寫開頭")
  [[ "$rest" == *. ]] && problems+=("subject 結尾不應有句點")

  if [ "${#problems[@]}" -eq 0 ]; then
    echo "  [OK]   $label: $subject"
  else
    local joined
    joined="$(IFS='; '; echo "${problems[*]}")"
    echo "  [FAIL] $label: \"$subject\" ($joined)"
    FAIL=1
  fi
}

mode="${1:-}"
case "$mode" in
  --file)
    [ -z "${2:-}" ] && { echo "用法: $0 --file <path>" >&2; exit 1; }
    check_one "$(cat "$2")" "$2"
    ;;
  --message)
    [ -z "${2:-}" ] && { echo "用法: $0 --message \"...\"" >&2; exit 1; }
    check_one "$2" "(inline message)"
    ;;
  --range)
    [ -z "${2:-}" ] && { echo "用法: $0 --range A..B" >&2; exit 1; }
    count=0
    while IFS= read -r sha; do
      [ -z "$sha" ] && continue
      check_one "$(git log -1 --format=%B "$sha")" "${sha:0:12}"
      count=$((count + 1))
    done < <(git rev-list "$2")
    if [ "$count" -eq 0 ]; then
      echo "警告: 範圍 $2 沒有任何 commit" >&2
    fi
    ;;
  "")
    check_one "$(git log -1 --format=%B HEAD)" "HEAD"
    ;;
  *)
    check_one "$(git log -1 --format=%B "$mode")" "$mode"
    ;;
esac

if [ "$FAIL" -eq 0 ]; then
  echo "commit-lint: 全部通過"
  exit 0
else
  echo "commit-lint: 有訊息不符合 governance/commit.md 的格式"
  exit 1
fi
