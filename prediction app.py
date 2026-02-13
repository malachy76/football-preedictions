import os
import requests
import streamlit as st

# -------------------- API KEY LOADING --------------------
# Try to get API key from Streamlit secrets first (for cloud deployment),
# then from environment variables (for local development with .env file)
try:
    API_KEY = st.secrets["API_KEY"]
except (KeyError, AttributeError):
    API_KEY = os.getenv("API_KEY")
# ---------------------------------------------------------

# Configuration
BASE_URL = "https://api.football-data.org/v4"
headers = {"X-Auth-Token": API_KEY}

def check_api_key():
    """Test if API key works by fetching Premier League info."""
    if not API_KEY:
        return "❌ API key not found. Please set it in Streamlit Secrets or a .env file."
    
    url = f"{BASE_URL}/competitions/PL"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return f"✅ API key works! Competition name: {data.get('name')}"
        else:
            return f"❌ API key failed. Status code: {response.status_code}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def has_five_wins(team_id):
    """Check if a team has won its last 5 matches."""
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
    except Exception as e:
        st.error(f"Error checking team wins: {str(e)}")
        return False

def get_upcoming_matches(league_id):
    """Fetch upcoming matches for a league."""
    if not API_KEY:
        return []
    
    url = f"{BASE_URL}/competitions/{league_id}/matches?status=SCHEDULED"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('matches', [])
        return []
    except Exception as e:
        st.error(f"Error fetching matches for league {league_id}: {str(e)}")
        return []

# Streamlit UI configuration
st.set_page_config(page_title="Football Prediction App", page_icon="⚽")
st.title("⚽ European League Prediction App")

st.write("This app highlights matches where:")
st.write("- A team has **5 consecutive wins**")
st.write("- That team has **odds ≤ 1.50** in their next fixture")

# Display API key status
if not API_KEY:
    st.error("⚠️ API key not found! Please configure it.")
    if not st.secrets:
        st.info("For Streamlit Cloud: Go to app settings → Secrets and add: `API_KEY = \"your_key_here\"`")
    st.stop()  # Stop execution if no API key

st.success("✅ API key loaded successfully")

# API key test button
if st.button("Check API Key"):
    with st.spinner("Testing API key..."):
        result = check_api_key()
        st.info(result)

# Main functionality
leagues = ["PL", "ELC", "BL1", "BL2", "PD", "SD"]  # Example league codes
league_names = {
    "PL": "Premier League",
    "ELC": "Championship",
    "BL1": "Bundesliga",
    "BL2": "2. Bundesliga", 
    "PD": "La Liga",
    "SD": "Segunda Division"
}

flagged_matches = []

with st.spinner("Fetching matches and analyzing streaks..."):
    for league in leagues:
        matches = get_upcoming_matches(league)
        for match in matches:
            home_id = match['homeTeam']['id']
            away_id = match['awayTeam']['id']
            home_name = match['homeTeam']['name']
            away_name = match['awayTeam']['name']

            # Check home team streak + odds
            if has_five_wins(home_id):
                odds = match.get('odds', {}).get('homeWin', None)
                if odds and odds <= 1.50:
                    flagged_matches.append((home_name, away_name, odds, league_names.get(league, league)))

            # Check away team streak + odds
            if has_five_wins(away_id):
                odds = match.get('odds', {}).get('awayWin', None)
                if odds and odds <= 1.50:
                    flagged_matches.append((away_name, home_name, odds, league_names.get(league, league)))

# Display results
st.subheader("📊 Predicted Matches")
if flagged_matches:
    for team, opponent, odds, league in flagged_matches:
        st.success(f"**{team}** vs {opponent} | Odds: {odds:.2f} | League: {league}")
    st.info(f"Found {len(flagged_matches)} qualifying matches")
else:
    st.write("No qualifying matches found at this time.")
