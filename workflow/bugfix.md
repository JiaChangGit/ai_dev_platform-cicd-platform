# Workflow：Bug 修復（Bugfix）

## 適用情境
既有行為與預期不符，需要修正。

> 本任務在 `registry/workflow.yaml` 中標記 `handoff_required: true`：角色交接時依 `templates/task-handoff.md` 產出交接檔案，不要只靠對話上下文交接（見 `AGENTS.md` 2.1 節）。

## 步驟

1. **重現**
   - 取得最小可重現步驟（Minimal Reproducible Example）
   - 記錄環境資訊（版本、平台、輸入資料）
   - 若無法重現，先把「如何嘗試重現、結果如何」寫清楚再回報，不要臆測根因

2. **寫失敗測試（Regression Test First）**
   - 在動手修之前，先寫一個目前會失敗、修好後應該通過的測試
   - 這個測試之後會留在測試套件中防止回歸

3. **根因分析**
   - 用 `workflow/debug.md` 的方法找出根因，而不是只治標
   - 區分「症狀」與「根因」，在 PR 描述中都寫出來

4. **修正**
   - 改動範圍越小越好，避免夾帶不相關的重構（如需要大重構，另開 issue/PR）

5. **收尾三層驗證**（見 `governance/agent-discipline.md` 第 2 節）
   - 第一層：第 2 步的測試應轉為通過，typecheck → test → build 依序跑過
   - 若是效能敏感區域的修正，額外跑一次 `workflow/benchmark.md`
   - 第二層：找獨立的 reviewer 過一次（`governance/review.md`）
   - 第三層：修正過程中引用到的版本號、套件名、API 用法，自己對照官方來源一次

6. **建立 PR**
   - 依 `templates/pr.md` 填寫，並在描述中連結原始 issue
   - 說明「為什麼原本會壞」與「為什麼這樣修是對的」，不是只有 diff

7. **合併後**
   - 若這是使用者可見的修正，於下個版本的 `templates/release-note.md` 補上一行
   - 若根因具代表性（例如某類 bug 反覆出現），考慮是否要新增 lint 規則或補充 `governance/` 文件避免再犯
