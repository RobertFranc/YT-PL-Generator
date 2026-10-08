import streamlit as st
import requests
import streamlit.components.v1 as components
import json

# 1. Fetch API Key securely
try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Missing API_KEY secret! Please add it to your Streamlit Cloud Advanced Settings.")
    st.stop()

def fetch_youtube_videos(query, api_key, max_results=5):
    """Fetches high-definition videos from YouTube API based on the query."""
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

        playlist = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            video_url = f"https://youtube.com{video_id}"
            
            playlist.append({
                'id': video_id,
                'title': title,
                'channel': channel,
                'video_url': video_url
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
    
    # Track selection jump box
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

    # --- THE AUTOPLAY IFRAME FIX ---
    # Prepare track IDs for the inline JavaScript player
    all_ids = [track['id'] for track in st.session_state.playlist]
    current_video_id = current_track['id']
    
    # Custom HTML element utilizing Streamlit Component API 
    # to communicate song termination back to Python state
    html_player_code = f"""
    <div id="yt-player-frame" style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden;">
        <div id="player" style="position:absolute; top:0; left:0; width:100%; height:100%;"></div>
    </div>

    <script>
      // Load YouTube IFrame API asynchronously
      var tag = document.createElement('script');
      tag.src = "https://youtube.com";
      var firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

      var player;
      function onYouTubeIframeAPIReady() {{
        player = new YT.Player('player', {{
          height: '100%',
          width: '100%',
          videoId: '{current_video_id}',
          playerVars: {{
            'autoplay': 1,
            'mute': 1,        // Browsers block autoplay unless muted initially
            'controls': 1,
            'rel': 0
          }},
          events: {{
            'onStateChange': onPlayerStateChange
          }}
        }});
      }}

      // Listen for playback state changes from YouTube
      function onPlayerStateChange(event) {{
        // YT.PlayerState.ENDED equals 0
        if (event.data === 0) {{
           // Send event backward into the Streamlit app container
           window.parent.postMessage({{
               isStreamlitMessage: true,
               type: "streamlit:setComponentValue",
               value: "track_finished_" + Date.now()
           }}, "*");
        }}
      }}
    </script>
    """
    
    # Render the custom player and capture its return message context 
    # Height 400px maintains standard 16:9 widescreen video scaling inside the app page
    player_event = components.html(html_player_code, height=400)

    # Detect when the Javascript component shoots an ending pulse event
    if player_event:
        if 'last_player_event' not in st.session_state:
            st.session_state.last_player_event = player_event
            
        if player_event != st.session_state.last_player_event:
            st.session_state.last_player_event = player_event
            # Advance index safely
            if st.session_state.current_index < len(st.session_state.playlist) - 1:
                st.session_state.current_index += 1
            else:
                st.session_state.current_index = 0  # Wrap around to start
            st.rerun()

    # --- Playlist Navigation Controls ---
    st.markdown("### 🎛️ Navigation Controls")
    btn_prev, btn_next = st.columns(2)
    
    with btn_prev:
        if st.button("⏮️ Previous Track", use_container_width=True):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
            else:
                st.session_state.current_index = len(st.session_state.playlist) - 1
            st.rerun()
            
    with btn_next:
        if st.button("⏭️ Next Track", use_container_width=True):
            if st.session_state.current_index < len(st.session_state.playlist) - 1:
                st.session_state.current_index += 1
            else:
                st.session_state.current_index = 0
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
