"""
generate.py — Pipeline script for Who's Bombing Who?

Fetches conflict news from RSS feeds, extracts structured conflict data
and global impact analysis using Gemini, and writes conflicts.json.

Usage:
    python generate.py              # Uses GEMINI_API_KEY from env/.env
    python generate.py              # Falls back to demo data if no key
"""

import json
import os
import time
from pathlib import Path

import feedparser

BASE_DIR = Path(__file__).resolve().parent
CONFLICTS_FILE = BASE_DIR / "conflicts.json"

# Load .env manually (no python-dotenv dependency)
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEMO_MODE = not API_KEY or API_KEY == "your-key-here"

if not DEMO_MODE:
    from google import genai
    client = genai.Client(api_key=API_KEY)

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]

CONFLICT_KEYWORDS = [
    "war", "conflict", "attack", "strike", "bomb", "missile", "troops",
    "military", "invasion", "airstrike", "shelling", "casualties", "killed",
    "fighting", "ceasefire", "escalation", "offensive", "artillery",
    "drone", "siege", "rebel", "insurgent", "militant", "combat",
    "occupation", "annex", "genocide", "humanitarian crisis",
]

DEMO_CONFLICTS = [
    {
        "id": 0,
        "name": "Russia-Ukraine War",
        "parties": ["Russia", "Ukraine"],
        "location": {"country": "Ukraine", "region": "Eastern Ukraine", "lat": 48.38, "lng": 37.62},
        "status": "active",
        "casualties": "Hundreds of thousands estimated on both sides",
        "summary": "Russia's full-scale invasion of Ukraine continues with heavy fighting along the eastern front. Ukraine maintains defensive positions while conducting counteroffensive operations. Western nations continue to supply military aid.",
        "global_impact": "- **Energy**: European gas prices elevated, raising global fuel and electricity costs\n- **Food**: Ukraine is a major grain exporter — wheat and sunflower oil prices remain disrupted\n- **Flights**: Airlines reroute around Ukrainian/Russian airspace, adding 1-3 hours to Europe-Asia routes\n- **Cyber**: Increased state-sponsored attacks on financial and tech infrastructure",
        "year_started": 2022,
        "travel_alert": "Airlines reroute around Ukrainian/Russian airspace — adds 1-3 hours to Europe-Asia flights",
    },
    {
        "id": 1,
        "name": "Israel-Palestine Conflict",
        "parties": ["Israel", "Hamas"],
        "location": {"country": "Palestine", "region": "Gaza Strip", "lat": 31.35, "lng": 34.31},
        "status": "active",
        "casualties": "Tens of thousands of Palestinian casualties reported",
        "summary": "The conflict in Gaza continues with Israeli military operations and a severe humanitarian crisis. International pressure mounts for ceasefire negotiations. Aid delivery remains critically restricted.",
        "global_impact": "- **Shipping**: Houthi Red Sea attacks have disrupted Suez Canal route, shipping costs up 2-3x\n- **Oil**: Regional instability keeps oil market sentiment volatile\n- **Flights**: Some airlines avoid Middle East overflights\n- **Tech**: Israel is a major tech hub — VC flows and startup activity affected",
        "year_started": 2023,
        "travel_alert": "Houthi Red Sea attacks disrupting Suez shipping — some airlines avoiding Middle East overflights",
    },
    {
        "id": 2,
        "name": "Sudan Civil War",
        "parties": ["Sudanese Armed Forces (SAF)", "Rapid Support Forces (RSF)"],
        "location": {"country": "Sudan", "region": "Khartoum / Darfur", "lat": 15.50, "lng": 32.56},
        "status": "active",
        "casualties": "Over 12,000 killed, millions displaced",
        "summary": "Fighting between the SAF and RSF has devastated Sudan, creating one of the world's worst humanitarian crises. Millions have been displaced internally and across borders. Reports of atrocities in Darfur continue.",
        "global_impact": "- **Refugees**: Millions displaced into Chad, Egypt, South Sudan — straining regional resources\n- **Gold**: Sudan is Africa's 3rd largest producer — supply chains disrupted\n- **Red Sea**: Instability near Port Sudan could affect shipping routes",
        "year_started": 2023,
        "travel_alert": None,
    },
    {
        "id": 3,
        "name": "Myanmar Civil War",
        "parties": ["Myanmar Military (Tatmadaw)", "Resistance forces (NUG, PDF, ethnic armed groups)"],
        "location": {"country": "Myanmar", "region": "Multiple regions", "lat": 19.76, "lng": 96.07},
        "status": "active",
        "casualties": "Thousands killed since 2021 coup",
        "summary": "Resistance forces have made significant territorial gains against the military junta. The Tatmadaw has lost control of large border areas. Civilian casualties continue from airstrikes on populated areas.",
        "global_impact": "- **Trade**: Disruption to China-Southeast Asia trade corridors\n- **Refugees**: Over a million displaced into Thailand, India, Bangladesh\n- **Drugs**: Conflict zones are major methamphetamine production areas",
        "year_started": 2021,
        "travel_alert": None,
    },
    {
        "id": 4,
        "name": "Ethiopian Internal Conflicts",
        "parties": ["Ethiopian government", "Fano militia", "Various regional forces"],
        "location": {"country": "Ethiopia", "region": "Amhara Region", "lat": 11.59, "lng": 37.39},
        "status": "active",
        "casualties": "Unknown — reporting restricted",
        "summary": "Despite the Tigray ceasefire, new fighting has erupted in the Amhara region between government forces and Fano militia. Internet blackouts and media restrictions make reporting difficult. Humanitarian access remains limited.",
        "global_impact": "- **Horn of Africa**: Instability risks spillover into Somalia, Eritrea, Djibouti\n- **Aid**: Diverts humanitarian resources from other regional crises\n- **Coffee**: Ethiopia is a top producer — prolonged conflict could affect supply",
        "year_started": 2023,
        "travel_alert": None,
    },
    {
        "id": 5,
        "name": "Sahel Insurgency",
        "parties": ["JNIM (al-Qaeda affiliate)", "ISIS Sahel", "Burkina Faso / Mali / Niger militaries"],
        "location": {"country": "Burkina Faso", "region": "Sahel Region", "lat": 14.0, "lng": -1.5},
        "status": "escalating",
        "casualties": "Thousands killed annually, millions displaced",
        "summary": "Jihadist insurgencies continue to expand across the Sahel. Military juntas in Burkina Faso, Mali, and Niger have expelled French forces and turned to Russian Wagner/Africa Corps for support. Civilian massacres are frequently reported.",
        "global_impact": "- **Migration**: Displacement fuels migration routes toward North Africa and Europe\n- **Resources**: Burkina Faso and Mali are gold and uranium producers\n- **Terrorism**: Expanding jihadist territory increases global security risk",
        "year_started": 2012,
        "travel_alert": None,
    },
    {
        "id": 6,
        "name": "DR Congo - M23 Conflict",
        "parties": ["M23 rebels (Rwanda-backed)", "DRC armed forces (FARDC)", "FDLR"],
        "location": {"country": "DR Congo", "region": "North Kivu", "lat": -1.68, "lng": 29.22},
        "status": "escalating",
        "casualties": "Hundreds killed, over a million displaced",
        "summary": "M23 rebels, widely reported to be backed by Rwanda, have seized significant territory in eastern Congo including areas near Goma. The conflict has displaced over a million people and strained regional diplomatic relations.",
        "global_impact": "- **Minerals**: Eastern Congo supplies cobalt, coltan, tin critical for electronics and EVs\n- **Refugees**: Over a million displaced — regional humanitarian burden\n- **Diplomacy**: Rwanda-DRC tensions straining East African relations",
        "year_started": 2022,
        "travel_alert": None,
    },
]

