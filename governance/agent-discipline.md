# Governance：執行紀律（Agent Discipline）

本文件定義 AI 代理人的執行紀律、完成條件與異常還原方式。commit 與審查的詳細規則分別以 `governance/commit.md`、`governance/review.md` 為準。

## 1. 每日執行紀律

下列三項規則適用於所有產品領域。

### 1.1 同一輪工作完成測試

修改程式碼時，必須在同一輪工作中完成並執行對應測試。延後補測試容易讓測試只反映現有實作，無法驗證原始需求。

`workflow/feature.md` 與 `workflow/bugfix.md` 已將測試納入同一流程。對應測試通過前，變更不視為完成。

### 1.2 優先使用已登記的 skill 或子代理人

開始前先確認子任務是否已登記於 `registry/skills.yaml`，或符合 `registry/providers.yaml` 的角色定義。若有對應項目，依其固定流程處理，以維持結果一致且可複查。

典型會用到專門 skill/sub-agent 的情境：

- 產生特定格式文件（Word／PDF／簡報）：使用 `registry/skills.yaml` 登記的 skill
- 可獨立完成且結果可驗證的子任務：可交由隔離工作階段的子代理人處理，只回傳必要結果
- 對應 planner、implementer、verifier、reviewer 或 researcher 的階段性工作：依 `AGENTS.md` 2.1 節交接

各工具的子代理人（sub-agent）設定方式見 `docs/tool-compatibility.md`。

若已安裝 superpowers，可使用其 subagent-driven-development 等 skill。未安裝或工具不支援時，仍須遵守本節的分工與交接規則。

### 1.3 一個邏輯改動一個 commit

原子 commit 是精準還原的前提。不同邏輯的變更若放在同一個 commit，後續將無法只撤銷其中一項。完整規則見 `governance/commit.md`。

判斷方式：commit 說明應能用一句話描述，且不包含第二個獨立目的。例如：

- 補 A 元件的測試 → 一個 commit
- 修 B 路由的 bug → 另一個 commit
- 重構 C 共用邏輯 → 另一個 commit

第 3 節的還原決策表，前提都是這條規則有被遵守。

## 2. 收尾驗證：三層安全網

合併前須完成下列三層驗證。每一層處理不同風險，不可互相取代。

### 2.1 第一層：typecheck → test → build

依序跑三段，任一段沒過就不算通過：

| 階段 | 驗證目標 | 例子 |
|---|---|---|
| typecheck / 靜態檢查 | 型別/介面層級的錯誤 | 把物件傳給只接受字串的函式；C 專案對應 `-Wall -Werror` 或 sparse 這類靜態分析，不是只有有型別系統的語言才有這一層 |
| test | 行為層級的錯誤 | 改了一個函式，該回傳 true 的情境變成回傳 false，但型別完全正確、編譯得過 |
| build | 打包或發布時才出現的錯誤 | import 路徑在 dev/debug 模式可用，但 release/production build 失敗；kernel 模組須以實際目標核心版本重新編譯 |

三段對應到 `workflow/feature.md`、`workflow/bugfix.md` 的驗證步驟；這裡的重點是**三段都要做，不能因為 test 過了就跳過 build**。

### 2.2 第二層：審查要獨立，不能自己審自己

同一工作階段完成實作後立即審查相同內容，容易產生確認偏誤（confirmation bias）。審查應使用不同供應商或全新工作階段。完整規則見 `governance/review.md`。

### 2.3 第三層：向官方來源核對版本與 API

每次引用具體版本號、套件名稱或 API 用法時，都須查閱當下的官方文件。這類資訊更新頻率高，不得只依模型記憶決定。

常見錯誤包含套件版本、API 參數順序、必要欄位及雲端服務介面路徑錯誤。核對結果須保留官方來源。

來源無法取得時（例如會員制規範、未文件化的團隊慣例或商業決策），依下列方式處理：

1. 說明缺少的資料、無法取得的原因及受影響的判斷
2. 不以推測內容補足空缺
3. 若任務為 `handoff_required: true`，使用 `templates/task-handoff.md` 記錄未解問題；否則直接請使用者或負責人裁定
4. 人員回答或後續取得來源後，將結論寫入產品儲存庫的 `docs/domain-standards.md`（見 `docs/domain-adaptation.md`）。團隊內規與商業決策通常不在公開文件中，必須保留決策紀錄

## 3. 異常還原（Rollback）

下表以第 1.3 節的原子 commit 為前提；變更範圍不乾淨時，依最後一列處理。

| 情境 | 建議動作 | 為什麼 |
|---|---|---|
| 改動還沒 commit，發現方向不對 | `git restore <file>` 或 `git stash` | 尚未進入 Git 歷程，可直接還原 |
| 已 commit、還沒 push，只有這一個 commit | `git commit --amend` 或 `git reset --soft HEAD~1` 重寫 | 純本地歷史，改寫不影響任何人 |
| 已 commit、還沒 push，但後面疊了好幾個 | `git rebase -i` 挑出要丟棄/合併的 commit | 前提是這幾個 commit 都還沒推上共用分支 |
| 已 push 到自己的功能分支，還沒有人 base 在上面 | 視情況 force-push 修正後的歷史，或直接補一個新 commit 修正 | 功能分支通常只有作者在用；force-push 前務必先確認沒有協作者已經 pull 過 |
| 已合併進 `main` 或其他共用分支 | 一律用 `git revert`，不對共用歷史做 force-push 改寫 | 共用歷史一旦改寫，其他人本地儲存庫會產生衝突 |
| 已合併進 `product-cicd-platform` 的 `main`，但還沒發布 | `git revert` 該 commit，重新走一次 `workflow/bugfix.md` | 靠第 1.3 節的原子 commit，revert 範圍應該剛好等於一個邏輯改動 |
| 已發布到 `product-release` | 依 `governance/release.md` 的「還原程序」處理，不是單純 `git revert` 能解決 | 發布後的還原可能牽涉已發出的建置成品與使用者端狀態 |
| 問題橫跨多個 commit，無法指定單一 revert 目標 | 先建立最小修正 commit，排除立即風險，再整理後續還原計畫 | 變更未依邏輯拆分，無法安全地一次還原 |
