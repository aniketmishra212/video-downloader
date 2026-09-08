import os
import streamlit as st
import yt_dlp
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Video Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Downloader")
st.caption("YouTube aur web videos ke direct high-speed download links generate karein")

groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

url = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

if st.checkbox("Verify link with Groq AI", value=False) and url:
    if not groq_api_key:
        st.warning("⚠️ Groq API Key configure nahi hai.")
    else:
        try:
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Aap ek URL verifier hain. Check karein link valid hai ya nahi. Short sentence mein answer dein."},
                    {"role": "user", "content": f"Check this URL: {url}"}
                ],
                max_tokens=60
            )
            st.info(f"🤖 **AI Agent:** {completion.choices[0].message.content.strip()}")
        except Exception as e:
            st.error(f"AI Verification error: {str(e)}")

if st.button("Download Links Generate Karein", type="primary"):
    url_clean = url.strip()
    if not url_clean or not url_clean.startswith("http"):
        st.error("Kripya valid URL dalein.")
    else:
        with st.spinner("Video details aur streams fetch kiye ja rahe hain..."):
            try:
                # Direct stream extraction options (bypass 403)
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios', 'android']
                        }
                    }
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_clean, download=False)
                    title = info.get('title', 'Video')
                    thumbnail = info.get('thumbnail')
                    duration = info.get('duration_string', 'N/A')
                    formats = info.get('formats', [])

                    st.success(f"✅ Found: **{title}**")
                    col_img, col_info = st.columns([1, 2])
                    with col_img:
                        if thumbnail:
                            st.image(thumbnail, use_container_width=True)
                    with col_info:
                        st.write(f"⏱️ **Duration:** {duration}")
                        st.write(f"👁️ **Views:** {info.get('view_count', 'N/A'):,}")

                    st.markdown("### 📥 Available Downloads:")

                    # Progressive MP4 formats (Video + Audio combined in single file)
                    mp4_formats = [
                        f for f in formats 
                        if f.get('ext') == 'mp4' 
                        and f.get('vcodec') != 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    # Audio only formats
                    audio_formats = [
                        f for f in formats 
                        if f.get('vcodec') == 'none' 
                        and f.get('acodec') != 'none' 
                        and f.get('url')
                    ]

                    if mp4_formats:
                        st.subheader("🎥 Video with Audio (Direct MP4)")
                        for f in reversed(mp4_formats):
                            res = f.get('resolution') or f"{f.get('height', 'Unknown')}p"
                            filesize = f.get('filesize')
                            size_str = f" (~{round(filesize / (1024 * 1024), 1)} MB)" if filesize else ""
                            stream_url = f.get('url')
                            
                            st.markdown(
                                f"- **{res}**{size_str} $\\rightarrow$ "
                                f"[Click to Download / Play Direct Stream]({stream_url})"
                            )

                    if audio_formats:
                        st.subheader("🎵 Audio Streams")
                        best_audio = audio_formats[-1]
                        abr = best_audio.get('abr', 'Unknown')
                        st.markdown(
                            f"- **Audio ({abr} kbps)** $\\rightarrow$ "
                            f"[Click to Download Audio Stream]({best_audio.get('url')})"
                        )

            except Exception as e:
                st.error(f"Error fetching streams: {str(e)}")
