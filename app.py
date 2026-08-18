from flask import Flask, redirect, request, session, render_template,url_for
import requests
import os, time
from urllib.parse import urlencode
from dotenv import load_dotenv
from collections import defaultdict


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SCOPE = "user-top-read user-read-recently-played playlist-modify-private playlist-modify-public"

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
def refresh_token():
    refresh = session.get("refresh_token")

    if not refresh:
        return None

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET,
        }
    )

    token_data = response.json()

    session["access_token"] = token_data["access_token"]
    session["expires_at"] = time.time() + token_data["expires_in"]

    return session["access_token"]
def get_token():
    access_token = session.get("access_token")
    expires_at = session.get("expires_at")

    if not access_token or not expires_at:
        return None

    if time.time() < expires_at - 60:
        return access_token

    return refresh_token()

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

    session['access_token'] = access_token
    session['refresh_token'] = refresh_token
    session['expires_at'] = time.time() + expires_in

    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    token = get_token()
    if not token:
        return redirect('/')

    headers = {"Authorization": f"Bearer {token}"}

    top_artists = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/top/artists?limit=3",
        headers=headers
    ).json().get("items", [])

    top_tracks = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/top/tracks?limit=3",
        headers=headers
    ).json().get("items", [])

    recent_res = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/player/recently-played?limit=50",
        headers=headers
    )
    recently_played = recent_res.json().get("items", [])

    profile = requests.get("https://api.spotify.com/v1/me",headers=headers).json()

    username = profile.get("display_name")

    album_scores = defaultdict(float)
    album_data = {}

    for rank, track in enumerate(top_tracks, start=1):
        # Higher-ranked tracks are worth more
        score = max(1, 11 - rank)

        album = track["album"]
        album_id = album["id"]

        album_scores[album_id] += score

        if album_id not in album_data:
            album_data[album_id] = {
                "id": album_id,
                "name": album["name"],
                "image": album["images"][0]["url"] if album.get("images") else None,
                "artist": track["artists"][0]["name"]
            }

    top_albums = sorted(
        album_data.values(),
        key=lambda album: album_scores[album["id"]],
        reverse=True
    )

    top_albums = top_albums[:3]

    return render_template(
    "dashboard.html",
    username=username,
    top_artists=top_artists,
    top_tracks=top_tracks,
    recently_played=recently_played,
    top_albums=top_albums)


@app.route('/top-tracks')
def top_tracks():
    token = session.get('access_token')
    if not token:
        return redirect('/')

    time_range = request.args.get("time_range", "medium_term")
    limit = int(request.args.get("limit", 25))  # convert to int

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/top/tracks",
        headers=headers,
        params={
            "limit": limit,
            "time_range": time_range
        }
    )

    if response.status_code != 200:
        return f"Error {response.status_code}: {response.text}"

    data = response.json()
    tracks = data.get("items", [])

    return render_template("top_tracks.html", tracks=tracks, time_range=time_range, limit=limit)

@app.route('/top-artists')
def top_artists():
    token = session.get('access_token')
    if not token:
        return redirect('/')

    time_range = request.args.get("time_range", "medium_term")
    limit = int(request.args.get("limit", 25))

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/top/artists",
        headers=headers,
        params={
            "time_range": time_range,
            "limit": limit
        }
    )

    if response.status_code != 200:
        return response.text, response.status_code

    data = response.json()
    artists = data.get("items", [])

    return render_template("top_artists.html", artists=artists, time_range=time_range, limit=limit)

@app.route('/recently-played')
def recently_played():
    token = session.get('access_token')
    if not token:
        return redirect('/')

    limit = int(request.args.get("limit", 25))

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/player/recently-played",
        headers=headers,
        params={
            "limit": limit
        }
    )

    if response.status_code != 200:
        return f"Error {response.status_code}: {response.text}"

    data = response.json()
    tracks = data.get("items", [])

    return render_template("recently_played.html", tracks=tracks, limit=limit)

@app.route('/generate-playlist', methods=['POST'])
def generate_playlist():
    token = session.get('access_token')
    if not token:
        return redirect('/')

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    user_id = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers).json()["id"]

    track_uris = request.form.getlist("track_uri")
    if not track_uris:
        return "No tracks selected", 400

    playlist_data = {
        "name": "My Top Tracks",
        "description": "Playlist generated from Spotify Dashboard",
        "public": False
    }
    create_resp = requests.post(f"{SPOTIFY_API_BASE_URL}/users/{user_id}/playlists", headers=headers, json=playlist_data)
    if create_resp.status_code != 201:
        return f"Error creating playlist: {create_resp.text}", create_resp.status_code

    playlist_id = create_resp.json()["id"]

    add_resp = requests.post(
        f"{SPOTIFY_API_BASE_URL}/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"uris": track_uris}
    )
    if add_resp.status_code != 201:
        return f"Error adding tracks: {add_resp.text}", add_resp.status_code

    return redirect(f"https://open.spotify.com/playlist/{playlist_id}")

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
        params={
            "q": album_name, 
            "type": "album", 
            "limit": 10
        }
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

    album = requests.get(f"{SPOTIFY_API_BASE_URL}/albums/{album_id}", headers=headers).json()
    tracks = requests.get(f"{SPOTIFY_API_BASE_URL}/albums/{album_id}/tracks", headers=headers).json().get("items", [])

    img = album["images"][0]["url"]

    for track in tracks:
        track["img"] = img

    return render_template("album_tournament.html", tracks=tracks)

@app.route('/test')
def test():
    return render_template("test.html")

@app.route('/album-bracket/<album_id>')
@app.route('/album-bracket/<album_id>')
def album_bracket(album_id):
    token = session.get('access_token')
    if not token:
        return redirect(url_for('album_search'))

    headers = {"Authorization": f"Bearer {token}"}

    album = requests.get(f"{SPOTIFY_API_BASE_URL}/albums/{album_id}", headers=headers).json()
    tracks = requests.get(f"{SPOTIFY_API_BASE_URL}/albums/{album_id}/tracks", headers=headers).json().get("items", [])

    img = album["images"][0]["url"]

    for track in tracks:
        track["img"] = img

    return render_template("album_bracket.html", tracks=tracks,album=album)
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)