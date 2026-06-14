@echo off
REM ──────────────────────────────────────────────────────────────────
REM  GPU Price Tracker — Windows タスクスケジューラ 登録スクリプト
REM  ※ 管理者権限で実行してください (右クリック → 管理者として実行)
REM ──────────────────────────────────────────────────────────────────

SET TASK_NAME=GPU_Price_Tracker
SET SCRIPT_DIR=%~dp0
SET PYTHON_CMD=python

REM ── Python のパスを自動検出 ──
where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    where python3 >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Python が見つかりません。先に Python をインストールしてください。
        echo         https://www.python.org/downloads/
        pause
        exit /b 1
    )
    SET PYTHON_CMD=python3
)

REM ── 依存パッケージのインストール ──
echo [INFO] 必要なパッケージをインストールします...
%PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet

REM ── 既存タスクを削除（再登録のため）──
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

REM ── タスク登録（毎朝 08:30 に実行）──
schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%scraper.py\"" ^
  /SC DAILY ^
  /ST 08:30 ^
  /F ^
  /RL HIGHEST ^
  /IT

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] タスクスケジューラへの登録が完了しました。
    echo      毎朝 08:30 に自動でデータを取得します。
    echo.
    echo [INFO] 今すぐ初回実行しますか？ (Y/N)
    set /p RUNNOW=
    if /i "%RUNNOW%"=="Y" (
        echo [INFO] scraper.py を実行中...
        %PYTHON_CMD% "%SCRIPT_DIR%scraper.py"
        echo [INFO] 完了しました。dashboard.html をブラウザで開いてください。
    )
) ELSE (
    echo [ERROR] タスク登録に失敗しました。管理者権限で実行しているか確認してください。
)

pause
