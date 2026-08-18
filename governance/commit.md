# Governance：Commit 規則

## 格式：Conventional Commits

```
<type>(<scope>): <subject>

<body（選填）>

<footer（選填，例如 Breaking change、關聯 issue、Signed-off-by）>
```

### type

`feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`

### scope

模組或子系統名稱，例如 `(auth)` `(driver/nvme)` `(ui/onboarding)`，跨多個模組時可省略

### subject 規則

- 祈使句、現在式：`add`、不是 `added` 或 `adds`
- 開頭小寫、結尾不加句點
- 50 字元內講清楚「做了什麼」，不是「為什麼」（為什麼放 body）

### body 規則

- 每行建議 72 字元內換行
- 說明「為什麼這樣改」與「有什麼影響」，不要重複 diff 內容

### footer

- 破壞性變更：`BREAKING CHANGE: <說明>`
- 關聯 issue：`Closes #123` / `Refs #123`
- 若專案採用 DCO（常見於 kernel 風格的專案）：`Signed-off-by: Name <email>`

### 破壞性變更的簡寫標記

除了 footer 的 `BREAKING CHANGE:`，也可以在 `type`/`scope` 後面加 `!` 標記同一件事，方便只看一行 log 就發現：`feat(api)!: change response schema`。兩種標記法擇一即可，不必重複寫；`scripts/commit-lint.sh` 兩種都接受。

## 原子性

一個 commit 只做一件事：**這個 commit 需要的說明，能不能用一句不含「而且」「順便」的句子講完**。以下情況要拆成多個 commit：
- 格式化 / 重排版 與 邏輯變更混在一起
- 相依套件升級與功能開發混在一起
- 兩個各自獨立、只是剛好同一輪對話一起做的修正（例如同時修了兩個不相關的 bug）

這條規則被列進每日執行紀律，見 `governance/agent-discipline.md` 1.3 節——原因是它直接決定了之後還原能不能乾淨執行。

## 禁止事項

- 不得提交任何密鑰、憑證、內部網址、個資（見 `governance/security.md`）
- 不得 commit 建置成品（build artifact）或暫存檔，應在 `.gitignore` 排除
- AI 產生的 commit 若包含未經使用者確認的假設，須在 body 中明確標註

## Squash 政策

功能分支合併進 `main` 時，建議 squash 成單一或少數幾個語意完整的 commit；`release/*` 分支的合併保留完整歷史以利追溯。
