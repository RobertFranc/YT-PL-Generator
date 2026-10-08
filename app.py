import json
import os
import streamlit as st
import requests

# =====================================================================
# ⚙️ STEP 1: PARAMETERS & PERSISTENT HISTORY STORAGE
# =====================================================================
API_KEY        = st.secrets["API_KEY"]
SEARCH_TOPIC   = "Country song"
VIDEO_COUNT    = 15
SEARCH_ORDER   = "relevance" # 'viewCount', 
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

# =====================================================================
# 🔍 STEP 2: SEARCH QUERY WITH ACTIVE LIVE-STREAM FILTERING
# =====================================================================


@st.cache_data(show_spinner="Searching YouTube & removing live streams...")
def fetch_filtered_youtube_urls():
    """Hits search index, checks video details, filters out live content."""
    search_url = "https://www.googleapis.com/youtube/v3/search"
    video_details_url = "https://googleapis.com"
    # FIXED: Added the full /youtube/v3/search path to the base domain
    
    # A. Execute keyword search lookup
    query = "Python programming tutorial"
    search_params = {
        "part": "snippet",
        "q": SEARCH_TOPIC, # query
        "maxResults": VIDEO_COUNT,
        "type": "video",
        "order": SEARCH_ORDER,
        "key": API_KEY
        'videoDefinition': 'high',
    }
    try:
        search_response = requests.get(search_url, params=search_params)
        
        print(f"\n--- Top Results for '{SEARCH_TOPIC}' ---")

        search_response.raise_for_status()
        search_data = search_response.json()
        
        for item in search_data.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            
            print(f"🎬 Title: {title}")
            print(f"   Channel: {channel}")
            print(f"   Link: https://www.youtube.com/watch?v={video_id}\n")


        
        items = search_data.get("items", [])
        if not items:
            return []
            
        # Collect extracted target video IDs for batch parsing validation
        video_ids = [item["id"]["videoId"] for item in items if "videoId" in item["id"]]
        
        # B. Bulk check structural attributes targeting /videos payload endpoint
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
            # STABILITY CHECK: If liveStreamingDetails block exists, it's a live stream or premiere
            if "liveStreamingDetails" in video_item:
                continue  # Skip item entirely
                
            title = video_item["snippet"]["title"]
            video_id = video_item["id"]
            
            playlist.append({
                "title": title,
                "url": f"https://youtube.com{video_id}"
            })
            
        return playlist

    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        st.error(f"Response Details: {response.text}")
        return []
    except Exception as err:
        st.error(f"An error occurred: {err}")
        return []
    except Exception as e:
        st.error(f"API Connection Failure: {e}")
        return []

# =====================================================================
# 🎛️ STEP 3: PLAYBACK LAYOUT CONTROLLER ENGINE
# =====================================================================
st.set_page_config(page_title="Smart Playlist Deck", page_icon="🎬", layout="wide")
st.title("🎬 Smart Media Deck (Filtered & Autosaved)")

video_playlist = fetch_filtered_youtube_urls()

if not video_playlist:
    st.warning("⚠️ Setup check: Please verify your API Key or adjust search parameters.")
else:
    # Set the cursor pointer state to the remembered file position history entry
    if "current_index" not in st.session_state:
        saved_pos = load_saved_index()
        # Bound check position indicator to prevent faults if the playlist length changes
        st.session_state.current_index = saved_pos if saved_pos < len(video_playlist) else 0

    total_videos = len(video_playlist)
    current_video = video_playlist[st.session_state.current_index]

    col_player, col_sidebar = st.columns([2.5, 1])

    with col_player:
        st.subheader(f" Now Streaming [{st.session_state.current_index + 1}/{total_videos}]: {current_video['title']}")
        st.video(current_video["url"])
        
        st.write("")
        nav_prev, _, nav_next = st.columns([1, 2, 1])
        
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
        st.info(f"💾 Autofreeze: Saved current track index location to `{HISTORY_FILE}`.")
        
        st.subheader("Up Next Queue")
        for idx, vid in enumerate(video_playlist):
            if idx == st.session_state.current_index:
                st.markdown(f"**🔊 Now Playing: {vid['title']}**")
            else:
                st.caption(f"{idx + 1}. {vid['title']}")
