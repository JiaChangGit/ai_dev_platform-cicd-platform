# 如何新增一個 workflow

1. 確認這是「跨產品領域通用」的流程，不是單一領域的操作細節（單一領域的內容屬於 `docs/domain-adaptation.md` 指引蒐集的範疇，應放進產品倉庫）
2. 在 `workflow/` 新增 `<name>.md`，建議結構：
   - 一行說明適用情境
   - 有序步驟清單
   - 每個步驟需要遵守的 governance / 需要用到的 template，用行內連結標明
3. 在 `registry/workflow.yaml` 新增對應項目：`doc`、`governance`、`templates`、`suggested_roles`、`handoff_required`、`deliverables`
   - `handoff_required`：`suggested_roles` 有兩個以上角色接力執行時設為 `true`，且 `templates` 必須包含 `templates/task-handoff.md`（`scripts/check.sh` 第 6 項會交叉檢查這一點，漏填不會被 YAML 語法檢查發現）
4. 若這個 workflow 常見的觸發情境值得寫進決策樹，更新 `AGENTS.md` 第 2 節的表格
5. 執行 `scripts/check.sh` 確認參照完整、YAML 語法正確
6. 依一般 PR 流程送審（`workflow/feature.md` 走一次，因為這本身就是對 ai-dev-platform 的一個功能新增）
