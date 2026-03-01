import json
import os
import time
from pathlib import Path

import feedparser
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
CONFLICTS_FILE = BASE_DIR / "conflicts.json"
PROFILE_FILE = BASE_DIR / "user_profile.json"
STALE_SECONDS = 4 * 60 * 60  # 4 hours

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEMO_MODE = not API_KEY or API_KEY == "your-key-here"

if not DEMO_MODE:
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

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
        "summary": "Russia's full-scale invasion of Ukraine continues with heavy fighting along the eastern front. Ukraine maintains defensive positions while conducting counteroffensive operations. Western nations continue to supply military aid."
    },
    {
        "id": 1,
        "name": "Israel-Palestine Conflict",
        "parties": ["Israel", "Hamas", "Palestinian civilians"],
        "location": {"country": "Palestine", "region": "Gaza Strip", "lat": 31.35, "lng": 34.31},
        "status": "active",
        "casualties": "Tens of thousands of Palestinian casualties reported",
        "summary": "The conflict in Gaza continues with Israeli military operations and a severe humanitarian crisis. International pressure mounts for ceasefire negotiations. Aid delivery remains critically restricted."
    },
    {
        "id": 2,
        "name": "Sudan Civil War",
        "parties": ["Sudanese Armed Forces (SAF)", "Rapid Support Forces (RSF)"],
        "location": {"country": "Sudan", "region": "Khartoum / Darfur", "lat": 15.50, "lng": 32.56},
        "status": "active",
        "casualties": "Over 12,000 killed, millions displaced",
        "summary": "Fighting between the SAF and RSF has devastated Sudan, creating one of the world's worst humanitarian crises. Millions have been displaced internally and across borders. Reports of atrocities in Darfur continue."
    },
    {
        "id": 3,
        "name": "Myanmar Civil War",
        "parties": ["Myanmar Military (Tatmadaw)", "Resistance forces (NUG, PDF, ethnic armed groups)"],
        "location": {"country": "Myanmar", "region": "Multiple regions", "lat": 19.76, "lng": 96.07},
        "status": "active",
        "casualties": "Thousands killed since 2021 coup",
        "summary": "Resistance forces have made significant territorial gains against the military junta. The Tatmadaw has lost control of large border areas. Civilian casualties continue from airstrikes on populated areas."
    },
    {
        "id": 4,
        "name": "Ethiopian Internal Conflicts",
        "parties": ["Ethiopian government", "Fano militia", "Various regional forces"],
        "location": {"country": "Ethiopia", "region": "Amhara Region", "lat": 11.59, "lng": 37.39},
        "status": "active",
        "casualties": "Unknown — reporting restricted",
        "summary": "Despite the Tigray ceasefire, new fighting has erupted in the Amhara region between government forces and Fano militia. Internet blackouts and media restrictions make reporting difficult. Humanitarian access remains limited."
    },
    {
        "id": 5,
        "name": "Sahel Insurgency",
        "parties": ["JNIM (al-Qaeda affiliate)", "ISIS Sahel", "Burkina Faso / Mali / Niger militaries"],
        "location": {"country": "Burkina Faso", "region": "Sahel Region", "lat": 14.0, "lng": -1.5},
        "status": "escalating",
        "casualties": "Thousands killed annually, millions displaced",
        "summary": "Jihadist insurgencies continue to expand across the Sahel. Military juntas in Burkina Faso, Mali, and Niger have expelled French forces and turned to Russian Wagner/Africa Corps for support. Civilian massacres are frequently reported."
    },
    {
        "id": 6,
        "name": "DR Congo - M23 Conflict",
        "parties": ["M23 rebels (Rwanda-backed)", "DRC armed forces (FARDC)", "FDLR"],
        "location": {"country": "DR Congo", "region": "North Kivu", "lat": -1.68, "lng": 29.22},
        "status": "escalating",
        "casualties": "Hundreds killed, over a million displaced",
        "summary": "M23 rebels, widely reported to be backed by Rwanda, have seized significant territory in eastern Congo including areas near Goma. The conflict has displaced over a million people and strained regional diplomatic relations."
    },
]

