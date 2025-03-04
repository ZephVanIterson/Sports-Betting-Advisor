@echo off
REM Run the Python script
C:\Users\zepht\AppData\Local\Programs\Python\Python312\python.exe D:\Github\Sports-Betting-Advisor\main.py

REM Navigate to the repository directory
cd /d D:\Github\Sports-Betting-Advisor

REM Add all changes to Git
git add .

REM Commit the changes with a timestamp
git commit -m "Automated daily update: %date% %time%"

REM Push the changes to GitHub
git push origin website

REM Close the terminal
exit