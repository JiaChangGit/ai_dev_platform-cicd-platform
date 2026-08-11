# 尚未同步

這個目錄是 `mattpocock-skills` subtree 的預留位置，目前尚未執行同步。

## 為什麼是整個 `skills/`，不是只有 `grill-with-docs` 一個資料夾

最初的設計是只 split `mattpocock/skills` 裡的 `skills/engineering/grill-with-docs/` 子資料夾。實際查證後發現這樣行不通：`grill-with-docs/SKILL.md` 本身只有一行——「用 `/domain-modeling` 技能跑一次 `/grilling`」——實際邏輯在另外兩個資料夾：`skills/productivity/grilling/` 與 `skills/engineering/domain-modeling/`，兩者跟 `grill-with-docs` 不同層級（一個在 `productivity/`、一個在 `engineering/`），沒有比 `skills/` 本身更小的共同上層資料夾能一次涵蓋三者。

追查這條相依關係時，也在 `domain-modeling/SKILL.md` 裡看到對 `/adr` 的引用，但倉庫裡沒有對應的 `/adr` 資料夾，判斷是指「產出 ADR 格式內容」這個動作本身，不是另一個技能資料夾——這也是「narrow split 容易漏掉隱藏相依」的例子。與其逐一追查、往後每次上游新增交叉引用就要重新確認一次，改成同步整個 `skills/`（948K，體積小）一次涵蓋所有現在與未來的內部相依，維護成本更低、也更不容易出錯。代價是連帶會拿到 `grill-with-docs` 以外、Matt Pocock 這個倉庫其他不相關的技能，可自行刪減不需要的部分。

## 同步步驟

完整原理見 `../../docs/how-sync-upstream.md`「只同步第三方倉庫的一部分」：

1. Fork `https://github.com/mattpocock/skills` 到你自己的 GitHub 帳號
2. 另外找一個資料夾 clone 你的 fork：

   ```bash
   git clone https://github.com/JiaChangGit/skills.git /path/to/mattpocock-skills-clone
   cd /path/to/mattpocock-skills-clone
   git subtree split --prefix=skills -b extract-mattpocock-skills
   git push origin extract-mattpocock-skills
   ```

3. 回到 `ai-dev-platform`，確認 `external/subtrees.yaml` 的 `mattpocock-skills` 項目 `repo` 已指到你的 fork
4. Commit 這個修改：

   ```bash
   git add external/subtrees.yaml
   git commit -m "chore(sync): point mattpocock-skills at fork"
   ```

5. 在倉庫根目錄執行：

   ```bash
   scripts/sync.sh add mattpocock-skills
   ```

6. **補回 LICENSE**：`git subtree split --prefix=skills` 不會帶進上游根目錄的 `LICENSE` 檔（mattpocock/skills 是 MIT License）。同步完成後，手動把上游倉庫根目錄的 `LICENSE` 內容複製一份到 `external/mattpocock-skills/LICENSE`，保留原作者的著作權聲明——這是授權條款要求的步驟，不能省略

執行成功後，這個目錄會被整個 `skills/` 的實際內容取代，`grill-with-docs` 會在 `engineering/grill-with-docs/` 底下。

## 另一條路：不 vendor，直接線上安裝

不需要離線/稽核用的靜態副本的話，可以跳過以上步驟，直接在**產品倉庫**內執行（三工具通用）。**三個技能要一起裝**，只裝 `grill-with-docs` 會缺少它實際依賴的另外兩個：

```bash
npx skills add mattpocock/skills --skill grill-with-docs --skill grilling --skill domain-modeling -a claude-code -a codex -a opencode -y
```

只帶 `--skill grill-with-docs` 這條指令執行雖然會成功，但裝出來的 `SKILL.md` 只有一行指向另外兩個技能，缺了它們就等於裝了一個沒有內容的殼，所以務必三個一起裝。

兩條路徑不衝突，也可以只做其中一個。差異與各自適用情境見 `../../docs/external-frameworks.md`。
