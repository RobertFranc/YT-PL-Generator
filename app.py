import streamlit as st
import requests
import os
import csv
from datetime import datetime

# 1. Fetch API Key securely
try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Missing API_KEY secret! Please add it to your Streamlit Cloud Advanced Settings.")
    st.stop()

# File path for our local history log
LOG_FILE_PATH = "video_playback_history.csv"

def log_track_to_csv(title, video_id, action="PLAYED"):
    """Logs track metadata along with a timestamp to a local CSV file."""
    file_exists = os.path.exists(LOG_FILE_PATH)
    
    # Structure data entry row
    row = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Track Title": title,
        "Video ID": video_id,
        "Action Status": action
    }
    
    # Append or create file safely
    with open(LOG_FILE_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Timestamp", "Track Title", "Video ID", "Action Status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def fetch_youtube_videos(query, api_key, max_results=5):
    """Fetches high-definition videos from YouTube API based on the query."""
    url = "https://googleapis.com"
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'videoDefinition': 'high',
        'order': 'viewCount',
        'maxResults': max_results,
        'key': api_key
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        playlist = []
        for item in data.get('items', []):
            playlist.append({
                'id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'channel': item['snippet']['channelTitle']
            })
        return playlist
    except Exception as err:
        st.error(f"Error fetching data from YouTube: {err}")
        return []

# --- Initialize Session States ---
if 'playlist' not in st.session_state:
    st.session_state.playlist = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'playback_speed' not in st.session_state:
    st.session_state.playback_speed = 1.0
if 'last_logged_video' not in st.session_state:
    st.session_state.last_logged_video = None

# Helper navigation blocks
def advance_track():
    if st.session_state.playlist:
        st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.playlist)

def reverse_track():
    if st.session_state.playlist:
        st.session_state.current_index = (st.session_state.current_index - 1) % len(st.session_state.playlist)

# --- App Layout ---
st.title("🎵 Interactive YouTube Autoplay Player")

# Search UI configuration
with st.expander("🔍 Search & Create Playlist", expanded=not bool(st.session_state.playlist)):
    search_query = st.text_input("Search term:", value="Rock music")
    results_count = st.slider("Tracks to fetch", min_value=2, max_value=15, value=5)
    
    if st.button("Generate Playlist"):
        with st.spinner("Fetching tracks..."):
            fetched_tracks = fetch_youtube_videos(search_query, API_KEY, results_count)
            if fetched_tracks:
                st.session_state.playlist = fetched_tracks
                st.session_state.current_index = 0  # Reset
                st.session_state.last_logged_video = None 
                st.rerun()
            else:
                st.warning("No videos found.")

# --- Main Player Area ---
if st.session_state.playlist:
    current_track = st.session_state.playlist[st.session_state.current_index]
    
    # Log track cleanly when it changes to prevent duplicate rows on re-renders
    if st.session_state.last_logged_video != current_track['id']:
        log_track_to_csv(current_track['title'], current_track['id'], action="START PLAYBACK")
        st.session_state.last_logged_video = current_track['id']

    st.subheader(f" Now Playing ({st.session_state.current_index + 1}/{len(st.session_state.playlist)}): {current_track['title']}")
    st.caption(f"**Channel:** {current_track['channel']}")
    
    # Speed and Selection Row Controls
    col_speed, col_jump = st.columns(2)
    with col_speed:
        speeds = [0.25, 0.5, 1.0, 1.25, 1.5, 2.0]
        selected_speed = st.selectbox(
            "Playback Speed", 
            options=speeds, 
            index=speeds.index(st.session_state.playback_speed)
        )
        st.session_state.playback_speed = selected_speed

    with col_jump:
        track_titles = [f"{i+1}. {t['title']}" for i, t in enumerate(st.session_state.playlist)]
        chosen_track_str = st.selectbox(
            "Jump to Track", 
            options=track_titles, 
            index=st.session_state.current_index
        )
        chosen_index = track_titles.index(chosen_track_str)
        if chosen_index != st.session_state.current_index:
            log_track_to_csv(current_track['title'], current_track['id'], action="SKIPPED VIA DROPDOWN")
            st.session_state.current_index = chosen_index
            st.rerun()

    # --- AUTOPLAY IFRAME INTEGRATION ---
    # Using window.parent.postMessage to alert Streamlit when the video ends natively
    player_html = f"""
    <div id="player" style="width:100%; max-width:640px; margin:0 auto; aspect-ratio:16/9;"></div>
    <script>
      var tag = document.createElement('script');
      tag.src = "https://youtube.com";
      var firstScriptTag = document.getElementsByTagName('script');
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

      var player;
      function onYouTubeIframeAPIReady() {{
        player = new YT.Player('player', {{
          height: '100%',
          width: '100%',
          videoId: '{current_track['id']}',
          playerVars: {{
            'playsinline': 1,
            'autoplay': 1,
            'controls': 1
          }},
          events: {{
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
          }}
        }});
      }}

      function onPlayerReady(event) {{
        event.target.setPlaybackRate({st.session_state.playback_speed});
      }}

      function onPlayerStateChange(event) {{
        // YT.PlayerState.ENDED code equals exactly 1
        if (event.data == YT.PlayerState.ENDED) {{
           // Send completion event up to the parent window frame
           window.parent.postMessage({{type: 'youtube_video_ended'}}, '*');
        }}
      }}
    </script>
    """
    
    # Render player component
    st.components.v1.html(player_html, height=400)

    # --- Capture the Autoplay PostMessage Trigger ---
    # We use a tiny hidden component trick to read the message event pipeline
    autoplay_handler = """
    <script>
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'youtube_video_ended') {
                // Click a hidden streamlit structural submit flag or button to step forward
                const buttons = window.parent.document.querySelectorAll('button');
                for (let btn of buttons) {
                    if (btn.innerText.includes('⏭️ Next Track')) {
                        btn.click();
                        break;
                    }
                }
            }
        });
    </script>
    """
    st.components.v1.html(autoplay_handler, height=0)

    # --- Playlist Navigation Controls ---
    st.markdown("### 🎛️ Navigation Controls")
    btn_prev, btn_next = st.columns(2)
    
    with btn_prev:
        if st.button("⏮️ Previous Track", use_container_width=True):
            log_track_to_csv(current_track['title'], current_track['id'], action="SKIPPED PREVIOUS")
            reverse_track()
            st.rerun()
            
    with btn_next:
        if st.button("⏭️ Next Track", use_container_width=True):
            # Check if clicked explicitly vs triggered by native autoplay finish loop
            log_track_to_csv(current_track['title'], current_track['id'], action="FORWARD NAVIGATION")
            advance_track()
            st.rerun()

    # --- Sidebar Playlist Queue & Log Download ---
    with st.sidebar:
        st.header("📋 Next Up Queue")
        for idx, track in enumerate(st.session_state.playlist):
            if idx == st.session_state.current_index:
                st.markdown(f"**👉 {idx+1}. {track['title']}** *(Playing)*")
            else:
                if st.button(f"{idx+1}. {track['title']}", key=f"side_{track['id']}_{idx}"):
                    log_track_to_csv(current_track['title'], current_track['id'], action="SKIPPED VIA SIDEBAR")
                    st.session_state.current_index = idx
                    st.rerun()
        
        st.markdown("---")
        st.header("📊 History Management")
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                csv_data = f.read()
            st.download_button(
                label="📥 Download History Log (.csv)",
                data=csv_data,
                file_name=LOG_FILE_PATH,
                mime="text/csv"
            )
else:
    st.info("Search a topic above to generate your playing queue.")
