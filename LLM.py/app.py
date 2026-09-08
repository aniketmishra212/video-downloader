import os
import tempfile
import streamlit as st
import yt_dlp
import imageio_ffmpeg
from groq import Groq
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Setup portable FFmpeg binary paths
FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(FFMPEG_BINARY)
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Page Configuration
st.set_page_config(
    page_title="AI Video Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Global Video Downloader")
st.caption("Download global and regional videos with automated stream merge and AI link verification")

# Fetch API Key from Streamlit secrets or local .env
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Video URL input
url = st.text_input("Enter Video URL:", placeholder="https://www.youtube.com/watch?v=...")

# Configuration Controls
col1, col2 = st.columns(2)
with col1:
    quality = st.selectbox(
        "Select Quality:",
        [
            "Best Available (Full HD / 4K Merged MP4)",
            "720p (Balanced MP4)",
            "Audio Only (MP3)"
        ]
    )

with col2:
    verify_with_ai = st.checkbox("Verify link with Groq AI Agent", value=False)

# Country Selector for Geo-Restricted/International Content
selected_country = st.selectbox(
    "Target Country (for region-restricted / international content):",
    ["US", "GB", "DE", "JP", "FR", "CA", "AU", "IN"],
    index=0,
    help="Select the originating country if the video is blocked outside a specific region."
)

# AI Verification Agent
if verify_with_ai and url:
    if not groq_api_key:
        st.warning("⚠️ Groq API key is missing. Add GROQ_API_KEY in Streamlit Secrets or .env file.")
    else:
        try:
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional URL and media validation agent. "
                            "Verify if the user link belongs to a valid streaming or video platform. "
                            "Answer in a single clear sentence strictly in English."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Validate this media URL: {url}"
                    }
                ],
                max_tokens=60
            )
            st.info(f"🤖 **AI Agent:** {completion.choices[0].message.content.strip()}")
        except Exception as e:
            st.error(f"AI Verification Error: {str(e)}")

# Download Execution Logic
if st.button("Process & Download Video", type="primary"):
    url_clean = url.strip()

    if not url_clean:
        st.error("Please enter a valid video link.")
    elif not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("Invalid URL format. The URL must begin with 'https://' or 'http://'.")
    elif "\n" in url_clean or "import " in url_clean or " " in url_clean:
        st.error("Malformed URL detected. Please ensure only the video URL is entered.")
    else:
        with st.spinner("Bypassing regional restrictions and merging streams, please wait..."):
            try:
                temp_dir = tempfile.mkdtemp()
                output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

                # Format routing with fallbacks
                if quality == "Audio Only (MP3)":
                    ydl_format = "bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                elif quality == "720p (Balanced MP4)":
                    ydl_format = "best[height<=720]/bestvideo[height<=720]+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                else:
                    ydl_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]

                # yt-dlp Configuration with Geo-Bypass and 403 Forbidden Anti-Block
                ydl_opts = {
                    'format': ydl_format,
                    'outtmpl': output_template,
                    'ffmpeg_location': FFMPEG_BINARY,
                    'postprocessors': postprocessors,
                    'merge_output_format': 'mp4',
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    
                    # International Geo-Bypass parameters
                    'geo_bypass': True,
                    'geo_bypass_country': selected_country,
                    
                    # Mobile Client Emulation (iOS/Android) to avoid server 403 bans
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios', 'android', 'web_safari'],
                            'skip': ['hls', 'dash']
                        }
                    },
                    'http_headers': {
                        'User-Agent': (
                            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) '
                            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'
                        ),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Sec-Fetch-Mode': 'navigate',
                    }
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url_clean, download=True)
                    video_title = info_dict.get('title', 'downloaded_video')

                    # Locate downloaded file
                    downloaded_files = [
                        f for f in os.listdir(temp_dir)
                        if not f.endswith('.part') and not f.endswith('.ytdl')
                    ]

                    if not downloaded_files:
                        st.error("File processing could not be completed.")
                    else:
                        file_path = os.path.join(temp_dir, downloaded_files[0])
                        file_name = os.path.basename(file_path)

                        st.success(f"✅ Successfully processed: **{video_title}**")

                        # Video player preview (only for video formats)
                        if quality != "Audio Only (MP3)":
                            st.video(file_path)

                        # Download button
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label="💾 Download File to Device",
                                data=f,
                                file_name=file_name,
                                mime="application/octet-stream"
                            )

            except Exception as e:
                st.error(f"Download Error: {str(e)}")
