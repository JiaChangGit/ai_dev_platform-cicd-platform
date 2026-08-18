# 如何用自動檢查落實規則

本文件供 CI 維護者使用，說明如何將 `governance/*.md` 的規則轉成可阻擋 PR 的自動檢查。文件規則若沒有對應檢查，只能仰賴人工審查，容易產生落差。

## 原則

> 如果違反規則會讓 PR 沒辦法合併，這條規則該接 CI；如果只是「審查者會皺眉頭」的程度，寫在 `governance/` 靠審查把關就好，不必每條都上 CI。

不是所有規則都值得自動化；優先接以下三類：

1. **格式類**：commit message 格式、檔案是否存在、YAML/JSON 語法——規則明確、沒有模糊地帶，最適合自動化
2. **安全類**：機密掃描、相依套件弱點掃描——人工審查最容易漏看的類別
3. **本儲存庫自身的完整性**：`registry/*.yaml` 參照是否斷鏈、模板是否存在——這類錯誤人工審查也很難每次都抓到

## 本儲存庫（ai-dev-platform 自身）的落地方式

本儲存庫已經提供兩個範例 pipeline，兩者做的檢查一致，差別只在跑的平台：

- `.github/workflows/check.yml`（GitHub Actions）
- `.gitlab-ci.yml`（GitLab CI）

兩者都執行：

1. `scripts/check.sh`：驗證本儲存庫的完整性（見該腳本內註解）
2. `scripts/pre_push_audit.py --ci`：在 CI 重跑敏感資料、建置成品、忽略規則與 remote 邊界檢查；CI runner 不建立 commit，因此只略過 `user.name`／`user.email`
3. `scripts/commit-lint.sh`：驗證 commit message 是否符合 `governance/commit.md` 的 Conventional Commits 格式

若你把本儲存庫的 CI 設定原封不動搬去別的平台（例如 Jenkins、內部自架系統），核心邏輯就是這兩個腳本，pipeline 設定檔只是負責「在什麼時機呼叫它們」，重寫 pipeline 設定不需要重寫檢查邏輯本身。

## 產品儲存庫（product-cicd-platform）的落地方式

`ai-dev-platform` 自身的 CI 只驗證這個框架儲存庫的完整性，**不能直接搬進產品儲存庫用**，因為產品儲存庫還需要：

- 實際的 build / test / lint（依語言與平台而定，屬於 `docs/domain-adaptation.md` 範疇，不是本框架能預先寫死的）
- `governance/security.md` 定義的機密掃描、相依套件弱點掃描
- `governance/commit.md` 的格式檢查（`scripts/commit-lint.sh` 可以直接複製過去用，這部分是產品無關的）

建議做法：AI 在 bootstrap 產品儲存庫時（見 `AGENTS.md` 第 3 節），以本儲存庫的兩份範例 pipeline 為起點，保留 `commit-lint` 與「跑一份自我檢查腳本」的結構，把 `scripts/check.sh` 換成產品儲存庫自己的驗證邏輯（build 是否成功、測試是否通過、lint 是否乾淨），並依 `governance/security.md` 加上機密掃描步驟。

## PR / Issue 模板變成強制

`templates/pr.md`、`templates/issue.md` 目前是「複製貼上」的模板，沒有東西強迫使用它。若使用 GitHub，把內容轉成：

- `.github/PULL_REQUEST_TEMPLATE.md`（PR 描述欄會自動帶入）
- `.github/ISSUE_TEMPLATE/*.yml`（開 issue 時會出現表單）

若使用 GitLab，對應轉成 `.gitlab/merge_request_templates/*.md` 與 `.gitlab/issue_templates/*.md`。轉換時保留模板的欄位結構，不需要逐字照抄本儲存庫的措辭。
