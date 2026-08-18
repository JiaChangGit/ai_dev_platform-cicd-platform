# Workflow：新功能開發（Feature）

> 本文件說明「怎麼做」。強制規則（分支命名、審查人數等）見對應的 `governance/*.md`。

> 本任務在 `registry/workflow.yaml` 中標記 `handoff_required: true`：角色交接時依 `templates/task-handoff.md` 產出交接檔案，不要只靠對話上下文交接（見 `AGENTS.md` 2.1 節）。

## 適用情境
新增一個先前不存在的能力，且不是修 bug。

## 步驟

1. **需求釐清**
   - 用一句話寫出「使用者故事」：作為 X，我想要 Y，以便 Z
   - 列出驗收標準（Acceptance Criteria），寫成可勾選的清單
   - 若需求描述中有「業務邏輯」相關的模糊點，向使用者確認，不要自行假設
   - 若模糊的不只是業務邏輯、連設計/用詞本身都還沒共識，且已安裝 grill-with-docs，用它取代純對話式確認；判斷依據與安裝方式見 `docs/external-frameworks.md`

2. **設計**
   - 評估是否為架構層級的決定（新增外部相依性、改變資料流、影響多個模組）
   - 若是，先寫 ADR（`templates/adr.md`），列出至少一個替代方案與取捨
   - 若這個功能大到本質上是新增一個模組/子系統（而不是在既有模組內擴充能力），同步更新 `docs/architecture.md`（依 `templates/architecture.md` 的結構）；一般規模的功能不需要為此新開架構文件
   - 規模達到上一點的等級、且已安裝 OpenSpec 時，改用它的 change 生命週期（propose → apply → archive）取代這裡臨場起草 ADR 的流程；兩者何時並存見 `docs/external-frameworks.md`
   - 若牽涉領域專屬慣例（例如 kernel 的鎖策略、Android 的生命週期），先查 `docs/domain-adaptation.md` 指引的來源

3. **建立分支**
   - 依 `governance/branch.md` 命名

4. **實作**
   - 小步提交，每個 commit 保持可編譯 / 可測試的狀態
   - 新程式碼需附對應測試（單元測試優先，必要時補整合測試）
   - 遇到跟需求不符或技術上做不到的地方，立刻回報，不要默默改需求

5. **收尾三層驗證**（見 `governance/agent-discipline.md` 第 2 節，三層都要過，不能只做其中一層）
   - 第一層：typecheck / 靜態分析 → test → build，依序跑，任一段沒過就還沒完成
   - 第二層：找獨立的 reviewer 過一次，符合 `governance/review.md` 的最低獨立性要求
   - 第三層：這次改動引用到的版本號、套件名、API 用法，自己去官方來源對一次
   - 對照第 1 步的驗收標準逐項打勾

6. **文件更新**
   - 若新增了對外行為（API、CLI 參數、UI），同一個 PR 內更新對應文件（見 `workflow/documentation.md`）

7. **建立 PR**
   - 依 `templates/pr.md` 填寫
   - 標明是否為 AI 產出、AI 的角色是哪個（對照 `registry/providers.yaml`）

8. **審查與合併**
   - 依 `workflow/review.md` 走審查流程，依 `governance/review.md` 判斷是否符合合併門檻

9. **收尾**
   - 若此功能會出現在下一個版本的 release note，先在 `templates/release-note.md` 草稿中補一行
