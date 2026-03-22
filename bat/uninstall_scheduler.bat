@echo off
echo 노션 자동 업로더를 작업 스케줄러에서 제거합니다...
schtasks /delete /tn "NotionSnippetUploader" /f
echo ✅ 제거 완료
pause