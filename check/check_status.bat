@echo off
echo ===== 노션 업로더 상태 =====
echo.
schtasks /query /tn "NotionSnippetUploader" /fo list 2>nul || echo 작업이 등록되지 않았습니다.
echo.
echo ===== 최근 로그 (마지막 20줄) =====
set LOG_PATH=C:\dev\GCS_API\watcher.log
if exist "%LOG_PATH%" (
    powershell -command "Get-Content '%LOG_PATH%' -Tail 20"
) else (
    echo 로그 파일이 없습니다. 아직 실행되지 않았습니다.
)
echo.
pause