DEFAULT_GLOBAL_IMPACT = (
    "- **Regional instability**: Affects regional security and trade\n"
    "- **Humanitarian**: Displacement strains international aid resources\n"
    "- **Geopolitical**: Shifts in alliances may have broader implications"
)


def call_llm(prompt):
    """Call Gemini Flash and return the text response."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def fetch_rss_articles():
    """Fetch and filter conflict-related articles from RSS feeds."""
    articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                text = f"{title} {summary}".lower()
                if any(kw in text for kw in CONFLICT_KEYWORDS):
                    articles.append({
                        "title": title,
                        "summary": summary[:500],
                        "link": entry.get("link", ""),
                        "source": feed.feed.get("title", url),
                    })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return articles


def extract_conflicts(articles):
    """Use Gemini to extract structured conflict data from articles."""
    if not articles:
        return []

    articles_text = "\n\n".join(
        f"[{a['source']}] {a['title']}\n{a['summary']}"
        for a in articles
    )

    prompt = f"""You are a conflict analyst. Your job is to produce a comprehensive list of ALL active armed conflicts in the world right now.

STEP 1: Read the news articles below and extract any conflicts mentioned.
STEP 2: Add any major ongoing armed conflicts worldwide that are NOT mentioned in the articles. Do not limit yourself to what's in the news — include all conflicts you know to be active, including those that receive little media coverage.

