# 尚未同步

這個目錄是 `openai-cookbook` subtree 的預留位置，目前尚未執行同步。

1. 到你自己的 GitHub 帳號 fork 對應的第三方倉庫
2. 編輯 `../subtrees.yaml`，把 `openai-cookbook` 項目的 `repo` 換成你的 fork URL
3. Commit 這個修改（git subtree 要求工作目錄乾淨才能執行，這步不能省）：

   ```bash
   git add external/subtrees.yaml
   git commit -m "chore(sync): point openai-cookbook at fork"
   ```

4. 在倉庫根目錄執行：

   ```bash
   scripts/sync.sh add openai-cookbook
   ```

執行成功後，這個目錄會被第三方倉庫的實際內容取代（包含這份 `PENDING.md` 也會被移除或覆蓋）。
