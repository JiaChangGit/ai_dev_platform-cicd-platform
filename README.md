# ai-dev-platform

一個「產品無關（product-agnostic）」的 AI 輔助開發框架倉庫。

它不寫任何產品的商業邏輯，只回答一個問題：**當 AI 代理人（Codex、Claude Code、opencode、或其他 agent）要幫你蓋一個新專案時，應該遵守什麼流程、什麼規範、用什麼模板？**

三個工具開箱即用，不需要額外設定：Codex 與 opencode 原生讀取根目錄的 `AGENTS.md`；Claude Code 透過根目錄的 `CLAUDE.md`（一行 `@AGENTS.md` 匯入）讀到同一份內容。細節與來源見 [`docs/tool-compatibility.md`](docs/tool-compatibility.md)。

適用範圍刻意做到與領域無關：同一套 `workflow/`、`governance/`、`templates/` 可以拿去指導一個 Android App 專案，也可以拿去指導一個 Linux kernel 模組專案。真正跟領域綁定的知識（例如 Android 的 Material Design 規範、kernel 的 coding-style）**不放在這裡**，而是由 [`docs/domain-adaptation.md`](docs/domain-adaptation.md) 告訴 AI 該去哪裡查、查什麼。

## 這個倉庫解決什麼問題

多數團隊在導入 AI 輔助開發時，會遇到三個重複發生的問題：

1. 每個新專案都要重新跟 AI「教」一次要怎麼開分支、怎麼寫 commit message、PR 要附什麼資訊
2. AI 對「這個任務該用哪個模型/哪個角色來做」沒有一致的判斷依據
3. 想借用別人維護的 prompt / skill 資源，但又不想用 submodule（clone 下來是空的，直接下載 zip 會看不到內容）

`ai-dev-platform` 用三個機制分別解決：

| 問題 | 解法 |
|---|---|
| 流程/規範重複教學 | `workflow/`、`governance/`、`templates/`，由 `AGENTS.md` 統一指揮 |
| 模型/角色分派沒依據 | `registry/providers.yaml`、`registry/workflow.yaml`、`registry/skills.yaml` |
| 借用第三方資源但要能單純下載 zip | `external/` 用 **git subtree**（不是 submodule）同步，內容會實際併入本倉庫 |
| 語意對齊、規格管理、執行紀律要各自重新摸索 | 整合現成的開源框架（grill-with-docs / OpenSpec / superpowers），本倉庫只負責「什麼時候用哪個、怎麼裝」，見 [`docs/external-frameworks.md`](docs/external-frameworks.md) |

## 建議的專案佈局

```
Work/
├── ai-dev-platform/        <- 本倉庫，唯讀參考，跨專案共用
├── product-cicd-platform/  <- 產品原始碼 + CI/CD（開發、build、test 都在這裡）
└── product-release/        <- CI/CD 驗證通過後，封裝與發布的產物
```

三者是**平行的獨立倉庫**，不是彼此的子目錄。`product-cicd-platform` 與 `product-release` 故意分開：前者是頻繁變動的開發現場，後者只接收「已通過驗證」的結果，讓「開發中」與「已發布」的邊界在倉庫層級就切清楚。AI 代理人在開任何產品倉庫的任務前，先讀 `ai-dev-platform/AGENTS.md`，把它當成「跨專案的操作手冊」；兩個產品倉庫間的交接細節寫在 `workflow/release.md`。細節見 [`docs/how-ai-works.md`](docs/how-ai-works.md)。

如果你想讓某個產品倉庫「自帶」這份操作手冊（例如要單獨開源、不能依賴外部平行目錄），可以用 `git subtree` 把 `workflow/`、`governance/`、`templates/` 併進該產品倉庫的 `.ai/` 目錄，做法同樣寫在 `docs/how-sync-upstream.md`。

## 目錄總覽

```
ai-dev-platform/
├── README.md            人類看的總覽（這份文件）
├── LICENSE               本倉庫原創內容的授權（MIT）
├── AGENTS.md             AI 代理人操作手冊（唯一事實來源，優先讀這份）
├── CLAUDE.md             Claude Code 轉接器（@AGENTS.md 匯入）
├── opencode.json         opencode 最小設定檔
├── CHANGELOG.md          框架本身的版本紀錄
├── .github/workflows/、.gitlab-ci.yml   驗證本倉庫 + commit lint 的範例 pipeline
├── external/             git subtree 同步進來的第三方資源
├── workflow/             「怎麼做」：各類任務的標準作業流程
├── governance/           「規則是什麼」：分支/commit/審查/發布/文件/安全政策/執行紀律
├── registry/             AI 供應商、workflow、skill、外部框架的機器可讀索引（YAML）
├── templates/            Issue / PR / ADR / 架構 / benchmark / release note / task-handoff 模板
├── docs/                 關於這個倉庫本身的說明文件
└── scripts/              sync.sh（同步 subtree）、check.sh（自我檢查）、commit-lint.sh
```

