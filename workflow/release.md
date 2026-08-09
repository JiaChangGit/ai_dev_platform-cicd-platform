# Workflow：發布流程（Release）

> 版本號規則、核准門檻等**強制規則**見 `governance/release.md`。

## 這個流程橫跨兩個倉庫

標準佈局下，`product-cicd-platform`（原始碼＋CI/CD）與 `product-release`（驗證後封裝發布）是分開的倉庫（見 `AGENTS.md` 第 3 節）。這個 workflow 分兩段：第 1～4 步在 `product-cicd-platform` 進行，第 5 步是兩倉庫的交接點，第 6～8 步在 `product-release` 進行。

## 步驟

1. **凍結範圍（Feature Freeze）**——`product-cicd-platform`
   - 確認此版本要包含哪些已合併的變更，之後只接受修 bug 的 PR

2. **產生變更清單**——`product-cicd-platform`
   - 彙整自上個版本以來的 commit / PR，分類為：新功能、修正、破壞性變更、已知問題

3. **版本號決定**——`product-cicd-platform`
   - 依 `governance/release.md` 的規則（語意化版本）決定版本號

4. **建置與驗證**——`product-cicd-platform`
   - 產生正式建置產物
   - 跑一次完整測試套件與（如適用）`workflow/benchmark.md`，確認沒有回歸
   - 進行 smoke test：核心流程手動或自動快速驗證一次
   - **只有這一步的 CI 全綠，才進入下一步；CI 沒過不得往 `product-release` 交接**

5. **交接到 `product-release`**——邊界
   - 依 `templates/task-handoff.md` 產出交接檔案，內容至少包含：版本號、對應 commit/tag、建置產物位置或下載方式、CI 執行紀錄連結、第 2 步的變更清單
   - 交接檔案隨建置產物一起帶到 `product-release`（例如放進 release 倉庫對應版本的目錄），不要只用口頭或聊天紀錄交接
   - 這一步也是 `governance/review.md` AI reviewer 獨立性要求最該落實的地方：核准「這個版本可以發布」的角色，理想上不是產生建置產物的同一個角色/同一個 context

6. **撰寫 Release Note**——`product-release`
   - 依 `templates/release-note.md`，用使用者看得懂的語言描述，而不是直接貼 commit log
   - 內容基於第 5 步交接檔案裡的變更清單，不要重新翻一次 `product-cicd-platform` 的 commit history

7. **標記與發布**——`product-release`
   - 依 `governance/release.md` 的標籤（tag）格式建立標籤
   - 發佈建置產物到對應通路

8. **發布後**——`product-release`（監控結果若需要修正，回到 `product-cicd-platform` 走 `workflow/bugfix.md`）
   - 監控錯誤回報 / 效能指標一段時間（依專案定義的觀察期）
   - 若發現嚴重問題，依 `governance/release.md` 的回滾（rollback）程序處理
   - 更新內部追蹤（例如：已發布版本清單）
