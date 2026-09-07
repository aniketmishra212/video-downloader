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
    page_icon="🎥",
    layout="centered"
)

# App Header
st.title("🎥 Universal Video Downloader AI")
st.caption("Download high-quality videos from YouTube and Instagram in your preferred video format.")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters from media titles."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_video_format_rule(format_choice: str) -> dict:
    """Configures yt-dlp to strictly download video formats."""
    if format_choice == "MP4 - Best Available (4K / 1080p)":
        return {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4'
        }
    elif format_choice == "MP4 - 720p (HD)":
        return {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'merge_output_format': 'mp4'
        }
    elif format_choice == "MP4 - 480p (Standard)":
        return {
            'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            'merge_output_format': 'mp4'
        }
    elif format_choice == "MKV - Best Quality Lossless":
        return {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mkv'
        }
    elif format_choice == "WEBM - High Quality Web Video":
        return {
            'format': 'bestvideo[ext=webm]+bestaudio[ext=webm]/best',
            'merge_output_format': 'webm'
        }
    return {'format': 'bestvideo+bestaudio/best', 'merge_output_format': 'mp4'}

def run_downloader(url: str, format_choice: str):
    format_settings = get_video_format_rule(format_choice)
    
    ydl_opts = {
        **format_settings,
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id')
        title = info.get('title', 'video_file')
        clean_title = sanitize_filename(title)
        
        # Locate the downloaded video file by ID
        matches = glob.glob(f"{DOWNLOAD_DIR}/{video_id}.*")
        valid_files = [f for f in matches if not f.endswith(('.part', '.ytdl'))]
        
        if valid_files:
            actual_file = valid_files[0]
            ext = actual_file.rsplit('.', 1)[-1].lower()
            return actual_file, clean_title, ext
        
        # Fallback: Find most recently created video file
        all_files = glob.glob(f"{DOWNLOAD_DIR}/*")
        valid_all = [f for f in all_files if not f.endswith(('.part', '.ytdl', '.txt'))]
        if valid_all:
            latest_file = max(valid_all, key=os.path.getctime)
            ext = latest_file.rsplit('.', 1)[-1].lower()
            return latest_file, clean_title, ext
            
        raise FileNotFoundError("Video file could not be found on local storage.")

# --- UI Form ---
url_input = st.text_input(
    "Enter Video URL:", 
    placeholder="https://www.youtube.com/watch?v=... or Instagram reel URL"
)

format_option = st.selectbox(
    "Choose Video Quality & Format:",
    [
        "MP4 - Best Available (4K / 1080p)",
        "MP4 - 720p (HD)",
        "MP4 - 480p (Standard)",
        "MKV - Best Quality Lossless",
        "WEBM - High Quality Web Video"
    ]
)

if st.button("Download Video", type="primary"):
    if not url_input.strip():
        st.warning("Please paste a valid video URL.")
    else:
        with st.spinner("Downloading video file... Please wait..."):
            try:
                file_path, title, ext = run_downloader(url_input.strip(), format_option)
                
                if os.path.exists(file_path):
                    st.success(f"Video Ready: **{title}**")
                    
                    # Direct in-browser video player preview
                    st.video(file_path)
                    
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"💾 Save {ext.upper()} Video to Device",
                            data=f.read(),
                            file_name=f"{title[:50]}.{ext}",
                            mime=f"video/{ext}"
                        )
                else:
                    st.error("Error: Video file not found.")
            except Exception as e:
                st.error(f"Download Error: {str(e)}")