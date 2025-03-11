@echo off

REM Navigate to the repository directory
cd /d D:\Github\Sports-Betting-Advisor

REM Store the current branch name
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set CURRENT_BRANCH=%%a

REM Check if the current branch is not the website branch
if not "%CURRENT_BRANCH%"=="website" (
    REM Stash changes if not on the website branch
    git stash
    set STASHED_CHANGES=true
) else (
    set STASHED_CHANGES=false
)

REM Checkout the website branch (switch to it)
git checkout website

REM Run the Python script
C:\Users\zepht\AppData\Local\Programs\Python\Python312\python.exe D:\Github\Sports-Betting-Advisor\main.py

REM Add all changes to Git
git add .

REM Commit the changes with a timestamp
git commit -m "Automated daily update: %date% %time%"

REM Push the changes to GitHub
git push origin website

REM Switch back to the original branch
git checkout %CURRENT_BRANCH%

REM Restore stashed changes if they were stashed
if %STASHED_CHANGES%==true (
    git stash pop
)

REM Close the terminal
pause