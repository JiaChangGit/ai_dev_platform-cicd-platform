# Governance：發布政策（Release）

> 發布「怎麼做」見 `workflow/release.md`；本文件定義**強制規則**。

## 版本號：Semantic Versioning

`MAJOR.MINOR.PATCH`

- `MAJOR`：破壞性變更（不相容的 API/行為改變）
- `MINOR`：新增功能，向下相容
- `PATCH`：修正 bug，向下相容

## 標籤格式

`v<MAJOR>.<MINOR>.<PATCH>`，例如 `v1.4.0`；預發布版本用 `v1.4.0-rc.1`

## 發布分支

- 正式版一律從 `main`（或對應的 `release/*` 分支）建置，不得從功能分支直接發布
- `release/*` 分支建立後，只接受修 bug 的 cherry-pick，不再合併新功能

## 核准門檻

- 正式發布需至少 1 位非發布執行者的核准（避免單人未經檢查就發布）
- 涉及使用者資料、金流、安全性的版本，額外要求 `governance/security.md` 中定義的安全檢查通過

## Changelog / Release Note

每次發布必須附 `templates/release-note.md`；不得只用 commit log 替代。

## 回滾程序

1. 立即標記該版本為已知有問題（依專案發布通路的機制，例如標記為 pre-release 或下架）
2. 評估是否可前滾（roll-forward，快速修正後發新 patch 版）或必須回滾到前一版本
3. 回滾後於 release note 補充說明原因與後續版本的修正計畫

這一節只涵蓋**已發布**之後的回滾。開發中（尚未發布到 `product-release`）的回滾情境，包含還沒 commit、還沒 push、已 push 未合併等，見 `governance/agent-discipline.md` 第 3 節的完整決策表。

## 產物可追溯性

正式發布的建置產物需可追溯回對應的 commit / tag；建議附上依賴清單（SBOM）或等效的依賴版本快照，特別是對外分發的產品。
