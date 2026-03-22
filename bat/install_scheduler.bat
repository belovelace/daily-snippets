@echo off
echo 노션 자동 업로더를 Windows 작업 스케줄러에 등록합니다...

:: Python 경로 자동 감지
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i

:: 현재 폴더 경로
set SCRIPT_DIR=C:\dev\GCS_API
set SCRIPT_PATH=%SCRIPT_DIR%\watcher.py
set LOG_PATH=%SCRIPT_DIR%\watcher.log

echo Python 경로: %PYTHON_PATH%
echo 스크립트 경로: %SCRIPT_PATH%

:: 작업 스케줄러 등록 (로그인 시 자동 실행, 백그라운드)
schtasks /create /tn "NotionSnippetUploader" ^
  /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\" --interval 30 >> \"%LOG_PATH%\" 2>&1" ^
  /sc onlogon ^
  /ru "%USERNAME%" ^
  /rl limited ^
  /f

echo.
echo ✅ 등록 완료!
echo    작업 이름: NotionSnippetUploader
echo    실행 조건: Windows 로그인 시 자동 시작
echo    폴링 간격: 30초
echo    로그 파일: %LOG_PATH%
echo.
echo 지금 바로 시작하려면:
echo    schtasks /run /tn "NotionSnippetUploader"
echo.
pause