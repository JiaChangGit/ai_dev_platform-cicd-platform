# GitHub Actions 轉接器

將 `github-actions/release-evidence.yml.template` 複製到產品的 `.github/workflows/`，再把所有 `<...>` 佔位符替換為產品指令與建置成品（artifact）儲存位置。發行證據須包含 GitHub Actions 執行網址（run URL）與 `GITHUB_SHA`。
