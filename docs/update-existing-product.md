# 更新已導入平台的 dev project

本文件供已經具備 `Work/ai-dev-platform`、`<product>-cicd-platform` 與 `<product>-release` 的產品使用。第一次把平台導入既有 repository 時，先依 `docs/how-adopt-existing.md` 完成差異盤點；不要把本文件當作第一次導入流程。

## 更新會改變什麼

產品的 `.ai/product.json` 使用 `platformVersionPolicy: always-current`，因此替換平行的 `Work/ai-dev-platform` 後，下一次 Codex、Claude Code 或 opencode 任務會直接讀取新規則。更新平台不會自動改寫產品程式碼、CI YAML、Gradle、Makefile、入口檔或 release repository。

同一個 `Work/ai-dev-platform` 可能被多個產品共用。更新前須列出所有產品，安排共同驗證時段，不能只測其中一個就宣告整個 workspace 完成。

## Step 0：唯讀盤點

先確認產品與 release repository 沒有未辨識的本機修改：

```bash
git -C /absolute/path/to/Work/my-product-cicd-platform status --short --branch
git -C /absolute/path/to/Work/my-product-release status --short --branch

python3 -B /absolute/path/to/Work/ai-dev-platform/scripts/audit_workspace.py \
  /absolute/path/to/Work --json
```

若 audit 原本就失敗，先保存錯誤輸出並區分「既有問題」與「更新造成的問題」。不要為了升級平台而改寫產品歷史或清除不明檔案。

## Step 1：下載並驗證正式 Release

以下使用已在 2026-08-25 驗證為非 draft、非 prerelease 的 `1.5.0`；改用其他版本前，先確認該版本已完成 promotion：

```bash
PLATFORM_VERSION=1.5.0
DOWNLOAD_DIR=/absolute/path/to/downloads/ai-dev-platform-${PLATFORM_VERSION}

mkdir -p "${DOWNLOAD_DIR}"
gh release download "v${PLATFORM_VERSION}" \
  -R JiaChangGit/ai_dev_platform-cicd-platform \
  --pattern "ai-dev-platform-${PLATFORM_VERSION}*" \
  --dir "${DOWNLOAD_DIR}"

cd "${DOWNLOAD_DIR}"
sha256sum -c "ai-dev-platform-${PLATFORM_VERSION}.zip.sha256"
sha256sum -c "ai-dev-platform-${PLATFORM_VERSION}.spdx.json.sha256"
sha256sum -c "ai-dev-platform-${PLATFORM_VERSION}.provenance.sigstore.json.sha256"
gh attestation verify "ai-dev-platform-${PLATFORM_VERSION}.zip" \
  -R JiaChangGit/ai_dev_platform-cicd-platform
```

核對 Release Note 的破壞性變更、來源 tag、commit、CI run、SBOM 與 evidence。只看到 ZIP 存在不代表 promotion 已完成。

## Step 2：先跑安裝 dry-run

使用目前已安裝平台的 installer。若 Release Note 明確要求新版 bootstrap installer，才改用同版已驗證 source tag：

```bash
PLATFORM_VERSION=1.5.0
DOWNLOAD_DIR=/absolute/path/to/downloads/ai-dev-platform-${PLATFORM_VERSION}

python3 -B /absolute/path/to/Work/ai-dev-platform/scripts/install_platform.py \
  "${DOWNLOAD_DIR}/ai-dev-platform-${PLATFORM_VERSION}.zip" \
  --checksum "${DOWNLOAD_DIR}/ai-dev-platform-${PLATFORM_VERSION}.zip.sha256" \
  --work-root /absolute/path/to/Work \
  --dry-run
```

安裝器若發現 `Work/ai-dev-platform/.git` 會拒絕替換。這代表目標是 maintenance checkout，不應直接刪除 `.git`；先釐清並把維護來源與唯讀安裝目錄分開。

## Step 3：原子更新共用平台

dry-run 通過後，以相同命令移除 `--dry-run`：

```bash
PLATFORM_VERSION=1.5.0
DOWNLOAD_DIR=/absolute/path/to/downloads/ai-dev-platform-${PLATFORM_VERSION}

python3 -B /absolute/path/to/Work/ai-dev-platform/scripts/install_platform.py \
  "${DOWNLOAD_DIR}/ai-dev-platform-${PLATFORM_VERSION}.zip" \
  --checksum "${DOWNLOAD_DIR}/ai-dev-platform-${PLATFORM_VERSION}.zip.sha256" \
  --work-root /absolute/path/to/Work
```

安裝器會在 staging 中驗證逐檔 hash、權限與 consumer self-check，成功後才原子替換目標；安裝階段失敗時會保留或還原舊平台。

## Step 4：驗證 workspace 與每個產品

```bash
bash /absolute/path/to/Work/ai-dev-platform/scripts/check.sh --consumer

python3 -B /absolute/path/to/Work/ai-dev-platform/scripts/audit_workspace.py \
  /absolute/path/to/Work --json
```

接著逐一進入每個產品 repository，依產品定義執行 lint／靜態檢查、test、build、package。例如：

```bash
# SSD firmware
make lint
make test
make all
make package

# Android
gradle --no-daemon :app:lintDebug
gradle --no-daemon :app:testDebugUnitTest
gradle --no-daemon :app:assembleDebug

# spec handbook
python3 -B validate.py
mkdir -p dist
python3 -m zipfile -c dist/spec-handbook.zip \
  SAMPLE.md source-register.md sample-spec.md reading-notes.md index.html validate.py
```

最後用開發工具從產品根目錄開始新任務，要求它回報讀到的平台版本、task type 與 workflow path；不要依賴更新前已開啟的長期 session。

## Step 5：判斷產品 repository 是否需要 migration PR

平台規則會立即更新，但產品自有檔案不會自動同步。閱讀新版本 CHANGELOG，再逐項判斷：

- 只有文件或 workflow 規則更新：產品通常不需修改，只要產品驗證通過。
- 初始化模板或 CI skeleton 更新：既有產品不會自動變更；開功能分支，人工比較並只採用適用差異。
- CLI 參數或 evidence schema 變更：更新產品 CI／release adapter，重新驗證後才發行。
- Android、SSD 工具鏈或規格版本變更：先查官方來源並更新產品的 `docs/domain-standards.md`，不因平台範例更新就自動升級產品。

若新版 CHANGELOG 指出產品 GitHub Actions 骨架已更新，既有產品應檢查第三方 action 是否固定完整 commit SHA，並確認 job 順序為 lint／靜態檢查、test、build。這類修改應走產品自己的 PR、CI 與獨立審查，不直接改 `main`。

## 回復到上一個平台版本

保留上一版已驗證的 ZIP、`.sha256`、SBOM 與 provenance。若平台更新成功但產品驗證失敗，先保存失敗輸出，再用相同 installer 對上一版 ZIP 執行 dry-run 與正式安裝。不要用 `git checkout`、手動覆蓋檔案或把 `.git` 加進唯讀平台。

回復共用平台後重新執行 workspace audit 與受影響產品的驗證；產品 repository 若已有獨立 migration commit，依共用歷史狀態使用 `git revert`，不要 force push `main`。
