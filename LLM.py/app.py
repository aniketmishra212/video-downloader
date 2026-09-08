import os
import streamlit as st
import yt_dlp
from groq import Groq
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Page Setup
st.set_page_config(
    page_title="AI Video Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Global Video Downloader")
st.caption("Direct stream link generator to bypass YouTube 403 Forbidden blocks")

# Groq API Key Setup
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Video URL input
url = st.text_input("Enter Video URL:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    verify_with_ai = st.checkbox("Verify link with Groq AI Agent", value=False)
with col2:
    selected_country = st.selectbox(
        "Target Region:",
        ["US", "GB", "DE", "JP", "FR", "IN"],
        index=0
    )

# AI Verification Agent
if verify_with_ai and url:
    if not groq_api_key:
        st.warning("⚠️ Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets or .env.")
    else:
        try:
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a media validation agent. Check if the URL is valid. Respond in one concise English sentence."
                    },
                    {
                        "role": "user",
                        "content": f"Validate URL: {url}"
                    }
                ],
                max_tokens=60
            )
            st.info(f"🤖 **AI Agent:** {completion.choices[0].message.content.strip()}")
        except Exception as e:
            st.error(f"AI Verification Error: {str(e)}")

# Process Stream Links
if st.button("Generate Download Links", type="primary"):
    url_clean = url.strip()

    if not url_clean or not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("Please enter a valid video link starting with http:// or https://")
    else:
        with st.spinner("Extracting direct video streams, please wait..."):
            try:
                # Direct extraction settings (No server downloading = No 403 error)
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'geo_bypass': True,
                    'geo_bypass_country': selected_country,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios', 'android', 'web']
                        }
                    }
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_clean, download=False)
                    title = info.get('title', 'Video')
                    thumbnail = info.get('thumbnail')
                    duration = info.get('duration_string', 'N/A')
                    formats = info.get('formats', [])

                    st.success(f"✅ Extracted: **{title}**")
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if thumbnail:
                            st.image(thumbnail, use_container_width=True)
                    with c2:
                        st.write(f"⏱️ **Duration:** {duration}")
                        st.write(f"👁️ **Views:** {info.get('view_count', 'N/A'):,}")

                    st.divider()
                    st.subheader("📥 Available Download Streams:")
                    st.info("💡 Right-click the link and select **'Save link as...'** (or click to stream directly in browser).")

                    # Combined Video + Audio streams (MP4)
                    combined_streams = [
                        f for f in formats 
                        if f.get('ext') == 'mp4' 
                        and f.get('vcodec') != 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    # Audio streams
                    audio_streams = [
                        f for f in formats 
                        if f.get('vcodec') == 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    if combined_streams:
                        st.markdown("#### 🎥 Video with Audio (Direct MP4)")
                        for f in reversed(combined_streams):
                            res = f.get('resolution') or f"{f.get('height', 'Unknown')}p"
                            filesize = f.get('filesize')
                            size_str = f" (~{round(filesize / (1024 * 1024), 1)} MB)" if filesize else ""
                            stream_url = f.get('url')
                            st.markdown(f"- **{res}**{size_str} ➔ [Download / Open Video]({stream_url})")

                    if audio_streams:
                        st.markdown("#### 🎵 Audio Only")
                        best_audio = audio_streams[-1]
                        abr = best_audio.get('abr', '128')
                        st.markdown(f"- **Audio ({abr} kbps)** ➔ [Download / Open Audio]({best_audio.get('url')})")

            except Exception as e:
                st.error(f"Extraction Error: {str(e)}")
