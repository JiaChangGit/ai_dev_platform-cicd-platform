# CI 轉接器

本目錄提供各 CI 系統的轉接器（CI adapter）。所有轉接器輸出相同的發行證據契約，但不取代產品自己的建置管線（build pipeline）。

每個產品先從 `registry/ci-adapters.yaml` 選擇轉接器，再依領域設定檔（profile）將建置、測試、靜態檢查、安全檢查與成品上傳指令填入模板。CI 必須產生符合 [`docs/release-evidence.md`](../../docs/release-evidence.md) 的發行證據 JSON，才能交接到該產品的發行儲存庫。
