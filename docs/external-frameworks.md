# 外部框架整合：grill-with-docs / OpenSpec / superpowers

## 為什麼要整合這三個框架

`workflow/documentation.md` 第 2 步已經要求「確認唯一資訊來源」，`README.md` 也把「單一事實來源」當成貫穿整個儲存庫的設計原則。這三個外部框架是這個原則在三個具體層面的**現成實作**，不是新規則：

| 層級 | 框架 | 擁有什麼 |
|---|---|---|
| 語意對齊與決策存證 | [grill-with-docs](https://github.com/mattpocock/skills)（`mattpocock/skills` 儲存庫，`skills/engineering/grill-with-docs/` 為核心技能，並相依於同儲存庫的兩個子技能，見下方安裝方式）| 訪談式釐清設計與用詞，寫入 `CONTEXT.md` 詞彙表與 `docs/adr/` 決策紀錄 |
| 規格與變更管理 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) | `openspec/specs/`（現行行為規格）與 `openspec/changes/<name>/`（變更提案：proposal/design/tasks/delta specs）|
| 執行紀律 | [superpowers](https://github.com/obra/superpowers) | TDD、brainstorm、write-plan、execute-plan、code review 等技能，自動依任務內容觸發 |

三者皆由外部社群維護。本儲存庫只定義適用時機、功能邊界與安裝方式，不複製其方法論。三者均為選用功能；未安裝時，`workflow/` 與 `governance/` 仍可獨立運作。

## 跟既有機制的對應：不重複維護

| 框架 | 這個儲存庫既有的對應機制 | 關係 |
|---|---|---|
| grill-with-docs | `templates/adr.md` | grill-with-docs 是「產生 ADR 內容」的具體工具；`templates/adr.md` 的格式不變，是它寫出來的 ADR 應該符合的結構。沒裝的話，`workflow/feature.md` 第 2 步原本的「先寫 ADR」流程照舊用人工訪談完成 |
| OpenSpec | `workflow/feature.md` 第 2 步（設計）、`templates/architecture.md` | 規模達到「新模組」等級、且已安裝 OpenSpec 時，用 change 生命週期（propose → apply → archive 三階段；三個工具實際的觸發語法不同，見下方安裝方式）取代原本臨場的 ADR 起草；change 資料夾（尤其 `design.md`）已經是這次決策的存證，**通常不需要再另開一份 ADR**，除非這個決策本身需要獨立於單一 change 存在、預期被日後其他 change 引用——這才是 ADR 真正的價值，此時兩者並存。`openspec/specs/` 記的是**行為**（這個能力現在做什麼），`docs/architecture.md` 記的是**結構**（元件怎麼拆、資料怎麼流），兩份文件描述的是現狀的不同截面，不是同一份東西的兩種格式，該次改動若兩者都受影響就兩份都更新 |
| superpowers | `governance/agent-discipline.md`（尤其 1.2 節） | `agent-discipline.md` 是**不論有沒有裝 superpowers 都必須遵守的最低紀律**（工具無關）；superpowers 是三個目標工具中，只要能裝上就建議採用的具體實作。兩者不衝突，**裝了 superpowers 不代表 `agent-discipline.md` 被取代或可以跳過**——superpowers 沒覆蓋到的部分（例如原子 commit、三層驗證裡的第三層版本查證）依然要照 `agent-discipline.md` 做 |

## 動手前的判斷順序

非小型/單人任務要不要用這三個框架，依序判斷（對照 `registry/frameworks.yaml` 的 `applies_to_workflows`）：

1. 設計或用詞本身還沒共識（不只是 `workflow/feature.md` 第 1 步講的「業務邏輯模糊」，而是連怎麼稱呼這個概念都還沒定案）→ 已安裝 grill-with-docs 就用它，沒裝就照原本的方式跟使用者對話釐清
2. 規模達到「新模組」或「跨多個現有模組」等級（`workflow/feature.md` 第 2 步的既有判準）→ 已安裝 OpenSpec 就開一個 change，沒裝就照原本的 ADR + 架構文件手動流程
3. 動手實作 → 已安裝 superpowers 的技能會自動接手；不論有沒有裝，`governance/agent-discipline.md` 的紀律都要遵守
4. 上述都沒裝、或任務規模明顯不需要 → 三個框架全部跳過，直接照 `workflow/*.md` 原本的流程做，這是完全正常且預期中的路徑，不是退而求其次

## 三個框架彼此的重疊：已知案例

三個框架底層共有 22 份 `SKILL.md`，其中兩處重疊值得知道，因為**這是三者一起裝之後才會出現的情境，任何一個框架自己的文件都不會提到**：

**OpenSpec 的 `explore` 跟 superpowers 的 `brainstorming`，都佔「動手前先想清楚」這塊地**：兩者觸發描述都在講「先探索/釐清需求」，但實際行為不同——`openspec-explore` 明確定位是「a stance, not a workflow」，沒有固定步驟、不強制產出任何文件；`brainstorming` 是強制的 7 步驟 checklist，且有 `<HARD-GATE>` 規定沒完成不准動手，最後**強制**寫一份 design doc 到 `docs/superpowers/specs/`。兩個都裝的情況下，同一句「幫我想一下這個功能怎麼做」理論上兩邊都可能觸發，且各自的產出位置不同（一個沒有固定產出，一個固定寫到 `docs/superpowers/specs/`，跟 `openspec/changes/<name>/design.md` 是不同路徑）。**建議**：規模已經達到 `openspec/changes/` 該出現的程度，讓 `openspec-explore` 接手就好（探索完直接接 `/opsx:propose`，設計內容自然流入 `openspec/changes/<name>/design.md`，不會有兩份設計文件）；只有明確還沒到開 change 的程度、單純想法還在發散階段，才讓 `brainstorming` 接手。這是本文件的建議，不是官方定論。

`grilling` 與 `grill-with-docs` 的觸發方式不同：`grilling` 可由描述中的 grill 關鍵字自動觸發；`grill-with-docs` 設定 `disable-model-invocation: true`，必須手動執行 `/grill-with-docs`。只有後者會同步產生 ADR 與 `CONTEXT.md`。需要保留文件時，必須明確執行 `/grill-with-docs`。

`grill-with-docs/SKILL.md` 的 `disable-model-invocation` 是工具特定 frontmatter，不屬於通用的 `name`／`description` 觸發契約，不能假設 Codex、Claude Code 與 opencode 都會用相同方式解讀。平台將此類 skill 登記為 `manualOnly`，以 `registry/skill-routing.yaml` 作為跨工具的共同護欄。使用上游原生安裝器時，仍須另行驗證目標工具支援的 frontmatter 欄位。

## 安裝方式

以下指令針對本儲存庫指定要通用的三個工具（Codex CLI、Claude Code、opencode）；其他工具的支援情況見各框架自己的文件。

### grill-with-docs

- 來源：`github.com/mattpocock/skills` 內的 `skills/engineering/grill-with-docs/`，並相依於同儲存庫的兩個 skill：`skills/productivity/grilling/`（負責訪談）與 `skills/engineering/domain-modeling/`（負責整理文件）。三個 skill 必須一起安裝
- 安裝（在**產品儲存庫**內執行，三工具通用）：

  ```bash
  npx skills add mattpocock/skills --skill grill-with-docs --skill grilling --skill domain-modeling -a claude-code -a codex -a opencode -y
  ```

- 觸發方式：**手動**。使用者在對話中執行 `/grill-with-docs` 後才會啟動；skill 定義檔標示 `disable-model-invocation: true`
- 產出位置：專案根目錄 `CONTEXT.md`（或 `CONTEXT-MAP.md` 所列各 context 的 `CONTEXT.md`）及 `docs/adr/`；有內容時才建立，不預先產生空檔案

### OpenSpec

- 來源：`github.com/Fission-AI/OpenSpec`，npm 套件 `@fission-ai/openspec`
- 安裝與初始化（在**產品儲存庫**內執行）：

  ```bash
  npm install -g @fission-ai/openspec@latest
  cd product-cicd-platform && openspec init --tools claude,codex,opencode
  ```

- 核心指令：`explore`（可選，先想清楚）、`propose`、`apply`、`archive`，另外還有 `sync`、`update` 兩個輔助指令；**三個工具的實際觸發語法不同，沒有一套通用寫法**：

  | 工具 | 觸發語法（以 propose 為例） |
  |---|---|
  | Claude Code | `/opsx:propose "描述"`（冒號分隔） |
  | opencode | `/opsx-propose "描述"`（連字號，不是冒號） |
  | Codex CLI | `$openspec-propose "描述"`，或讓它依任務內容自動觸發該 skill |

  其餘 apply/archive/explore/sync/update 依此規律替換指令名稱即可
- 產出位置：`openspec/specs/<domain>/spec.md`（現行規格）、`openspec/changes/<change-name>/{proposal.md,design.md,tasks.md,specs/}`（變更提案；封存後移到 `openspec/changes/archive/`）
- 三工具的實際轉接檔位置（`openspec init` 自動產生，不需手動處理）：

  | 工具 | Skill 路徑 | Command 路徑 |
  |---|---|---|
  | Claude Code | `.claude/skills/openspec-*/SKILL.md` | `.claude/commands/opsx/<id>.md` |
  | Codex CLI | `.codex/skills/openspec-*/SKILL.md` | 不產生（僅走 skill，Codex 目前沒有 command 轉接器）|
  | opencode | `.opencode/skills/openspec-*/SKILL.md` | `.opencode/commands/opsx-<id>.md` |

### superpowers

- 來源：`github.com/obra/superpowers`（MIT License，作者 Jesse Vincent / Prime Radiant）
- 觸發方式：**自動**，技能依任務內容自動觸發，安裝完不需要每次手動叫用
- 安裝依工具而異，**沒有單一指令能通吃三個工具**，各自的外掛市集機制彼此獨立：

  | 工具 | 安裝方式 |
  |---|---|
  | Claude Code | `/plugin install superpowers@claude-plugins-official`（Anthropic 官方市集），或 `/plugin marketplace add obra/superpowers-marketplace` 後 `/plugin install superpowers@superpowers-marketplace` |
  | Codex CLI | 在 Codex 對話中打 `/plugins`，搜尋 `superpowers`，選擇安裝 |
  | opencode | 告訴 opencode agent：「Fetch and follow instructions from `https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md`」——這是 opencode 特有的自我安裝模式，由 agent 自己讀取並執行安裝步驟 |

- 若同時用多個工具，每個工具要分別安裝一次，不是裝一次就對所有工具生效
- 以上是各工具目前的外掛市集安裝方式，`/plugin install superpowers@claude-plugins-official` 用的是 Claude Code 官方市集（見 `code.claude.com/docs/en/discover-plugins`）；三個工具都是互動式介面內操作，裝完建議直接在對話中確認技能有沒有正常運作

## 離線 / 網路受限環境

上述原生安裝方式都需要對外網路（npm registry、GitHub、各工具的外掛市集）。預設下載包透過 git subtree 快照提供可直接載入的第三方 skill、授權與必要參考內容：

- `external/anthropic-skills/skills/` 保存穩定 skill 集合；未填寫的 `template/` 不進入預設包。
- OpenAI Cookbook 預設只保留 `docs-editor` 與 `bootstrap-realtime-eval` 兩個真正的 skill、授權及說明；需要完整 notebook／範例快照時，改用 `openai-cookbook` 選用套件。
- `external/mattpocock-skills/` 的預設包範圍只包含 `engineering/`、`misc/`、`productivity/` 穩定類別，並保留 grill-with-docs 所需的 grilling、domain-modeling；`in-progress/` 與 `deprecated/` 不進入預設包。
- `external/superpowers/` 保存上游完整 skills 子樹。
- OpenSpec 不透過 subtree 分發（見 `registry/frameworks.yaml` 該項目的 `subtree_ref: null`）——它是要在產品儲存庫內執行的 CLI 工具，不是被動參考內容，離線環境下需要另外解決 npm registry 的鏡像問題，不在本儲存庫範圍內

**離線保證的邊界**：預設包完整內含已登記第三方 skill 本體、其相依 skill 與授權證據；大型 Cookbook 參考資料分離為選用套件。平台不保證各 AI 工具的外掛掛載程式也能離線安裝。Claude Code plugin、Codex 外掛市集等機制與工具版本綁定，若要在無網路環境維持原生自動觸發，仍需私有 npm registry 或內部 Git／外掛鏡像。沒有掛載機制時，AI 仍可依 `registry/skills.yaml` 直接讀取中央平台的 `SKILL.md`。

## 跟三個工具讀取機制的關係

`docs/tool-compatibility.md` 講的是這個儲存庫自己的 `AGENTS.md`/`CLAUDE.md`/`opencode.json` 入口檔如何被三個工具讀到；本文件這三個框架用的是另一組獨立機制（各工具自己的 skill 目錄、外掛市集），兩組機制互不取代、同時並存，細節見該文件「外部框架的多工具轉接方式」一節，不在這裡重複。

## 跟 release 流程的銜接

已安裝 OpenSpec 時，一個 change 的 archive 時機建議對齊 `workflow/release.md` 裡 `product-cicd-platform` 的 CI 驗證通過、準備交接給 `product-release` 的時間點——archive 後 `openspec/specs/` 才會是這次變更後的最新狀態，過早 archive 等於在還沒驗證過的狀態下宣告「這就是現行規格」。

## 參考來源

這個領域的工具更新速度快，若內容與實際行為有出入，以各工具當下的官方文件為準。

- OpenSpec：`github.com/Fission-AI/OpenSpec`（`docs/getting-started.md`、`docs/supported-tools.md`、`docs/cli.md`）
- superpowers：`github.com/obra/superpowers`（README 的 Installation、The Basic Workflow 兩節）
- grill-with-docs：`github.com/mattpocock/skills`（`skills/engineering/grill-with-docs/SKILL.md` 及其所需的 `skills/productivity/grilling/SKILL.md`、`skills/engineering/domain-modeling/SKILL.md`）
- 跨工具 skill 安裝機制（`npx skills add`）：`github.com/vercel-labs/skills`
