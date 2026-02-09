import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px
import random
from datetime import datetime

# --- Database Setup ---
conn = sqlite3.connect("sports_analytics.db")
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    balance INTEGER DEFAULT 1000
)""")

c.execute("""CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    team TEXT,
    coins INTEGER,
    odds REAL,
    result TEXT,
    balance INTEGER,
    date TEXT
)""")

conn.commit()

# --- API Keys ---
FD_API_KEY = "YOUR_FOOTBALL_DATA_KEY"
ODDS_API_KEY = "YOUR_ODDS_API_KEY"

FD_BASE_URL = "https://api.football-data.org/v4"
ODDS_BASE_URL = "https://api.odds-api.com/v4/sports"

fd_headers = {"X-Auth-Token": FD_API_KEY}

# --- Football-Data.org ---
def get_competitions():
    url = f"{FD_BASE_URL}/competitions"
    response = requests.get(url, headers=fd_headers)
    return response.json()

# --- Odds API ---
def get_odds(league_key):
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    response = requests.get(f"{ODDS_BASE_URL}/{league_key}/odds", params=params)
    return response.json()

# --- Visualization ---
def plot_balance(username):
    df = pd.read_sql("SELECT * FROM bets WHERE username=?", conn, params=(username,))
    if df.empty:
        st.info("No balance history yet.")
        return
    fig = px.line(df, x="date", y="balance", title=f"{username}'s Balance Over Time")
    st.plotly_chart(fig)

def plot_leaderboard():
    df_users = pd.read_sql("SELECT username, balance FROM users ORDER BY balance DESC", conn)
    st.table(df_users)

# --- Streamlit UI ---
st.title("⚽ European Sports Analytics Dashboard with Live Odds")

# --- User Login ---
st.sidebar.title("👤 User Login")
username = st.sidebar.text_input("Enter username")
if st.sidebar.button("Login/Register"):
    try:
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        st.sidebar.success(f"New user {username} registered with 1000 coins!")
    except sqlite3.IntegrityError:
        st.sidebar.info(f"Welcome back, {username}!")

# --- Automatic League Detection ---
competitions_data = get_competitions()
european_leagues = []
for comp in competitions_data["competitions"]:
    if comp["area"]["name"] in [
        "England","Spain","Italy","Germany","France","Netherlands","Portugal",
        "Turkey","Belgium","Switzerland","Austria","Scotland","Greece","Poland",
        "Czech Republic","Russia","Ukraine","Norway","Sweden","Denmark","Finland"
    ]:
        if comp["type"] == "LEAGUE":
            european_leagues.append({
                "name": comp["name"],
                "code": comp["code"],
                "country": comp["area"]["name"]
            })

df_leagues = pd.DataFrame(european_leagues)
st.subheader("🇪🇺 European Leagues (Auto-Detected)")
st.dataframe(df_leagues)

league_choice = st.selectbox("Select a League", df_leagues["name"])
league_code = df_leagues[df_leagues["name"] == league_choice]["code"].values[0]

st.write(f"You selected: {league_choice} ({league_code})")

# --- Live Odds Integration ---
st.subheader("📊 Live Odds (Odds ≤ 1.50)")
odds_data = get_odds("soccer_epl")  # Example: EPL, map league_code to Odds API key

for match in odds_data:
    home = match["home_team"]
    away = match["away_team"]
    bookmakers = match["bookmakers"]

    for bookmaker in bookmakers:
        for market in bookmaker["markets"]:
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    if outcome["price"] <= 1.50:
                        st.success(f"{outcome['name']} vs {home if outcome['name'] != home else away} - Odds: {outcome['price']} ({bookmaker['title']})")

# --- Fantasy Coins Simulator ---
st.subheader("🎮 Fantasy Coins Simulator")
coins = st.number_input("Enter coins to bet:", min_value=0, step=10)

if st.button("Simulate Bet"):
    if username:
        c.execute("SELECT balance FROM users WHERE username=?", (username,))
        balance = c.fetchone()[0]

        # Random win/loss simulation
        result = random.choice(["WIN", "LOSS"])
        odds = 1.50  # Example odds
        if result == "WIN":
            balance += int(coins * odds)
            st.success(f"{username} WON! New balance: {balance} coins")
        else:
            balance -= coins
            st.error(f"{username} LOST. New balance: {balance} coins")

        c.execute("UPDATE users SET balance=? WHERE username=?", (balance, username))
        c.execute("INSERT INTO bets (username, team, coins, odds, result, balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (username, "Demo Team", coins, odds, result, balance, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
    else:
        st.warning("Please log in first!")

# --- Leaderboard ---
st.subheader("🏆 Leaderboard")
plot_leaderboard()

# --- Balance Trend ---
if username:
    st.subheader("💰 Balance Trend")
    plot_balance(username)