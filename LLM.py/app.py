import os
import tempfile
import streamlit as st
import yt_dlp
import imageio_ffmpeg
from groq import Groq
from dotenv import load_dotenv

# Local .env load karein
load_dotenv()

# Streamlit Cloud aur local system dono ke liye FFmpeg binary path setup
FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(FFMPEG_BINARY)
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Page Configuration
st.set_page_config(
    page_title="AI Video Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Downloader")
st.caption("YouTube aur web videos download karein without 403 errors")

# Groq API Key access (Secrets ko pehle check karega, fir .env)
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Input URL
url = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# Download Options
col1, col2 = st.columns(2)
with col1:
    quality = st.selectbox(
        "Quality chunein:",
        [
            "Best Available (Merged MP4)",
            "720p / Balanced",
            "Audio Only (MP3)"
        ]
    )

with col2:
    verify_with_ai = st.checkbox("Verify link with Groq AI", value=False)

# AI Verification
if verify_with_ai and url:
    if not groq_api_key:
        st.warning("⚠️ Groq API Key nahi mili. Streamlit Secrets ya .env mein set karein.")
    else:
        try:
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Aap ek URL verifier agent hain. Check karein ki user ka URL ek valid video stream link hai ya nahi. Short single sentence mein answer dein."
                    },
                    {
                        "role": "user",
                        "content": f"Check this URL: {url}"
                    }
                ],
                max_tokens=60
            )
            st.info(f"🤖 **AI Agent:** {completion.choices[0].message.content.strip()}")
        except Exception as e:
            st.error(f"AI Verification error: {str(e)}")

# Download Button Logic
if st.button("Download Process Karein", type="primary"):
    url_clean = url.strip()
    
    # Input Validation
    if not url_clean:
        st.error("Kripya pehle valid URL dalein.")
    elif not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("❌ Yeh valid URL nahi hai! Kripya 'https://' se shuru hone wala link dalein.")
    elif "\n" in url_clean or "import " in url_clean or " " in url_clean:
        st.error("❌ Invalid link format detected.")
    else:
        with st.spinner("Video stream fetch aur process ho rahi hai, kripya intezar karein..."):
            try:
                temp_dir = tempfile.mkdtemp()
                output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

                # Format selection with fail-safe fallbacks
                if quality == "Audio Only (MP3)":
                    ydl_format = "bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                elif quality == "720p / Balanced":
                    ydl_format = "best[height<=720]/bestvideo[height<=720]+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                else:
                    ydl_format = "bestvideo+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]

                # YouTube 403 Forbidden Anti-Block Configuration
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
                    # YouTube 403 bypass: Android & iOS client emulate karein
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'ios', 'web'],
                            'skip': ['hls', 'dash']
                        }
                    },
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-us,en;q=0.5',
                        'Sec-Fetch-Mode': 'navigate',
                    }
                }

                # Download execution
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url_clean, download=True)
                    video_title = info_dict.get('title', 'downloaded_video')

                    # Locate downloaded file
                    downloaded_files = [
                        f for f in os.listdir(temp_dir) 
                        if not f.endswith('.part') and not f.endswith('.ytdl')
                    ]
                    
                    if not downloaded_files:
                        st.error("File processing complete nahi ho saki.")
                    else:
                        file_path = os.path.join(temp_dir, downloaded_files[0])
                        file_name = os.path.basename(file_path)

                        st.success(f"✅ Success! **{video_title}** taiyar hai.")

                        # Preview if video
                        if quality != "Audio Only (MP3)":
                            st.video(file_path)

                        # File Download Button
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label="💾 Apne device par save karein",
                                data=f,
                                file_name=file_name,
                                mime="application/octet-stream"
                            )

            except Exception as e:
                st.error(f"Download Error: {str(e)}")
