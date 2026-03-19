@echo off
chcp 936 >nul
color 5F

echo.
echo ========================================
echo    Claude Team - Main Window
echo ========================================
echo.
echo  Role: Product Manager (PM)
echo.
echo  You are the PM. Talk with user, then
echo  dispatch tasks to team via Agent tool.
echo.
echo ========================================
echo.
echo  Team Members (Auto-dispatched):
echo  - Project Manager
echo  - Architect
echo  - Developer
echo  - Tester
echo  - Reviewer
echo.
echo ========================================
echo.

cd /d "%~dp0.."
claude
