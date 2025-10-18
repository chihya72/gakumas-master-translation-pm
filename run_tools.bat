@echo off
chcp 65001 >nul

:start
cls
echo ================================
echo       翻译工具集合
echo ================================
echo.
echo 请选择要执行的工具：
echo.
echo 1. 更新JP-CN映射文件工具 (命令行)
echo 2. 翻译填充工具 (图形界面)
echo 3. JSON文件对比工具 (图形界面)
echo 4. 退出
echo.
set /p choice=请输入选项 (1-4): 

if "%choice%"=="3" (
    echo.
    echo 正在启动JSON对比工具...
    echo ================================
    echo.
    python trans_tools\json_compare_gui.py
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto start
) else if "%choice%"=="1" (
    echo.
    echo 正在更新JP-CN映射文件...
    echo ================================
    echo.
    python trans_tools\jp_cn.py
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto start
) else if "%choice%"=="2" (
    echo.
    echo 正在启动翻译填充工具...
    echo ================================
    echo.
    python trans_tools\full_trans_gui.py
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto start
) else if "%choice%"=="4" (
    echo.
    echo 退出程序...
    exit /b 0
) else (
    echo.
    echo 无效选项，请重新选择...
    echo.
    pause
    goto start
)