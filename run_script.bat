@echo off
setlocal

REM Optional local fallback. GitHub Actions should be used for normal daily updates.
pushd "%~dp0" || exit /b 1

for /f "tokens=*" %%a in ('git branch --show-current') do set "CURRENT_BRANCH=%%a"
if /i not "%CURRENT_BRANCH%"=="website" (
    echo Update cancelled: switch to the website branch first.
    popd
    exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
    python main.py
) else (
    py -3 main.py
)

if errorlevel 1 goto :error

git add -- static/data/nhl_better_odds.json static/data/nhl_results.json static/data/nba_better_odds.json static/data/nba_results.json static/data/nfl_better_odds.json static/data/nfl_results.json static/data/last_updated.txt
if errorlevel 1 goto :error

git diff --cached --quiet
if not errorlevel 1 goto :no_changes

git commit -m "Automated odds update"
if errorlevel 1 goto :error

git push origin website
if errorlevel 1 goto :error

echo Odds update completed and pushed successfully.
popd
exit /b 0

:no_changes
echo Update completed, but no website data changed.
popd
exit /b 0

:error
echo Update failed. Existing website data was not intentionally replaced.
popd
exit /b 1
