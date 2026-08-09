# AGENTS.md — AI 代理人操作手冊

本文件是給 AI 代理人（Claude Code、Codex CLI、opencode、或任何在此倉庫 / 由此倉庫指導的產品倉庫中工作的 agent）看的唯一事實來源。人類貢獻者請看 `README.md`。

> **你是怎麼讀到這份文件的？** Codex、opencode 會直接原生讀取這份 `AGENTS.md`。若你是 Claude Code，你是透過專案根目錄 `CLAUDE.md` 裡的 `@AGENTS.md` 匯入語法讀到這裡的內容——`CLAUDE.md` 只是轉接器，不要去那份文件找規則，規則都在這裡。細節與各工具差異見 `docs/tool-compatibility.md`。

## 0. 你在跟什麼互動

`ai-dev-platform` 本身**不是**產品倉庫，不要在這裡寫產品程式碼、不要在這裡建立產品的 issue/PR。它是被其他產品倉庫引用的「規範與流程來源」。你可能是：

- 直接在 `ai-dev-platform` 裡工作（新增/修改 workflow、governance、template、registry）→ 見第 4 節
- 在某個產品倉庫（如 `product-cicd-platform`）裡工作，`ai-dev-platform` 是平行目錄或已被 subtree 進 `.ai/`，你要**引用**它的規範 → 見第 1～3 節

## 1. 開始任何任務前，先做這三件事

> 若任務是「用這套框架 bootstrap 一個全新產品倉庫」（例如使用者說「幫我開一個新專案」），這裡的分類不適用——bootstrap 不屬於 feature/bugfix/debug/review/benchmark/release/documentation 任何一類，**不要**嘗試把它硬套進下面的分類，直接跳到第 3 節。以下三件事是「已經在一個 bootstrap 完成的產品倉庫裡、要做具體開發任務」時才適用。

1. 判斷任務類型（feature / bugfix / debug / review / benchmark / release / documentation），對照 `registry/workflow.yaml` 找到：
   - 要遵守的 `governance/*.md`
   - 要使用的 `templates/*.md`
   - 建議的角色分工（`suggested_roles`，對照 `registry/providers.yaml`）與是否需要交接（`handoff_required`）
2. 讀該任務類型對應的 `workflow/*.md`，照裡面的步驟走，不要自創流程
3. 若任務涉及你不熟悉的產品領域（Android / kernel / 前端框架 / ...），先讀 `docs/domain-adaptation.md`，依清單去查該領域的權威資料來源，**不要憑記憶臆測領域慣例**
4. 若任務規模夠大、或設計/用詞還沒共識，先讀 `docs/external-frameworks.md`，判斷這次是否該先用 grill-with-docs / OpenSpec，而不是直接進 `workflow/*.md` 動手——上一點是「查什麼」，這點是「動手前的規模/共識判斷」，兩者互不取代

## 2. 判斷任務類型

不要在這裡另外維護一份對照表——`registry/workflow.yaml` 是唯一事實來源，這裡維護第二份只會兩邊不同步。快速判斷用這個粗略對應：

新增能力→`feature`；修正異常→`bugfix`；找原因→`debug`；審查他人變更→`review`；量測效能→`benchmark`；準備發布→`release`；只動文件→`documentation`。

判斷好類型後，查 `registry/workflow.yaml` 裡對應項目的 `doc`（該讀哪個 workflow 檔）、`governance`（要遵守什麼）、`templates`（要用什麼模板）、`handoff_required`（是否為多角色任務，見第 2.1 節）。不確定屬於哪一類時，先用一句話向使用者確認，不要套用最接近的流程硬做。

### 2.1 多角色任務的交接

