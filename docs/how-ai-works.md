# AI 代理人如何使用這個倉庫

> 你是怎麼「進到」這個倉庫的內容的？Codex、opencode 原生讀取根目錄 `AGENTS.md`；Claude Code 透過根目錄 `CLAUDE.md` 的 `@AGENTS.md` 匯入語法。三者最終看到的是同一份內容。細節見 `docs/tool-compatibility.md`。

## 讀取順序

1. `AGENTS.md`（永遠先讀這份，是整個倉庫的入口）
2. 依任務類型查 `registry/workflow.yaml`，取得該讀哪些 `workflow/` 與 `governance/` 文件
3. 需要模板時查 `templates/`
4. 需要決定「這個子任務該用哪個角色/模型」時查 `registry/providers.yaml`
5. 遇到領域相關的不確定性時查 `docs/domain-adaptation.md`，去查權威來源，而不是憑訓練資料裡的印象作答

## 端到端範例：AI 執行一個 feature 任務

1. 使用者說：「幫我加一個匯出 CSV 的功能」
2. 代理人查 `registry/workflow.yaml` → 任務類型 `feature` → 需讀 `workflow/feature.md`，需遵守 `governance/branch.md`、`governance/commit.md`、`governance/review.md`、`governance/documentation.md`，需用 `templates/issue.md`、`templates/pr.md`、`templates/adr.md`
3. 依 `workflow/feature.md` 步驟：先確認驗收標準 → 判斷是否需要 ADR（例如「要不要引入新的 CSV 套件」算架構決策）→ 依 `governance/branch.md` 命名分支 → 實作＋測試 → 依 `governance/commit.md` 寫 commit → 依 `templates/pr.md` 開 PR
4. 若這是 Android 專案，實作過程中發現需要知道「Android 上背景寫檔的建議做法」→ 這是領域知識，查 `docs/domain-adaptation.md` 的 Android 章節，去官方文件求證，不要用猜的

## 多代理人協作時

若使用 `registry/providers.yaml` 定義的多角色分工（例如一個模型負責規劃、一個負責實作、一個負責驗證），且該任務在 `registry/workflow.yaml` 中 `handoff_required: true`：

- 交接時依 `templates/task-handoff.md` 產出實體交接檔案，把上一個角色的產出（設計決策、假設、未解問題）寫下來帶到下一個角色，不要靠對話上下文口頭交接——多數 CLI 呼叫是無狀態的，沒寫下來的東西下一輪就不存在了
- 若角色間對某個決定有分歧，記錄在交接檔案裡，必要時升級給人類裁定（見 `governance/review.md` 的升級機制）
- 若其中一個角色要扮演 reviewer，額外確認符合 `governance/review.md` 的 AI reviewer 最低獨立性要求——不能是同一個 context 順便自己審自己
