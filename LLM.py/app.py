import os
import glob
import re
import streamlit as st
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# Page Setup
st.set_page_config(
    page_title="OmniStream | Professional Media Downloader",
    page_icon="⚡",
    layout="centered"
)

# Professional SaaS Dark Theme Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #0b0f17;
        color: #f1f5f9;
    }

    /* Clean Card Container */
    .pro-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    /* Professional Headings */
    h1 {
        font-weight: 700 !important;
        font-size: 28px !important;
        color: #ffffff !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 4px !important;
    }

    .sub-heading {
        color: #94a3b8;
        font-size: 14px;
        font-weight: 400;
        margin-bottom: 24px;
    }

    /* Input Fields */
    .stTextInput>div>div>input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
        transition: border-color 0.2s;
    }
    .stTextInput>div>div>input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }

    /* Selectbox Dropdown */
    .stSelectbox>div>div {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-size: 14px !important;
    }

    /* Primary Processing Button */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        width: 100% !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.45) !important;
        transform: translateY(-1px);
    }

    /* Download Deliverable Button */
    .stDownloadButton>button {
        background: #059669 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border: none !important;
        border-radius: 8px !important;
        width: 100% !important;
        padding: 10px 20px !important;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.3) !important;
    }
    .stDownloadButton>button:hover {
        background: #047857 !important;
        transform: translateY(-1px);
    }

    label {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #cbd5e1 !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.title("⚡ OmniStream Downloader")
st.markdown("<div class='sub-heading'>High-performance media extraction engine for YouTube & Instagram.</div>", unsafe_allow_html=True)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def run_downloader(url: str, quality_choice: str):
    url_lower = url.lower()
    is_instagram = "instagram.com" in url_lower
    is_youtube = "youtube.com" in url_lower or "youtu.be" in url_lower

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_chunk_size': 10485760,  # 10MB chunking prevents mid-stream 403 throttling
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    if is_instagram:
        ydl_opts['format'] = 'best'
    elif is_youtube:
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['mweb', 'ios'],
                'skip': ['dash', 'hls']
            }
        }

        if quality_choice == "Best Available (Up to 4K / 1080p)":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
        elif quality_choice == "High Definition (720p)":
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        elif quality_choice == "Standard Definition (480p)":
            ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
        elif quality_choice == "Audio Only (MP3)":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id')
        title = info.get('title', 'media_file')
        clean_title = sanitize_filename(title)

        expected_ext = "mp3" if quality_choice == "Audio Only (MP3)" and is_youtube else "mp4"

        # Check matched file
        specific_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{expected_ext}")
        if os.path.exists(specific_path):
            return specific_path, clean_title, expected_ext

        matches = glob.glob(f"{DOWNLOAD_DIR}/{video_id}.*")
        valid_files = [f for f in matches if not f.endswith(('.part', '.ytdl'))]
        if valid_files:
            target = valid_files[0]
            ext = target.rsplit('.', 1)[-1].lower()
            return target, clean_title, ext

        all_files = glob.glob(f"{DOWNLOAD_DIR}/*")
        valid_all = [f for f in all_files if not f.endswith(('.part', '.ytdl', '.txt'))]
        if valid_all:
            latest = max(valid_all, key=os.path.getctime)
            ext = latest.rsplit('.', 1)[-1].lower()
            return latest, clean_title, ext

        raise FileNotFoundError("Processed output could not be located on disk.")

# Input Panel
st.markdown("<div class='pro-card'>", unsafe_allow_html=True)
url_input = st.text_input(
    "Media Source URL", 
    placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/..."
)

quality_option = st.selectbox(
    "Export Preset",
    [
        "Best Available (Up to 4K / 1080p)",
        "High Definition (720p)",
        "Standard Definition (480p)",
        "Audio Only (MP3)"
    ]
)

process_btn = st.button("Extract & Process Stream")
st.markdown("</div>", unsafe_allow_html=True)

if process_btn:
    if not url_input.strip():
        st.warning("Please provide a valid media link to proceed.")
    else:
        with st.spinner("Processing media streams and preparing payload..."):
            try:
                file_path, title, ext = run_downloader(url_input.strip(), quality_option)

                if os.path.exists(file_path):
                    st.success(f"Stream Ready: **{title}**")

                    if ext == "mp3":
                        st.audio(file_path)
                        mime_type = "audio/mp3"
                    else:
                        st.video(file_path)
                        mime_type = f"video/{ext}"

                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"Download {ext.upper()} File",
                            data=f.read(),
                            file_name=f"{title[:45]}.{ext}",
                            mime=mime_type
                        )
                else:
                    st.error("Output generation failed: File missing from storage.")

            except Exception as e:
                err = str(e)
                if "login" in err.lower():
                    st.error("Access Restricted: Instagram authentication required for private media.")
                elif "403" in err or "sign in to confirm" in err.lower():
                    st.error("Rate Limit Detected: Server received HTTP 403. Please retry after a brief delay.")
                else:
                    st.error(f"Execution Error: {err}")
