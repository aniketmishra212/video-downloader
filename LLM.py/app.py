import os
import glob
import re
import streamlit as st
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="Universal Video Downloader AI",
    page_icon="🎬",
    layout="centered"
)

# App Header
st.title("🎬 Universal Video Downloader AI")
st.caption("Download YouTube & Instagram videos with full audio.")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters from media titles."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def run_downloader(url: str, quality_choice: str):
    is_instagram = "instagram.com" in url.lower()

    # Instagram uses a single combined stream; YouTube uses split streams
    if is_instagram:
        format_rule = "best"
    else:
        if quality_choice == "Best Available (Highest / 1080p / 4K)":
            format_rule = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        elif quality_choice == "720p (High Definition)":
            format_rule = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"
        elif quality_choice == "480p (Standard Definition)":
            format_rule = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"
        elif quality_choice == "Audio Only (MP3)":
            format_rule = "bestaudio/best"
        else:
            format_rule = "bestvideo+bestaudio/best"

    ydl_opts = {
        'format': format_rule,
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
        # Real browser headers to bypass Instagram blocking
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    if quality_choice == "Audio Only (MP3)" and not is_instagram:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id')
        title = info.get('title', 'instagram_video' if is_instagram else 'video')
        clean_title = sanitize_filename(title)

        # Expected extension
        expected_ext = "mp3" if quality_choice == "Audio Only (MP3)" and not is_instagram else "mp4"

        # Check exact matched file
        specific_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.{expected_ext}")
        if os.path.exists(specific_file):
            return specific_file, clean_title, expected_ext

        # Fallback: scan by video_id
        matches = glob.glob(f"{DOWNLOAD_DIR}/{video_id}.*")
        valid_files = [f for f in matches if not f.endswith(('.part', '.ytdl'))]
        if valid_files:
            actual_file = valid_files[0]
            ext = actual_file.rsplit('.', 1)[-1].lower()
            return actual_file, clean_title, ext

        # Fallback 2: pick latest created file
        all_files = glob.glob(f"{DOWNLOAD_DIR}/*")
        valid_all = [f for f in all_files if not f.endswith(('.part', '.ytdl', '.txt'))]
        if valid_all:
            latest_file = max(valid_all, key=os.path.getctime)
            ext = latest_file.rsplit('.', 1)[-1].lower()
            return latest_file, clean_title, ext

        raise FileNotFoundError("Video file could not be saved to disk.")

# --- UI Layout ---
url_input = st.text_input(
    "Paste Media Link:", 
    placeholder="https://www.instagram.com/reel/... or https://www.youtube.com/watch?v=..."
)

quality_option = st.selectbox(
    "Select Preferred Quality:",
    [
        "Best Available (Highest / 1080p / 4K)",
        "720p (High Definition)",
        "480p (Standard Definition)",
        "Audio Only (MP3)"
    ]
)

if st.button("Fetch & Download", type="primary"):
    if not url_input.strip():
        st.warning("Please paste a valid link first.")
    else:
        with st.spinner("Processing link and downloading media... Please wait..."):
            try:
                file_path, title, ext = run_downloader(url_input.strip(), quality_option)

                if os.path.exists(file_path):
                    st.success(f"Ready: **{title}**")

                    if ext == "mp3":
                        st.audio(file_path)
                        mime_type = "audio/mp3"
                    else:
                        st.video(file_path)
                        mime_type = f"video/{ext}"

                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"💾 Save {ext.upper()} to Device",
                            data=f.read(),
                            file_name=f"{title[:40]}.{ext}",
                            mime=mime_type
                        )
                else:
                    st.error("Error: Media file could not be located.")
            except Exception as e:
                error_msg = str(e)
                if "login" in error_msg.lower():
                    st.error("Instagram Login Required: This account is private or Instagram blocked guest access for this reel.")
                else:
                    st.error(f"Download Failed: {error_msg}")
