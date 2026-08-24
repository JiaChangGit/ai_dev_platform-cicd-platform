# GitHub、GitLab 與公開安全設定

本文件供 repository owner 在不購買 GitHub Pro 或 GitLab Premium 的前提下設定公開專案。介面與方案會改版；以下狀態於 2026-08-24 重新核對。

## 目前已驗證的 GitHub 狀態

兩個 repository 都是 Public：

- `JiaChangGit/ai_dev_platform-cicd-platform`
- `JiaChangGit/ai_dev_platform-release`

兩者的 `main` 都要求 PR、1 位核准者、CODEOWNERS、最後一次 push 的他人核准、必要 CI、linear history，並禁止 force push 與刪除；管理員也受規則約束。`v*` tag 有規則集，只有 owner 可繞過。預設 `GITHUB_TOKEN` 是唯讀且不能核准 PR，Actions 必須以完整 SHA 固定。

來源 repository 的必要檢查是 `self-check`、`android-example`、`analyze-actions`、`analyze-python`；release repository 是 `repository-policy`、`analyze-python`。Secret scanning、push protection、Dependabot security updates 與 private vulnerability reporting 已啟用。Projects 與 Wiki 已關閉。

GitHub 官方確認公開 repository 可在 Free 方案使用 protected branches；artifact attestations 在 Free 方案只提供給公開 repository：

- [Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [Artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)

## GitHub 新 repository 設定清單

1. 建立 Public repository，不勾選 README、`.gitignore` 或 License，避免與本機歷史衝突。
2. 推送功能分支，建立 PR；不要先直接推送 `main`。
3. 在 Settings → Branches／Rulesets 設定 `main` 與 `v*`。
4. 在 Settings → Actions → General 將 workflow permissions 設為 Read repository contents，關閉允許 Actions 核准 PR。
5. 在 Settings → Environments 建立 release environment，限制 `v*` tag、指定 reviewer、啟用 prevent self-review 並禁止管理員繞過。
6. 在 Settings → Code security and analysis 啟用可用的掃描與私密弱點通報。
7. 送一個測試 PR，確認 required checks 名稱與 branch rule 完全一致。

## GitLab Free 鏡像

截至 2026-08-24，GitLab 帳號 `JiaChangGit` 的公開專案清單尚未出現這兩個平台 repository，因此 GitLab 尚未完成。

GitHub 是 canonical source。GitLab Free 的 push mirror 是「GitLab 推到外部」，而外部來源拉進 GitLab的 pull mirroring 需要 Premium／Ultimate；因此免費方案採手動鏡像：[GitLab repository mirroring](https://docs.gitlab.com/user/project/repository/mirror/)、[push mirroring](https://docs.gitlab.com/user/project/repository/mirror/push/)。

1. 在 GitLab 建立兩個空白 Public project，名稱與 GitHub 相同，不初始化 README。
2. 對每個本機 repository 新增不同名稱的 remote：

   ```bash
   git remote add gitlab git@gitlab.com:JiaChangGit/ai_dev_platform-cicd-platform.git
   git push gitlab main
   git push gitlab --tags
   ```

   release repository 改用 `ai_dev_platform-release.git`。

3. Settings → Repository → Branch rules：`main` 的 Allowed to push and merge 設為 No one；Allowed to merge 設為 Maintainers。GitLab Free 支援 protected branches，但強制 merge request approval rules 是 Premium／Ultimate，不能把 CODEOWNERS 檔案誤當成免費方案的強制核准。[GitLab protected branches](https://docs.gitlab.com/user/project/repository/branches/protected/)、[approval rules tier](https://docs.gitlab.com/user/project/merge_requests/approvals/rules/)
4. 保持 `.gitlab-ci.yml` 的 `ENABLE_GITLAB_MAIN_CI` 未設定；這可避免 GitHub 與 GitLab 對同一個 main commit 重複消耗 runner 分鐘。需要驗收 GitLab 時，以 Web 手動 pipeline 或 merge request pipeline 執行。
5. 每次 GitHub `main` 合併或推送正式 tag 後執行：

   ```bash
   git fetch origin --prune --tags
   git switch main
   git pull --ff-only origin main
   git push gitlab main
   git push gitlab --tags
   ```

不要在 GitLab 鏡像直接 commit、merge 或建立不同 tag，否則兩邊會分岔。

## 隱私與機密

Public repository 的 commit、PR、Actions log、attestation 與 Release asset 都可被複製或長期保存。個人 Gmail 與 hostname 已由 owner 明確接受公開，所以本次不重寫歷史；下列資料仍不得公開：

- access token、deploy key 私鑰、cookie、session、雲端憑證；
- 客戶名稱、內部網址、未公開漏洞、裝置金鑰；
- 受 NDA、會員資格或授權條款限制的完整規格。

若憑證曾公開，先撤銷或輪替，再清理目前檔案並私密通報。只新增 `.gitignore` 不能消除既有歷史；是否重寫歷史必須另案評估 clone、tag、PR 與 attestation 的破壞範圍。
