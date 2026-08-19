# Changelog

本檔案記錄 `ai-dev-platform` 框架本身的版本演進。產品不鎖定平台版本，維護者可用此處了解目前平台內容的變更。

格式參考 [Keep a Changelog](https://keepachangelog.com/)，版本號採語意化版本（見 `governance/release.md`）。

## [1.3.0]

- 新增各 repository 可獨立執行的 collaborator 管理腳本，同步 GitHub／GitLab CODEOWNERS、reviewer、必要 CI 與預設分支保護；管理 Token 不進入 CI 或 Git 歷史
- 修正平台安裝器誤用維護儲存庫檢查的問題；發行包改用 consumer mode，並在檢查失敗時保留舊版與顯示具體原因

## [1.2.0]

- 精簡預設離線包，只保留可直接載入的第三方 skill、授權與必要參考內容；完整 OpenAI Cookbook 改為選用套件
- 新增安全、保留執行權限且預設唯讀的平台安裝／更新工具
- 新增 Work 工作區稽核，檢查產品儲存庫是否固定讀取共用平台目前版本
- 發行關卡改為嚴格驗證：必要 CI 檢查、SBOM、SLSA 來源證明、簽章、獨立核准、版本與 tag 不一致均阻擋發行
- 新增 CI 轉接器契約驗證，並修正內部 CI 輸出格式
- 新增第三方 skill 治理與自動稽核：排除範本／實驗內容、仲裁重疊功能，並以正反案例驗證觸發條件
- 新增推送前敏感資料稽核、GitHub 協作設定與發佈指南，避免把憑證、建置成品或本機 AI 工作狀態提交到 Git
- 修正 CI runner 沒有 `user.name`／`user.email` 時的誤判；新增明確 `--ci` 模式，並同步 GitHub Actions、GitLab CI 與發行儲存庫重建指引

## [1.1.0]

- 區分唯讀平台包與 Git 維護儲存庫，不再要求下載版初始化 Git
- 新增完整離線 ZIP、逐檔 SHA-256、授權證據與發行包驗證
- 新增 GitHub Actions、GitLab CI、Jenkins、內部 CI 的發行證據轉接器，以及 Android／嵌入式韌體設定檔
- 新增產品初始化工具，同時建立開發與發行 Git 儲存庫，固定讀取共用平台目前版本
- 新增最小 Android App 與 SSD PCIe 韌體範例，驗證跨領域建置、測試與封裝流程
- 限制發行儲存庫只保存發行證據、Release Note、Git tag 與成品 URI／SHA-256
- 明確界定只有第三方 skill 必須完整離線內含；產品建置工具由本機或 CI 環境提供
- 修正 ZIP 頂層目錄、第三方目錄驗證、未 commit 工作目錄發行、發行／SBOM 契約與過時文件參照
- 統一台灣繁體中文術語，補充英文關鍵字，並為主要跨儲存庫流程加入 Mermaid 圖

## [1.0.0]

首次公開版本。

涵蓋範圍：
- 三儲存庫協作模型（`ai-dev-platform` / `product-cicd-platform` / `product-release`），適用於任意 product 領域
- Codex CLI、Claude Code、opencode 三工具的入口檔與相容性設計
- `workflow/`（任務流程）與 `governance/`（治理規則）的分工架構
- `registry/` 機器可讀索引（AI 供應商、workflow、skill、外部框架）
- `external/` 的 git subtree 同步機制，含完整儲存庫與子資料夾兩種同步方式
- 三個選用的外部框架整合：OpenSpec（規格管理）、superpowers（執行紀律）、grill-with-docs（語意對齊），詳見 `docs/external-frameworks.md`
- 既有專案導入指南、跨儲存庫規則落地機制、領域知識查證流程
