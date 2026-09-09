import os
import re
import streamlit as st
import yt_dlp
from groq import Groq
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Load local environment variables
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="AI Media & Transcription Hub",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ AI Media Downloader & Transcriber")
st.caption("Cloud-safe stream links & dynamic AI summaries via Groq")

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
    patterns = [
        r"(?:v=|\/|youtu\.be\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    return None

# Helper to fetch transcript safely without byte downloads
def fetch_safe_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 1. Try manual transcript (English or Hindi)
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'hi', 'hi-Latn'])
            return " ".join([item['text'] for item in transcript.fetch()])
        except Exception:
            pass

        # 2. Try generated transcript (English or Hindi)
        try:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'hi', 'hi-Latn'])
            return " ".join([item['text'] for item in transcript.fetch()])
        except Exception:
            pass

        # 3. Fallback: Take first available transcript and translate to English
        for t in transcript_list:
            try:
                translated = t.translate('en')
                return " ".join([item['text'] for item in translated.fetch()])
            except Exception:
                return " ".join([item['text'] for item in t.fetch()])

    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None

# Helper function to get an active, working text model dynamically from Groq
def get_working_groq_model(client):
    try:
        models_data = client.models.list()
        available_ids = [m.id for m in models_data.data if hasattr(m, 'id')]
        
        # Priority list of known chat models
        preferred_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        
        for pref in preferred_models:
            if pref in available_ids:
                return pref
                
        # If none of the preferred match, pick any non-whisper model
        for m_id in available_ids:
            if "whisper" not in m_id.lower() and "guard" not in m_id.lower():
                return m_id
                
        return "llama-3.1-8b-instant"
    except Exception:
        return "llama-3.1-8b-instant"

# Main Processing Execution
if st.button("Process & Generate Content", type="primary"):
    url_clean = url.strip()

    if not url_clean or not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("Please enter a valid video link starting with http:// or https://")
    else:
        with st.spinner("Extracting media streams and info..."):
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
                    description = info.get('description', '')
                    formats = info.get('formats', [])

                    st.success(f"✅ Successfully Found: **{title}**")

                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if thumbnail:
                            st.image(thumbnail, use_container_width=True)
                    with c2:
                        st.write(f"⏱️ **Duration:** {duration}")
                        st.write(f"👁️ **Views:** {info.get('view_count', 'N/A'):,}")

                    # AI Transcription & Summary Pipeline
                    if enable_transcription:
                        if not groq_api_key:
                            st.warning("⚠️ Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets.")
                        else:
                            st.divider()
                            st.subheader("🤖 Groq AI Content Intelligence")

                            client = Groq(api_key=groq_api_key)
                            video_id = get_youtube_id(url_clean)
                            transcription_text = None

                            if video_id:
                                with st.spinner("Extracting transcript data (Cloud-safe)..."):
                                    transcription_text = fetch_safe_transcript(video_id)

                            context_source = "Transcript"
                            content_to_summarize = transcription_text

                            if not content_to_summarize and description:
                                content_to_summarize = description[:3000]
                                context_source = "Video Overview & Description"
                                st.info("ℹ️ Captions were not present for this video; generating summary from official video details.")

                            if content_to_summarize:
                                if transcription_text:
                                    with st.expander("📄 View Full Video Transcript"):
                                        st.write(transcription_text)

                                with st.spinner("Selecting active Groq model and generating summary..."):
                                    try:
                                        active_model = get_working_groq_model(client)
                                        
                                        summary_completion = client.chat.completions.create(
                                            model=active_model,
                                            messages=[
                                                {
                                                    "role": "system",
                                                    "content": (
                                                        "You are an expert executive content analyst. "
                                                        "Provide a clear, high-impact bulleted summary of the core concepts, "
                                                        "key arguments, and action steps from the provided text."
                                                    )
                                                },
                                                {
                                                    "role": "user",
                                                    "content": f"Analyze this {context_source}:\n\n{content_to_summarize[:4500]}"
                                                }
                                            ],
                                            max_tokens=350
                                        )

                                        summary_res = summary_completion.choices[0].message.content.strip()

                                        st.markdown(f"#### 📌 Key Takeaways & Actionable Summary `({active_model})`")
                                        st.markdown(summary_res)

                                    except Exception as sum_err:
                                        st.error(f"Summary Error: {str(sum_err)}")
                            else:
                                st.warning("⚠️ No captions or descriptions found to generate summary.")

                    # Direct Download Streams
                    st.divider()
                    st.subheader("📥 Direct Download Streams")
                    st.caption("💡 Right-click any stream link and select 'Save Link As...' to download directly onto your device.")

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
                        st.markdown("#### 🎵 Audio Streams (Direct Track)")
                        best_audio = audio_streams[-1]
                        abr = best_audio.get('abr', '128')
                        st.markdown(f"- **Audio ({abr} kbps)** ➔ [Open / Download Audio]({best_audio.get('url')})")

            except Exception as e:
                st.error(f"Processing Error: {str(e)}")