各目錄的詳細說明見 [`docs/repository-structure.md`](docs/repository-structure.md)。

## 快速開始

```bash
# 1. 解壓縮後先自己初始化 git（這份 zip 不含 .git，用你自己的帳號/簽名建立第一個 commit）
cd ai-dev-platform
git init
git add -A
git commit -m "chore: initial commit"

# 2. 看一下目前設定了哪些第三方 subtree
scripts/sync.sh list

# 3. 把 external/subtrees.yaml 裡的 repo 換成你自己的 fork
#    （編輯完先 commit ——git subtree 要求工作目錄乾淨才能執行，這步不能省）
git add external/subtrees.yaml
git commit -m "chore(sync): point subtrees at my fork"

# 4. 實際拉進來
scripts/sync.sh add anthropic-skills

# 5. 自我檢查（確認 registry 參照的檔案都存在、YAML 語法正確）
scripts/check.sh
```

## 下載成壓縮檔

因為 `external/` 用的是 **git subtree** 而不是 submodule，第三方內容會被實際複製進本倉庫的檔案樹、寫進 commit history。這代表：

- GitHub 網頁的「Download ZIP」或 `git archive` 匯出的壓縮檔，`external/` 底下會是**完整內容**，不會是空資料夾
- 對方（例如面試官、稽核單位）不需要額外 `git clone` 第三方倉庫就能看到完整程式碼

代價是倉庫體積會變大、且更新第三方內容需要用 `scripts/sync.sh pull`（而不是 submodule 的 `git submodule update`）。取捨說明在 `docs/how-sync-upstream.md`。

## CI 驗證

`.github/workflows/check.yml`、`.gitlab-ci.yml` 兩份範例 pipeline 會在 push / PR 時自動跑 `scripts/check.sh`（倉庫完整性）與 `scripts/commit-lint.sh`（commit message 格式），把 `governance/` 的規則變成真的會擋 PR 的檢查，而不只是文件。套用到產品倉庫時如何調整，見 [`docs/how-enforce-rules.md`](docs/how-enforce-rules.md)。

## 執行紀律

`governance/agent-discipline.md` 是 AI 代理人動手做事時要守的三條每日紀律（測試同輪補完、能委派給專門 skill/sub-agent 就不現場即興、一個邏輯改動一個 commit）、收尾要過的三層驗證（typecheck/test/build、獨立審查、版本與 API 自我核對），以及東西壞掉之後的回滾決策表。`workflow/feature.md`、`workflow/bugfix.md` 的驗證步驟已經照這三層改寫，`AGENTS.md` 的硬性規則也指到這份文件。

## 外部框架整合

語意對齊、規格與變更管理、執行紀律這三件事，分別交給三個持續在維護的外部開源框架（grill-with-docs、OpenSpec、superpowers）處理，都是**選用**，不裝也不影響本倉庫其餘部分的運作。分工判斷、確切安裝指令（含三個工具各自的機制）、離線環境替代方案，見 [`docs/external-frameworks.md`](docs/external-frameworks.md)；機器可讀索引在 `registry/frameworks.yaml`。

## 版本

框架本身的版本演進記錄在 [`CHANGELOG.md`](CHANGELOG.md)。產品倉庫若採內嵌模式（見上）同步了特定版本的 `workflow/`、`governance/`，建議在該倉庫記錄同步時對應的版本號，方便日後回答「這個產品倉庫是照哪一版規則蓋的」。

## 為新專案套用這套框架

不要把產品程式碼放進這個倉庫。正確流程：

1. 建立一個新的、獨立的 `product-cicd-platform` 倉庫，與 `ai-dev-platform` 平行放在 `Work/` 底下——這是實際寫程式碼、跑 CI 的地方
2. 讓 AI 代理人讀 `ai-dev-platform/AGENTS.md`，依照裡面「Bootstrap 一個全新產品倉庫的標準流程」章節執行
3. AI 依 [`docs/domain-adaptation.md`](docs/domain-adaptation.md) 的清單，去蒐集該產品領域（Android / kernel / web / ... ）專屬的規範，寫成 `product-cicd-platform/docs/domain-standards.md`——**這份文件不會進到 `ai-dev-platform`**，因為它是產品專屬的，而且是活文件，會隨專案進展持續更新，不是寫一次就結束
4. 等 `product-cicd-platform` 第一次跑出通過 CI 驗證的版本，準備真正發布時，才建立 `product-release`，依 `workflow/release.md` 處理交接

## 授權與貢獻

本倉庫本身內容（除 `external/` 下由 subtree 帶入的第三方內容外）可自由複製、修改，用於個人或團隊的開發框架。修改前建議先讀 `governance/documentation.md` 了解文件風格要求。
