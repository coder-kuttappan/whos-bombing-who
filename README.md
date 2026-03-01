# Who's Bombing Who?

A live dashboard tracking active armed conflicts around the world. No doomscrolling required.

**[whosbombingwho.coderkuttappan.com](https://whosbombingwho.coderkuttappan.com)**

## How it works

```
Every 4 hours (GitHub Actions cron):
  RSS feeds (BBC, Al Jazeera, NYT)
    → Gemini AI extracts conflicts + global impact + travel alerts
      → Commits conflicts.json

GitHub Pages (static):
  index.html loads conflicts.json → Leaflet map + sidebar
  No backend. No API calls from the browser. Zero runtime cost.
```

The AI is also prompted to include major ongoing conflicts that may not be in the current news cycle, so coverage isn't limited to what's trending today.

## What the map shows

- **Colored dots** — red (escalating), orange (active), teal (ceasefire/de-escalating)
- **Pulse speed** — faster = higher intensity
- **Dashed arcs** — connect countries/groups involved in each conflict
- **Click a conflict** — sidebar with summary, parties, casualties, global impact, and travel disruptions

## Running locally

1. Clone the repo
2. Open `index.html` via a local server:
   ```bash
   python3 -m http.server 8000
   open http://localhost:8000
   ```

To regenerate data with live news (instead of the checked-in `conflicts.json`):

1. Get a free [Gemini API key](https://aistudio.google.com/apikey)
2. Create `.env` with `GEMINI_API_KEY=your-key`
3. `pip install -r requirements.txt`
4. `python generate.py`

Without an API key, `generate.py` produces demo data.

## Stack

- **Frontend**: Vanilla HTML/JS + [Leaflet.js](https://leafletjs.com/) + [CARTO](https://carto.com/) dark tiles
- **Data pipeline**: Python ([feedparser](https://pypi.org/project/feedparser/) + [Google Gemini](https://ai.google.dev/))
- **Hosting**: GitHub Pages (static)
- **Refresh**: GitHub Actions cron (every 4 hours)

## Accuracy

**This is not a verified news source.** All conflict data, summaries, impact analysis, and travel alerts are AI-generated from public news headlines. They may contain errors, omissions, or biases from the source material. Casualty figures are approximate and often contested. Travel alerts are indicative only — always check official government advisories. See the About modal in the app for full disclaimers.

## License

MIT

---

Built by [coder kuttappan](https://coderkuttappan.com)
