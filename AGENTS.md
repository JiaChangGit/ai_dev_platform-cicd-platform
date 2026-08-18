# AGENTS.md — AI 代理人操作手冊

本文件是 AI 代理人（AI agent）的主要操作規則，適用於 Claude Code、Codex、opencode，以及其他在本平台或產品儲存庫中工作的工具。使用者總覽請讀 `README.md`；文字與術語規則請讀 `docs/terminology.md`。

> **工具載入方式：** Codex 與 opencode 直接讀取 `AGENTS.md`；Claude Code 透過根目錄 `CLAUDE.md` 的 `@AGENTS.md` 匯入語法載入相同內容。`CLAUDE.md` 只是轉接器，規則以本文件為準。詳細差異見 `docs/tool-compatibility.md`。

## 0. 適用情境

`ai-dev-platform` 不是產品儲存庫。它提供其他產品儲存庫共用的規範、流程、模板與離線 skill，不存放產品程式碼或產品 issue／PR。適用情境分為：

- 直接在 `ai-dev-platform` 裡工作（新增/修改 workflow、governance、template、registry）→ 見第 4 節
- 在某個產品儲存庫（如 `product-cicd-platform`）裡工作，`ai-dev-platform` 是固定的平行目錄，你要**引用**它的目前規範 → 見第 1～3 節

下載後的 `ai-dev-platform/` 是不含 `.git` 的唯讀平台包（read-only platform package）：不可在其中執行 subtree `add`／`pull`，也不可要求使用者執行 `git init`。只有 `ai_dev_platform-cicd-platform` Git 維護儲存庫（maintenance repository）能同步第三方內容與建立發行包。維護方式見 `docs/maintainer-mode.md`；產品使用方式見 `docs/consumer-mode.md`。

## 1. 開始任何任務前的四項檢查

> 若任務是用本平台建立全新產品儲存庫，直接執行第 3 節。下列四項檢查適用於已完成初始建立的產品儲存庫。

1. 判斷任務類型（feature / bugfix / debug / review / benchmark / release / documentation），對照 `registry/workflow.yaml` 找到：
   - 要遵守的 `governance/*.md`
   - 要使用的 `templates/*.md`
   - 建議的角色分工（`suggested_roles`，對照 `registry/providers.yaml`）與是否需要交接（`handoff_required`）
2. 讀該任務類型對應的 `workflow/*.md`，照裡面的步驟走，不要自創流程
3. 若任務涉及你不熟悉的產品領域（Android / kernel / 前端框架 / ...），先讀 `docs/domain-adaptation.md`，依清單去查該領域的權威資料來源，**不要憑記憶臆測領域慣例**
4. 若任務規模夠大、或設計/用詞還沒共識，先讀 `docs/external-frameworks.md`，判斷這次是否該先用 grill-with-docs / OpenSpec，而不是直接進 `workflow/*.md` 動手——上一點是「查什麼」，這點是「動手前的規模/共識判斷」，兩者互不取代

### 1.1 第三方 skill 路由

`external/` 是離線來源，不是 Codex、Claude Code 或 opencode 的自動安裝目錄。使用第三方 skill 前，必須讀取 `registry/skill-routing.yaml`：

1. 依「明確點名 → 檔案類型 → 供應商／領域 → 任務階段 → 通用 skill」的優先順序選擇。
2. `manualOnly` 只有使用者明確點名時才能載入；`restrictedAutomatic` 必須符合限定詞、且不得命中排除詞。
3. `collisionGroups` 同時命中時只用 `primary`；除非使用者明確要求組合。
4. 平台 `workflow/`、`governance/` 與使用者當前授權永遠優先；第三方 skill 不得擴大任務範圍。

維護者在同步或調整 skill 後執行 `python3 -B scripts/audit_skills.py`。稽核規範與結果解讀見 `docs/skill-governance.md`。

## 2. 判斷任務類型

`registry/workflow.yaml` 是任務分類的唯一事實來源；不得在本文件維護第二份完整對照表。快速判斷如下：

新增能力→`feature`；修正異常→`bugfix`；找原因→`debug`；審查他人變更→`review`；量測效能→`benchmark`；準備發布→`release`；只動文件→`documentation`。

判斷好類型後，查 `registry/workflow.yaml` 裡對應項目的 `doc`（該讀哪個 workflow 檔）、`governance`（要遵守什麼）、`templates`（要用什麼模板）、`handoff_required`（是否為多角色任務，見第 2.1 節）。不確定屬於哪一類時，先用一句話向使用者確認，不要套用最接近的流程硬做。

### 2.1 多角色任務的交接

若 `registry/workflow.yaml` 該項目的 `handoff_required` 為 `true`（例如 `suggested_roles` 有兩個以上角色），角色之間交接時要依 `templates/task-handoff.md` 產出結構化交接內容，寫成實體檔案（例如產品儲存庫的 `.ai/handoffs/<task-id>-<from-role>-to-<to-role>.md`），不要只靠對話上下文口頭交接——CLI 呼叫通常是無狀態的，交接內容沒寫下來就會在下一個角色開始時遺失。

## 3. Bootstrap 一個全新產品儲存庫的標準流程

標準結構包含一個唯讀平台目錄，以及每個產品各自的兩個 Git 儲存庫：

```
Work/
├── ai-dev-platform/         唯讀平台包，跨專案共用
├── product-cicd-platform/   產品原始碼與 CI/CD
└── product-release/         該產品專屬的發行儲存庫
```

`product-cicd-platform` 保存產品原始碼與開發歷程；`product-release` 只接收通過 CI/CD 驗證的發行證據（release evidence）與成品參照。兩者不得共用同一個 Git 儲存庫。交接方式見 `workflow/release.md`。