Include at minimum: wars, civil wars, insurgencies, military occupations, and armed territorial disputes with active hostilities. Do NOT include frozen conflicts with no recent fighting, protests, or political tensions without armed combat.

For each conflict, provide:
- name: Short name (e.g., "Russia-Ukraine War")
- parties: Array of belligerent sides involved (military/armed groups only — do NOT include civilian populations)
- location: {{country, region, lat, lng}} — use approximate center coordinates
- status: one of "active", "ceasefire", "escalating", "de-escalating"
- casualties: Brief note on total casualties if known, otherwise "Unknown"
- summary: 2-3 sentence summary of current situation. For conflicts in the articles, use the latest reported developments. For others, describe the general state of the conflict.
- year_started: The year this conflict/war began (integer, e.g. 2022). Use the start of the current phase if the conflict has distinct phases (e.g. Russia-Ukraine is 2022 for the full-scale invasion, not 2014).
- travel_alert: A one-line travel disruption note if this conflict affects international flights, shipping routes, or travel safety (e.g. "Airlines rerouting around Iranian airspace — affects Dubai/Doha transit"). Set to null if no significant travel impact.

Return ONLY valid JSON array. No markdown, no explanation. Example format:
[{{"name": "...", "parties": ["...", "..."], "location": {{"country": "...", "region": "...", "lat": 0.0, "lng": 0.0}}, "status": "active", "casualties": "...", "summary": "...", "year_started": 2022, "travel_alert": "..." or null}}]

Articles:
{articles_text}"""

    try:
        text = call_llm(prompt).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        conflicts = json.loads(text)
        for i, c in enumerate(conflicts):
            c["id"] = i
        return conflicts
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        print(f"Failed to parse conflict extraction response: {e}")
        return []


def generate_global_impacts(conflicts):
    """Use Gemini to generate global impact for all conflicts in a single call."""
    if not conflicts:
        return

    conflict_summaries = "\n\n".join(
        f"[{c['id']}] {c['name']} — {c['parties']}\n"
        f"Location: {c['location']['country']}, {c['location'].get('region', '')}\n"
        f"Status: {c['status']}\n"
        f"Summary: {c['summary']}"
        for c in conflicts
    )

    prompt = f"""For each conflict below, provide a global impact analysis.

Cover: economic effects (commodity prices, trade, supply chains), transport disruptions (flights, shipping), humanitarian consequences, and geopolitical implications.
3-4 bullet points per conflict. Be specific and factual, not alarmist. Start each bullet with a bold topic label like **Energy**: or **Shipping**:.

Return ONLY valid JSON object mapping conflict ID to impact string. Each impact string should use markdown bullet format (- **Topic**: explanation). No other text.

Example format:
{{"0": "- **Energy**: ...\\n- **Food**: ...", "1": "- **Shipping**: ...\\n- **Oil**: ..."}}

Conflicts:
{conflict_summaries}"""

    try:
        text = call_llm(prompt).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        impacts = json.loads(text)
        for c in conflicts:
            c["global_impact"] = impacts.get(str(c["id"]), DEFAULT_GLOBAL_IMPACT)
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        print(f"Failed to parse global impact response: {e}")
        for c in conflicts:
            c.setdefault("global_impact", DEFAULT_GLOBAL_IMPACT)


def generate():
    """Main pipeline: fetch → extract → enrich → write JSON."""
    if DEMO_MODE:
        print("No API key found — generating demo data")
        data = {
            "timestamp": time.time(),
            "demo": True,
            "conflicts": DEMO_CONFLICTS,
        }
    else:
        print("Fetching RSS feeds...")
        articles = fetch_rss_articles()
        print(f"Found {len(articles)} conflict-related articles")

        print("Extracting conflicts via Gemini...")
        conflicts = extract_conflicts(articles)
        print(f"Extracted {len(conflicts)} conflicts")

        if conflicts:
            print("Generating global impact analysis...")
            generate_global_impacts(conflicts)

        data = {
            "timestamp": time.time(),
            "demo": False,
            "conflicts": conflicts,
        }

    CONFLICTS_FILE.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(data['conflicts'])} conflicts to {CONFLICTS_FILE.name}")


if __name__ == "__main__":
    generate()
