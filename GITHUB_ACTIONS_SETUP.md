# GitHub Actions setup

This repository uses `main` as its default branch and `website` as the GitHub
Pages branch. The scheduled workflow must exist on `main`, but it checks out,
updates, and pushes `website`.

## 1. Publish the current fixes

The current working branch is `website`. Review and commit the changes, then
push them:

```powershell
git add .gitignore README.md GITHUB_ACTIONS_SETUP.md index.html main.py requirements.txt run_script.bat static/css/styles.css static/js/main.js tests/test_main.py
git commit -m "Archive stale data and harden odds updater"
git push origin website
```

Bring the same source changes into the default branch:

```powershell
git switch main
git pull --ff-only origin main
git merge website
git push origin main
```

Resolve merge conflicts before pushing if Git reports any. Never add or commit
the local `.env` file.

## 2. Add the API key as a repository secret

1. Open the GitHub repository.
2. Select **Settings**.
3. Select **Secrets and variables** and then **Actions**.
4. Select **New repository secret**.
5. Enter `API_KEY` as the name.
6. Copy only the key value from the local `.env` file into the secret value.
7. Select **Add secret**.

The secret should not be pasted into a workflow file, committed file, issue, or
workflow log.

## 3. Allow the workflow to update the website branch

1. Open **Settings > Actions > General**.
2. Under **Workflow permissions**, select **Read and write permissions**.
3. Save the setting.

If the `website` branch has branch protection, allow GitHub Actions to push or
adjust the workflow to use a pull request instead.

## 4. Create the workflow on `main`

Create `.github/workflows/update-odds.yml` on the `main` branch with the
following content:

```yaml
name: Update sports odds

on:
  schedule:
    - cron: "17 06 * * *"
      timezone: "America/Toronto"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: daily-odds-update
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Check out the website branch
        uses: actions/checkout@v7
        with:
          ref: website
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: python -m pip install -r requirements.txt

      - name: Run offline tests
        run: python -m unittest discover -s tests -v

      - name: Fetch current odds
        env:
          API_KEY: ${{ secrets.API_KEY }}
        run: python main.py

      - name: Commit updated website data
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -- \
            static/data/nhl_better_odds.json \
            static/data/nhl_results.json \
            static/data/nba_better_odds.json \
            static/data/nba_results.json \
            static/data/nfl_better_odds.json \
            static/data/nfl_results.json \
            static/data/last_updated.txt

          if git diff --cached --quiet; then
            echo "No website data changed."
            exit 0
          fi

          git commit -m "Automated daily odds update"
          git push origin HEAD:website
```

The workflow runs daily at 6:17 AM Toronto time. Using minute 17 avoids the
busier start-of-hour scheduling window. `workflow_dispatch` also provides a
manual **Run workflow** button.

## 5. Test before relying on the schedule

1. Open the repository's **Actions** tab.
2. Select **Update sports odds**.
3. Select **Run workflow**, choose `main`, and confirm.
4. Open the run and confirm that all five steps are green.
5. Confirm that `website` received an `Automated daily odds update` commit.
6. Open the hosted site in a private browser window.
7. Confirm that the displayed timestamp is current and the archived-data banner
   disappears. The banner automatically returns if the data becomes more than
   48 hours old.

If the workflow fails, its nonzero result will preserve the last known-good
JSON and timestamp. Check the failing step in the Actions log; the API key is
not printed by the updater.

## 6. Update the project status after the first successful run

After verifying the workflow, change the README status from "updates paused"
to "updates daily through GitHub Actions." The website banner does not need to
be removed: JavaScript hides it while the data is less than 48 hours old and
shows it again when updates become stale.

GitHub may disable scheduled workflows in public repositories after 60 days
without repository activity. If that happens, open the workflow in the Actions
tab and re-enable it, then run it manually once.
