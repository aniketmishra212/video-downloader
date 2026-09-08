import os
import tempfile
import streamlit as st
import yt_dlp
import imageio_ffmpeg
from groq import Groq
from dotenv import load_dotenv

# Local development ke liye .env load karein
load_dotenv()

# Streamlit Cloud aur local dono ke liye FFmpeg path configure karein
FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(FFMPEG_BINARY)
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Page Setup
st.set_page_config(
    page_title="AI Video Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Downloader")
st.caption("YouTube aur web videos download karein with automatic audio/video merge")

# Groq API Key access (Streamlit secrets priority, fallback to os.getenv)
groq_api_key = None
if "GROQ_API_KEY" in st.secrets:
    groq_api_key = st.secrets["GROQ_API_KEY"]
else:
    groq_api_key = os.getenv("GROQ_API_KEY")

# URL Input
url = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# Download Options
col1, col2 = st.columns(2)
with col1:
    quality = st.selectbox(
        "Quality chunein:",
        ["Best Video + Best Audio (1080p+)", "720p (Single Stream)", "Audio Only (MP3)"]
    )

with col2:
    verify_with_ai = st.checkbox("Verify link with Groq AI", value=False)

# AI verification check
if verify_with_ai and url:
    if not groq_api_key:
        st.warning("⚠️ Groq API Key configure nahi hai (Streamlit Secrets ya .env mein add karein).")
    else:
        try:
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Aap ek URL verifier agent hain. User ke URL ko verify karke batayein ki kya yeh valid video link format hai ya nahi. Short 1 sentence answer dein."
                    },
                    {
                        "role": "user",
                        "content": f"Verify this URL: {url}"
                    }
                ],
                max_tokens=60
            )
            st.info(f"🤖 **AI Agent:** {completion.choices[0].message.content.strip()}")
        except Exception as e:
            st.error(f"AI Verification error: {str(e)}")

# Download Button Logic
if st.button("Download Process Karein", type="primary"):
    if not url.strip():
        st.error("Kripya pehle valid URL dalein.")
    else:
        with st.spinner("Video process ho rahi hai, kripya intezar karein..."):
            try:
                # Temporary download directory create karein
                temp_dir = tempfile.mkdtemp()
                output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

                # Format selection logic
                if quality == "Audio Only (MP3)":
                    ydl_format = "bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                elif quality == "720p (Single Stream)":
                    ydl_format = "best[height<=720]"
                    postprocessors = []
                else:
                    ydl_format = "bestvideo+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]

                ydl_opts = {
                    'format': ydl_format,
                    'outtmpl': output_template,
                    'ffmpeg_location': FFMPEG_BINARY,
                    'postprocessors': postprocessors,
                    'quiet': True,
                    'no_warnings': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    video_title = info_dict.get('title', 'downloaded_video')
                    
                    # Downloaded file locate karein
                    downloaded_files = os.listdir(temp_dir)
                    if not downloaded_files:
                        st.error("File download nahi ho saki.")
                    else:
                        file_path = os.path.join(temp_dir, downloaded_files[0])
                        file_name = os.path.basename(file_path)

                        st.success(f"✅ Success! **{video_title}** taiyar hai.")

                        # Video preview (agar audio nahi hai to)
                        if not quality == "Audio Only (MP3)":
                            st.video(file_path)

                        # File download button Streamlit par
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label="💾 Apne device par save karein",
                                data=f,
                                file_name=file_name,
                                mime="application/octet-stream"
                            )

            except Exception as e:
                st.error(f"Download Error: {str(e)}")
