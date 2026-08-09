# 工具相容性：Codex / Claude Code / opencode

## 核心策略：單一事實來源 + 輕量轉接

`AGENTS.md` 是唯一「真的」被維護的內容。`CLAUDE.md`、`opencode.json` 都只是轉接器，內容不重複寫死，只負責告訴各工具去讀 `AGENTS.md`。新增任何規則一律改 `AGENTS.md`（或它指向的 `workflow/` `governance/` 等），不要去轉接器裡加內容，否則規則會分岔成兩份、之後對不起來。

## 各工具讀取方式對照

| 工具 | 原生讀取檔案 | 需要轉接檔？ | 本倉庫的轉接方式 |
|---|---|---|---|
| Codex CLI | `AGENTS.md`（專案根目錄） | 不需要 | 原生支援，直接讀 |
| opencode | `AGENTS.md`（專案根目錄，優先於 `CLAUDE.md` fallback） | 不需要 | 原生支援；仍附上最小的 `opencode.json` 供未來擴充 |
| Claude Code | `CLAUDE.md`（專案根目錄） | 需要 | `CLAUDE.md` 用 `@AGENTS.md` 匯入語法帶入內容 |

## Claude Code：為什麼需要 `CLAUDE.md`

Claude Code 目前原生只讀 `CLAUDE.md`，還不會自動讀 `AGENTS.md`——這是社群反應熱烈（anthropics/claude-code 倉庫上有多個相關 issue）但截至目前官方尚未承諾支援的功能請求。官方文件記載的 `@path` 檔案匯入語法可以把 `AGENTS.md` 的內容帶進 `CLAUDE.md`，本倉庫根目錄的 `CLAUDE.md` 就是這個最小轉接器：只有一行 `@AGENTS.md`，加上少數幾條「只有 Claude Code 需要知道」的補充（例如 auto memory 的使用邊界），不重複抄一份規則。

## opencode：`opencode.json` 的角色

opencode 會原生讀取根目錄的 `AGENTS.md`，不需要任何額外設定就能運作；若同一個專案同時有 `AGENTS.md` 與 `CLAUDE.md`，opencode 只採用 `AGENTS.md`。本倉庫仍附上一個最小的 `opencode.json`，純粹是為了：

1. 明確聲明這個倉庫遵循的 config schema
2. 預留擴充點——未來若要用 opencode 的具名 agent 機制，對應 `registry/providers.yaml` 定義的角色（planner / implementer / verifier / reviewer / researcher），可以直接在 `agent` 欄位擴充，不需要重新設計

opencode 的 `opencode.json` 也支援 `instructions` 陣列來額外載入 `AGENTS.md` 以外的檔案（例如子目錄各自的 `AGENTS.md`、或特定規範文件）。本倉庫刻意留空，因為 `AGENTS.md` 已經教 AI 代理人在需要時主動去讀 `workflow/` `governance/` 等檔案，不需要在 session 一開始就全部預先載入、浪費 context。

## 多倉庫情境：product-cicd-platform 如何讀到 ai-dev-platform

`AGENTS.md` 第 3 節的「平行參考模式」只講了意圖（AI 執行任務時讀取旁邊
`ai-dev-platform/` 目錄），沒講機制——三個工具的原生探索範圍都**不包含
sibling 目錄**：

- **Codex CLI**：只沿「git root → cwd」這條路徑往下找 `AGENTS.md`。
  `product-cicd-platform` 是獨立 git repo，Codex 不會走到旁邊的
  `ai-dev-platform/`，即使兩者是平行目錄。
- **opencode**：官方文件明講不會自動解析 `AGENTS.md` 裡的 `@file` 參照；
  `@` 在 opencode 的 `AGENTS.md` 裡只是純文字，不是真的 import。
- **Claude Code**：`@path` import 是三者中唯一保證可靠的跨檔案機制，但要
  有一個會被探索到的 `CLAUDE.md`（在 cwd 往上的路徑上）明確寫出來才行，
  不會自動發生。

因此 `product-cicd-platform` 一定要有自己的入口檔，`templates/product-entrypoint/`
提供三個工具各自最可靠的機制：

