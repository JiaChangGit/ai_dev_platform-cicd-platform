# 如何新增一個 template

1. 確認現有 `templates/` 中沒有可以擴充覆蓋這個用途的模板，避免重複
2. 在 `templates/` 新增 `<name>.md`，內容用一個 fenced code block（```markdown ... ```）包住實際可複製使用的模板本體，模板外可加簡短使用說明
3. 保持欄位精簡：每個欄位都要有人真的會填，避免「看起來完整但沒人會用」的空泛欄位
4. 若此模板應該在某個 workflow 中被使用，更新 `registry/workflow.yaml` 對應項目的 `templates` 清單
5. 執行 `scripts/check.sh`
