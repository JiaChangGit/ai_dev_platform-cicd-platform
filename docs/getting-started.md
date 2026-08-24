# 建立與使用產品專案

本文件供第一次使用平台的開發者建立產品開發與 release 儲存庫。它不替產品決定套件、硬體、商業邏輯或發布帳號。

## 1. 準備環境

平台腳本與 GitHub CI 使用 Python 3.12；本機至少需要 Git、Bash、Python 3 與 PyYAML。Ubuntu／WSL 可執行：

```bash
python3 --version
git --version
python3 -m pip install --user "PyYAML==6.0.3"
```

Android 案例另外需要 JDK 17、Android SDK 36 與 Gradle 9.4.1；SSD 案例需要 `make` 與支援 C11 的編譯器。

## 2. 取得平台

### 維護來源

需要修改平台時才 clone 來源儲存庫：

```bash
cd /absolute/path/to/Work
git clone https://github.com/JiaChangGit/ai_dev_platform-cicd-platform.git
cd ai_dev_platform-cicd-platform
bash scripts/check.sh
```

### 穩定唯讀包

目前 GitHub 尚未發布第一份正式 Release。完成 `v1.5.0` 發行後，從來源 repository 的 Releases 下載 ZIP 與 `.sha256`，再以來源儲存庫內的安裝器執行：

```bash
cd /absolute/path/to/Work/ai_dev_platform-cicd-platform
python3 -B scripts/install_platform.py \
  /absolute/path/to/ai-dev-platform-1.5.0.zip \
  --checksum /absolute/path/to/ai-dev-platform-1.5.0.zip.sha256 \
  --work-root /absolute/path/to/Work \
  --dry-run
```

dry-run 通過後移除 `--dry-run`。安裝器會核對 sidecar SHA-256、ZIP 逐檔 hash、檔案權限與 consumer 自我檢查，再原子替換 `Work/ai-dev-platform/`。目標若是 Git 儲存庫會拒絕覆寫。

## 3. 建立產品

先選產品領域與 CI。所有命令先跑 dry-run，再移除 `--dry-run`。

### Android App

```bash
cd /absolute/path/to/Work/ai-dev-platform
python3 -B scripts/init_product.py \
  --name sample-android \
  --display-name "Sample Android" \
  --domain android \
  --ci github-actions \
  --with-example \
  --dry-run
```

### SSD PCIe 韌體

```bash
python3 -B scripts/init_product.py \
  --name sample-ssd-fw \
  --display-name "Sample SSD Firmware" \
  --domain ssd-pcie-fw \
  --ci gitlab-ci \
  --with-example \
  --dry-run
```

### 規格閱讀與靜態手冊

```bash
python3 -B scripts/init_product.py \
  --name sample-spec-handbook \
  --display-name "Sample Spec Handbook" \
  --domain generic \
  --ci github-actions \
  --build-command "python3 -B examples/spec-notes/validate.py" \
  --test-command "python3 -B examples/spec-notes/validate.py" \
  --lint-command "python3 -B examples/spec-notes/validate.py" \
  --package-command "python3 -m zipfile -c dist/spec-handbook.zip examples/spec-notes" \
  --artifact-path "dist/spec-handbook.zip" \
  --dry-run
```

工具建立：

```text
Work/
├── ai-dev-platform/
├── sample-*-cicd-platform/
└── sample-*-release/
```

兩個新儲存庫各自有 `.git`、入口檔、README、CODEOWNERS 與選定的 CI 骨架；工具遇到既有目錄會停止，不會覆寫。

## 4. 補齊產品內容

1. 在 `*-cicd-platform/docs/domain-standards.md` 記錄產品採用的官方規格、工具鏈版本、查詢日期與未決事項。
2. 以實際指令取代初始化骨架中的 build、test、lint、security 與 package 佔位內容。
3. 寫 `docs/architecture.md` 與第一份 ADR，描述實際元件、資料流、限制與選型原因。
4. 執行本機驗證，再建立功能分支與 PR。
5. 依 `docs/repository-operations.md` 建立 GitHub 遠端；GitLab 若只作備份鏡像，不在 GitLab 直接開發。

## 5. 驗證內建案例

```bash
cd /absolute/path/to/Work/ai_dev_platform-cicd-platform
make -C examples/ssd-pcie-fw clean all test lint package
python3 -B examples/spec-notes/validate.py
cd examples/android-app
gradle --no-daemon :app:assembleDebug
gradle --no-daemon :app:testDebugUnitTest
gradle --no-daemon :app:lintDebug
```

SSD ELF 是 host 模擬成品；Android APK 是除錯簽章；規格內容為虛構。三者都不能直接成為產品成品或正式規格。

## 6. 既有專案

不要執行初始化器覆蓋既有專案。先依 `docs/how-adopt-existing.md` 只讀盤點分支、歷史、CI、測試、架構與團隊規則，再逐項導入。
