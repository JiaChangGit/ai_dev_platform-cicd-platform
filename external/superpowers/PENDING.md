# 尚未同步

這個目錄是 `superpowers` subtree 的預留位置，目前尚未執行同步。

來源是 `obra/superpowers` 倉庫裡的 `skills/` 子資料夾（只要方法論本身的 skill 內容，不要 `.claude-plugin/`、`.codex-plugin/`、`hooks/` 等安裝期才需要的機制檔案），流程與 `grill-with-docs` 相同，完整原理見 `../../docs/how-sync-upstream.md`「只同步第三方倉庫的一部分」：

1. Fork `https://github.com/obra/superpowers` 到你自己的 GitHub 帳號
2. 另外找一個資料夾 clone 你的 fork：

   ```bash
   git clone https://github.com/JiaChangGit/superpowers.git /path/to/superpowers-clone
   cd /path/to/superpowers-clone
   git subtree split --prefix=skills -b extract-skills
   git push origin extract-skills
   ```

3. 回到 `ai-dev-platform`，確認 `external/subtrees.yaml` 的 `superpowers` 項目 `repo` 已指到你的 fork
4. Commit 這個修改：

   ```bash
   git add external/subtrees.yaml
   git commit -m "chore(sync): point superpowers at fork"
   ```

5. 在倉庫根目錄執行：

   ```bash
   scripts/sync.sh add superpowers
   ```

6. **補回 LICENSE**：`git subtree split --prefix=skills` 不會帶進上游根目錄的 `LICENSE` 檔（obra/superpowers 是 MIT License）。同步完成後，手動把上游倉庫根目錄的 `LICENSE` 內容複製一份到 `external/superpowers/LICENSE`，保留原作者的著作權聲明——這是授權條款要求的步驟，不能省略

執行成功後，這個目錄會被 `skills/` 底下的實際內容取代。

## 這個 subtree 拿不到什麼

vendor 進來的只有 skill 說明文字本身（靜態參考內容），**不包含**讓 skill 真正「自動觸發」的外掛掛載機制（Claude Code 的 plugin 系統、Codex 的外掛市集等）——那些機制與各工具版本綁定，subtree 拿不到，一定要另外照 `../../docs/external-frameworks.md` 的各工具安裝指令啟用。這個 subtree 的價值是離線可讀、可稽核、可搜尋，不是取代正式安裝。

## 另一條路：直接照各工具指令線上安裝

不需要離線副本的話，可以跳過以上步驟，直接照 `../../docs/external-frameworks.md` 的表格，依實際使用的工具（Claude Code / Codex CLI / opencode）分別安裝——三個工具的外掛機制彼此獨立，沒有單一指令能通吃。
