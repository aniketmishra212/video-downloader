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
st.caption("YouTube aur web videos download karein with automatic audio/video merge")

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
            "Best Available (1080p / 4K Merged)",
            "720p (Fast Download)",
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
                        "content": "Aap ek URL verifier agent hain. Check karein ki user ka URL ek valid video streamable platform (jaise YouTube, Instagram, etc.) ka link hai ya nahi. Short single sentence mein Hindi/Hinglish mein answer dein."
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
    if not url.strip():
        st.error("Kripya pehle valid URL dalein.")
    else:
        with st.spinner("Video process ho rahi hai, kripya intezar karein..."):
            try:
                # Temporary download directory
                temp_dir = tempfile.mkdtemp()
                output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

                # Format selection logic with multiple fallbacks
                if quality == "Audio Only (MP3)":
                    ydl_format = "bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                elif quality == "720p (Fast Download)":
                    # Progressive 720p pehle dekhega, na mile to adaptive video+audio merge karega
                    ydl_format = "best[height<=720]/bestvideo[height<=720]+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                else:
                    # Best video + best audio with generic fallback
                    ydl_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                    postprocessors = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]

                ydl_opts = {
                    'format': ydl_format,
                    'outtmpl': output_template,
                    'ffmpeg_location': FFMPEG_BINARY,
                    'postprocessors': postprocessors,
                    'merge_output_format': 'mp4',
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                }

                # Download execution
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    video_title = info_dict.get('title', 'downloaded_video')

                    # Downloaded file retrieve karein
                    downloaded_files = [
                        f for f in os.listdir(temp_dir) 
                        if not f.endswith('.part') and not f.endswith('.ytdl')
                    ]
                    
                    if not downloaded_files:
                        st.error("File download nahi ho saki.")
                    else:
                        file_path = os.path.join(temp_dir, downloaded_files[0])
                        file_name = os.path.basename(file_path)

                        st.success(f"✅ Success! **{video_title}** taiyar hai.")

                        # Preview video if not MP3
                        if quality != "Audio Only (MP3)":
                            st.video(file_path)

                        # Download button
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label="💾 Apne device par save karein",
                                data=f,
                                file_name=file_name,
                                mime="application/octet-stream"
                            )

            except Exception as e:
                st.error(f"Download Error: {str(e)}")
