import os
import tempfile
import re
import streamlit as st
import yt_dlp
import imageio_ffmpeg
from groq import Groq
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables
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

# Helper function to extract YouTube Video ID
def get_youtube_id(video_url):
    regex = r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})"
    match = re.search(regex, video_url)
    return match.group(1) if match else None

# Helper function to safely fetch audio using yt-dlp internal downloader
def download_audio_safe(video_url, output_path, country):
    ydl_audio_opts = {
        'format': 'ba/b[ext=m4a]/b',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'geo_bypass': True,
        'geo_bypass_country': country,
        'ffmpeg_location': FFMPEG_BINARY,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',  # Light size for fast transcription
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
        ydl.download([video_url])

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

                    # AI Transcription Pipeline
                    if enable_transcription:
                        if not groq_api_key:
                            st.warning("⚠️ Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets.")
                        else:
                            st.divider()
                            st.subheader("🤖 Groq AI Audio Transcription & Summary")

                            transcription = None
                            client = Groq(api_key=groq_api_key)

                            # Method 1: YouTube Official Subtitles / Captions (Zero bandwidth, 100% bypass 403)
                            yt_id = get_youtube_id(url_clean)
                            if yt_id:
                                try:
                                    with st.spinner("Searching for native subtitles/captions..."):
                                        transcript_list = YouTubeTranscriptApi.list_transcripts(yt_id)
                                        # First find manual or auto captions (en, hi, etc.)
                                        try:
                                            transcript_obj = transcript_list.find_transcript(['en', 'en-US', 'hi', 'hi-Latn'])
                                        except Exception:
                                            transcript_obj = next(iter(transcript_list))
                                        
                                        data = transcript_obj.fetch()
                                        transcription = " ".join([t['text'] for t in data])
                                except Exception:
                                    transcription = None

                            # Method 2: Safe yt-dlp Audio Fetch for Whisper (if captions are unavailable)
                            if not transcription:
                                temp_base = os.path.join(tempfile.gettempdir(), 'audio_payload')
                                target_mp3 = f"{temp_base}.mp3"

                                try:
                                    with st.spinner("Downloading audio track for Groq Whisper..."):
                                        download_audio_safe(url_clean, temp_base, selected_country)

                                    if os.path.exists(target_mp3):
                                        with st.spinner("Transcribing via Groq Whisper-large-v3..."):
                                            with open(target_mp3, "rb") as file_obj:
                                                transcription = client.audio.transcriptions.create(
                                                    file=(os.path.basename(target_mp3), file_obj.read()),
                                                    model="whisper-large-v3",
                                                    response_format="text"
                                                )
                                except Exception as ai_err:
                                    st.warning(f"Audio download blocked by platform CDN: {str(ai_err)}. Direct download links are still available below.")
                                finally:
                                    if os.path.exists(target_mp3):
                                        try:
                                            os.remove(target_mp3)
                                        except Exception:
                                            pass

                            # Summary Generation
                            if transcription:
                                with st.expander("📄 View Full Audio Transcript"):
                                    st.write(transcription)

                                with st.spinner("Generating executive summary via Llama 3.3..."):
                                    try:
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
                                    except Exception as sum_err:
                                        st.error(f"Summary Generation Error: {str(sum_err)}")

                    # Direct Download Links
                    st.divider()
                    st.subheader("📥 Direct Download Links")

                    combined_streams = [
                        f for f in formats 
                        if f.get('ext') == 'mp4' 
                        and f.get('vcodec') and f.get('vcodec') != 'none' 
                        and f.get('acodec') and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    audio_streams = [
                        f for f in formats 
                        if f.get('vcodec') == 'none' 
                        and f.get('acodec') and f.get('acodec') != 'none' 
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
