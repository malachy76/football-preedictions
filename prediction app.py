import os
import requests
import streamlit as st
import time

# -------------------- API KEY LOADING --------------------
try:
    API_KEY = st.secrets["API_KEY"]
except (KeyError, AttributeError):
    API_KEY = os.getenv("API_KEY")
# ---------------------------------------------------------

BASE_URL = "https://api.football-data.org/v4"
headers = {"X-Auth-Token": API_KEY}

def check_api_key():
    if not API_KEY:
        return "❌ API key not found."
    url = f"{BASE_URL}/competitions/PL"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return f"✅ API key works!"
        else:
            return f"❌ API key failed. Status: {response.status_code}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_european_competitions():
    """Fetch all competitions and return those in Europe (UEFA area id: 2077)."""
    url = f"{BASE_URL}/competitions"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            competitions = data.get('competitions', [])
            # Filter by UEFA area (area id 2077 is Europe)
            euro_comps = [c for c in competitions if c.get('area', {}).get('id') == 2077]
            return euro_comps
        else:
            st.error(f"Failed to fetch competitions: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching competitions: {str(e)}")
        return []

def has_five_wins(team_id):
    if not API_KEY:
        return False
    url = f"{BASE_URL}/teams/{team_id}/matches?status=FINISHED&limit=5"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return False
        data = response.json()
        matches = data.get('matches', [])
        if len(matches) < 5:
            return False
        return all(
            (m['score']['winner'] == "HOME_TEAM" and m['homeTeam']['id'] == team_id) or
            (m['score']['winner'] == "AWAY_TEAM" and m['awayTeam']['id'] == team_id)
            for m in matches
        )
    except:
        return False

def get_upcoming_matches(competition_id):
    url = f"{BASE_URL}/competitions/{competition_id}/matches?status=SCHEDULED"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('matches', [])
        return []
    except:
        return []

# -------------------- STREAMLIT UI --------------------
st.set_page_config(page_title="Football Prediction App", page_icon="⚽")
st.title("⚽ European League Prediction App")
st.write("This app highlights matches where:")
st.write("- A team has **5 consecutive wins**")
st.write("- That team has **odds ≤ 1.50** in their next fixture")

if not API_KEY:
    st.error("⚠️ API key not found! Please set it in Streamlit Secrets or a .env file.")
    st.stop()

if st.button("Check API Key"):
    with st.spinner("Testing API key..."):
        result = check_api_key()
        st.info(result)

# Fetch all European competitions
with st.spinner("Fetching European leagues..."):
    competitions = get_european_competitions()

if not competitions:
    st.warning("No European competitions found. Your API key may not have access or there might be an issue.")
    st.stop()

st.success(f"Found {len(competitions)} European leagues.")

flagged_matches = []
progress_bar = st.progress(0, text="Analyzing matches...")

for i, comp in enumerate(competitions):
    comp_id = comp['code']  # e.g., "PL", "BL1"
    comp_name = comp['name']
    
    # Update progress
    progress_bar.progress((i + 1) / len(competitions), text=f"Checking {comp_name}...")
    
    matches = get_upcoming_matches(comp_id)
    
    for match in matches:
        home_id = match['homeTeam']['id']
        away_id = match['awayTeam']['id']
        home_name = match['homeTeam']['name']
        away_name = match['awayTeam']['name']

        # Check home team
        if has_five_wins(home_id):
            odds = match.get('odds', {}).get('homeWin')
            if odds and odds <= 1.50:
                flagged_matches.append((home_name, away_name, odds, comp_name))

        # Check away team
        if has_five_wins(away_id):
            odds = match.get('odds', {}).get('awayWin')
            if odds and odds <= 1.50:
                flagged_matches.append((away_name, home_name, odds, comp_name))
    
    # Small delay to avoid hitting rate limits (free tier: 10 requests/minute)
    time.sleep(0.5)

progress_bar.empty()

# Display results
st.subheader("📊 Predicted Matches")
if flagged_matches:
    for team, opponent, odds, league in flagged_matches:
        st.success(f"**{team}** vs {opponent} | Odds: {odds:.2f} | League: {league}")
    st.info(f"Found {len(flagged_matches)} qualifying matches across {len(competitions)} leagues.")
else:
    st.write("No qualifying matches found at this time.")