DEMO_GLOBAL_IMPACT = {
    "Russia-Ukraine War": "- **Energy**: European gas prices elevated, raising global fuel and electricity costs\n- **Food**: Ukraine is a major grain exporter — wheat and sunflower oil prices remain disrupted\n- **Flights**: Airlines reroute around Ukrainian/Russian airspace, adding 1-3 hours to Europe-Asia routes\n- **Cyber**: Increased state-sponsored attacks on financial and tech infrastructure",
    "Israel-Palestine Conflict": "- **Shipping**: Houthi Red Sea attacks have disrupted Suez Canal route, shipping costs up 2-3x\n- **Oil**: Regional instability keeps oil market sentiment volatile\n- **Flights**: Some airlines avoid Middle East overflights\n- **Tech**: Israel is a major tech hub — VC flows and startup activity affected",
    "Sudan Civil War": "- **Refugees**: Millions displaced into Chad, Egypt, South Sudan — straining regional resources\n- **Gold**: Sudan is Africa's 3rd largest producer — supply chains disrupted\n- **Red Sea**: Instability near Port Sudan could affect shipping routes",
    "Myanmar Civil War": "- **Trade**: Disruption to China-Southeast Asia trade corridors\n- **Refugees**: Over a million displaced into Thailand, India, Bangladesh\n- **Drugs**: Conflict zones are major methamphetamine production areas",
    "Ethiopian Internal Conflicts": "- **Horn of Africa**: Instability risks spillover into Somalia, Eritrea, Djibouti\n- **Aid**: Diverts humanitarian resources from other regional crises\n- **Coffee**: Ethiopia is a top producer — prolonged conflict could affect supply",
    "Sahel Insurgency": "- **Migration**: Displacement fuels migration routes toward North Africa and Europe\n- **Resources**: Burkina Faso and Mali are gold and uranium producers\n- **Terrorism**: Expanding jihadist territory increases global security risk",
    "DR Congo - M23 Conflict": "- **Minerals**: Eastern Congo supplies cobalt, coltan, tin critical for electronics and EVs\n- **Refugees**: Over a million displaced — regional humanitarian burden\n- **Diplomacy**: Rwanda-DRC tensions straining East African relations",
}

DEMO_PERSONAL_IMPACT = {
    "Russia-Ukraine War": "- **Your electricity bill** may be higher due to elevated European gas prices rippling globally\n- **Flights to Europe** may cost more and take longer due to airspace closures\n- **Wheat-based food prices** (bread, pasta) remain above pre-war levels",
    "Israel-Palestine Conflict": "- **Online shopping** and imports may cost more due to Red Sea shipping disruptions\n- **Flights through Middle East** (Dubai, Doha transit) may see occasional rerouting\n- **Fuel prices** are sensitive to any regional escalation",
    "Sudan Civil War": "- **Gold prices** partly influenced by Sudan supply disruption\n- **Humanitarian fundraising** — you may see more appeals from aid organizations",
}


def call_llm(prompt):
    """Call Gemini Flash and return the text response."""
    response = model.generate_content(prompt)
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

    prompt = f"""Analyze these news articles and extract all distinct active conflicts/wars.

For each conflict, provide:
- name: Short name (e.g., "Russia-Ukraine War")
- parties: Array of sides involved
- location: {{country, region, lat, lng}} — use approximate center coordinates
- status: one of "active", "ceasefire", "escalating", "de-escalating"
- casualties: Brief note if mentioned, otherwise "Unknown"
- summary: 2-3 sentence summary of current situation

Return ONLY valid JSON array. No markdown, no explanation. Example format:
[{{"name": "...", "parties": ["...", "..."], "location": {{"country": "...", "region": "...", "lat": 0.0, "lng": 0.0}}, "status": "active", "casualties": "...", "summary": "..."}}]

Articles:
{articles_text}"""

    try:
        text = call_llm(prompt).strip()
        # Handle potential markdown wrapping
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        conflicts = json.loads(text)
        for i, c in enumerate(conflicts):
            c["id"] = i
        return conflicts
    except (json.JSONDecodeError, IndexError, ValueError) as e:
        print(f"Failed to parse LLM response: {e}")
        return []


def load_conflicts():
    """Load conflicts from cache, refreshing if stale."""
    if CONFLICTS_FILE.exists():
        data = json.loads(CONFLICTS_FILE.read_text())
        age = time.time() - data.get("timestamp", 0)
        if age < STALE_SECONDS:
            return data

    if DEMO_MODE:
        return {"timestamp": time.time(), "conflicts": DEMO_CONFLICTS, "demo": True}

    return refresh_conflicts()


