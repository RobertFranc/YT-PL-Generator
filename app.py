import datetime
import streamlit as st
import requests

# Set page configuration
title = "Custom YouTube Playlist Generator"

st.set_page_config(
    page_title=title,
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 " + title + " 🎵")
st.caption("Generate custom playback flows using the free YouTube Data API.")

# 1. API Authentication Side Panel
with st.sidebar:
    # api key
    api_key = st.text_input(
        "Enter YouTube API Key",
        type="password",
        help="Get a free key from Google Cloud Console."
    )

    # Page text layout:
    st.header("🔑 API 🔑🔑 Authentication 🔑")
    st.markdown("---")
    st.header("⚙️ Playlist Controls ⚙️")

    # The clear button:
    if st.button("🗑️ Clear Playlist",
                 use_container_width=True
                ):
        st.session_state.playlist = []
        st.session_state.current_index = 0
        st.rerun()


# 1. API Authentication check and default:
if not api_key:
    api_key = st.secrets.API_KEY
print('🔑apikey:', api_key is not None)
# Initialize Session States
if "playlist" not in st.session_state:
    st.session_state.playlist = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# 2. Search Criteria Form
st.subheader("🔍 Define Your Criteria")
content_type = st.radio(
    "Select Content Type:",
    ["Music", "Video"],
    horizontal=True
)

# Layout main columns
col1, col2, col3 = st.columns(3)

with col1: # content type - Music or Video
    if content_type == "Music":
        genre = st.text_input(
            "Music Genre",
            placeholder="e.g., Synthwave, Lofi, Jazz"
        )
        if not genre:
            genre = 'Rock'
    else: # Video content
        video_type = st.selectbox(
            "Video Type",
            ["Tutorial", "Movie", "Documentary", "General Content"]
        )
        if not video_type:
            video_type = 'Tutorial'
            
        genre = st.text_input(
            "Genre / Topic Keyword",
            placeholder="e.g., Python, Sci-Fi, DIY, Cooking"
        )
        if not genre:
            genre = 'Python'

with col2: # Playlist length (quantity)
    quantity = st.number_input(
        "Playlist Size (Quantity)",
        min_value=1,
        max_value=25,
        value=5
    )

with col3: # Year
    current_year = datetime.datetime.now().year
    year_range = st.slider(
        "Year Period",
        min_value=1950,
        max_value=current_year,
        value=(2015, current_year)
    )

# 3. Fetching Data from YouTube API
if st.button("🚀 Generate Playlist", type="primary", use_container_width=True):
    if not api_key:
        st.error("❌🔑❌ Please enter your YouTube API Key in the sidebar.")
    else:
        with st.spinner("Searching YouTube catalog..."):
            # Format dates to RFC 3339 strings for YouTube API
            published_after = f"{year_range[0]}-01-01T00:00:00Z"
            published_before = f"{year_range[1]}-12-31T23:59:59Z"
            
            # Construct the search query phrase
            if content_type == "Music":
                search_query = f"{genre} music"
                video_category = "10" # Music Category ID
            else:
                search_query = f"{video_type} {genre}"
                video_category = "" # Default

            # FIX 1: Correct URL endpoint for YouTube Video Search
            url = "https://googleapis.com/"
            params = {
                "part": "snippet",
                "q": search_query,
                "maxResults": quantity,
                "type": "video",
                "videoEmbeddable": "true",
                "publishedAfter": published_after,
                "publishedBefore": published_before,
                "key": api_key
            }
            print('🪪 parameters:', params)
            if video_category:
                params["videoCategoryId"] = video_category
            url = f"https://googleapis.com{st.secrets.API_KEY}"

            # response = requests.get(url)
            response = requests.get(url, params=params)
            # response.raise_for_status() 
            
            # 1. Check if Google blocked or rejected the request
            if response.status_code != 200:
                print(f"❌ HTTP Error Code: {response.status_code}")
                print("--- RAW SERVER RESPONSE ---")
                print(response.text[:500])  # Look at the first 500 characters of the error
                print("---------------------------")
            else:
                # 2. Safely check if the response content-type is JSON
                try:
                    data = response.json()
                    print("✅ Success! Video Title:", data['items'][0]['snippet']['title'])
                
                    if response.status_code == 200:
                        st.markdown(f"👏 requests satus ✅ {response.status_code}")
                        st.markdown(f"👏 search_query ✅ {search_query}")
                        st.markdown(f"👏 genre ✅ {genre}")
                        print(type(response), response.status_code, response)
    
    
                        results = response.json().get("items", [])
                        
                        # Parse results into custom playlist schema
                        new_playlist = []
                        for item in results:
                            video_id = item["id"]["videoId"]
                            # Populate playlist:
                            new_playlist.append({
                                "id": video_id,
                                "title": item["snippet"]["title"],
                                # FIX 2: Correctly formatted YouTube Watch URL string
                                "url": f"https://youtube.com/{video_id}",
                                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                                "channel": item["snippet"]["channelTitle"]
                            })
                        
                        if new_playlist:
                            st.session_state.playlist = new_playlist
                            st.session_state.current_index = 0
                            st.success(f"Successfully generated a playlist with {len(new_playlist)} items!")
                            st.rerun()
                        else:
                            st.warning("👻 No videos matched your precise criteria. Try widening the year range or changing keywords.")
                    else:
                        st.error(f"🙅🏻‍♂️ API Error 🙅🏻‍♂️ ({response.status_code}): {response.json().get('error', {}).get('message', 'Unknown Error')}")
                except ValueError as ve:
                    st.error('❌' * 10)
                    st.error(f"❌ Status code was 200, but data wasn't JSON. ❌")
                    st.error(f'ValueError: {ve}')
                    st.error(f"Raw text: {response.text}")
                except Exception as e:
                    st.error(f"🚨 Failed to connect to the API: {e}")

# 4. Playlist & Playback Section
if st.session_state.playlist:
    st.markdown("---")
    main_col, side_col = st.columns([2, 1])
    
    current_track = st.session_state.playlist[st.session_state.current_index]
    
    with main_col:
        st.subheader("📺 Now Playing")
        # Native playback embed window
        st.video(current_track["url"])
        st.markdown(f"### **{current_track['title']}**")
        st.caption(f"Channel: {current_track['channel']}")
        
        # Playback navigation buttons
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col1:
            if st.button("⏮️ Previous", use_container_width=True):
                if st.session_state.current_index > 0:
                    st.session_state.current_index -= 1
                    st.rerun()
        with btn_col2:
            st.markdown(f"<p style='text-align: center;'>Track {st.session_state.current_index + 1} of {len(st.session_state.playlist)}</p>", unsafe_allow_html=True)
        with btn_col3:
            if st.button("⏭️ Next", use_container_width=True):
                if st.session_state.current_index < len(st.session_state.playlist) - 1:
                    st.session_state.current_index += 1
                    st.rerun()

    with side_col:
        st.subheader("📋 Up Next")
        for idx, track in enumerate(st.session_state.playlist):
            # Highlight the currently playing track
            if idx == st.session_state.current_index:
                st.markdown(f"👉 **{track['title']}** (Playing)")
            else:
                if st.button(f"🎵 {track['title'][:40]}...", key=f"track_{idx}", use_container_width=True):
                    st.session_state.current_index = idx
                    st.rerun()
else:
    st.info("🪫 Your playlist is currently empty. Adjust the parameters and hit 'Generate Playlist' above.") 


