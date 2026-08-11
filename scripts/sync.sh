#!/usr/bin/env bash
#
# scripts/sync.sh
# 依 external/subtrees.yaml 的設定，透過 git subtree 同步第三方倉庫。
#
# 用法:
#   scripts/sync.sh add   [name]     # 第一次加入 subtree（省略 name 則處理全部）
#   scripts/sync.sh pull  [name]     # 拉取上游更新（省略 name 則處理全部）
#   scripts/sync.sh list             # 列出目前設定的 subtree
#
# 注意: 這是針對 external/subtrees.yaml 固定格式（name/repo/branch/prefix）寫的
# 輕量解析器，不是通用 YAML parser；請勿在該檔案中使用複雜的 YAML 語法
# （例如多層巢狀、行內 flow-style 等）。
#
# 注意: add/pull 執行前會先檢查是否在 git 倉庫內、且工作目錄乾淨——這是
# git subtree 指令本身的硬性要求，不是本腳本額外加的限制。最常見的觸發情境
# 是剛編輯完 external/subtrees.yaml 但還沒 commit；請先 commit 該修改再執行
# 本腳本（docs/how-sync-upstream.md 的步驟已包含這一步）。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${SUBTREES_CONFIG:-$ROOT_DIR/external/subtrees.yaml}"

if [ ! -f "$CONFIG" ]; then
  echo "找不到設定檔: $CONFIG" >&2
  exit 1
fi

cmd="${1:-}"
target="${2:-}"

if [ -z "$cmd" ]; then
  echo "用法: $0 {add|pull|list} [name]" >&2
  exit 1
fi

# git subtree add/pull 要求：(1) 必須在 git 倉庫內執行 (2) 工作目錄必須乾淨（無
# 未 commit 的變更），否則會在跑到一半時失敗，留下「PENDING.md 已移除但新內容
# 沒進來」之類不上不下的狀態。這裡在做任何事之前先擋下來，給出明確的修正步驟，
# 而不是讓使用者在操作到一半時才看到 git 底層丟出的錯誤。
if [ "$cmd" = "add" ] || [ "$cmd" = "pull" ]; then
  if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[錯誤] $ROOT_DIR 不是一個 git 倉庫。" >&2
    echo "       git subtree 必須在 git 倉庫內執行。若你是用「Download ZIP」" >&2
    echo "       取得本倉庫但沒有 .git，請先執行 git init 並建立至少一個 commit。" >&2
    exit 1
  fi
  if [ -n "$(git -C "$ROOT_DIR" status --porcelain)" ]; then
    echo "[錯誤] 工作目錄有未 commit 的變更，git subtree 需要乾淨的工作目錄才能執行。" >&2
    echo "       最常見的原因：剛編輯完 external/subtrees.yaml 但還沒 commit。" >&2
    echo "       請先執行：" >&2
    echo "         git add external/subtrees.yaml" >&2
    echo "         git commit -m \"chore(sync): update subtrees.yaml\"" >&2
    echo "       再重新執行本指令。" >&2
    exit 1
  fi
fi

declare -a NAMES=()
declare -a REPOS=()
declare -a BRANCHES=()
declare -a PREFIXES=()

# 解析策略：優先用 yq（mikefarah/yq，Go 版本）做正規 YAML 解析；
# 偵測不到就退回下面針對固定格式（name/repo/branch/prefix）手寫的輕量解析器。
# 手寫解析器永遠存在、永遠可用，是這支腳本不依賴外部工具也能動的保底路徑；
# 設 FORCE_FALLBACK_PARSER=1 可以強制略過 yq、直接用手寫解析器（除錯用）。
USE_YQ=0
if [ "${FORCE_FALLBACK_PARSER:-0}" != "1" ] && command -v yq >/dev/null 2>&1; then
  if yq --version 2>&1 | grep -qi "mikefarah"; then
    USE_YQ=1
  fi
fi

parse_config_yq() {
  local n i
  n="$(yq '.subtrees | length' "$CONFIG")"
  for ((i = 0; i < n; i++)); do
    NAMES+=("$(yq ".subtrees[$i].name" "$CONFIG")")
    REPOS+=("$(yq ".subtrees[$i].repo" "$CONFIG")")
    BRANCHES+=("$(yq ".subtrees[$i].branch" "$CONFIG")")
    PREFIXES+=("$(yq ".subtrees[$i].prefix" "$CONFIG")")
  done
}

