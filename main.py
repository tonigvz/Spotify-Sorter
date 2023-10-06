import concurrent.futures
from dotenv import load_dotenv
import os
from requests import post, get
import json

# Load environment variables
load_dotenv()

# Initialize variables
refresh_token = os.getenv("REFRESH")
auth_base64 = os.getenv("AUTH_BASE64")
playlist_id = ""

track_info_set = set()  # Set to store track information
approved_artist_ids = set()  # Set to store approved artist IDs
matching_tracks = set()  # Set to store tracks that match criteria


def get_token(refresh_token):
    """Function to obtain access token using refresh token."""
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        response_data = response.json()
        print(f"Failed to get access token. Status code: {response.status_code}")
        print(f"Error message: {response_data}")
        return None


def fetch_track_info(token):
    """Function to fetch track information from the Spotify API."""
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }

    while url:
        response = get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                track_info = item.get("track")
                if track_info:
                    track_id = track_info.get("uri", "")
                    artist_id = track_info["artists"][0].get("id", "")
                    track_info_set.add((track_id, artist_id))

            url = data.get('next')  # Move to the next page of results if available
        else:
            print(f"Failed to fetch tracks. Status code: {response.status_code}")
            break



def fetch_artist_genres(artist_id):
    """Function to fetch artist genres using artist ID."""
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }

    response = get(url, headers=headers)
    if response.status_code == 200:
        artist_data = response.json()
        genres = artist_data.get("genres", [])
        if any('r&b' in genre for genre in genres):
            approved_artist_ids.add(artist_id)
    else:
        print(f"Failed to fetch artist genres for Artist ID {artist_id}. Status code: {response.status_code}")



def create_playlist(token):
    """Function to create a new playlist on Spotify."""
    endpoint = f"https://api.spotify.com/v1/users/druggedbiebs/playlists"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
    playlist_data = {
        "name": "only r&b",
        "description": "playlist created by API",
        "public": True,
    }

    response = post(endpoint, headers=headers, json=playlist_data)

    if response.status_code == 201:
        playlist_id = response.json().get('id')
        print(f"Playlist created with ID: {playlist_id}")
        return playlist_id
    else:
        print(f"Failed to create playlist. Status code: {response.status_code}")
        print(f"Error message: {response.text}")
        return None


def add_songs_to_playlist(token, playlist_id, track_uris):
    """Function to add songs to a playlist on Spotify."""
    if not token or not playlist_id or not track_uris:
        print("Invalid input. Please provide a valid access token, playlist ID, and track URIs.")
        return False

    endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }

    max_tracks_per_request = 100
    for i in range(0, len(track_uris), max_tracks_per_request):
        data = {
            "uris": track_uris[i:i + max_tracks_per_request]
        }

        try:
            response = post(endpoint, headers=headers, json=data)
            response_data = response.json()

            if response.status_code == 201:
                print("Songs added to the playlist successfully.")
            else:
                print(f"Failed to add songs to the playlist. Status code: {response.status_code}")
                print(f"Error message: {response_data}")
                return False
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON. Details: {str(e)}")
            return False

    return True


def main():
    global token
    token = get_token(refresh_token)

    # Fetch track information
    fetch_track_info(token)

    unique_artist_ids = {artist_id for _, artist_id in track_info_set}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Fetch artist genres in parallel
        executor.map(fetch_artist_genres, list(unique_artist_ids))


    # Get matching tracks based on approved artist IDs
    for track_id, artist_id in track_info_set:
        if artist_id in approved_artist_ids:
            matching_tracks.add(track_id)

    playlist_id1 = create_playlist(token)

    if playlist_id1:
        # Add songs to the playlist
        add_songs_to_playlist(token, playlist_id1, list(matching_tracks))

    



if __name__ == "__main__":
    main()
