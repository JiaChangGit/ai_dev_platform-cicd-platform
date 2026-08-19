# 如何同步上游（git subtree）

本文件只適用於開發下一版平台的 Git 維護儲存庫。下載後的唯讀 `ai-dev-platform/` 已內含預設離線第三方 skill；完整 Cookbook 可由選用套件提供。使用者不需要、也不應執行 `git init`、`scripts/sync.sh add` 或 `pull`。

## 為什麼用 subtree 不用 submodule

| | git submodule | git subtree（本儲存庫採用） |
|---|---|---|
| 內容是否實際進儲存庫 | 否，只存指標（commit hash） | 是，檔案實際併入 |
| `git clone` 後內容是否完整 | 否，需額外 `git submodule update --init` | 是，直接就有 |
| 下載 ZIP（GitHub 網頁 / `git archive`） | `external/` 會是空的 | `external/` 是完整內容 |
| 儲存庫體積 | 小 | 較大（含第三方歷史或快照） |
| 更新上游 | `git submodule update --remote` | `scripts/sync.sh pull` |

因為需求明確要「能直接下載成壓縮檔」，所以本儲存庫選 subtree。

## 加入一個新的第三方儲存庫

1. 先將目標儲存庫 fork 到自己的 GitHub 帳號或組織，之後才能使用 subtree push 回傳貢獻，也能避免上游未預期的變動直接影響平台
2. 在 `external/subtrees.yaml` 新增一個項目：

   ```yaml
   - name: <目錄名>
     repo: https://github.com/<你的帳號>/<repo>.git
     branch: main
     prefix: external/<目錄名>
   ```

3. **Commit 這個修改**（git subtree 要求工作目錄乾淨才能執行，這步不能省，`scripts/sync.sh` 會在偵測到未 commit 的變更時直接擋下並提示）：

   ```bash
   SUBTREE_NAME=example-tools
   git add external/subtrees.yaml
   git commit -m "chore(sync): add ${SUBTREE_NAME} subtree config"
   ```

4. 執行：

   ```bash
   scripts/sync.sh add "$SUBTREE_NAME"
   ```

   內部等同於：`git subtree add --prefix=external/<目錄名> <repo> <branch> --squash`

## 只同步第三方儲存庫的「一部分」

`scripts/sync.sh` 會同步上游儲存庫指定分支的完整檔案樹。只需要其中一個子目錄時，先在上游複本建立只含該子目錄歷程的分支，再依一般流程同步。`external/subtrees.yaml` 與 `scripts/sync.sh` 不需修改。

### 首次同步某個子資料夾

以「只要上游 `some-repo` 裡的 `skill-a/`，不要其他東西」為例：

1. Fork `some-repo` 到自己帳號（見上一節），本機另外 clone 一份（跟 ai-dev-platform 分開的資料夾）：

   ```bash
   read -rp "Fork repository HTTPS URL: " FORK_REPOSITORY_URL
   read -rp "Absolute clone destination: " UPSTREAM_CLONE
   git clone "$FORK_REPOSITORY_URL" "$UPSTREAM_CLONE"
   cd "$UPSTREAM_CLONE"
   ```

2. 切出只含 `skill-a/` 歷史的分支，資料夾本身會變成該分支的根目錄：

   ```bash
   git subtree split --prefix=skill-a -b extract-skill-a
   ```

3. 把這個分支推回你的 fork（這樣 `external/subtrees.yaml` 才有穩定的網址可以指）：

   ```bash
   git push origin extract-skill-a
   ```

4. 回到 `ai-dev-platform`，在 `external/subtrees.yaml` 新增項目，`branch` 指到剛剛切出來的分支，不是上游的 `main`：

   ```yaml
   - name: skill-a
     repo: https://github.com/<你的帳號>/some-repo.git
     branch: extract-skill-a
     prefix: external/skill-a
   ```