parse_config_fallback() {
  local name="" repo="" branch="" prefix=""
  while IFS= read -r line; do
    case "$line" in
      *"- name:"*)
        if [ -n "$name" ]; then
          NAMES+=("$name"); REPOS+=("$repo"); BRANCHES+=("$branch"); PREFIXES+=("$prefix")
        fi
        name="$(echo "$line" | sed -E 's/^[^:]*name:[[:space:]]*//')"
        repo=""; branch=""; prefix=""
        ;;
      *"repo:"*)
        repo="$(echo "$line" | sed -E 's/^[^:]*repo:[[:space:]]*//')"
        ;;
      *"branch:"*)
        branch="$(echo "$line" | sed -E 's/^[^:]*branch:[[:space:]]*//')"
        ;;
      *"prefix:"*)
        prefix="$(echo "$line" | sed -E 's/^[^:]*prefix:[[:space:]]*//')"
        ;;
    esac
  done < "$CONFIG"
  if [ -n "$name" ]; then
    NAMES+=("$name"); REPOS+=("$repo"); BRANCHES+=("$branch"); PREFIXES+=("$prefix")
  fi
}

parse_config() {
  if [ "$USE_YQ" = "1" ]; then
    parse_config_yq
  else
    parse_config_fallback
  fi
}

parse_config

if [ "$USE_YQ" = "1" ]; then
  echo "[info] 使用 yq 解析 $CONFIG" >&2
else
  echo "[info] 未偵測到 mikefarah/yq，使用內建輕量解析器（見檔頭註解）" >&2
fi

if [ "${#NAMES[@]}" -eq 0 ]; then
  echo "設定檔中沒有任何 subtree 項目: $CONFIG" >&2
  exit 1
fi

run_one() {
  local action="$1" name="$2" repo="$3" branch="$4" prefix="$5"

  case "$repo" in
    *"JiaChangGit"*)
      echo "[skip] $name: 請先在 external/subtrees.yaml 將 repo 換成你自己的 fork URL" >&2
      return 0
      ;;
  esac

  cd "$ROOT_DIR"
  case "$action" in
    add)
      if [ -d "$prefix" ]; then
        contents="$(ls -A "$prefix" 2>/dev/null)"
        if [ -n "$contents" ]; then
          if [ "$contents" = "PENDING.md" ]; then
            # 這是本倉庫自己放的佔位檔（見 external/README.md），代表尚未同步，
            # 不是「已有內容」；git subtree add 要求目標路徑必須全新、且
            # working tree 乾淨，所以要先移除並「commit」掉，不能只是 git rm 到 index 就好。
            echo "[info] $name: 偵測到未同步佔位檔 $prefix/PENDING.md，移除後繼續 add"
            git rm -q "$prefix/PENDING.md"
            git commit -q -m "chore(sync): remove pending placeholder for $prefix before subtree add"
          else
            echo "[skip] $name: $prefix 已有內容，改用 pull"
            return 0
          fi
        fi
      fi
      echo "[add] $name  <-  $repo ($branch) -> $prefix"
      git subtree add --prefix="$prefix" "$repo" "$branch" --squash \
        -m "chore(sync): add $name from $repo@$branch"
      ;;
    pull)
      if [ ! -d "$prefix" ]; then
        echo "[warn] $name: $prefix 不存在，改用 add"
        git subtree add --prefix="$prefix" "$repo" "$branch" --squash \
          -m "chore(sync): add $name from $repo@$branch"
        return 0
      fi
      echo "[pull] $name  <-  $repo ($branch) -> $prefix"
      git subtree pull --prefix="$prefix" "$repo" "$branch" --squash \
        -m "chore(sync): pull $name from $repo@$branch"
      ;;
  esac
}

case "$cmd" in
  list)
    printf '%-24s %-26s %-40s\n' "NAME" "BRANCH" "PREFIX"
    for i in "${!NAMES[@]}"; do
      printf '%-24s %-26s %-40s\n' "${NAMES[$i]}" "${BRANCHES[$i]}" "${PREFIXES[$i]}"
    done
    ;;
  add|pull)
    found=0
    for i in "${!NAMES[@]}"; do
      if [ -z "$target" ] || [ "$target" = "${NAMES[$i]}" ]; then
        run_one "$cmd" "${NAMES[$i]}" "${REPOS[$i]}" "${BRANCHES[$i]}" "${PREFIXES[$i]}"
        found=1
      fi
    done
    if [ "$found" -eq 0 ]; then
      echo "找不到名稱為 '$target' 的 subtree 設定" >&2
      exit 1
    fi
    ;;
  *)
    echo "未知指令: $cmd" >&2
    echo "用法: $0 {add|pull|list} [name]" >&2
    exit 1
    ;;
esac
