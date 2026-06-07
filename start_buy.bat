@echo off
setlocal enabledelayedexpansion
set PYTHONIOENCODING=gbk
title BUFF 自动化购买工具集

:menu
cls
echo ============================================
echo   BUFF 自动化购买工具集
echo ============================================
echo.
echo   1. 指定饰品购买 (item_buyer)
echo   2. 涂鸦饰品购买 (buff_buyer)
echo   3. 挂件搜枪 (charm_searcher)
echo   4. 价格监控仪表盘 (dashboard)
echo.
set /p TOOL="请选择工具 (1/2/3/4): "
if "!TOOL!"=="" goto menu

if "!TOOL!"=="1" goto item_buyer
if "!TOOL!"=="2" goto buff_buyer
if "!TOOL!"=="3" goto charm_searcher
if "!TOOL!"=="4" goto dashboard

echo 无效选择，请重试
pause >nul
goto menu

:: ============================================
:: 工具 1：指定饰品购买
:: ============================================
:item_buyer
cls
echo ============================================
echo   指定饰品购买
echo ============================================
echo.
echo   1. 搜索饰品 (按名称查找 goods_id)
echo   2. 购买饰品 (按 goods_id 或 URL)
echo   3. 批量监控 (从文件读取多个商品)
echo   0. 返回主菜单
echo.
set /p ACTION="请选择 (1/2/3/0, 默认 2): "
if "!ACTION!"=="" set ACTION=2
if "!ACTION!"=="0" goto menu

if "!ACTION!"=="1" (
    echo.
    set /p KEYWORD="搜索关键词 (如 AK-47 | 二西莫夫): "
    if "!KEYWORD!"=="" (
        echo 错误：关键词不能为空
        pause
        goto item_buyer
    )
    set /p SEARCH_LIMIT="返回结果数量 (默认 20): "
    if "!SEARCH_LIMIT!"=="" set SEARCH_LIMIT=20
    echo.
    call :run python "%~dp0scripts\item_buyer.py" --search "!KEYWORD!" --limit !SEARCH_LIMIT!
    echo.
    set /p GOODS_ID="输入上方 goods_id 进行购买 (回车返回): "
    if "!GOODS_ID!"=="" goto item_buyer
    goto item_buy
)

if "!ACTION!"=="3" (
    echo.
    set /p BATCH_FILE="批量文件路径 (如 items.txt): "
    if "!BATCH_FILE!"=="" (
        echo 错误：文件路径不能为空
        pause
        goto item_buyer
    )
    set /p INTERVAL="轮询间隔秒数 (默认 30): "
    if "!INTERVAL!"=="" set INTERVAL=30
    call :run python "%~dp0scripts\item_buyer.py" --batch "!BATCH_FILE!" --interval !INTERVAL!
    goto end
)

echo.
echo 支持的输入格式：
echo   URL:  https://buff.163.com/goods/12345
echo   ID:   12345
echo.
set /p GOODS_ID="输入饰品 URL 或 goods_id: "
if "!GOODS_ID!"=="" (
    echo 错误：goods_id 不能为空
    pause
    goto item_buyer
)

:item_buy
set /p MAX_PRICE="最高价格，元 (默认 1.0): "
if "!MAX_PRICE!"=="" set MAX_PRICE=1.0

set /p MAX_ITEMS="最大购买数量 (默认 5): "
if "!MAX_ITEMS!"=="" set MAX_ITEMS=5

echo.
echo 选择模式：
echo   1. 单次运行
echo   2. 轮询监控
set /p MODE="请选择 (1/2, 默认 1): "
if "!MODE!"=="" set MODE=1

set EXTRA_ARGS=

if "!MODE!"=="2" (
    set /p INTERVAL="轮询间隔秒数 (默认 30): "
    if "!INTERVAL!"=="" set INTERVAL=30
    set /p MAX_ROUNDS="最大轮次，0=无限 (默认 0): "
    if "!MAX_ROUNDS!"=="" set MAX_ROUNDS=0
    set EXTRA_ARGS=--interval !INTERVAL! --max-rounds !MAX_ROUNDS!
)

echo.
echo ============================================
echo   商品:      !GOODS_ID!
echo   最高价格:  !MAX_PRICE! 元
echo   最大数量:  !MAX_ITEMS!
if "!MODE!"=="2" echo   模式:      轮询，间隔 !INTERVAL! 秒
if "!MODE!"=="1" echo   模式:      单次运行
echo ============================================
echo.