若 `registry/workflow.yaml` 該項目的 `handoff_required` 為 `true`（例如 `suggested_roles` 有兩個以上角色），角色之間交接時要依 `templates/task-handoff.md` 產出結構化交接內容，寫成實體檔案（例如產品倉庫的 `.ai/handoffs/<task-id>-<from-role>-to-<to-role>.md`），不要只靠對話上下文口頭交接——CLI 呼叫通常是無狀態的，交接內容沒寫下來就會在下一個角色開始時遺失。

## 3. Bootstrap 一個全新產品倉庫的標準流程

標準佈局是三個平行倉庫：

```
Work/
├── ai-dev-platform/         本倉庫，唯讀參考，跨專案共用
├── product-cicd-platform/   產品原始碼 + CI/CD（開發、build、test 都在這裡發生）
└── product-release/         product-cicd-platform 的 CI/CD 驗證通過後，封裝與發布的產物
```

`product-cicd-platform` 與 `product-release` 是**故意分開的兩個倉庫**，不是同一倉庫的兩個資料夾：前者是會頻繁變動的開發現場，後者只接收「已經通過驗證」的結果，讓「正在開發中」與「已發布」的邊界在倉庫層級就切清楚，不必依賴分支慣例去區分。兩者交接的細節見 `workflow/release.md`。

以下流程假設是**全新專案**。若使用者要求的是「把這套框架導入一個既有專案」（原本只有人類在開發、已經有歷史/團隊慣例/可能已有 CI），流程不一樣，直接看 `docs/how-adopt-existing.md`，不要照搬以下步驟——既有專案最容易出錯的地方就是直接套用全新專案的流程，跟既有慣例硬碰硬。

當使用者要求「用這套框架開一個新專案」時：

1. **確認產品領域與基本資訊**：產品是什麼（App / kernel module / web service / ...）、目標平台
2. **建立 `product-cicd-platform`**，與 `ai-dev-platform` 平行放置，不要巢狀在裡面。這是實際寫程式碼、跑 CI 的地方。
3. **決定引用模式**（兩者擇一，向使用者確認）：
   - *平行參考模式（預設）*：`product-cicd-platform` 不含 `workflow/`、`governance/` 等內容，AI 執行任務時直接讀取旁邊 `ai-dev-platform/` 目錄。優點：更新框架不需要每個產品倉庫各自同步。
   - *內嵌模式*：用 `scripts/sync.sh`（或在產品倉庫端反向操作 git subtree）把 `workflow/`、`governance/`、`templates/` 併入 `product-cicd-platform/.ai/` 目錄。優點：產品倉庫可以獨立分發、不依賴外部路徑。

   **不論選哪種模式，`product-cicd-platform` 都需要自己的入口檔**——Codex CLI 只沿 git root 往下找 `AGENTS.md`、opencode 不會自動解析 `AGENTS.md` 裡的 `@` 參照、Claude Code 需要有會被探索到的 `CLAUDE.md` 才會匯入，三個工具都不會自動跨到 sibling 目錄讀取。把 `templates/product-entrypoint/` 底下三個 `.template` 檔複製到 `product-cicd-platform/` 根目錄（去掉 `.template` 副檔名），依實際專案資訊填入 `<PRODUCT_NAME>` 等佔位符；若是內嵌模式，把檔案內 `../ai-dev-platform/` 換成實際內嵌路徑——例如用 `git subtree add --prefix=.ai <ai-dev-platform-repo> main` 把內容併進 `product-cicd-platform/.ai/` 後，`CLAUDE.md` 裡的 `@../ai-dev-platform/AGENTS.md` 要改成 `@.ai/AGENTS.md`（同倉庫內的相對路徑，不再需要 `../` 跳出去），`opencode.json` 的 `instructions` 陣列同理改成 `.ai/AGENTS.md`。機制細節見 `docs/tool-compatibility.md`「多倉庫情境」一節。
