@echo off
setlocal
set SCRIPT_DIR=%~dp0
start "MMKE visual PaliGemma monitor" powershell -NoExit -ExecutionPolicy Bypass -File "%SCRIPT_DIR%monitor_mmke_visual_paligemma.ps1" -Beep
start "MMKE entity epoch50 monitor" powershell -NoExit -ExecutionPolicy Bypass -File "%SCRIPT_DIR%monitor_mmke_entity_epoch50.ps1" -Beep
