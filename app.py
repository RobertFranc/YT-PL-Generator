import json
import os
import streamlit as st
import requests

# =====================================================================
# ⚙️ STEP 1: PERSISTENT HISTORY STORAGE UTILITIES
# =====================================================================
API_KEY        = st.secrets['API_KEY']
HISTORY_FILE   = "last_played_track.txt"

def load_saved_index():
    """Reads the local history file to recall where you left off."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return int(f.read().strip())
        except ValueError:
            return 0
    return 0

def save_current_index(index):
    """Saves the active cursor position back to disk storage immediately."""
    with open(HISTORY_FILE, "w") as f:
        f.write(str(index))

def clear_saved_index():
    """Deletes the tracking history file to start completely fresh."""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

# =====================================================================
# 🔍 STEP 2: SEARCH QUERY WITH ACTIVE LIVE-STREAM FILTERING
# =====================================================================
@st.cache_data(show_spinner="Searching YouTube & removing live streams...")
def fetch_filtered_youtube_urls(topic, max_results, order_by):
    """Hits search index, checks video details, filters out live content."""
    # Ensure empty inputs do not execute broken API streams
    if not topic.strip():
        return []
        
    #search_url = "https://googleapis.com"
    search_url = "https://www.googleapis.com/youtube/v3/search"
    video_details_url = "https://googleapis.com"
    
    search_params = {
        "part": "snippet",
        "q": topic,
        "maxResults": max_results,
        "type": "video",
        "order": order_by,
        "key": API_KEY
    }
    
    try:
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        items = search_data.get("items", [])
        if not items:
            return []
            
        video_ids = [item["id"]["videoId"] for item in items if "videoId" in item["id"]]
        
        details_params = {
            "part": "snippet,liveStreamingDetails",
            "id": ",".join(video_ids),
            "key": API_KEY
        }
        
        details_response = requests.get(video_details_url, params=details_params)
        details_response.raise_for_status()
        details_data = details_response.json()
        
        playlist = []
        for video_item in details_data.get("items", []):
            # Skip live streams or upcoming premieres completely
            if "liveStreamingDetails" in video_item:
                continue 
                
            playlist.append({
                "title": video_item["snippet"]["title"],
                "url": f"https://youtube.com{video_id}"
            })
            
        return playlist
        
    except Exception as e:
        st.error(f"API Connection Failure: {e}")
        return []

# =====================================================================
# 🎛️ STEP 3: PLAYBACK LAYOUT CONTROLLER ENGINE
# =====================================================================
st.set_page_config(page_title="Smart Playlist Deck", page_icon="🎬", layout="wide")
st.title("🎬 Smart Media Deck (Interactive Engine)")

# Define Sidebar Controls
st.sidebar.header("🔍 Global Search Config")
search_topic = st.sidebar.text_input("Search Keyword / Topic", value="Chillhop Lofi Beats")
video_count  = st.sidebar.slider("Videos to Query", min_value=5, max_value=50, value=15)
search_order = st.sidebar.selectbox("Sort Order", ["relevance", "date", "viewCount", "rating"])

# Pull filtered data arrays using dynamic UI parameters
video_playlist = fetch_filtered_youtube_urls(search_topic, video_count, search_order)

if not video_playlist:
    st.warning("⚠️ Setup check: Enter a search topic and verify your API Key.")
else:
    # Synchronize index memory
    if "current_index" not in st.session_state:
        saved_pos = load_saved_index()
        st.session_state.current_index = saved_pos if saved_pos < len(video_playlist) else 0

    total_videos = len(video_playlist)
    current_video = video_playlist[st.session_state.current_index]

    col_player, col_sidebar = st.columns([2.5, 1])

    with col_player:
        st.subheader(f" Now Streaming [{st.session_state.current_index + 1}/{total_videos}]: {current_video['title']}")
        st.video(current_video["url"])
        
        st.write("")
        nav_prev, _, nav_next = st.columns()
        
        with nav_prev:
            if st.button("⏮️ Previous Video", use_container_width=True):
                if st.session_state.current_index > 0:
                    st.session_state.current_index -= 1
                    save_current_index(st.session_state.current_index)
                    st.rerun()
                    
        with nav_next:
            if st.button("Next Video ⏭️", use_container_width=True):
                if st.session_state.current_index < total_videos - 1:
                    st.session_state.current_index += 1
                    save_current_index(st.session_state.current_index)
                    st.rerun()

    with col_sidebar:
        st.header("📋 Track Manager")
        
        # Interactive Jump Dropdown List Selector
        titles_list = [f"{i+1}. {vid['title']}" for i, vid in enumerate(video_playlist)]
        selected_track = st.selectbox(
            "🎯 Jump directly to track:", 
            options=titles_list, 
            index=st.session_state.current_index
        )
        
        target_index = titles_list.index(selected_track)
        if target_index != st.session_state.current_index:
            st.session_state.current_index = target_index
            save_current_index(target_index)
            st.rerun()

        # History Clear Engine
        if st.button("🔄 Reset Position History to First Track", use_container_width=True):
            clear_saved_index()
            st.session_state.current_index = 0
            st.success("History log wiped out! Resetting position tracker.")
            st.rerun()

        # Data Manifest Bundle Exporter Utilities
        st.write("---")
        st.subheader("💾 Export Current Queue")
        
        json_string = json.dumps(video_playlist, indent=4)
        txt_string = "\n".join([f"Title: {v['title']}\nURL: {v['url']}\n" for v in video_playlist])

        dl_json, dl_txt = st.columns(2)
        with dl_json:
            st.download_button("📥 Download JSON", data=json_string, file_name="youtube_playlist.json", mime="application/json", use_container_width=True)
        with dl_txt:
            st.download_button("📥 Download TXT", data=txt_string, file_name="youtube_playlist.txt", mime="text/plain", use_container_width=True)

        # Active Queue Tracker Dashboard Monitor
        st.write("---")
        st.info(f"💾 Autosave tracking active to `{HISTORY_FILE}`.")
        
        st.subheader("Up Next Queue")
        for idx, vid in enumerate(video_playlist):
            if idx == st.session_state.current_index:
                st.markdown(f"**🔊 Now Playing: {vid['title']}**")
            else:
                st.caption(f"{idx + 1}. {vid['title']}")
