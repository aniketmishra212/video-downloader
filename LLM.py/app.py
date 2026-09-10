import os
import re
import streamlit as st
import yt_dlp
from groq import Groq
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Load local environment variables
load_dotenv()

# Page Setup
st.set_page_config(
    page_title="MediaFlow AI | Video Intelligence & Dubbing Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom SaaS-style CSS
st.markdown("""
<style>
    /* Global Styles */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1100px;
    }
    
    /* Modern Header */
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    /* Cards */
    .meta-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(8px);
    }
    
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #1e293b;
        color: #38bdf8;
        border: 1px solid #0284c7;
        margin-right: 0.4rem;
    }

    /* Download Action Buttons */
    .download-pill {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
        transition: all 0.2s ease;
    }
    .download-pill:hover {
        border-color: #38bdf8;
        background: #1e293b;
    }
    .download-link {
        background: #2563eb;
        color: #ffffff !important;
        text-decoration: none;
        padding: 0.4rem 0.9rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        transition: background 0.2s ease;
    }
    .download-link:hover {
        background: #1d4ed8;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown('<div class="main-title">⚡ MediaFlow AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Next-gen media stream extractor, cross-lingual localization, & voiceover director engine</div>', unsafe_allow_html=True)

# Groq API Key Setup
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Sidebar Controls
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    selected_country = st.selectbox(
        "Geo-Bypass Routing:",
        ["US", "GB", "DE", "JP", "FR", "IN"],
        index=0,
        help="Select proxy origin to resolve region-locked media streams."
    )
    target_language = st.selectbox(
        "Target Localization Language:",
        ["Hindi", "English", "Spanish", "French", "German", "Japanese", "Arabic", "Russian"],
        index=0,
        help="Target language for executive summary, key quotes, and voiceover guides."
    )
    enable_ai_suite = st.toggle("Enable AI Intelligence Pipeline", value=True)
    
    st.divider()
    st.markdown("#### 💡 Pro Tips")
    st.caption("• **Zero Cloud Egress:** Video bytes never hit the server, completely eliminating 403 Forbidden bans.")
    st.caption("• **Dynamic Model Fallback:** AI automatically binds to currently available Groq LPU models.")

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

# Safe Transcript Ingestion
def fetch_safe_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'hi', 'hi-Latn'])
            return " ".join([item['text'] for item in transcript.fetch()])
        except Exception:
            pass

        try:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'hi', 'hi-Latn'])
            return " ".join([item['text'] for item in transcript.fetch()])
        except Exception:
            pass

        for t in transcript_list:
            try:
                return " ".join([item['text'] for item in t.fetch()])
            except Exception:
                pass
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None

# Dynamic Groq Model Detection
def get_working_groq_model(client):
    try:
        models_data = client.models.list()
        available_ids = [m.id for m in models_data.data if hasattr(m, 'id')]
        preferred = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]
        for p in preferred:
            if p in available_ids:
                return p
        for m_id in available_ids:
            if "whisper" not in m_id.lower() and "guard" not in m_id.lower():
                return m_id
        return "llama-3.1-8b-instant"
    except Exception:
        return "llama-3.1-8b-instant"

# Input Bar Section
col_in, col_btn = st.columns([4, 1])
with col_in:
    url = st.text_input("Enter Media URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
with col_btn:
    process_btn = st.button("🚀 Analyze & Extract", type="primary", use_container_width=True)

# Processing Logic
if process_btn:
    url_clean = url.strip()
    if not url_clean or not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        st.error("Please enter a valid video link starting with http:// or https://")
    else:
        with st.status("Analyzing media and spinning up AI pipeline...", expanded=True) as status:
            try:
                st.write("Fetching metadata and building CDN routes...")
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'geo_bypass': True,
                    'geo_bypass_country': selected_country,
                    'extractor_args': {
                        'youtube': {'player_client': ['ios', 'android', 'web']}
                    }
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_clean, download=False)
                    title = info.get('title', 'Media_Content')
                    thumbnail = info.get('thumbnail')
                    duration = info.get('duration_string', 'N/A')
                    views = info.get('view_count', 0)
                    author = info.get('uploader', 'Unknown Creator')
                    description = info.get('description', '')
                    formats = info.get('formats', [])

                st.write("Resolving subtitles and audio dialogue tracks...")
                video_id = get_youtube_id(url_clean)
                transcription_text = fetch_safe_transcript(video_id) if video_id else None
                source_content = transcription_text or (description[:3000] if description else None)

                # AI Processing
                summary_output = ""
                dubbing_output = ""
                active_model = "llama-3.1-8b-instant"

                if enable_ai_suite and groq_api_key and source_content:
                    st.write("Running Groq LPU reasoning and localization...")
                    client = Groq(api_key=groq_api_key)
                    active_model = get_working_groq_model(client)

                    # 1. Summary Prompt
                    trans_prompt = f"""
You are an expert multilingual translator and localization specialist.
Translate the key concepts and provide an executive summary strictly in {target_language}.
Format clearly with:
- **Executive Overview (3-4 concise points)**
- **Key Dialogues / Quotes translated into {target_language}**

Content:
{source_content[:4000]}
"""
                    t_resp = client.chat.completions.create(
                        model=active_model,
                        messages=[{"role": "user", "content": trans_prompt}],
                        max_tokens=450
                    )
                    summary_output = t_resp.choices[0].message.content.strip()

                    # 2. Dubbing Persona Prompt
                    dub_prompt = f"""
You are a professional audio dubbing director. Analyze this video content and provide actionable guidelines for localizing this video into {target_language}:
1. **Target Voice Persona:** (Recommended vocal tone, age profile, confidence level)
2. **Pacing & Lip-Sync Rhythm:** (Estimated speaking speed, pauses, and cadence matching)
3. **Emotional Cadence:** (Humorous, Urgent, Instructional, Dramatic)
4. **Cultural Nuances:** (Important idioms or context adjustments for {target_language} listeners)

Context:
{source_content[:3500]}
"""
                    d_resp = client.chat.completions.create(
                        model=active_model,
                        messages=[{"role": "user", "content": dub_prompt}],
                        max_tokens=400
                    )
                    dubbing_output = d_resp.choices[0].message.content.strip()

                status.update(label="Processing Complete!", state="complete", expanded=False)

                # Video Meta Showcase
                st.markdown(f"""
                <div class="meta-card">
                    <div style="display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap;">
                        <img src="{thumbnail}" style="width: 220px; border-radius: 8px; object-fit: cover; aspect-ratio: 16/9;" />
                        <div style="flex: 1; min-width: 250px;">
                            <h3 style="margin: 0 0 0.5rem 0; font-size: 1.25rem;">{title}</h3>
                            <div style="margin-bottom: 0.6rem;">
                                <span class="badge">👤 {author}</span>
                                <span class="badge">⏱️ {duration}</span>
                                <span class="badge">👁️ {views:,} views</span>
                                <span class="badge">🤖 Model: {active_model}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Tabbed Output Interface
                tab_summary, tab_dubbing, tab_downloads, tab_transcript = st.tabs([
                    f"📝 Summary ({target_language})",
                    "🎙️ Dubbing Director Guide",
                    "📥 Direct Media Streams",
                    "📄 Full Transcript"
                ])

                with tab_summary:
                    if summary_output:
                        st.markdown(summary_output)
                        st.download_button(
                            label="💾 Export Summary as .txt",
                            data=summary_output,
                            file_name=f"summary_{target_language.lower()}.txt",
                            mime="text/plain"
                        )
                    else:
                        st.info("No summary available. Ensure captions are available or add a valid Groq API key.")

                with tab_dubbing:
                    if dubbing_output:
                        st.markdown(dubbing_output)
                    else:
                        st.info("Dubbing guidelines could not be generated for this media.")

                with tab_downloads:
                    st.caption("Direct CDN streams routed client-side. Right-click any button and select 'Save Link As...' if preferred.")
                    
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

                    col_v, col_a = st.columns(2)
                    with col_v:
                        st.markdown("##### 🎥 Video (MP4 Combined)")
                        if combined_streams:
                            for f in reversed(combined_streams):
                                res = f.get('resolution') or f"{f.get('height', 'Unknown')}p"
                                filesize = f.get('filesize')
                                size_str = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Direct CDN"
                                st.markdown(f"""
                                <div class="download-pill">
                                    <span><b>{res}</b> ({size_str})</span>
                                    <a class="download-link" href="{f.get('url')}" target="_blank">Download MP4</a>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.write("No combined video stream found.")

                    with col_a:
                        st.markdown("##### 🎵 Audio Track (MP3/M4A)")
                        if audio_streams:
                            best_audio = audio_streams[-1]
                            abr = best_audio.get('abr', '128')
                            filesize = best_audio.get('filesize')
                            size_str = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "High Quality"
                            st.markdown(f"""
                            <div class="download-pill">
                                <span><b>Audio Stream</b> (~{abr} kbps, {size_str})</span>
                                <a class="download-link" href="{best_audio.get('url')}" target="_blank">Download Audio</a>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.write("No audio stream found.")

                with tab_transcript:
                    if transcription_text:
                        st.text_area("Original Captions", transcription_text, height=350)
                        st.download_button(
                            label="💾 Export Raw Transcript",
                            data=transcription_text,
                            file_name="transcript.txt",
                            mime="text/plain"
                        )
                    else:
                        st.info("Direct captions were not published for this video.")

            except Exception as e:
                status.update(label="Error Occurred", state="error", expanded=True)
                st.error(f"Processing Error: {str(e)}")
