# 內部 CI 轉接器

CI 系統不在既有清單內時，依 `internal/release-evidence.contract.json` 實作相同的發行證據欄位。內部平台可透過 webhook、API 或管線步驟（pipeline step）傳遞 JSON；發行儲存庫必須先驗證 commit、成品摘要（artifact digest）與核准紀錄，才能推進正式發行（promotion）。
