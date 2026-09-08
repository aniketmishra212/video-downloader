import os
import tempfile
import requests
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
    page_title="AI Media & Transcription Hub",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ AI Media Downloader & Transcriber")
st.caption("Direct streams, audio extraction, and AI summary via Groq")

# Groq API Key Setup
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Video URL input
url = st.text_input("Enter Video URL:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    selected_country = st.selectbox(
        "Target Region:",
        ["US", "GB", "DE", "JP", "FR", "IN"],
        index=0
    )
with col2:
    enable_transcription = st.checkbox("Generate AI Transcript & Summary", value=True)

# Helper function to download stream via mobile headers without 403
def download_stream_to_file(stream_url, output_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    response = requests.get(stream_url, headers=headers, stream=True, timeout=60)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

# Main Processing Execution
if st.button("Process & Generate Content", type="primary"):
    url_clean = url.strip()

    if not url_clean or not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("Please enter a valid video link starting with http:// or https://")
    else:
        with st.spinner("Extracting media streams and info, please wait..."):
            try:
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
                    title = info.get('title', 'Media_Content')
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

                    # Audio streams filter
                    audio_streams = [
                        f for f in formats 
                        if f.get('vcodec') == 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    # AI Transcription Pipeline
                    if enable_transcription:
                        if not groq_api_key:
                            st.warning("⚠️ Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets.")
                        elif not audio_streams:
                            st.warning("⚠️ No direct audio stream found for transcription.")
                        else:
                            st.divider()
                            st.subheader("🤖 Groq AI Audio Transcription & Summary")

                            temp_audio_file = os.path.join(tempfile.gettempdir(), 'temp_audio.m4a')
                            try:
                                client = Groq(api_key=groq_api_key)
                                
                                # Lowest bitrate audio stream select karein (chhoti size = fast transcription)
                                target_audio_stream = audio_streams[0].get('url')
                                
                                with st.spinner("Fetching audio stream safely..."):
                                    download_stream_to_file(target_audio_stream, temp_audio_file)

                                with st.spinner("Transcribing audio using Groq Whisper-large-v3..."):
                                    with open(temp_audio_file, "rb") as file_obj:
                                        transcription = client.audio.transcriptions.create(
                                            file=(os.path.basename(temp_audio_file), file_obj.read()),
                                            model="whisper-large-v3",
                                            response_format="text"
                                        )

                                with st.expander("📄 View Full Audio Transcript"):
                                    st.write(transcription)

                                with st.spinner("Generating summary via Llama 3.3..."):
                                    summary_completion = client.chat.completions.create(
                                        model="llama-3.3-70b-versatile",
                                        messages=[
                                            {
                                                "role": "system",
                                                "content": "You are an expert summarizer. Provide a concise bulleted summary highlighting the core takeaways."
                                            },
                                            {
                                                "role": "user",
                                                "content": f"Summarize this transcript: {transcription[:4000]}"
                                            }
                                        ],
                                        max_tokens=300
                                    )
                                    summary_text = summary_completion.choices[0].message.content.strip()

                                    st.markdown("#### 📌 Key Takeaways & Summary")
                                    st.markdown(summary_text)

                            except Exception as ai_err:
                                st.error(f"AI Transcription Error: {str(ai_err)}")
                            finally:
                                if os.path.exists(temp_audio_file):
                                    try:
                                        os.remove(temp_audio_file)
                                    except Exception:
                                        pass

                    # Direct Download Links
                    st.divider()
                    st.subheader("📥 Direct Download Links")

                    combined_streams = [
                        f for f in formats 
                        if f.get('ext') == 'mp4' 
                        and f.get('vcodec') != 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    if combined_streams:
                        st.markdown("#### 🎥 Video Streams (MP4)")
                        for f in reversed(combined_streams):
                            res = f.get('resolution') or f"{f.get('height', 'Unknown')}p"
                            filesize = f.get('filesize')
                            size_str = f" (~{round(filesize / (1024 * 1024), 1)} MB)" if filesize else ""
                            stream_url = f.get('url')
                            st.markdown(f"- **{res}**{size_str} ➔ [Open / Download Video]({stream_url})")

                    if audio_streams:
                        st.markdown("#### 🎵 Audio Streams")
                        best_audio = audio_streams[-1]
                        abr = best_audio.get('abr', '128')
                        st.markdown(f"- **Audio ({abr} kbps)** ➔ [Open / Download Audio]({best_audio.get('url')})")

            except Exception as e:
                st.error(f"Processing Error: {str(e)}")
