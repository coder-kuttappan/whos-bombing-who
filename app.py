import json
import os
import time
from pathlib import Path

import feedparser
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
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

DEMO_IMPACT = {
    "Russia-Ukraine War": "- **Energy prices**: European gas prices remain elevated, contributing to global energy cost pressures that affect fuel and electricity bills worldwide\n- **Food supply**: Ukraine is a major grain exporter — the conflict continues to impact global wheat and sunflower oil prices\n- **Flight routes**: Most airlines reroute around Ukrainian and parts of Russian airspace, adding 1-3 hours to many Europe-Asia flights\n- **Cybersecurity**: Increased state-sponsored cyber activity affects global infrastructure; heightened risk for financial and tech sectors\n- **Nuclear risk**: Low but non-zero escalation risk keeps geopolitical uncertainty elevated, affecting markets globally",
    "Israel-Palestine Conflict": "- **Oil prices**: Regional instability affects oil market sentiment, though direct supply disruption has been limited\n- **Shipping**: Houthi attacks on Red Sea shipping (linked to the conflict) have disrupted the Suez Canal route, increasing shipping costs 2-3x on affected routes\n- **Flight routes**: Some airlines avoid overflying parts of the Middle East; routes through the region may see diversions\n- **Tech sector**: Israel is a major tech hub — prolonged conflict affects venture capital flows and startup activity in the region\n- **Humanitarian**: One of the worst humanitarian crises in recent history, with significant implications for international law and institutions",
    "Sudan Civil War": "- **Refugee crisis**: Millions fleeing to neighboring countries (Chad, Egypt, South Sudan) straining regional resources and aid budgets\n- **Gold supply**: Sudan is Africa's third-largest gold producer — conflict disrupts supply chains\n- **Red Sea security**: Instability near Port Sudan could affect Red Sea shipping routes\n- **Humanitarian funding**: Diverts international aid resources from other crises\n- **Regional stability**: Risk of conflict spillover into neighboring countries, particularly Chad and South Sudan",
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

    # Demo mode — return canned impact or generic message
    if DEMO_MODE:
        impact = DEMO_IMPACT.get(
            conflict["name"],
            f"- **Regional instability**: The {conflict['name']} affects regional security and may impact travel routes\n"
            f"- **Economic effects**: Potential disruption to local and regional trade\n"
            f"- **Humanitarian**: Displacement and humanitarian needs strain international aid resources\n"
            f"- **Geopolitical**: Shifts in alliances and international relations may have broader implications"
        )
        return jsonify({"impact": impact})

    profile = load_profile()
    profile_text = ""
    if profile:
        parts = []
        if profile.get("location"):
            parts.append(f"Lives in: {profile['location']}")
        if profile.get("travel"):
            parts.append(f"Upcoming travel: {profile['travel']}")
        if profile.get("interests"):
            parts.append(f"Interests/concerns: {profile['interests']}")
        profile_text = "\n".join(parts)

    prompt = f"""Analyze how this conflict might personally affect someone.

Conflict: {conflict['name']}
Parties: {', '.join(conflict['parties'])}
Location: {conflict['location']['country']}, {conflict['location'].get('region', '')}
Status: {conflict['status']}
Summary: {conflict['summary']}
"""
    if profile_text:
        prompt += f"\nUser's context:\n{profile_text}\n"
        prompt += "\nProvide a personalized impact analysis covering: flight route disruptions, economic impacts (prices, supply chains), regional stability implications, and any direct relevance to their location or travel plans."
    else:
        prompt += "\nNo user profile available. Provide a general impact analysis covering: global economic effects, flight route disruptions, humanitarian implications, and potential escalation risks."

    prompt += "\n\nKeep it concise — 3-5 bullet points max. Be specific and practical, not alarmist."

    impact_text = call_llm(prompt)
    return jsonify({"impact": impact_text})


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