def refresh_conflicts():
    """Fetch fresh conflict data and cache it."""
    print("Refreshing conflict data...")
    articles = fetch_rss_articles()
    conflicts = extract_conflicts(articles)
    data = {
        "timestamp": time.time(),
        "conflicts": conflicts,
    }
    CONFLICTS_FILE.write_text(json.dumps(data, indent=2))
    print(f"Cached {len(conflicts)} conflicts.")
    return data


def load_profile():
    """Load user profile if it exists."""
    if PROFILE_FILE.exists():
        return json.loads(PROFILE_FILE.read_text())
    return None


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/conflicts")
def api_conflicts():
    data = load_conflicts()
    return jsonify(data)


@app.route("/api/impact", methods=["POST"])
def api_impact():
    body = request.json
    conflict_id = body.get("conflict_id")

    data = load_conflicts()
    conflict = next(
        (c for c in data.get("conflicts", []) if c["id"] == conflict_id),
        None
    )
    if not conflict:
        return jsonify({"error": "Conflict not found"}), 404

    profile = load_profile()
    has_profile = profile and any(profile.get(k) for k in ("location", "travel", "interests"))

    # Demo mode
    if DEMO_MODE:
        global_impact = DEMO_GLOBAL_IMPACT.get(
            conflict["name"],
            f"- **Regional instability**: Affects regional security and trade\n"
            f"- **Humanitarian**: Displacement strains international aid resources\n"
            f"- **Geopolitical**: Shifts in alliances may have broader implications"
        )
        personal = None
        if has_profile:
            personal = DEMO_PERSONAL_IMPACT.get(conflict["name"])
        return jsonify({
            "global_impact": global_impact,
            "personal_impact": personal,
            "has_profile": has_profile,
        })

    # Live mode — two separate LLM calls
    conflict_context = (
        f"Conflict: {conflict['name']}\n"
        f"Parties: {', '.join(conflict['parties'])}\n"
        f"Location: {conflict['location']['country']}, {conflict['location'].get('region', '')}\n"
        f"Status: {conflict['status']}\n"
        f"Summary: {conflict['summary']}"
    )

    global_prompt = f"""{conflict_context}

What is the global impact of this conflict? Cover: economic effects (commodity prices, trade, supply chains), transport disruptions (flights, shipping), humanitarian consequences, and geopolitical implications.

3-4 bullet points max. Be specific and factual, not alarmist. Start each bullet with a bold topic label."""

    global_impact = call_llm(global_prompt)

    personal = None
    if has_profile:
        parts = []
        if profile.get("location"):
            parts.append(f"Lives in: {profile['location']}")
        if profile.get("travel"):
            parts.append(f"Upcoming travel: {profile['travel']}")
        if profile.get("interests"):
            parts.append(f"Interests/concerns: {profile['interests']}")
        profile_text = "\n".join(parts)

        personal_prompt = f"""{conflict_context}

This person's context:
{profile_text}

How might this conflict specifically affect THIS person? Think about: prices they pay, flights they might take, supply chains for things they care about, safety of places they live or travel to.

2-3 bullet points max. Be concrete and specific to their situation. If there's no real connection, say so honestly — don't stretch."""

        personal = call_llm(personal_prompt)

    return jsonify({
        "global_impact": global_impact,
        "personal_impact": personal,
        "has_profile": has_profile,
    })


@app.route("/api/profile", methods=["GET"])
def get_profile():
    profile = load_profile()
    return jsonify(profile or {})


@app.route("/api/profile", methods=["POST"])
def save_profile():
    profile = request.json
    PROFILE_FILE.write_text(json.dumps(profile, indent=2))
    return jsonify({"status": "saved"})


if __name__ == "__main__":
    if DEMO_MODE:
        print("\n   No API key found — running in DEMO MODE with sample data")
        print("   To use live data, add your key to .env: GEMINI_API_KEY=...")
        print("   Get a free key at: https://aistudio.google.com/apikey")
    print("\n   Opening http://localhost:5001\n")
    app.run(debug=True, port=5001)
