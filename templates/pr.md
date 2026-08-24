# PR 模板

複製以下內容建立新 PR：

```markdown
## 摘要
（這個 PR 做了什麼，一到三句話）

## 關聯 Issue
Closes #

## 變更類型
- [ ] feat 新功能
- [ ] fix 修正
- [ ] docs 文件
- [ ] refactor 重構（不改變行為）
- [ ] perf 效能
- [ ] chore 雜項

## 變更說明
（為什麼這樣改、有什麼取捨；不要只重複 diff）

## 測試方式
（如何驗證這個變更是正確的：新增的測試、手動驗證步驟）

## Checklist
- [ ] 通過既有測試，且新增了對應測試
- [ ] 通過 lint / 靜態分析
- [ ] typecheck、test、build 三段都跑過（`governance/agent-discipline.md` 2.1 節）
- [ ] 對外行為變更已同步更新文件
- [ ] Commit message 符合 `governance/commit.md`（一個邏輯改動一個 commit）
- [ ] 未包含任何密鑰、憑證、內部網址
- [ ] 若為架構層級變更，已附上 ADR

## 工具協作揭露（如適用）
- 使用的開發工具與範圍：
- 人工審查重點：

## 截圖 / Log（如適用）
```
