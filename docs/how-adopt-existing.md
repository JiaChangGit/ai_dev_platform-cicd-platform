# 如何將平台導入既有專案

本文件供導入既有專案的維護者使用。既有專案已有 commit 歷程、團隊慣例或 CI，不能直接套用 `AGENTS.md` 第 3 節的全新專案流程；應先盤點差異，再逐項導入。

## 跟全新專案的差異

| Bootstrap 步驟 | 全新專案 | 既有專案 |
|---|---|---|
| 建立儲存庫 | `git init` 從零開始 | 儲存庫已存在，**不動既有歷史** |
| 入口檔 | 空白模板直接填 | 要先讀懂現況才能填 |
| `domain-standards.md` | 只查外部文件 | 團隊內規要用訪談方式挖出來，外部文件查不到 |
| CI | 直接建立 | **疊加**在既有 pipeline 上，不打斷現況 |
| 架構文件 | 設計未來 | 記錄現狀，AI 要先讀懂程式碼才能寫 |
| 治理規則 | 全部直接採用 | 每條規則要判斷「採用/調適/暫緩」，不整包套用 |

## Step 0：稽核先於一切

這是既有專案的必要步驟。先要求 AI 只讀取儲存庫並回報下列內容，不進行修改：

- 現有分支策略（有沒有明確規則，還是每個人做法不一樣）
- 現有 commit message 習慣（是否已經接近 Conventional Commits，還是完全沒有規範）
- 現有 CI 設定（跑什麼檢查、卡不卡 merge）
- 測試覆蓋率現況、有沒有明顯沒人維護的部分
- 有沒有既有的架構文件、ADR，或者這些決策只存在資深成員的記憶裡

這份稽核結果會直接決定接下來每一步怎麼做，跳過這步等於在不了解現況的情況下開始改動，風險很高。

## Step 1：入口檔，內容要反映現況

一樣用 `templates/product-entrypoint/` 三個模板，但**不要留空白佔位符直接套用**——`既有程式碼庫` 那類欄位要填 Step 0 稽核的摘要，不是「有 / 沒有」這種空泛答案。

```bash
cp ../ai-dev-platform/templates/product-entrypoint/AGENTS.md.template ./AGENTS.md
cp ../ai-dev-platform/templates/product-entrypoint/CLAUDE.md.template ./CLAUDE.md
cp ../ai-dev-platform/templates/product-entrypoint/opencode.json.template ./opencode.json
```

若專案已經有自己的（不管是不是寫得完整的）貢獻規範文件，先讓 AI 讀過，決定哪些內容要併入新的 `AGENTS.md`，不要憑空重寫一份跟現況脫節的。

## Step 2：治理規則逐條做「採用 / 調適 / 暫緩」判斷

`governance/branch.md`、`commit.md`、`review.md`、`security.md` 每一條，針對現有專案的情況判斷三選一，不要整包直接套用：

- **採用**：現有做法剛好一致，或現有做法明顯有問題（例如完全沒有 commit 規範、沒有任何 review 要求）
- **調適**：現有慣例合理但跟框架預設不同（例如團隊 branch 命名習慣不一樣），寫一份 `templates/adr.md` 記錄「保留原因」——不要為了套框架硬改團隊已經穩定運作的習慣，那不是這個框架的目的
- **暫緩**：現有做法問題不小，但改動成本或風險太高（例如牽涉到已經上線的自動化流程），先記錄成技術債，排進之後的 `workflow/feature.md` 任務，不要一次到位硬改

將三類判斷結果整理成清單，放入 Step 1 建立的 `AGENTS.md`「專案專屬補充規則」。後續維護者與 AI 都能查到與平台預設不同的原因。

## Step 3：CI 只加不改，只管未來的 commit

```bash
cp ../ai-dev-platform/scripts/commit-lint.sh scripts/commit-lint.sh
```

用**新增**的 CI job 疊上去，不要動既有 pipeline 的 job；一開始可以先設成非阻斷（只顯示結果不擋 merge），團隊適應一陣子後再改成必過，不要第一天就把既有工作流程卡死。

`scripts/commit-lint.sh --range` 只檢查 PR 的 `base..head`，也就是該 PR 新增的 commit，不檢查整個儲存庫歷程。既有的不合規 commit message 不受影響，也不得為此改寫共用歷程。詳細規則見 `governance/agent-discipline.md` 第 3 節。

## Step 4：`docs/domain-standards.md` 用訪談方式建立，不只是查外部文件

`docs/domain-adaptation.md` 的查證程序同樣適用。既有專案還須盤點未文件化的團隊慣例：AI 先閱讀程式碼，列出「做法明確但找不到決策原因」的項目，再由維護者確認並寫入 `domain-standards.md`。團隊內規的確認優先於補充一般官方文件。

## Step 5：架構文件用「考古」寫法，不是設計

`templates/architecture.md` 照樣用，但填法反過來：不是先設計再寫，是先讓 AI 完整讀過程式碼，畫出**實際的**元件拆解跟資料流，不是理想中應該長怎樣。「已知風險與限制」這欄特別重要，這個過程通常會挖出團隊自己都已經忘記的技術債，值得認真寫。

若專案已經有一些零散的架構筆記（wiki、過期文件、程式碼裡的大段註解），先讓 AI 讀過再動筆整合，不要無視既有的、即使是過時的紀錄——過時的紀錄裡通常還是藏著「當初為什麼這樣設計」的線索。

## Step 6-8

完成現況架構文件後，依全新專案流程評估外部框架。若該產品尚無發行儲存庫，導入時一併建立獨立的 `<product>-release`，並依 `docs/release-evidence.md` 的允許清單建立空骨架；不要等到第一次發行才臨時建立。CI adapter 與 release evidence 依 `docs/ci-adapters.md`、`docs/release-evidence.md` 疊加到既有 pipeline，不回頭改寫既有 Git 歷史。

## 注意事項

- Step 0 不能跳過，這是既有專案風險最高的地方——沒做稽核就直接套規則，最常見的後果是團隊覺得這套框架在「找麻煩」而不是在幫忙
- Step 2 的「調適」是正式選項。若需調適的項目過多，應重新評估導入範圍，可只採用缺少的部分，例如保留既有分支策略，僅採用 `scripts/check.sh` 的驗證邏輯
