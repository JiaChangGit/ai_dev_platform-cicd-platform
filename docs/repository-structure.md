# 儲存庫結構說明

## 兩個核心分類：workflow vs governance

本儲存庫將操作流程與強制規則分開，讓兩者可以獨立維護：

- **`workflow/`（怎麼做）**：操作步驟、方法論，較常隨經驗調整
- **`governance/`（規則）**：強制規範、門檻、格式，變動應該更謹慎（改動代表團隊規則改變）

同一主題常常兩邊都有文件，例如 `workflow/review.md`（審查時實際怎麼看）與 `governance/review.md`（幾人核准才能合併）。閱讀時兩份要一起看。

## 目錄總覽

| 目錄/檔案 | 內容 | 是否產品無關 |
|---|---|---|
| `README.md` | 使用者總覽 | — |
| `LICENSE` | 本儲存庫原創內容的授權（`external/` 底下另有各自授權，見該目錄 README） | — |
| `AGENTS.md` | AI 代理人操作手冊（唯一事實來源），執行任務前優先讀 | — |
| `CLAUDE.md` | Claude Code 的轉接器，`@AGENTS.md` 匯入，不重複內容 | — |
| `opencode.json` | opencode 的最小設定檔（opencode 原生讀 `AGENTS.md`，這份非必要但便於未來擴充） | — |
| `CHANGELOG.md` | 框架本身的版本紀錄 | — |
| `.github/workflows/check.yml`、`.gitlab-ci.yml` | 驗證本儲存庫完整性 + commit lint 的範例 pipeline | 是（邏輯是；平台設定需依專案調整） |
| `adapters/` | GitHub Actions、GitLab CI、Jenkins、內部 CI 的發行證據轉接模板 | 是 |
| `distribution/` | 無 Git 離線包清單、第三方授權證據與 release evidence schema | 是 |
| `external/` | git subtree 同步的第三方資源 | 依來源而定 |
| `examples/` | 最小 Android App 與 SSD PCIe 韌體驗收範例，用於證明流程可跨領域套用 | 否（驗收 fixture） |
| `profiles/` | Android、嵌入式韌體（embedded firmware）等領域的 CI 起始檢查清單 | 否（選用） |
| `workflow/` | 各類任務的標準作業流程 | 是 |
| `governance/` | 分支/commit/審查/發布/文件/安全政策/執行紀律 | 是 |
| `registry/` | AI 供應商、workflow、skill、外部框架（`frameworks.yaml`）的機器可讀索引 | 是（內容為範例，需依專案覆寫） |
| `templates/` | Issue / PR / ADR / 架構 / benchmark / release note / task-handoff 模板；`product-entrypoint/` 子目錄是產品儲存庫的入口檔模板（見 `AGENTS.md` 第 3 節） | 是 |
| `docs/` | 關於本儲存庫自身的說明 | — |
| `scripts/` | 產品初始化、發行邊界檢查、subtree 同步、自我檢查、commit lint、離線發行包建立與驗證 | 是 |
| `tests/` | 初始化、範例、發行包、發行證據與同步契約的回歸測試 | 是 |

## 不納入平台核心的內容

- 任何單一產品領域的具體規範（例如 Android Gradle 設定慣例、kernel coding-style 細節）——這些屬於「領域知識」，做法見 `docs/domain-adaptation.md`，成果應該寫進**產品儲存庫**自己的文件，而不是這裡
- 產品的商業邏輯、程式碼
- 團隊或個人的機密設定（API key 等）——`registry/providers.yaml` 只放模型選型的中繼資料，不放憑證
