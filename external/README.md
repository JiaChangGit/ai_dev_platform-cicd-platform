# external/

存放透過 **git subtree** 同步進來的第三方資源。與 submodule 不同，這裡的內容是實際併入本倉庫的檔案，`git clone` 或下載 ZIP 後都能直接看到完整內容。

## 目前追蹤的項目

見 `subtrees.yaml`，或執行：

```bash
../scripts/sync.sh list
```

## 加入 / 更新

見 [`../docs/how-sync-upstream.md`](../docs/how-sync-upstream.md) 的完整說明。快速版：

```bash
# 第一次加入：先把 subtrees.yaml 中的 repo 換成你自己的 fork，並 commit 這個修改
# （git subtree 要求工作目錄乾淨才能執行，編輯完不 commit 直接 add 一定會失敗）
git add external/subtrees.yaml && git commit -m "chore(sync): update subtrees.yaml"
../scripts/sync.sh add <name>

# 拉取上游更新（工作目錄同樣要先保持乾淨）
../scripts/sync.sh pull <name>
```

## 注意事項

- 不建議直接手動修改這裡的檔案；若需要客製，優先在你自己 fork 的第三方倉庫上修改，再同步下來，避免下次 pull 時產生大量衝突
- 每個子目錄的授權條款以其原始倉庫為準，本倉庫根目錄的 `LICENSE` 不涵蓋 `external/` 底下的內容
- **整倉庫同步**（`anthropic-skills`、`openai-cookbook`）：上游的 `LICENSE` 檔案會隨整個倉庫一起併入，不用額外處理，但同步前先確認該倉庫的授權條款是否符合你的使用情境（尤其打算公開這個倉庫的話）
- **子資料夾同步**（`mattpocock-skills`、`superpowers`）：`git subtree split --prefix=X` 只會帶進 `X` 底下的檔案，若上游的 `LICENSE` 放在倉庫根目錄（這兩個都是），split 出來的內容**不會包含 LICENSE 檔**。兩者上游都是 MIT License，同步完成後記得手動在對應目錄（`external/mattpocock-skills/`、`external/superpowers/`）補一份 `LICENSE`，內容抄自上游倉庫根目錄的 `LICENSE`，保留原作者的著作權聲明——這是 MIT 授權條款要求的，不是選用的裝飾