4. **產出領域規範文件**：依 `docs/domain-adaptation.md` 的檢查清單，蒐集該領域的官方文件、規範、慣例，整理成 `product-cicd-platform/docs/domain-standards.md`（附來源連結）。這份文件**只存在於產品倉庫**，是活文件，隨專案演進持續更新，不要回寫進 `ai-dev-platform`。
5. **初始化治理骨架**：先問使用者要用哪個 CI 平台（GitHub Actions／GitLab CI／其他），不要預設；在 `product-cicd-platform` 建立 `CODEOWNERS`（如適用）、CI 設定，內容需符合 `governance/branch.md`、`governance/commit.md`、`governance/review.md` 的規則；CI 檢查的落地方式參考 `docs/how-enforce-rules.md`
6. **初始架構文件與第一個 ADR**：用 `templates/architecture.md` 寫一份 `product-cicd-platform/docs/architecture.md`，描述整體元件拆解與資料流的起始樣貌；用 `templates/adr.md` 記錄「為什麼選這個技術棧 / 架構」這個決策本身。兩者用途不同、不互相取代：架構文件是「現狀地圖」，會隨專案演進持續更新；ADR 是「某次決策的存證」，寫定後不回頭改，之後架構變了就再開一份新 ADR（`Superseded by`）。專案進行中若新增的功能大到本質上是「新模組」而不是在既有模組內擴充，同步更新架構文件，見 `workflow/feature.md` 第 2 步。
7. **評估是否啟用外部框架（選用）**：讀 `docs/external-frameworks.md`，依專案規模與使用者實際會用的工具，判斷是否啟用 grill-with-docs（語意對齊）、OpenSpec（規格與變更管理）、superpowers（執行紀律；Claude Code / Codex CLI / opencode 三者安裝機制不同）。這步永遠是**選用**，不啟用也完全能照本文件其餘流程運作，小型/單人專案通常不需要，向使用者確認後再決定，不要自行預設要裝
8. **`product-release` 何時建立**：不必一開始就建立，等 `product-cicd-platform` 第一次跑出通過 CI 驗證的版本、準備真正發布時再建立，依 `workflow/release.md` 的流程處理交接
9. 回報使用者：已完成的項目、還需要人類決策的項目（例如商業邏輯、內部專屬規範）

## 4. 若任務是修改 `ai-dev-platform` 本身

- 新增 workflow 前讀 `docs/how-add-workflow.md`
- 新增 template 前讀 `docs/how-add-template.md`
- 新增/更新 subtree 前讀 `docs/how-sync-upstream.md`
- 任何新增都必須同步更新 `registry/workflow.yaml`（若適用）並跑一次 `scripts/check.sh`
- **保持產品無關**：如果你發現自己想寫「Android 要用 XXX Gradle 設定」這種具體到單一領域的規則，那應該寫進某個產品倉庫的 `docs/domain-standards.md`，而不是這裡

## 5. 硬性規則（不可違反）

- 不臆測業務邏輯或內部專屬規範；缺這類資訊時，停下來問使用者，不要編造
- 蒐集領域知識時，優先引用官方 / 一手來源（見 `docs/domain-adaptation.md`），並在產出文件中附上來源
- 不在 commit / PR / issue 中留下憑證、金鑰、內部網址等敏感資訊（見 `governance/security.md`）
- 所有 commit message 遵守 `governance/commit.md`；所有 PR 遵守 `templates/pr.md`
- 修改 `registry/*.yaml` 後，若有對應檔案路徑異動，務必連動更新，避免斷鏈（可用 `scripts/check.sh` 驗證）
- 你自己不能同時扮演同一個任務的 implementer 與 reviewer；即使全程只有你在操作，審查角色也必須符合 `governance/review.md` 定義的最低獨立性要求
- 動手實作時遵守 `governance/agent-discipline.md` 的每日執行紀律：測試在同一輪對話補完、找得到對應 skill/sub-agent 就優先指派、一個邏輯改動一個 commit；收尾前過完三層驗證（typecheck/test/build、獨立審查、版本與 API 自我核對）才算任務完成
