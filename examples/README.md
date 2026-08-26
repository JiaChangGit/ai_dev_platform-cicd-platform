# 跨領域驗收範例

本目錄保存三個最小產品範例，用來驗證 `ai-dev-platform` 不依賴單一產品領域。它們是測試 fixture，不是正式產品，也不包含未公開的硬體規格。

| 範例 | 驗證重點 | 本機驗證 |
|---|---|---|
| `android-app/` | Kotlin、Gradle、Android App 目錄與 CI 指令 | 結構測試；完整 Android build 由 GitHub Actions 執行 |
| `ssd-pcie-fw/` | C11、Make、host unit test、韌體成品流程 | `make all test lint package` |
| `spec-notes/` | 虛構規格、來源 revision、需求追溯與離線靜態 HTML | `python3 -B validate.py` |

初始化實際產品時，從解壓後的 `Work/ai-dev-platform/` 執行：

```bash
python3 scripts/init_product.py \
  --name sample-product \
  --domain android \
  --ci github-actions \
  --with-example
```

初始化工具會在 `Work/` 建立 `sample-product-cicd-platform/` 與 `sample-product-release/`。範例原始碼只會進入開發儲存庫。
