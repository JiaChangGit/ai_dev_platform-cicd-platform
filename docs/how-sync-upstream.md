# 如何同步上游（git subtree）

## 為什麼用 subtree 不用 submodule

| | git submodule | git subtree（本倉庫採用） |
|---|---|---|
| 內容是否實際進倉庫 | 否，只存指標（commit hash） | 是，檔案實際併入 |
| `git clone` 後內容是否完整 | 否，需額外 `git submodule update --init` | 是，直接就有 |
| 下載 ZIP（GitHub 網頁 / `git archive`） | `external/` 會是空的 | `external/` 是完整內容 |
| 倉庫體積 | 小 | 較大（含第三方歷史或快照） |
| 更新上游 | `git submodule update --remote` | `scripts/sync.sh pull` |

因為需求明確要「能直接下載成壓縮檔」，所以本倉庫選 subtree。

## 加入一個新的第三方倉庫

1. 先把目標倉庫 fork 到自己的 GitHub 帳號/組織（這樣才能之後用 subtree push 貢獻回去，也避免直接依賴他人倉庫的變動）
2. 在 `external/subtrees.yaml` 新增一個項目：

   ```yaml
   - name: <目錄名>
     repo: https://github.com/<你的帳號>/<repo>.git
     branch: main
     prefix: external/<目錄名>
   ```

3. **Commit 這個修改**（git subtree 要求工作目錄乾淨才能執行，這步不能省，`scripts/sync.sh` 會在偵測到未 commit 的變更時直接擋下並提示）：

   ```bash
   git add external/subtrees.yaml
   git commit -m "chore(sync): add <目錄名> subtree config"
   ```

4. 執行：

   ```bash
   scripts/sync.sh add <目錄名>
   ```

   內部等同於：`git subtree add --prefix=external/<目錄名> <repo> <branch> --squash`

## 只同步第三方倉庫的「一部分」

`scripts/sync.sh` 同步的是上游倉庫在某個分支上的**整個檔案樹**。如果只想要上游倉庫裡的某個子資料夾（例如一個大型 skill 集合裡的其中一個 skill），標準做法是先在上游的複本上「切」出只含那個子資料夾歷史的分支，再照一般流程同步那個分支——`external/subtrees.yaml` 與 `scripts/sync.sh` 完全不需要修改，因為對它們來說，一個「切過的分支」跟一般分支沒有差別。

### 首次同步某個子資料夾

以「只要上游 `some-repo` 裡的 `skill-a/`，不要其他東西」為例：

1. Fork `some-repo` 到自己帳號（見上一節），本機另外 clone 一份（跟 ai-dev-platform 分開的資料夾）：

   ```bash
   git clone https://github.com/<你的帳號>/some-repo.git /path/to/some-repo-clone
   cd /path/to/some-repo-clone
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

   結果 `external/skill-a` 只會有 `skill-a/` 原本的內容，`some-repo` 其他資料夾不會進來。

### 之後同步上游更新

**保留住第 1 步的本機 clone**（不要刪掉），下次要抓新的上游變更時：

```bash
cd /path/to/some-repo-clone
git checkout main
git pull upstream main         # 先決定怎麼讓 main 跟到真正的上游，見下方註記
git subtree split --prefix=skill-a -b extract-skill-a
git push origin extract-skill-a
```

回到 `ai-dev-platform` 執行 `scripts/sync.sh pull skill-a` 即可。留著同一份本機 clone 重複使用，`git subtree split` 才能接續上次的切點做增量更新（fast-forward），不用每次都整個重切、也不需要 force push。

> 註：`git pull upstream main` 假設你已經在這個 clone 裡把原始上游加成第二個 remote：`git remote add upstream https://github.com/anthropics/skills.git`（把網址換成實際上游）。這樣你的 fork 落後上游時，才能先同步 fork、再切分支。

### 同時追蹤多個第三方倉庫的多個子資料夾

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

## 拉取上游更新（整個倉庫）

```bash
scripts/sync.sh pull <目錄名>
# 或省略名稱，處理 subtrees.yaml 中所有項目
scripts/sync.sh pull
```

## 把本地修改貢獻回上游

subtree 支援反向推送，但 `scripts/sync.sh` 目前不封裝這個操作（避免誤推），請手動執行：

```bash
git subtree push --prefix=external/<目錄名> <你的 fork 的 repo url> <branch>
```

之後在該第三方倉庫另外開 PR 給原始上游。

## 衝突處理

`--squash` 模式下，pull 若遇到本地對 `external/<目錄名>` 有手動修改、又跟上游變更衝突，行為與一般 `git merge` 衝突相同：手動解決衝突檔案後 `git commit` 完成合併。建議盡量不要手動修改 `external/` 底下的內容，若真的需要客製，優先考慮在自己 fork 上改，再同步下來。

## 移除一個 subtree

```bash
git rm -r external/<目錄名>
git commit -m "chore(sync): remove <目錄名> subtree"
```

並記得從 `external/subtrees.yaml` 移除對應項目。
