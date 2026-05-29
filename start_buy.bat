@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title BUFF Item Buyer

echo ============================================
echo   BUFF Item Auto-Buyer
echo ============================================
echo.
echo   1. Search by name (find goods_id)
echo   2. Buy by goods_id or URL
echo.
set /p ACTION="Select action (1/2, default 2): "
if "!ACTION!"=="" set ACTION=2

if "!ACTION!"=="1" (
    echo.
    set /p KEYWORD="Enter search keyword: "
    if "!KEYWORD!"=="" (
        echo Error: keyword cannot be empty
        pause
        exit /b 1
    )
    set /p SEARCH_LIMIT="Number of results (default 20): "
    if "!SEARCH_LIMIT!"=="" set SEARCH_LIMIT=20
    echo.
    python "%~dp0item_buyer.py" --search "!KEYWORD!" --limit !SEARCH_LIMIT!
    echo.
    set /p GOODS_ID="Enter goods_id from above to buy (or press Enter to exit): "
    if "!GOODS_ID!"=="" (
        echo Done.
        pause >nul
        exit /b 0
    )
    goto buy
)

echo.
echo Supported input:
echo   - URL:  https://buff.163.com/goods/12345
echo   - ID:   12345
echo.
set /p GOODS_ID="Enter item URL or goods_id: "

if "!GOODS_ID!"=="" (
    echo Error: goods_id cannot be empty
    pause
    exit /b 1
)

:buy
set /p MAX_PRICE="Max price in CNY (default 1.0): "
if "!MAX_PRICE!"=="" set MAX_PRICE=1.0

set /p MAX_ITEMS="Max buy count (default 5): "
if "!MAX_ITEMS!"=="" set MAX_ITEMS=5

echo.
echo Select mode:
echo   1. Single run ^(check once and exit^)
echo   2. Polling monitor ^(keep checking^)
set /p MODE="Enter choice (1/2, default 1): "
if "!MODE!"=="" set MODE=1

set EXTRA_ARGS=

if "!MODE!"=="2" (
    set /p INTERVAL="Polling interval in seconds (default 30): "
    if "!INTERVAL!"=="" set INTERVAL=30
    set /p MAX_ROUNDS="Max rounds, 0=infinite (default 0): "
    if "!MAX_ROUNDS!"=="" set MAX_ROUNDS=0
    set EXTRA_ARGS=--interval !INTERVAL! --max-rounds !MAX_ROUNDS!
    echo.
    echo ============================================
    echo   Item:       !GOODS_ID!
    echo   Max price:  !MAX_PRICE! CNY
    echo   Max count:  !MAX_ITEMS!
    echo   Mode:       Polling every !INTERVAL!s
    echo   Max rounds: !MAX_ROUNDS!
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   Item:       !GOODS_ID!
    echo   Max price:  !MAX_PRICE! CNY
    echo   Max count:  !MAX_ITEMS!
    echo   Mode:       Single run
    echo ============================================
)

echo.

python "%~dp0item_buyer.py" "!GOODS_ID!" --max-price !MAX_PRICE! --max-items !MAX_ITEMS! !EXTRA_ARGS!

if !errorlevel! neq 0 (
    echo.
    echo Script exited with error code: !errorlevel!
)

echo.
echo Press any key to close...
pause >nul
