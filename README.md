# Sports Betting Advisor

A static website that compares NHL, NBA, and NFL moneyline odds across multiple
bookmakers to identify stronger prices and show the best available line for each
team.

> **Automation status (September 24, 2026):** GitHub's native scheduler is not
> reliably creating scheduled runs for this repository. Manual workflow runs
> still work, but daily automatic updates are temporarily degraded. Always check
> the displayed update timestamp before using the odds.

**Live site:** https://zephvaniterson.github.io/Sports-Betting-Advisor/

## Features

### Better Odds Than Average

- Selects the strongest above-consensus price for each game and outcome.
- Shows the bookmaker price, consensus-equivalent price, price improvement, and
  implied-probability difference.

An above-average price is not proof that a wager has positive expected value.
The comparison reflects only the bookmakers returned by the API and includes
their margins.

### Best Odds per Game

- Displays the best home and away moneyline available for each game.
- Shows the bookmaker offering each best price.
- Calculates the theoretical two-outcome arbitrage margin from the best decimal
  prices.

A positive theoretical margin does not guarantee that an arbitrage can be
executed. Lines can move, limits may differ, and wagers can be rejected.

## Automation

The workflow is configured to run daily at 6:17 AM in the
`America/Toronto` timezone. GitHub's native scheduler is currently failing to
create scheduled runs reliably, although manual `workflow_dispatch` runs work.
The intended automation process is:

1. GitHub Actions reads the workflow from the default `main` branch.
2. It checks out the `website` branch, which is the GitHub Pages source.
3. Offline tests run before any API request.
4. Current odds are fetched using an encrypted `API_KEY` repository secret.
5. Generated JSON and the UTC update timestamp are committed to `website`.
6. GitHub Pages republishes the updated static site.

Daily generated-data commits remain on `website`, keeping `main` focused on
source changes. Failed API requests exit without replacing the last known-good
website data or timestamp.

Detailed configuration and troubleshooting instructions are available in
[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md).

## Local development

Requires Python 3.12 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local `.env` file containing:

```dotenv
API_KEY=your_api_key_here
```

The `.env` file is ignored by Git and must never be committed.

Run the offline tests:

```powershell
python -m unittest discover -s tests -v
```

Run a manual data update from the repository root:

```powershell
python main.py
```

This consumes API credits and updates files under `static/data`. To preview the
website locally, serve the repository through an HTTP server rather than opening
`index.html` directly:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Project structure

- `main.py` fetches, validates, analyzes, and publishes odds data.
- `static/data/` contains the generated JSON consumed by the website.
- `static/js/main.js` loads and formats the generated data.
- `index.html` and `static/css/styles.css` provide the GitHub Pages interface.
- `tests/` contains offline regression tests.
- `.github/workflows/update-odds.yml` defines the daily workflow on `main`.

## Disclaimer

*This tool is for informational purposes only. Always verify odds before placing
bets and gamble responsibly.*
