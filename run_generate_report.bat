@echo off
chcp 65001 > nul

REM 出力ファイル名オプション
set OUTPUT=%~1
if "%OUTPUT%"=="" set OUTPUT=report_output.csv

REM スクリプト名 generate_report.py に変更して実行
python "%~dp0generate_report.py" --output "%OUTPUT%"

pause
