# Bundle Game Extractor (Playwright)

Automated extractor for game data from [Fanatical](https://www.fanatical.com) pick-and-mix bundles and [Humble Bundle](https://www.humblebundle.com/games). Each title is enriched with Steam metadata (price, reviews, categories, tags, etc.) and exported as an interactive HTML report (DataTables).

Optional `--pretty` mode adds cover art, dark styling, and a gold highlight for local / shared-screen multiplayer titles.

> For personal / educational use. Respect Fanatical, Humble Bundle and Steam terms of service, and avoid aggressive request rates.

## Features

- Two-phase flow: collect items from Fanatical/Humble, then query Steam
- Single-bundle report, one report per listing item, or one **combined** HTML
- Humble: unlock tiers with price and games per tier
- Combined reports include Steam + source-bundle links
- `--pretty`: Steam/Humble covers and local-multiplayer highlighting

## Requirements

- Python 3.10+
- Windows, macOS or Linux

## Setup

```bash
git clone <REPO_URL>
cd FanaticalGameExtractorPlaywright

python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

## CLI options

| Option | Description |
|--------|-------------|
| `--url` | Bundle URL (parametrized tests) |
| `--pretty` | Enriched HTML report |
| `--html-output` | Output basename (without `.html`) |
| `--headed` | Show the browser (pytest-playwright) |

## Fanatical

```bash
# Single pick-and-mix
pytest tests/test_fanatical_to_html_parametrized.py -s --pretty \
  --url "https://www.fanatical.com/en/pick-and-mix/YOUR-BUNDLE"

# All pick-and-mix from /en/bundle/games (one HTML each)
pytest tests/test_fanatical_all_bundles.py -s --pretty

# All pick-and-mix in one HTML
pytest tests/test_fanatical_all_bundles_combined.py -s --pretty
```

Output example: `reports/all_fanatical_pick_and_mix_combined_pretty.html`

## Humble Bundle

```bash
# Single bundle
pytest tests/test_humble_to_html_parametrized.py -s --pretty \
  --url "https://www.humblebundle.com/games/YOUR-BUNDLE"

# All bundles from /games (one HTML each)
pytest tests/test_humble_all_bundles.py -s --pretty

# All bundles in one HTML
pytest tests/test_humble_all_bundles_combined.py -s --pretty
```

Output example: `reports/all_humble_game_bundles_combined_pretty.html`

## Project layout

```
├── config/
├── pages/          # Fanatical, Humble, Steam page objects
├── tests/          # pytest entrypoints + HTML builders
├── reports/        # generated HTML (gitignored)
├── .github/workflows/
├── requirements.txt
└── pytest.ini
```

## Steam fields

Name, URL, price, reviews (overall + 30 days), categories, tags, release date, publisher, developer. Pretty mode also stores cover images and local/shared-screen detection. Humble reports add the unlock-tier price.

## GitHub Pages

A workflow can generate the **combined** Fanatical and/or Humble reports and publish them to GitHub Pages (landing page + both HTMLs). See [`.github/workflows/publish-reports.yml`](.github/workflows/publish-reports.yml).

Enable Pages in the repo: **Settings → Pages → Source: GitHub Actions**.

## License

Use personally as you prefer. Add an explicit license file (e.g. MIT) if you publish the repository.
