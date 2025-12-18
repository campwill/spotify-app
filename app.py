from flask import Flask, redirect, request, session, render_template
import requests
import os
from urllib.parse import urlencode
from dotenv import load_dotenv
#import db


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
    access_token = response_data.get("access_token")
    refresh_token = response_data.get("refresh_token")
    expires_in = response_data.get("expires_in")
    headers = {"Authorization": f"Bearer {access_token}"}
    user_profile = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers).json()

    user_id = user_profile["id"]
    display_name = user_profile.get("display_name")
    email = user_profile.get("email")

    # Save to DB
    #db.save_user(user_id, display_name, email, access_token, refresh_token, expires_in)

    # Save to session
    session['user_id'] = user_id
    session['access_token'] = access_token

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
    
    if response.status_code != 200:
        return f"Error {response.status_code}: {response.text}", response.status_code
    try:
        data = response.json()
    except ValueError:
        return f"Invalid response from Spotify: {response.text}"

    if not data or not data.get("items"):
        return "No tracks found."

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

@app.route('/album-search')
def album_search():
    return render_template("album_search.html")
@app.route('/album-results')
def album_results():
    album_name = request.args.get("album")
    token = session.get('access_token')

    if not token or not album_name:
        return redirect(url_for('album_search'))

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/search",
        headers=headers,
        params={"q": album_name, "type": "album", "limit": 10}
    )

    data = response.json()
    albums = data.get("albums", {}).get("items", [])

    return render_template("album_results.html", albums=albums)
@app.route('/album-tournament/<album_id>')
def album_tournament(album_id):
    token = session.get('access_token')
    if not token:
        return redirect(url_for('album_search'))
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/albums/{album_id}/tracks", headers=headers)
    tracks = response.json().get("items", [])

    return render_template("album_tournament.html", tracks=tracks)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