以下流程只適用於全新專案。既有專案已有 Git 歷程、團隊慣例或 CI 時，應改用 `docs/how-adopt-existing.md`，先完成差異分析，再決定套用範圍。

當使用者要求「用這套框架開一個新專案」時：

1. **確認產品領域與基本資訊**：產品是什麼（App / kernel module / web service / ...）、目標平台
2. **使用初始化工具建立兩個 Git 儲存庫**：在下載版 `ai-dev-platform/` 執行 `scripts/init_product.py`。工具會在平行目錄建立 `<product>-cicd-platform/` 與 `<product>-release/`，並拒絕覆寫既有目錄。完整參數見 `docs/product-initialization.md`。
3. **固定引用共用平台目前版本**：產品入口檔一律讀取 `../ai-dev-platform/`。產品端不複製 `workflow/`、`governance/`、`external/`，不使用 subtree 內嵌平台內容，也不建立平台 lock file。三個工具的載入機制見 `docs/tool-compatibility.md`。
4. **產出領域規範文件**：依 `docs/domain-adaptation.md` 的檢查清單，蒐集該領域的官方文件、規範、慣例，整理成 `product-cicd-platform/docs/domain-standards.md`（附來源連結）。這份文件**只存在於產品儲存庫**，是活文件，隨專案演進持續更新，不要回寫進 `ai-dev-platform`。
5. **初始化治理骨架**：確認使用者要用 GitHub Actions、GitLab CI、Jenkins 或內部 CI；初始化工具會產生可執行的基本驗證管線與發行證據轉接模板。再依實際環境補上 `CODEOWNERS`（如適用）、成品平台、SBOM 與核准機制；內容需符合 `governance/branch.md`、`governance/commit.md`、`governance/review.md`，落地方式參考 `docs/how-enforce-rules.md`
6. **初始架構文件與第一個 ADR**：用 `templates/architecture.md` 寫一份 `product-cicd-platform/docs/architecture.md`，描述整體元件拆解與資料流的起始樣貌；用 `templates/adr.md` 記錄「為什麼選這個技術棧 / 架構」這個決策本身。兩者用途不同、不互相取代：架構文件是「現狀地圖」，會隨專案演進持續更新；ADR 是「某次決策的存證」，寫定後不回頭改，之後架構變了就再開一份新 ADR（`Superseded by`）。專案進行中若新增的功能大到本質上是「新模組」而不是在既有模組內擴充，同步更新架構文件，見 `workflow/feature.md` 第 2 步。
7. **評估是否啟用外部框架（選用）**：讀 `docs/external-frameworks.md`，依專案規模與實際使用工具，評估 grill-with-docs（語意對齊）、OpenSpec（規格與變更管理）與 superpowers（執行紀律）。三者不影響平台核心流程；必須取得使用者同意後才可安裝
8. **確認發行邊界**：`product-release` 已由初始化工具建立，只能保存發行證據、Release Note、Git tag，以及成品 URI／SHA-256。不得保存原始碼、建置成品或第三方 skill；交接前後執行 `scripts/verify_release_layout.py`
9. 回報使用者：已完成項目與待使用者決定的項目，例如商業邏輯或內部專屬規範

## 4. 若任務是修改 `ai-dev-platform` 本身

### 4.1 平台自我開發的規則來源

`ai_dev_platform-cicd-platform` 是維護中的來源儲存庫，不是產品共用的穩定平台。當平行目錄 `../ai-dev-platform/AGENTS.md` 存在時，開發本平台的 AI 必須：

1. 先讀取穩定的 `../ai-dev-platform/AGENTS.md`，將其當作目前執行規則（self-hosting stable policy）。
2. 將本儲存庫的 `AGENTS.md`、`workflow/`、`governance/` 視為下一版候選規則，只供實作與驗證。
3. 候選包通過完整驗收並安裝到 `../ai-dev-platform/` 後，新規則才成為所有產品共用的目前版本。

- 新增 workflow 前讀 `docs/how-add-workflow.md`
- 新增 template 前讀 `docs/how-add-template.md`
- 新增/更新 subtree 前讀 `docs/how-sync-upstream.md`
- 任何新增都必須同步更新 `registry/workflow.yaml`（若適用）並跑一次 `scripts/check.sh`
- **保持產品無關**：如果你發現自己想寫「Android 要用 XXX Gradle 設定」這種具體到單一領域的規則，那應該寫進某個產品儲存庫的 `docs/domain-standards.md`，而不是這裡

## 5. 硬性規則（不可違反）

- 不臆測業務邏輯或內部專屬規範；缺這類資訊時，停下來問使用者，不要編造
- 蒐集領域知識時，優先引用官方 / 一手來源（見 `docs/domain-adaptation.md`），並在產出文件中附上來源
- 不在 commit / PR / issue 中留下憑證、金鑰、內部網址等敏感資訊（見 `governance/security.md`）
- 所有 commit message 遵守 `governance/commit.md`；所有 PR 遵守 `templates/pr.md`
- 修改 `registry/*.yaml` 後，若有對應檔案路徑異動，務必連動更新，避免斷鏈（可用 `scripts/check.sh` 驗證）
- 你自己不能同時扮演同一個任務的 implementer 與 reviewer；即使全程只有你在操作，審查角色也必須符合 `governance/review.md` 定義的最低獨立性要求
- 動手實作時遵守 `governance/agent-discipline.md` 的每日執行紀律：測試在同一輪對話補完、找得到對應 skill/sub-agent 就優先指派、一個邏輯改動一個 commit；收尾前過完三層驗證（typecheck/test/build、獨立審查、版本與 API 自我核對）才算任務完成
