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

# Cache for team matches to reduce API calls
team_matches_cache = {}

def get_team_last_matches(team_id, limit=5):
    """Fetch last 'limit' matches for a team, using cache if available."""
    if team_id in team_matches_cache:
        return team_matches_cache[team_id]
    
    url = f"{BASE_URL}/teams/{team_id}/matches?status=FINISHED&limit={limit}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            team_matches_cache[team_id] = matches
            return matches
        else:
            return []
    except Exception as e:
        st.error(f"Error fetching matches for team {team_id}: {str(e)}")
        return []

def check_api_key():
    if not API_KEY:
        return "❌ API key not found."
    url = f"{BASE_URL}/competitions/PL"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return "✅ API key works!"
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
    """Check if a team has won its last 5 matches (uses cached data)."""
    matches = get_team_last_matches(team_id, 5)
    if len(matches) < 5:
        return False
    return all(
        (m['score']['winner'] == "HOME_TEAM" and m['homeTeam']['id'] == team_id) or
        (m['score']['winner'] == "AWAY_TEAM" and m['awayTeam']['id'] == team_id)
        for m in matches
    )

def has_over_2_5_in_last_four(team_id):
    """Check if a team's last 4 matches each had total goals >= 3 (over 2.5)."""
    matches = get_team_last_matches(team_id, 4)  # Get last 4 matches
    if len(matches) < 4:
        return False
    for match in matches[:4]:  # Use the 4 most recent matches
        score = match.get('score', {})
        full_time = score.get('fullTime', {})
        home_goals = full_time.get('home') or 0
        away_goals = full_time.get('away') or 0
        if home_goals + away_goals < 3:
            return False
    return True

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
st.write("This app highlights:")
st.write("✅ **Teams on a 5‑win streak** with **odds between 1.50 and 2.0** in their next fixture")
st.write("✅ **Teams whose last 4 matches all had over 2.5 goals** (total goals ≥ 3 per match)")

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

# Containers for results
flagged_matches = []          # (team, opponent, odds, league)
over_2_5_teams = set()        # (team_name, league_name) to avoid duplicates

progress_bar = st.progress(0, text="Analyzing matches...")

for i, comp in enumerate(competitions):
    comp_id = comp['code']      # e.g., "PL", "BL1"
    comp_name = comp['name']
    
    # Update progress
    progress_bar.progress((i + 1) / len(competitions), text=f"Checking {comp_name}...")
    
    matches = get_upcoming_matches(comp_id)
    
    for match in matches:
        home_id = match['homeTeam']['id']
        away_id = match['awayTeam']['id']
        home_name = match['homeTeam']['name']
        away_name = match['awayTeam']['name']

        # ---- 5‑win streak + odds 1.50–2.0 ----
        if has_five_wins(home_id):
            odds = match.get('odds', {}).get('homeWin')
            if odds and 1.50 <= odds <= 2.0:
                flagged_matches.append((home_name, away_name, odds, comp_name))

        if has_five_wins(away_id):
            odds = match.get('odds', {}).get('awayWin')
            if odds and 1.50 <= odds <= 2.0:
                flagged_matches.append((away_name, home_name, odds, comp_name))

        # ---- Over 2.5 goals in last 4 matches ----
        if has_over_2_5_in_last_four(home_id):
            over_2_5_teams.add((home_name, comp_name))
        if has_over_2_5_in_last_four(away_id):
            over_2_5_teams.add((away_name, comp_name))
    
    # Small delay to respect rate limits (free tier: 10 requests/minute)
    time.sleep(0.5)

progress_bar.empty()

# -------------------- DISPLAY RESULTS --------------------
st.subheader("📊 Predicted Matches (5‑win streak + odds 1.50–2.0)")
if flagged_matches:
    for team, opponent, odds, league in flagged_matches:
        st.success(f"**{team}** vs {opponent} | Odds: {odds:.2f} | League: {league}")
    st.info(f"Found {len(flagged_matches)} qualifying matches across {len(competitions)} leagues.")
else:
    st.write("No qualifying matches found at this time.")

st.subheader("⚽ Teams with Over 2.5 Goals in Last 4 Matches")
if over_2_5_teams:
    # Sort alphabetically by league then team
    for team, league in sorted(over_2_5_teams, key=lambda x: (x[1], x[0])):
        st.write(f"• **{team}** ({league})")
    st.info(f"Found {len(over_2_5_teams)} teams with this pattern.")
else:
    st.write("No teams found with over 2.5 goals in their last 4 matches.")

