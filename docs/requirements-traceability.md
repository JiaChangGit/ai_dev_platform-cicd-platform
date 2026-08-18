# 需求與功能追蹤矩陣

本文件把已對齊的需求連到實作與自動驗證，避免文件、腳本與發行流程各自演進後失去同步。

| ID | 需求 | 實作 | 驗證 |
|---|---|---|---|
| R1 | 下載版平台無 `.git`、可安全更新且預設唯讀 | `distribution/manifest.json`、`scripts/package_release.py`、`scripts/install_platform.py` | ZIP 路徑／hash／權限驗證、原子替換與唯讀測試 |
| R2 | 預設離線包只保留真正 skill、授權與必要參考內容；完整 Cookbook 可選裝 | `distribution/manifest.json`、`distribution/optional-packs.json`、`distribution/third-party-notices.json` | 預設打包清單排除完整 Cookbook，選用套件 dry run 覆蓋完整快照 |
| R3 | 產品 CI/CD 與發行儲存庫不複製 skill | `templates/product-entrypoint/`、`scripts/init_product.py` | 初始化測試確認兩個產品儲存庫皆無 `external/` |
| R4 | Codex、Claude Code、opencode 共用規則 | `AGENTS.md` 與 `templates/product-entrypoint/` | 必要入口檔與參照完整性檢查 |
| R5 | 支援 GitHub、GitLab、Jenkins、內部 CI | `adapters/ci/`、`registry/ci-adapters.yaml` | `scripts/validate_ci_adapters.py` 驗證路徑、佔位符、YAML／Jenkins 結構與內部 JSON 契約；實際環境連線由產品驗收 |
| R6 | 每個產品有獨立發行儲存庫 | `workflow/release.md`、`docs/release-evidence.md`、`scripts/init_product.py` | 初始化與發行目錄邊界測試 |
| R7 | 可用 Git 同步多個上游的部分內容 | `scripts/sync.sh`、`docs/how-sync-upstream.md` | subtree 設定與第三方 snapshot 一致性檢查 |
| R8 | 平台使用自我開發模式，維護中規則不影響穩定平台 | `AGENTS.md` 4.1、`.ai/product.json`、`docs/maintainer-mode.md` | `scripts/check.sh` 檢查穩定規則來源；`audit_workspace.py` 檢查平行目錄 |
| R9 | 文件採用台灣繁體中文、補充英文關鍵字，並以圖表呈現跨儲存庫流程 | `docs/terminology.md`、主要入口與發行文件 | `scripts/check.sh` 術語檢查與 Markdown 結構檢查 |
| R10 | 初始化工具同時建立開發與發行 Git 儲存庫 | `scripts/init_product.py`、`docs/product-initialization.md` | 產品初始化單元測試與既有目錄防覆寫測試 |
| R11 | 所有產品永遠讀取 `Work/ai-dev-platform/` 目前版本 | 產品入口範本、`.ai/product.json`、初始化 ADR | 初始化單元測試 + `scripts/audit_workspace.py` 對整個 Work 執行只讀稽核 |
| R12 | 以 Android App 與 SSD PCIe 韌體驗證平台通用性 | `examples/android-app/`、`examples/ssd-pcie-fw/` | GitHub Actions 實際執行 Android build／unit test／lint；韌體本機／CI 編譯／測試／lint／封裝 |
| R13 | 發行儲存庫只保存發行證據、Release Note、tag 與成品 URI／SHA-256，所有準備條件均為阻擋 | `verify_release_layout.py`、`verify_release_evidence.py`、`verify_release_readiness.py` | 邊界拒絕案例、schema v2、真實 Git／tag／OpenSSL／SBOM／SLSA 整合測試 |
| R14 | 第三方 skill 離線內含，產品建置工具不內含 | `distribution/manifest.json`、`registry/skills.yaml`、`docs/consumer-mode.md` | 發行包核對登記 skill／授權；範例建置工具由 CI 環境提供 |
| R15 | 第三方 skill 不重複觸發、不誤用供應商／儲存庫專屬流程 | `registry/skill-routing.yaml`、`docs/skill-governance.md` | `scripts/audit_skills.py` 逐份稽核 62 份 skill，檢查 6 組重疊與 15 個正反觸發案例 |
| R16 | Push 前排除敏感資料、建置成品與個人工具設定 | `.gitignore`、`scripts/pre_push_audit.py` | 掃描 Git 追蹤與未追蹤非忽略檔；本機要求 commit 身分，CI 以明確 `--ci` 模式只略過 runner 身分，仍重跑憑證樣式與 remote 邊界檢查 |

預設 ZIP 由乾淨的 CI／發行工作建立。PR 階段執行清單預演（dry run）與小型 ZIP 回歸測試；完整 Cookbook 選用套件只在發行工作建立。
