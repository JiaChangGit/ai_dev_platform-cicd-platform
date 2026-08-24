# 領域知識蒐集指引（Domain Adaptation）

## 為什麼這份文件存在

`ai-dev-platform` 核心維持產品無關，同一套 workflow／governance 可套用到 Android App、Linux kernel 或其他領域。實作產品程式碼時，開發者仍須取得該領域的具體知識，例如 Android 生命週期或 kernel 鎖定策略。

這份文件**不提供**這些具體知識本身，而是列出查證順序與權威來源。查到的結果應整理進**產品儲存庫**自己的 `docs/domain-standards.md`，附上來源連結，不要回寫進 `ai-dev-platform`。

## 通用原則

1. 優先引用官方 / 一手來源（vendor 文件、標準規格、原始碼本身），其次才是社群文章
2. 記錄來源與查詢日期，因為這類資訊會隨版本更新而改變
3. 遇到內部專屬慣例（公司內部規範、非公開的產品決策），停下來問使用者，不要用公開資料庫的通例取代
4. 同一份 domain-standards.md 內，若不同來源有衝突，明確標註衝突並選擇較新 / 較權威的來源，而不是靜默選一個

這份文件講的是**專案剛開始、或改版時**要查一次的領域慣例。**每次寫程式碼**引用到具體版本號、套件名、API 用法時的即時查證，是另一條每日執行紀律，見 `governance/agent-discipline.md` 2.3 節——兩者都遵守「優先信任官方來源」，差別只在查證的時機與頻率。

## `domain-standards.md` 是活文件

第一次 bootstrap 產品儲存庫時查到的資料，不代表之後就不用再查。`product-cicd-platform/docs/domain-standards.md` 應該被當成活文件持續維護：

- 每次因為「不確定領域慣例」而重新查證時，若結果跟文件裡已記錄的不同（例如官方指南改版、框架升級後慣例改變），直接更新該文件，並更新查詢日期，不要另外開一份新文件
- 若專案實際踩到文件沒涵蓋的情況，查完之後補進去，讓文件隨專案實際遇到的問題增長，而不是一開始就想寫成一份完整清單
- 若查證後仍找不到來源（會員制規範、團隊內規或需由人員裁定的商業決策），不得自行補寫；依 `governance/agent-discipline.md` 2.3 節處理
- 不要因為文件已經存在就跳過查證直接套用——先確認文件裡的查詢日期是否還合理，版本敏感的內容（API 行為、政策）優先重新查證

## 已知領域的建議來源

### Android App 開發
- Android Developers 官方文件（developer.android.com）：API 行為、生命週期、Jetpack 函式庫
- Android Open Source Project 原始碼與風格指南（source.android.com）
- Material Design 規範（m3.material.io）：UI/UX 慣例
- Google Play 政策中心：上架與內容規範
- Kotlin 官方風格指南（kotlinlang.org 的 coding conventions）

### Linux Kernel 開發
- `Documentation/process/` 目錄（特別是 `coding-style.rst`、`submitting-patches.rst`）
- Linux Kernel Mailing List 封存（lore.kernel.org）：了解特定子系統的慣例與近期討論
- `scripts/checkpatch.pl` 規則（隨 kernel 原始碼附帶）
- 原始碼交叉索引（elixir.bootlin.com）：查特定 API/巨集的實際用法
- `MAINTAINERS` 檔案：找對應子系統的負責人與提交慣例

### Web 前端
- MDN Web Docs（developer.mozilla.org）：Web 標準 API
- 所用框架的官方文件（版本要對齊實際使用版本，注意主要版本間的破壞性差異）
- WCAG（無障礙規範）

### 嵌入式韌體
- 所用 RTOS 的官方文件（例如 Zephyr、FreeRTOS）
- 晶片廠商提供的 SDK / Reference Manual（通常需要對應到確切型號）
- 若專案要求 MISRA C 等編碼規範，注意這類規範通常需要授權取得完整條文，只能引用可公開取得的摘要
- 儲存裝置韌體（SSD controller / NVMe）：NVMe 規範（nvmexpress.org）、PCIe 規範（pcisig.com，需會員資格才能取得完整條文，這是 `governance/agent-discipline.md` 2.3 節「查不到來源的時候」實際會遇到的情境，只能引用可公開取得的摘要）、NAND flash 相關標準（jedec.org）

### 後端 / 雲端服務
- 對應雲端供應商的 Well-Architected / 最佳實踐文件
- OWASP（owasp.org）：常見安全風險與防範

## 遇到未列出的領域

1. 先搜尋該領域是否有廣泛採用的官方風格指南或標準規範文件
2. 找該領域最活躍的原始碼儲存庫，觀察其實際慣例（但需註明這是「觀察慣例」而非「官方規定」）
3. 把找到的來源與整理結果記錄進產品儲存庫的 `docs/domain-standards.md`，並在 `AGENTS.md`（產品儲存庫自己的版本，若有）中補上指向該文件的提示
