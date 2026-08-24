# 如何將平台導入既有專案

本文件供導入既有專案的維護者使用。既有專案已有 commit 歷程、團隊慣例或 CI，不能直接套用 `AGENTS.md` 第 3 節的全新專案流程；應先盤點差異，再逐項導入。

## 跟全新專案的差異

| Bootstrap 步驟 | 全新專案 | 既有專案 |
|---|---|---|
| 建立儲存庫 | `git init` 從零開始 | 儲存庫已存在，**不動既有歷史** |
| 入口檔 | 空白模板直接填 | 先盤點現況再填寫 |
| `domain-standards.md` | 只查外部文件 | 透過訪談確認未文件化的團隊規範 |
| CI | 直接建立 | **疊加**在既有 pipeline 上，不打斷現況 |
| 架構文件 | 設計未來 | 讀取程式碼後記錄實際架構 |
| 治理規則 | 全部直接採用 | 每條規則都標記「採用／調適／暫緩」 |

## Step 0：稽核先於一切

這是既有專案的必要步驟。先以只讀方式盤點下列內容，不進行修改：

- 現有分支策略與規則一致性
- 現有 commit message 格式與 Conventional Commits 的差異
- 現有 CI 驗證項目與 merge 阻擋條件
- 測試覆蓋與維護狀態
- 既有架構文件、ADR 與未文件化的決策

稽核結果決定後續導入範圍。未完成稽核時不得開始改動。

## Step 1：入口檔，內容要反映現況

使用 `templates/product-entrypoint/` 的三個模板，並以 Step 0 稽核結果取代所有佔位符。

```bash
cp ../ai-dev-platform/templates/product-entrypoint/AGENTS.md.template ./AGENTS.md
cp ../ai-dev-platform/templates/product-entrypoint/CLAUDE.md.template ./CLAUDE.md
cp ../ai-dev-platform/templates/product-entrypoint/opencode.json.template ./opencode.json
```

若專案已有貢獻規範，先讀取再決定哪些內容併入新的 `AGENTS.md`。不得用新範本覆蓋現有有效規則。

## Step 2：治理規則逐條做「採用 / 調適 / 暫緩」判斷

`governance/branch.md`、`commit.md`、`review.md`、`security.md` 每一條，針對現有專案的情況判斷三選一，不要整包直接套用：

- **採用**：現有做法一致，或缺少必要的 commit 與 review 規範。
- **調適**：現有慣例合理但與平台預設不同。使用 `templates/adr.md` 記錄保留原因。
- **暫緩**：需要改善，但立即改動的成本或風險過高。記錄為技術債，並排入後續 `workflow/feature.md` 任務。

將三類判斷結果整理成清單，放入 Step 1 建立的 `AGENTS.md`「專案專屬補充規則」。後續維護者與代理工具可由此查詢與平台預設不同的原因。

## Step 3：CI 只加不改，只管未來的 commit

```bash
cp ../ai-dev-platform/scripts/commit-lint.sh scripts/commit-lint.sh
```

以新 CI job 疊加驗證，不修改既有 pipeline job。初期可設為非阻擋，確認結果穩定後再改為 merge 阻擋條件。

`scripts/commit-lint.sh --range` 只檢查 PR 的 `base..head`，也就是該 PR 新增的 commit，不檢查整個儲存庫歷程。既有的不合規 commit message 不受影響，也不得為此改寫共用歷程。詳細規則見 `governance/agent-discipline.md` 第 3 節。

## Step 4：`docs/domain-standards.md` 用訪談方式建立，不只是查外部文件

`docs/domain-adaptation.md` 的查證程序同樣適用。既有專案還須盤點未文件化的團隊慣例：先閱讀程式碼，列出「做法明確但找不到決策原因」的項目，再由維護者確認並寫入 `domain-standards.md`。團隊內規的確認優先於補充一般官方文件。

## Step 5：架構文件用「考古」寫法，不是設計

`templates/architecture.md` 用於記錄現狀：先讀取程式碼，再畫出實際元件與資料流。「已知風險與限制」必須包含盤點過程發現的技術債。

若專案已有 wiki、舊文件或程式碼註解，先讀取再整合。舊文件可能保留當時的設計理由，但必須與現行程式碼比對。

## Step 6：建立發行邊界

若產品尚無發行儲存庫，導入時一併建立獨立的 `<product>-release`，並依 `docs/architecture.md` 的允許清單建立空骨架；不要等到第一次發行才臨時建立。CI adapter 與 release evidence 依 `docs/ci-adapters.md`、`docs/ci-cd-release.md` 疊加到既有 pipeline，不回頭改寫既有 Git 歷史。

## 注意事項

- Step 0 是阻擋條件。未稽核現況就套用規則，可能破壞現有流程或覆蓋團隊規範。
- Step 2 的「調適」是正式選項。若需調適的項目過多，應重新評估導入範圍，可只採用缺少的部分，例如保留既有分支策略，僅採用 `scripts/check.sh` 的驗證邏輯
