import streamlit as st
import requests

# 1. Fetch API Key securely
try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Missing API_KEY secret! Please add it to your Streamlit Cloud Advanced Settings.")
    st.stop()

def fetch_youtube_videos(query, api_key, max_results=5):
    """Fetches high-definition videos from YouTube API based on the query."""
    url = "https://googleapis.com"
    url = "https://www.googleapis.com/youtube/v3/search"
    
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
        print(data['items'][0].keys())
        
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

# --- App Layout ---
st.title("🎵 YouTube Playlist Player")

# Search UI Side panel / Header
with st.expander("🔍 Search & Create Playlist", expanded=not bool(st.session_state.playlist)):
    search_query = st.text_input("Search term:", value="love song")
    results_count = st.slider("Tracks to fetch", min_value=2, max_value=15, value=5)
    
    if st.button("Generate Playlist"):
        with st.spinner("Fetching tracks..."):
            fetched_tracks = fetch_youtube_videos(search_query, API_KEY, results_count)
            if fetched_tracks:
                st.session_state.playlist = fetched_tracks
                st.session_state.current_index = 0  # Reset to first track
                st.rerun()
            else:
                st.warning("No videos found.")

# --- Main Player Area ---
if st.session_state.playlist:
    current_track = st.session_state.playlist[st.session_state.current_index]
    
    st.subheader(f" Now Playing ({st.session_state.current_index + 1}/{len(st.session_state.playlist)}): {current_track['title']}")
    st.caption(f"**Channel:** {current_track['channel']}")
    
    # Control Sidebar / Row for playback adjustments
    col_speed, col_jump = st.columns([1, 2])
    with col_speed:
        # Playback speed map
        speeds = [0.25, 0.5, 1.0, 1.25, 1.5, 2.0]
        selected_speed = st.selectbox(
            "Playback Speed", 
            options=speeds, 
            index=speeds.index(st.session_state.playback_speed),
            key="speed_selector"
        )
        st.session_state.playback_speed = selected_speed

    with col_jump:
        # Jump directly to any track dropdown
        track_titles = [f"{i+1}. {t['title']}" for i, t in enumerate(st.session_state.playlist)]
        chosen_track_str = st.selectbox(
            "Jump to Track", 
            options=track_titles, 
            index=st.session_state.current_index
        )
        chosen_index = track_titles.index(chosen_track_str)
        if chosen_index != st.session_state.current_index:
            st.session_state.current_index = chosen_index
            st.rerun()

    # --- ADVANCED IFRAME PLAYER COMPONENT ---
    # We use Javascript YouTube Iframe Player API to support custom runtime playback speeds natively
    player_html = f"""
    <div id="player" style="width:100%; max-width:640px; margin:0 auto; aspect-ratio:16/9;"></div>
    <script>
      var tag = document.createElement('script');
      tag.src = "https://youtube.com";
      var firstScriptTag = document.getElementsByTagName('script')[0];
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
            'onReady': onPlayerReady
          }}
        }});
      }}

      function onPlayerReady(event) {{
        // Dynamically inject the custom speed selected from Streamlit
        event.target.setPlaybackRate({st.session_state.playback_speed});
      }}
    </script>
    """
    
    # Render player component (keeps static structural position on page)
    st.components.v1.html(player_html, height=400)

    # --- Playlist Navigation Controls ---
    st.markdown("### 🎛️ Navigation Controls")
    btn_prev, btn_next = st.columns(2)
    
    with btn_prev:
        if st.button("⏮️ Previous Track", use_container_width=True):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
            else:
                st.session_state.current_index = len(st.session_state.playlist) - 1  # Loop to end
            st.rerun()
            
    with btn_next:
        if st.button("⏭️ Next Track", use_container_width=True):
            if st.session_state.current_index < len(st.session_state.playlist) - 1:
                st.session_state.current_index += 1
            else:
                st.session_state.current_index = 0  # Loop to beginning
            st.rerun()

    # --- Sidebar Playlist Overview Queue ---
    with st.sidebar:
        st.header("📋 Next Up Queue")
        for idx, track in enumerate(st.session_state.playlist):
            if idx == st.session_state.current_index:
                st.markdown(f"**👉 {idx+1}. {track['title']}** *(Playing)*")
            else:
                if st.button(f"{idx+1}. {track['title']}", key=f"side_{track['id']}_{idx}"):
                    st.session_state.current_index = idx
                    st.rerun()
else:
    st.info("Search a topic above to generate a playable playlist queue.")
