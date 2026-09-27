import os
import glob
import re
import streamlit as st
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="Wall Maria Media Extractor | Scout Regiment",
    page_icon="⚔️",
    layout="centered"
)

# Custom Attack on Titan Aesthetic CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;900&family=Crimson+Text:ital,wght@0,400;0,700;1,400&display=swap');

    /* Global Dark Medieval / Survey Corps Atmosphere */
    .stApp {
        background: radial-gradient(circle at 50% 20%, #1e261f 0%, #0d120e 70%, #050806 100%);
        color: #e5dac1;
        font-family: 'Crimson Text', serif;
    }

    /* Survey Corps Crest Banner & Titles */
    h1 {
        font-family: 'Cinzel', serif !important;
        font-weight: 900 !important;
        color: #c9a050 !important;
        text-shadow: 2px 2px 10px rgba(0, 0, 0, 0.9), 0 0 15px rgba(201, 160, 80, 0.4);
        text-transform: uppercase;
        letter-spacing: 3px;
        text-align: center;
        border-bottom: 2px solid #5a4625;
        padding-bottom: 12px;
        margin-top: 10px;
    }

    .subtitle-box {
        text-align: center;
        font-family: 'Cinzel', serif;
        font-size: 14px;
        letter-spacing: 2px;
        color: #799a77;
        margin-bottom: 25px;
    }

    /* Tactical Military Card Box */
    .aot-card {
        background: rgba(18, 24, 19, 0.85);
        border: 2px solid #735930;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.8), inset 0 0 15px rgba(0, 0, 0, 0.6);
        padding: 24px;
        border-radius: 4px;
        margin-bottom: 20px;
    }

    /* Input Field - Military Parchment */
    .stTextInput>div>div>input {
        background-color: #121813 !important;
        color: #e8dcc4 !important;
        border: 1px solid #735930 !important;
        border-radius: 2px !important;
        font-family: 'Crimson Text', serif !important;
        font-size: 17px !important;
        box-shadow: inset 0 0 5px rgba(0,0,0,0.8);
    }
    .stTextInput>div>div>input:focus {
        border: 1px solid #c9a050 !important;
        box-shadow: 0 0 10px rgba(201, 160, 80, 0.3) !important;
    }

    /* Dropdown Selector */
    .stSelectbox>div>div {
        background-color: #121813 !important;
        color: #e8dcc4 !important;
        border: 1px solid #735930 !important;
        border-radius: 2px !important;
    }

    /* Scout Regiment Golden Blades Button */
    .stButton>button {
        font-family: 'Cinzel', serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        background: linear-gradient(180deg, #445942 0%, #20311f 100%) !important;
        color: #f4ecd8 !important;
        border: 2px solid #c9a050 !important;
        border-radius: 3px !important;
        padding: 10px 24px !important;
        width: 100% !important;
        transition: all 0.3s ease;
        text-shadow: 1px 1px 3px black;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.6);
    }
    .stButton>button:hover {
        background: linear-gradient(180deg, #597756 0%, #2a4129 100%) !important;
        border-color: #ffd700 !important;
        box-shadow: 0 0 15px rgba(201, 160, 80, 0.6) !important;
        transform: translateY(-1px);
    }

    /* Download Finished Button */
    .stDownloadButton>button {
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        background: linear-gradient(180deg, #8c6827 0%, #4f3b14 100%) !important;
        color: #ffffff !important;
        border: 2px solid #e5c365 !important;
        border-radius: 3px !important;
        width: 100% !important;
    }

    /* Streamlit labels */
    label {
        font-family: 'Cinzel', serif !important;
        color: #c9a050 !important;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# AOT Header
st.markdown("<h1>⚔️ Scout Regiment Dispatch</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle-box'>SHINZOU WO SASAGEYO • RETRIEVE ARCHIVED VISUALS BEYOND THE WALLS</div>", unsafe_allow_html=True)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def sanitize_filename(name: str) -> str:
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
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    if is_instagram:
        ydl_opts['format'] = 'best'
        try:
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
        except Exception:
            pass
    elif is_youtube:
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
        if quality_choice == "Maximum Titan Force (1080p / 4K)":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
        elif quality_choice == "Standard Scout (720p HD)":
            ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]'
        elif quality_choice == "Wall Patrol (480p SD)":
            ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]'
        elif quality_choice == "War Horns Only (MP3 Audio)":
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
        title = info.get('title', 'scout_intel')
        clean_title = sanitize_filename(title)

        expected_ext = "mp3" if quality_choice == "War Horns Only (MP3 Audio)" and is_youtube else "mp4"

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

        raise FileNotFoundError("Visual parchment could not be located inside the archives.")

# UI Form
st.markdown("<div class='aot-card'>", unsafe_allow_html=True)
url_input = st.text_input(
    "Target Reel / Video Coordinates (URL):", 
    placeholder="Paste YouTube or Instagram reconnaissance link..."
)

quality_option = st.selectbox(
    "Select Tactical Output Quality:",
    [
        "Maximum Titan Force (1080p / 4K)",
        "Standard Scout (720p HD)",
        "Wall Patrol (480p SD)",
        "War Horns Only (MP3 Audio)"
    ]
)

fetch_button = st.button("⚔️ INITIATE RETRIEVAL (SASAGEYO)")
st.markdown("</div>", unsafe_allow_html=True)

if fetch_button:
    if not url_input.strip():
        st.warning("Commander! Provide a valid target URL first.")
    else:
        with st.spinner("ODM Gear Engaged... Breaching the firewall and securing the video stream..."):
            try:
                file_path, title, ext = run_downloader(url_input.strip(), quality_option)

                if os.path.exists(file_path):
                    st.success(f"Intel Secured: **{title}**")

                    if ext == "mp3":
                        st.audio(file_path)
                        mime_type = "audio/mp3"
                    else:
                        st.video(file_path)
                        mime_type = f"video/{ext}"

                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"🛡️ SECURE {ext.upper()} ARCHIVE TO DEVICE",
                            data=f.read(),
                            file_name=f"{title[:40]}.{ext}",
                            mime=mime_type
                        )
                else:
                    st.error("Operation Failed: File missing from Wall archives.")

            except Exception as e:
                err = str(e)
                if "login" in err.lower():
                    st.error("Titan Barrier: Instagram requires login verification for this coordinate.")
                elif "sign in to confirm" in err.lower() or "bot" in err.lower():
                    st.error("Anti-Personnel Gear Detected: YouTube flagged the request. Wait 1 minute and re-engage.")
                else:
                    st.error(f"Recon Mission Failed: {err}")
