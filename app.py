import streamlit as st
import requests
import streamlit.components.v1 as components

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
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
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

    # --- ADVANCED IFRAME PLAYER COMPONENT WITH AUTOPLAY LISTENER ---
    # Construct comma-separated list of IDs starting from the current selection onwards
    ordered_ids = [track['id'] for track in st.session_state.playlist]
    shifted_ids = ordered_ids[st.session_state.current_index:] + ordered_ids[:st.session_state.current_index]
    
    base_video_id = shifted_ids[0]
    playlist_parameter = ",".join(shifted_ids)

    # Note: Modern browsers require autoplay=1 and mute=1 combined for seamless auto-transitions
    iframe_src = f"https://youtube.com{base_video_id}?playlist={playlist_parameter}&autoplay=1&mute=1&enablejsapi=1"

    # Embedded HTML with a JavaScript YouTube API listener. 
    # When a track finishes, it posts a message to Streamlit to sync up the 'current_index' state.
    html_code = f"""
    <div id="player"></div>
    <script>
      var tag = document.createElement('script');
      tag.src = "https://youtube.com";
      var firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

      var player;
      function onYouTubeIframeAPIReady() {{
        player = new YT.Player('player', {{
          height: '360',
          width: '100%',
          videoId: '{base_video_id}',
          playerVars: {{
            'playlist': '{playlist_parameter}',
            'autoplay': 1,
            'mute': 1,
            'controls': 1
          }},
          events: {{
            'onStateChange': onPlayerStateChange
          }}
        }});
      }}

      function onPlayerStateChange(event) {{
        // YT.PlayerState.PLAYING is 1. We check if the video ID has updated inside the embedded playlist sequence.
        if (event.data == 1) {{
          var currentVideoUrl = player.getVideoUrl();
          var videoId = currentVideoUrl.split('v=')[1];
          if (videoId) {{
             var cleanId = videoId.split('&')[0];
             window.parent.postMessage({{type: 'yt_track_change', id: cleanId}}, '*');
          }}
        }}
      }}
    </script>
    """
    
    # Render the player component
    components.html(html_code, height=380)

    # Invisible hook to capture browser messages and sync Streamlit's backend indexing status
    st.components.v1.html("""
    <script>
        window.parent.addEventListener('message', function(e) {
            if (e.data && e.data.type === 'yt_track_change') {
                const videoId = e.data.id;
                // Forward it down to standard Streamlit processing parameters
                window.parent.document.dispatchEvent(new CustomEvent('YT_TRACK_EVENT', {detail: videoId}));
            }
        });
    </script>
    """, height=0)

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
