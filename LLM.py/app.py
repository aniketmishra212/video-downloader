
import os
import tempfile
import streamlit as st
import yt_dlp
import imageio_ffmpeg
from groq import Groq
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Setup portable FFmpeg binary paths for local and cloud runtimes
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
st.caption("Extract direct video streams, download audio, and generate instant AI transcript summaries via Groq")

# Groq API Key Setup (Prioritize Streamlit Secrets, fallback to env)
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Video URL input
url = st.text_input("Enter Video or Media URL:", placeholder="https://www.youtube.com/watch?v=...")

# Advanced Feature Options
col1, col2 = st.columns(2)
with col1:
    selected_country = st.selectbox(
        "Target Region (Geo-Bypass):",
        ["US", "GB", "DE", "JP", "FR", "IN"],
        index=0
    )
with col2:
    enable_transcription = st.checkbox("Generate AI Transcript & Summary", value=True)

# Main Processing Execution
if st.button("Process & Generate Content", type="primary"):
    url_clean = url.strip()

    if not url_clean or not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("Please enter a valid video link starting with http:// or https://")
    else:
        with st.spinner("Processing media streams and running AI pipelines, please wait..."):
            try:
                # 1. yt-dlp Options for Stream Extraction & Temporary Audio Download
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

                    st.success(f"✅ Successfully Processed: **{title}**")

                    # Display Metadata & Thumbnail
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if thumbnail:
                            st.image(thumbnail, use_container_width=True)
                    with c2:
                        st.write(f"⏱️ **Duration:** {duration}")
                        st.write(f"👁️ **Views:** {info.get('view_count', 'N/A'):,}")

                    # 2. AI Transcription & Summary Pipeline (Using Groq Whisper & Llama)
                    if enable_transcription:
                        if not groq_api_key:
                            st.warning("⚠️ Groq API key is missing. Skipping AI transcription. Add GROQ_API_KEY to secrets.")
                        else:
                            st.divider()
                            st.subheader("🤖 Groq AI Audio Transcription & Summary")
                            
                            try:
                                client = Groq(api_key=groq_api_key)
                                
                                # Download temporary audio file for Whisper transcription
                                audio_opts = {
                                    'format': 'bestaudio/best',
                                    'postprocessors': [{
                                        'key': 'FFmpegExtractAudio',
                                        'preferredcodec': 'mp3',
                                        'preferredquality': '128',
                                    }],
                                    'outtmpl': os.path.join(tempfile.gettempdir(), 'temp_audio.%(ext)s'),
                                    'quiet': True,
                                    'ffmpeg_location': FFMPEG_BINARY
                                }
                                
                                with yt_dlp.YoutubeDL(audio_opts) as audio_ydl:
                                    audio_ydl.download([url_clean])
                                
                                audio_file_path = os.path.join(tempfile.gettempdir(), 'temp_audio.mp3')
                                
                                if os.path.exists(audio_file_path):
                                    with st.spinner("Transcribing audio using Groq Whisper model..."):
                                        with open(audio_file_path, "rb") as file:
                                            transcription = client.audio.transcriptions.create(
                                                file=(os.path.basename(audio_file_path), file.read()),
                                                model="whisper-large-v3",
                                                response_format="text"
                                            )
                                    
                                    # Display Transcript expander
                                    with st.expander("📄 View Full Audio Transcript"):
                                        st.write(transcription)

                                    # Generate AI Summary using Llama model based on transcript
                                    with st.spinner("Generating executive summary..."):
                                        summary_completion = client.chat.completions.create(
                                            model="llama-3.3-70b-versatile",
                                            messages=[
                                                {
                                                    "role": "system",
                                                    "content": "You are an expert content summarizer. Provide a concise bulleted summary of the following transcript highlighting core takeaways."
                                                },
                                                {
                                                    "role": "user",
                                                    "content": f"Summarize this transcript: {transcription[:4000]}" # Truncate token limit safety
                                                }
                                            ],
                                            max_tokens=300
                                        )
                                        summary_text = summary_completion.choices[0].message.content.strip()
                                        
                                        st.markdown("#### 📌 Key Takeaways & Summary")
                                        st.markdown(summary_text)

                                    # Cleanup temp audio file
                                    if os.path.exists(audio_file_path):
                                        os.remove(audio_file_path)

                            except Exception as ai_err:
                                st.error(f"AI Transcription/Summary Error: {str(ai_err)}")

                    # 3. Direct Download Links Section
                    st.divider()
                    st.subheader("📥 Direct Download Links")

                    combined_streams = [
                        f for f in formats 
                        if f.get('ext') == 'mp4' 
                        and f.get('vcodec') != 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    audio_streams = [
                        f for f in formats 
                        if f.get('vcodec') == 'none' 
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
                        st.markdown("#### 🎵 Audio Streams (MP3)")
                        best_audio = audio_streams[-1]
                        abr = best_audio.get('abr', '128')
                        st.markdown(f"- **Audio ({abr} kbps)** ➔ [Open / Download Audio]({best_audio.get('url')})")

            except Exception as e:
                st.error(f"Processing Error: {str(e)}")
