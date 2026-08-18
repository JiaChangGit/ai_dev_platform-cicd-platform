# 貢獻指南

變更發生在 `ai_dev_platform-cicd-platform/` Git 維護儲存庫。不要在無 `.git` 的 `Work/ai-dev-platform/` 直接修改，也不要將發行證據或成品混入本儲存庫。

## 開發流程

1. 從 `main` 建立短期功能分支，命名依 `governance/branch.md`。
2. 依 `AGENTS.md` 選擇 workflow，只修改本次需求範圍。
3. 第三方內容只透過 `scripts/sync.sh` 與 git subtree 同步；不直接改寫上游快照。
4. 提交前執行驗證：

   ```bash
   bash scripts/check.sh
   python3 -B -m unittest discover -s tests -v
   python3 -B scripts/audit_skills.py
   python3 -B scripts/pre_push_audit.py
   python3 -B scripts/package_release.py --dry-run
   ```

5. Commit 依 `governance/commit.md` 使用 Conventional Commits；PR 填寫 `.github/pull_request_template.md`。

## 發行邊界

`dist/`、建置成品、金鑰、憑證、`.env`、個人 AI 工具設定與 `.ai/handoffs/` 不得提交。平台 ZIP 只能由乾淨 commit 或 CI 建立，成品留在 CI／成品平台。