call :run python "%~dp0scripts\item_buyer.py" "!GOODS_ID!" --max-price !MAX_PRICE! --max-items !MAX_ITEMS! !EXTRA_ARGS!
goto end

:: ============================================
:: 工具 2：涂鸦饰品购买
:: ============================================
:buff_buyer
cls
echo ============================================
echo   涂鸦饰品购买
echo ============================================
echo.
echo   1. 运行 (默认参数)
echo   2. 自定义参数运行
echo   3. 模拟模式 (dry-run)
echo   0. 返回主菜单
echo.
set /p ACTION="请选择 (1/2/3/0, 默认 1): "
if "!ACTION!"=="" set ACTION=1
if "!ACTION!"=="0" goto menu

if "!ACTION!"=="3" (
    call :run python "%~dp0scripts\buff_buyer.py" --dry-run
    goto end
)

if "!ACTION!"=="1" (
    call :run python "%~dp0scripts\buff_buyer.py"
    goto end
)

set /p MAX_PRICE="最高价格，元 (默认 0.05): "
if "!MAX_PRICE!"=="" set MAX_PRICE=0.05
set /p MAX_ITEMS="最大购买数量 (默认 10): "
if "!MAX_ITEMS!"=="" set MAX_ITEMS=10

call :run python "%~dp0scripts\buff_buyer.py" --max-price !MAX_PRICE! --max-items !MAX_ITEMS!
goto end

:: ============================================
:: 工具 3：挂件搜枪
:: ============================================
:charm_searcher
cls
echo ============================================
echo   挂件搜枪
echo ============================================
echo.
echo 可用赛事：
call :run python "%~dp0scripts\buff_charm_searcher.py" --list-events
echo.
echo   0. 返回主菜单
echo.
set /p EVENT="输入赛事名称 (如 austin): "
if "!EVENT!"=="" goto charm_searcher
if "!EVENT!"=="0" goto menu

echo.
echo   1. 运行 (默认参数)
echo   2. 自定义参数运行
echo   3. 模拟模式 (dry-run)
set /p ACTION="请选择 (1/2/3, 默认 1): "
if "!ACTION!"=="" set ACTION=1

if "!ACTION!"=="3" (
    call :run python "%~dp0scripts\buff_charm_searcher.py" --event !EVENT! --dry-run
    goto end
)

if "!ACTION!"=="1" (
    call :run python "%~dp0scripts\buff_charm_searcher.py" --event !EVENT!
    goto end
)

set /p MAX_PRICE="最高价格，元 (默认 0.3): "
if "!MAX_PRICE!"=="" set MAX_PRICE=0.3
set /p MAX_ITEMS="最大购买数量 (默认 10): "
if "!MAX_ITEMS!"=="" set MAX_ITEMS=10

call :run python "%~dp0scripts\buff_charm_searcher.py" --event !EVENT! --max-price !MAX_PRICE! --max-items !MAX_ITEMS!
goto end

:: ============================================
:: 工具 4：价格监控仪表盘
:: ============================================
:dashboard
cls
echo ============================================
echo   价格监控仪表盘
echo ============================================
echo.
echo   1. 启动仪表盘 (默认 127.0.0.1:5000)
echo   2. 自定义端口启动
echo   0. 返回主菜单
echo.
set /p ACTION="请选择 (1/2/0, 默认 1): "
if "!ACTION!"=="" set ACTION=1
if "!ACTION!"=="0" goto menu

if "!ACTION!"=="2" (
    set /p PORT="端口 (默认 5000): "
    if "!PORT!"=="" set PORT=5000
    echo.
    echo 启动仪表盘: http://127.0.0.1:!PORT!
    start "" "http://127.0.0.1:!PORT!"
    call :run python "%~dp0scripts\dashboard.py" --port !PORT!
    goto end
)

echo.
echo 启动仪表盘: http://127.0.0.1:5000
start "" "http://127.0.0.1:5000"
call :run python "%~dp0scripts\dashboard.py"
goto end

:: ============================================
:: 子程序：执行命令并在出错时暂停
:: ============================================
:run
%*
if !errorlevel! neq 0 (
    echo.
    echo [错误] 退出码: !errorlevel!
    echo.
    pause
)
goto :eof

:end
echo.
echo 按任意键返回主菜单...
pause >nul
goto menu
