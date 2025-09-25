from flask import Flask, redirect, request, session, render_template
import requests
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SCOPE = "user-top-read user-read-recently-played"

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

def get_auth_url():
    payload = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPE
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(payload)}"

@app.route('/')
def index():
    if session.get('access_token'):
        return redirect('/dashboard')
    return render_template('index.html', auth_url=get_auth_url())

@app.route('/callback')
def callback():
    code = request.args.get("code")
    
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=payload)
    response_data = response.json()

    session['access_token'] = response_data.get("access_token")
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    token = session.get('access_token')
    if not token:
        return redirect('/')
    
    return render_template("dashboard.html")

@app.route('/top-tracks')
def top_tracks():
    token = session.get('access_token')
    if not token:
        return redirect('/')
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/me/top/tracks?limit=10", headers=headers)
    data = response.json()
    return render_template("top_tracks.html", tracks=data['items'])

@app.route('/top-artists')
def top_artists():
    token = session.get('access_token')
    if not token:
        return redirect('/')
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/me/top/artists?limit=10", headers=headers)
    data = response.json()
    return render_template("top_artists.html", artists=data['items'])

@app.route('/recently-played')
def recently_played():
    token = session.get('access_token')
    if not token:
        return redirect('/')
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/me/player/recently-played?limit=50", headers=headers)
    data = response.json()
    return render_template("recently_played.html", tracks=data['items'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
