# 開發輔助規則

本文件供在平台或產品儲存庫工作的開發工具讀取。使用者操作從 `README.md` 開始；固定術語見 `docs/terminology.md`。

## 1. 平台邊界

`ai-dev-platform` 提供任務流程、審查規則、模板、初始化與發行驗證腳本。它不保存產品原始碼、不內含第三方 Cookbook／skill，也不設定模型、帳號或 Token。

工作區採三個平行目錄：

```text
Work/
├── ai-dev-platform/          唯讀、無 .git 的穩定平台包
├── product-cicd-platform/    產品原始碼、測試與 CI/CD
└── product-release/          Release Note 與發行證據
```

產品入口檔固定讀取 `../ai-dev-platform/AGENTS.md`。不要把平台規則複製進產品，也不要把原始碼或建置成品提交到 release 儲存庫。

## 2. 開始任務

1. 依任務內容在 `registry/workflow.yaml` 選擇 `feature`、`bugfix`、`debug`、`review`、`benchmark`、`release` 或 `documentation`。
2. 只讀取該項目列出的 workflow、governance 與 template，避免載入無關文件。
3. 先確認需求、完成條件、可修改範圍與不可修改範圍。會影響商業邏輯、非公開規格或不可逆操作的缺失資訊，必須詢問使用者。
4. Android、SSD／PCIe 韌體或其他版本敏感內容，依 `docs/domain-adaptation.md` 查官方或一手來源，記錄版本與查詢日期。不得用記憶補寫規格。

## 3. 實作與驗證

- 保持改動小且可追溯；移除失效路徑後，同步移除設定、測試與文件中的引用。
- 程式碼與同輪測試一起完成。修正錯誤時先加入可重現案例。
- 完成前依風險執行型別／語法檢查、測試、建置與安全檢查，並記錄實際指令與結果。
- `handoff_required: true` 的任務使用 `templates/task-handoff.md` 保存交接內容；實作者不得核准自己的 PR。審查門檻見 `governance/review.md`。
- 文件只描述已實作或已實際驗證的行為；無法在線驗證的 GitLab、Jenkins、硬體或商店發布步驟要明列限制。

## 4. 全新產品

先以 dry-run 檢查路徑，再建立產品開發與 release 兩個儲存庫：

```bash
cd ../ai-dev-platform
python3 -B scripts/init_product.py \
  --name sample-product \
  --domain generic \
  --ci github-actions \
  --dry-run
```

完整參數、Android／SSD 範例與 GitHub／GitLab 設定見 `docs/getting-started.md`。

## 5. 修改平台本身

`ai_dev_platform-cicd-platform` 是候選來源；`../ai-dev-platform/` 是目前穩定規則（self-hosting stable policy）。修改平台時：

1. 先讀穩定包的 `AGENTS.md`，再把來源儲存庫內容視為下一版候選。
2. 更新相關 registry、文件、測試與 `CHANGELOG.md`。
3. 執行 `bash scripts/check.sh`、完整 unittest、範例建置及發行包 dry-run。
4. 透過功能分支與 PR 合併；不得直接推送受保護的 `main`。
5. 候選包通過 release 流程並安裝後，才成為共用穩定版本。維護步驟見 `docs/maintainer-mode.md`。

## 6. 安全與版本規則

- 不提交憑證、私鑰、session、內部網址或未獲准公開的規格內容；通報方式見 `SECURITY.md`。
- GitHub Actions 必須以完整 commit SHA 固定第三方 action；相依版本由 Dependabot PR 更新並重新驗證。
- 公開歷史中的 Gmail／hostname 不視為本專案阻擋項；憑證、Token 或客戶資料仍必須立即撤銷並依 `governance/security.md` 處理。
- commit、分支、PR、文件與發行規則分別以 `governance/` 對應文件為準。
