import streamlit as st
import requests

def youtube_search_requests(query, api_key, max_results=5):
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
        
        items = data.get('items', [])
        if not items:
            st.warning("No videos found for this search.")
            return

        st.success(f"Found {len(items)} videos!")
        
        # Display each result as a clean web card
        for item in items:
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Web UI Layout
            st.subheader(f"🎬 {title}")
            st.caption(f"**Channel:** {channel}")
            st.video(video_url)  # Embeds the playable video directly in the app!
            st.markdown("---")
            
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        st.code(response.text, language="json")
    except Exception as err:
        st.error(f"An error occurred: {err}")

# Streamlit App UI
st.title("📺 YouTube Video Search App")

# 1. Fetch API Key securely (using proper dictionary syntax)
try:
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Missing API_KEY secret! Please add it in your Streamlit Cloud Advanced Settings.")
    st.stop()

# 2. Add an interactive search box and button
search_query = st.text_input("Enter what you want to search for:", value="Rock music")
results_count = st.slider("Number of results", min_value=1, max_value=10, value=5)

if st.button("Search YouTube"):
    with st.spinner("Searching..."):
        youtube_search_requests(search_query, API_KEY, max_results=results_count)
