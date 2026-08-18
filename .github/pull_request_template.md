## 摘要

<!-- 一到三句說明改了什麼。 -->

## 關聯 Issue

<!-- 例如 Closes #123；沒有時填 N/A。 -->

## 變更說明

<!-- 說明原因、邊界與取捨，不重複 diff。 -->

## 驗證結果

- [ ] `bash scripts/check.sh`
- [ ] `python3 -B -m unittest discover -s tests -v`
- [ ] `python3 -B scripts/audit_skills.py`
- [ ] `python3 -B scripts/pre_push_audit.py`
- [ ] typecheck／test／build 均完成

## 發行與安全檢查

- [ ] 沒有金鑰、憑證、Token、個資或內部網址
- [ ] 沒有建置成品、`dist/`、快取或個人工具設定
- [ ] 第三方內容的來源、snapshot 與授權證據已同步
- [ ] 對外行為、schema 或 CLI 變更已更新文件

## AI 協作揭露

- 是否使用 AI：
- 工具／模型：
- 人工審查重點：
