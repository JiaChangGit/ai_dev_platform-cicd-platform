# Governance：發行政策（Release）

> 發行步驟見 `workflow/release.md`；本文件定義強制規則。

## 版本號：Semantic Versioning

`MAJOR.MINOR.PATCH`

- `MAJOR`：破壞性變更（不相容的 API/行為改變）
- `MINOR`：新增功能，向下相容
- `PATCH`：修正 bug，向下相容

## 標籤格式

`v<MAJOR>.<MINOR>.<PATCH>`，例如 `v1.4.0`；預發布版本用 `v1.4.0-rc.1`

## 發行分支

- 正式版一律從 `main`（或對應的 `release/*` 分支）建置，不得從功能分支直接發行
- `release/*` 分支建立後，只接受修 bug 的 cherry-pick，不再合併新功能

## 核准門檻

- 正式發行至少需要 1 位非發行執行者核准
- 涉及使用者資料、金流、安全性的版本，額外要求 `governance/security.md` 中定義的安全檢查通過

## Changelog / Release Note

每次發行必須附 `templates/release-note.md`；不得只用 commit log 替代。

## 還原程序（Rollback）

1. 立即標記該版本為已知有問題（依專案發布通路的機制，例如標記為 pre-release 或下架）
2. 評估是否可前滾（roll-forward，快速修正後發新 patch 版）或必須還原到前一版本
3. 還原後於 release note 補充說明原因與後續版本的修正計畫

本節只涵蓋已發布版本的還原。開發中（尚未進入 `product-release`）的還原情境，見 `governance/agent-discipline.md` 第 3 節。

## 建置成品可追溯性

正式發行的建置成品（artifact）必須可追溯到對應的 commit／tag，並附上符合 `distribution/release-evidence.schema.json` 的發行證據（release evidence）、SHA-256 與軟體物料清單（Software Bill of Materials, SBOM）。該領域無法產生 SBOM 時，須提供等效且完整的相依套件版本快照。缺少任一項，不得推進正式發行（promotion）。

`product-release` 只保存發行證據、Release Note、Git tag、成品 URI／SHA-256 與必要的儲存庫管理檔；產品原始碼、建置成品與第三方 skill 必須留在各自的來源或成品系統。正式發布前必須通過 `scripts/verify_release_readiness.py`；目錄邊界、版本／tag、五項 CI 檢查、實體 SHA-256、可驗證簽章（OpenSSL 或受限制身分的 GitHub artifact attestation）、SBOM、SLSA 來源證明與獨立核准任一缺少都必須阻擋發行。