| 檔案 | 對應工具 | 可靠性 |
|---|---|---|
| `CLAUDE.md.template` | Claude Code | 高——`@` import 是 CLI 層級保證載入，不依賴 AI 自己判斷要不要讀 |
| `opencode.json.template` | opencode | 高——`instructions` 欄位是官方文件明確保證的機制 |
| `AGENTS.md.template` | Codex CLI（也是 opencode/Claude Code 最終讀到的內容來源） | 中——純文字指示 AI 去讀 `../ai-dev-platform/AGENTS.md`，沒有 CLI 層級保證，依賴模型的 agentic 行為主動讀取 |

Codex 這條路徑的可靠性跟本倉庫其餘部分本來就依賴的機制一樣（例如
`AGENTS.md` 指示 AI 遇到領域問題先讀 `docs/domain-adaptation.md`，也是純
文字指示、沒有結構性保證）——不是這裡新引入的風險，只是目前沒有更強的
機制可以疊加。若特別在意 Codex 的可靠性，用 session 一開始明確提醒它讀
`../ai-dev-platform/AGENTS.md`，或改用內嵌模式讓內容直接在同一個 git repo
的探索路徑上。

## 外部框架（OpenSpec / superpowers / grill-with-docs）的多工具轉接方式

以上談的都是「這個倉庫自己的 `AGENTS.md`/`CLAUDE.md`/`opencode.json` 三個入口檔」如何被三個工具讀到。`docs/external-frameworks.md` 提到的三個外部框架用的是另一組機制，彼此獨立、互不取代：

- OpenSpec：以 `.claude/skills/`、`.codex/skills/`、`.opencode/skills/`（及 Claude Code、opencode 各自額外的 command 轉接器）分發，由 `openspec init` 在**產品倉庫**內產生，不是本倉庫 `AGENTS.md` 那套匯入機制的延伸
- grill-with-docs：透過 `npx skills add` 分發，落地位置同樣是各工具自己的 skill 目錄
- superpowers：透過各工具原生的外掛市集機制安裝（Claude Code 的 `/plugin`、Codex CLI 的 `/plugins`、opencode 的自訂安裝腳本），跟 skill 目錄又是另一套機制

三套機制（入口檔匯入、skill 目錄、外掛市集）同時存在，AI 代理人不需要為了統一它們而做任何事——各工具會依自己支援的機制分別讀取。逐一框架的確切安裝指令與離線替代方案見 `docs/external-frameworks.md`，不在這裡重複。

## 若要新增別的工具

多數新一代工具（例如 Cursor、Windsurf、Cline）已經直接支援讀取專案根目錄的 `AGENTS.md`，通常不需要額外轉接檔。新增前，先確認該工具的官方文件是否已原生支援 `AGENTS.md`；如果沒有，比照 `CLAUDE.md` 的模式做一個最小轉接器，不要複製第二份內容。

## 專門 skill / sub-agent 委派：各工具的實際機制

`governance/agent-discipline.md` 1.2 節講的是「什麼時候該委派」，這裡補「各工具實際上怎麼設定」——這部分本來就是工具相關細節，不強行塞進 governance 保持產品無關：

- **Claude Code**：官方的 subagent 機制，用 markdown 檔案定義，放在專案層級 `.claude/agents/` 或使用者層級 `~/.claude/agents/`，各自有獨立 context window、可限制可用工具。Claude 會依委派設定自動比對任務內容決定要不要交給某個 subagent。細節見 `code.claude.com/docs/en/sub-agents`。
- **opencode**：對應 `opencode.json` 的 `agent` 欄位（見本倉庫 `opencode.json` 的預留擴充點），可以對應 `registry/providers.yaml` 定義的角色各自設定。
- **Codex**：委派機制隨版本演進較快，設定前建議直接查 Codex 當下的官方文件，這裡不寫死可能過時的細節。

## 來源

以下為主要參考來源。這個領域的工具更新速度快，若內容與實際行為有出入，以各工具當下的官方文件為準：

- Claude Code 記憶機制官方文件：`code.claude.com/docs/en/memory`
- Claude Code subagents 官方文件：`code.claude.com/docs/en/sub-agents`
- Claude Code 尚未原生支援 `AGENTS.md` 的功能請求討論：`github.com/anthropics/claude-code`（issue #6235、#34235）
- opencode 規則文件（`AGENTS.md` 原生支援、與 `CLAUDE.md` 的 fallback 優先序）：`opencode.ai/docs/rules/`
- opencode 設定文件（`opencode.json`、`instructions` 欄位）：`opencode.ai/docs/config/`
- AGENTS.md 開放標準：`agents.md`