5. Commit 這個修改，再執行 `scripts/sync.sh add skill-a`（同上，工作目錄必須乾淨）：

   ```bash
   git add external/subtrees.yaml
   git commit -m "chore(sync): add skill-a subtree config"
   scripts/sync.sh add skill-a
   ```

   完成後，`external/skill-a` 只包含原 `skill-a/` 的內容，不會包含 `some-repo` 的其他目錄。

### 之後同步上游更新

**保留住第 1 步的本機 clone**（不要刪掉），下次要抓新的上游變更時：

```bash
cd "$UPSTREAM_CLONE"
git checkout main
git pull upstream main         # 先決定怎麼讓 main 跟到真正的上游，見下方註記
git subtree split --prefix=skill-a -b extract-skill-a
git push origin extract-skill-a
```

回到 `ai-dev-platform` 執行 `scripts/sync.sh pull skill-a` 即可。留著同一份本機 clone 重複使用，`git subtree split` 才能接續上次的切點做增量更新（fast-forward），不用每次都整個重切、也不需要 force push。

> 註：`git pull upstream main` 假設你已經在這個 clone 裡把原始上游加成第二個 remote。先執行 `read -rp "Upstream repository HTTPS URL: " UPSTREAM_REPOSITORY_URL`，再執行 `git remote add upstream "$UPSTREAM_REPOSITORY_URL"`。這樣 fork 落後上游時，才能先同步 fork、再切分支。

### 同時追蹤多個第三方儲存庫的多個子資料夾

`external/subtrees.yaml` 本來就是清單，重複上面的流程、每個子資料夾各自一個項目即可：

```yaml
subtrees:
  - name: anthropic-skill-docx
    repo: https://github.com/<你的帳號>/skills.git
    branch: extract-docx
    prefix: external/anthropic-skill-docx

  - name: openai-cookbook-rag
    repo: https://github.com/<你的帳號>/openai-cookbook.git
    branch: extract-rag-examples
    prefix: external/openai-cookbook-rag
```

`scripts/sync.sh add`（不帶名稱）會依序處理清單中所有項目；`scripts/sync.sh add <name>` 只處理單一項目。

## 拉取上游更新（整個儲存庫）

```bash
read -rp "Subtree name from external/subtrees.yaml: " SUBTREE_NAME
scripts/sync.sh pull "$SUBTREE_NAME"
# 或省略名稱，處理 subtrees.yaml 中所有項目
scripts/sync.sh pull
```

## 把本地修改貢獻回上游

subtree 支援反向推送，但 `scripts/sync.sh` 目前不封裝這個操作（避免誤推），請手動執行：

```bash
read -rp "Subtree name: " SUBTREE_NAME
read -rp "Fork repository URL: " FORK_REPOSITORY_URL
read -rp "Fork branch: " FORK_BRANCH
git subtree push \
  --prefix="external/${SUBTREE_NAME}" \
  "$FORK_REPOSITORY_URL" \
  "$FORK_BRANCH"
```

之後在該第三方儲存庫另外開 PR 給原始上游。

## 衝突處理

`--squash` 模式下，若 `external/<目錄名>` 的本地修改與上游衝突，處理方式與一般 `git merge` 相同：解決衝突後執行 `git commit`。原則上不直接修改 `external/`；需要客製時，先在自己的 fork 修改，再同步回平台。

## 移除一個 subtree

```bash
read -rp "Subtree name to remove: " SUBTREE_NAME
case "$SUBTREE_NAME" in
  ""|*[!a-z0-9_-]*) echo "Invalid subtree name" >&2; exit 1 ;;
esac
SUBTREE_PATH="external/${SUBTREE_NAME}"
test -d "$SUBTREE_PATH"
git status --short -- "$SUBTREE_PATH"
git rm -r -- "$SUBTREE_PATH"
git commit -m "chore(sync): remove ${SUBTREE_NAME} subtree"
```

並記得從 `external/subtrees.yaml` 移除對應項目。
