# 代理工具如何載入平台規則

Codex 與 opencode 直接讀取根目錄 `AGENTS.md`；Claude Code 透過根目錄 `CLAUDE.md` 的 `@AGENTS.md` 匯入語法載入同一份規則。工具差異見 `docs/tool-compatibility.md`。

## 讀取順序

1. `AGENTS.md`（主要入口，開始任務時優先讀取）
2. 依任務類型查 `registry/workflow.yaml`，取得該讀哪些 `workflow/` 與 `governance/` 文件
3. 需要模板時查 `templates/`
4. 需要決定「這個子任務該用哪個角色/模型」時查 `registry/providers.yaml`
5. 遇到領域相關的不確定性時查 `docs/domain-adaptation.md`，以權威來源驗證，不憑訓練資料印象作答

## Feature 任務範例

1. 使用者說：「幫我加一個匯出 CSV 的功能」
2. 代理人查 `registry/workflow.yaml` → 任務類型 `feature` → 需讀 `workflow/feature.md`，需遵守 `governance/branch.md`、`governance/commit.md`、`governance/review.md`、`governance/documentation.md`，需用 `templates/issue.md`、`templates/pr.md`、`templates/adr.md`
3. 依 `workflow/feature.md` 步驟：先確認驗收標準 → 判斷是否需要 ADR（例如「要不要引入新的 CSV 套件」算架構決策）→ 依 `governance/branch.md` 命名分支 → 實作＋測試 → 依 `governance/commit.md` 寫 commit → 依 `templates/pr.md` 開 PR
4. Android 專案若需確認背景寫檔做法，先查 `docs/domain-adaptation.md` 的 Android 章節，再以官方文件求證

## 多代理人協作時

若使用 `registry/providers.yaml` 定義的多角色分工（例如一個模型負責規劃、一個負責實作、一個負責驗證），且該任務在 `registry/workflow.yaml` 中 `handoff_required: true`：

- 交接時依 `templates/task-handoff.md` 建立實體檔案，記錄設計決策、假設與未解問題。多數 CLI 呼叫無對話狀態，不得只靠對話上下文交接。
- 若角色間對某個決定有分歧，記錄在交接檔案裡，必要時升級給人員裁定（見 `governance/review.md` 的升級機制）
- reviewer 必須符合 `governance/review.md` 的最低獨立性要求，不得在同一個 context 內同時實作與審查。
