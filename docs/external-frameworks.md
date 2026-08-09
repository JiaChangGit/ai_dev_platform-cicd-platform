# 外部框架整合：grill-with-docs / OpenSpec / superpowers

## 為什麼要整合這三個框架

`workflow/documentation.md` 第 2 步已經要求「確認唯一資訊來源」，`README.md` 也把「單一事實來源」當成貫穿整個倉庫的設計原則。這三個外部框架是這個原則在三個具體層面的**現成實作**，不是新規則：

| 層級 | 框架 | 擁有什麼 |
|---|---|---|
| 語意對齊與決策存證 | [grill-with-docs](https://github.com/mattpocock/skills)（`mattpocock/skills` 倉庫，`skills/engineering/grill-with-docs/` 為核心技能，另依賴同倉庫兩個子技能，見下方安裝方式）| 訪談式釐清設計/用詞，寫入 `CONTEXT.md` 詞彙表與 `docs/adr/` 決策紀錄 |
| 規格與變更管理 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) | `openspec/specs/`（現行行為規格）與 `openspec/changes/<name>/`（變更提案：proposal/design/tasks/delta specs）|
| 執行紀律 | [superpowers](https://github.com/obra/superpowers) | TDD、brainstorm、write-plan、execute-plan、code review 等技能，自動依任務內容觸發 |

三者都不是這個倉庫發明或維護的——它們各自是外部社群持續在更新的專案，這個倉庫**只負責回答「什麼時候用哪一個、彼此邊界在哪、怎麼裝」**，不重寫它們的方法論本身。這也是為什麼三者都是**選用**：不裝也完全不影響本倉庫其餘 `workflow/` `governance/` 的運作，那些是不論有沒有這三個框架都必須遵守的底線。

## 跟既有機制的對應：不重複維護

| 框架 | 這個倉庫既有的對應機制 | 關係 |
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

**grill-with-docs 生態系內，`grilling` 跟 `grill-with-docs` 的觸發範圍有落差**：`grilling`（會自動觸發，描述包含「uses any 'grill' trigger phrases」）跟 `grill-with-docs`（`disable-model-invocation: true`，只能手動打 `/grill-with-docs` 觸發）兩者都在講「grill 使用者的想法」，差別是後者「順便寫文件」（ADR、`CONTEXT.md`）。實務上的風險是：使用者想要「grill + 順便留文件」，但只講了會命中 `grilling` 自動觸發條件的話，結果拿到單純的訪談，沒有文件產出，使用者可能沒發現少了這一半。這不是錯誤，是這兩個技能刻意分成「輕量自動版」跟「留痕手動版」的設計取捨，但值得知道——想要文件產出，一定要明確打 `/grill-with-docs`，不能只靠自動觸發。

順帶一提，`grill-with-docs/SKILL.md` 的 `disable-model-invocation` 這個 frontmatter 欄位，不在 Anthropic 目前公開文件的 SKILL.md schema（`name`/`description`/`license`/`allowed-tools`/`metadata`/`compatibility`）裡，用官方 `skill-creator` 的 `quick_validate.py` 驗證會失敗。不影響它透過 `npx skills add` 在 Claude Code/Codex/opencode 的專案層級安裝使用（三個工具的檔案系統層級 skill 載入器會容忍未知欄位），但如果要把這個資料夾包成正式 `.skill` 檔案透過 Skills API／claude.ai 上傳，會被官方驗證器擋下來——這是上游倉庫的事，不在這裡處理。

## 安裝方式

以下指令針對本倉庫指定要通用的三個工具（Codex CLI、Claude Code、opencode）；其他工具的支援情況見各框架自己的文件。

### grill-with-docs

- 來源：`github.com/mattpocock/skills` 內的 `skills/engineering/grill-with-docs/`，**依賴同倉庫另外兩個技能**：`skills/productivity/grilling/`（實際負責訪談）、`skills/engineering/domain-modeling/`（實際負責整理成文件）；`grill-with-docs` 本身只是呼叫這兩者的一行入口，三個技能要一起裝，缺任何一個都不完整
- 安裝（在**產品倉庫**內執行，三工具通用）：

  ```bash
  npx skills add mattpocock/skills --skill grill-with-docs --skill grilling --skill domain-modeling -a claude-code -a codex -a opencode -y
  ```

- 觸發方式：**手動**，人類在對話中打 `/grill-with-docs` 才會啟動，工具不會自己主動叫用（技能定義檔明確標示 `disable-model-invocation: true`）
- 產物位置：專案根目錄 `CONTEXT.md`（或 `CONTEXT-MAP.md` 標記的多 context 情境下，各自的 `CONTEXT.md`）、`docs/adr/`；兩者都是「有內容才建立」，不會一開始就產生空檔案

### OpenSpec

- 來源：`github.com/Fission-AI/OpenSpec`，npm 套件 `@fission-ai/openspec`
- 安裝與初始化（在**產品倉庫**內執行）：

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
- 產物位置：`openspec/specs/<domain>/spec.md`（現行規格）、`openspec/changes/<change-name>/{proposal.md,design.md,tasks.md,specs/}`（變更提案，已 archive 的移到 `openspec/changes/archive/`）
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

上述安裝方式都需要對外網路（npm registry、GitHub、各工具的外掛市集）。半導體/嵌入式相關廠商的內網經常無法直接連外，這種情況改用本倉庫既有的 git subtree 機制，把（可離線存取的）**靜態內容**預先併入 `external/`：

- `external/mattpocock-skills/`（含 grill-with-docs 及其依賴的 grilling、domain-modeling）、`external/superpowers/` 已在 `external/subtrees.yaml` 登記為 PENDING，逐步指令見各自目錄下的 `PENDING.md`，機制原理見 `docs/how-sync-upstream.md`「只同步第三方倉庫的一部分」一節
- OpenSpec 不透過 subtree 分發（見 `registry/frameworks.yaml` 該項目的 `subtree_ref: null`）——它是要在產品倉庫內執行的 CLI 工具，不是被動參考內容，離線環境下需要另外解決 npm registry 的鏡像問題，不在本倉庫範圍內

**注意 subtree 進來的是什麼、不是什麼**：vendor 進來的只有 skill 說明文字本身（可離線讀、可搜尋、可稽核），**不包含**讓 skill 真正「自動觸發」的外掛掛載機制（Claude Code 的 plugin 系統、Codex 的外掛市集等）——那些機制與各工具版本綁定，subtree 拿不到，離線環境下若要讓自動觸發也生效，需要另外處理內部鏡像（私有 npm registry、內部 git server），這需要團隊自行評估。

## 跟三個工具讀取機制的關係

`docs/tool-compatibility.md` 講的是這個倉庫自己的 `AGENTS.md`/`CLAUDE.md`/`opencode.json` 入口檔如何被三個工具讀到；本文件這三個框架用的是另一組獨立機制（各工具自己的 skill 目錄、外掛市集），兩組機制互不取代、同時並存，細節見該文件「外部框架的多工具轉接方式」一節，不在這裡重複。

## 跟 release 流程的銜接

已安裝 OpenSpec 時，一個 change 的 archive 時機建議對齊 `workflow/release.md` 裡 `product-cicd-platform` 的 CI 驗證通過、準備交接給 `product-release` 的時間點——archive 後 `openspec/specs/` 才會是這次變更後的最新狀態，過早 archive 等於在還沒驗證過的狀態下宣告「這就是現行規格」。

## 參考來源

這個領域的工具更新速度快，若內容與實際行為有出入，以各工具當下的官方文件為準。

- OpenSpec：`github.com/Fission-AI/OpenSpec`（`docs/getting-started.md`、`docs/supported-tools.md`、`docs/cli.md`）
- superpowers：`github.com/obra/superpowers`（README 的 Installation、The Basic Workflow 兩節）
- grill-with-docs：`github.com/mattpocock/skills`（`skills/engineering/grill-with-docs/SKILL.md` 及其依賴的 `skills/productivity/grilling/SKILL.md`、`skills/engineering/domain-modeling/SKILL.md`）
- 跨工具 skill 安裝機制（`npx skills add`）：`github.com/vercel-labs/skills`
