import streamlit as st
import requests
import asyncio
import os
import re
from gradio_client import Client
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips

st.set_page_config(page_title="ध्यानी AI — 3D Video Studio", page_icon="🎬", layout="wide")

GIST_ID = "da462194ae74329486942ddc30f9c414"

@st.cache_data(ttl=15)
def get_auto_kaggle_url():
    try:
        res = requests.get(f"https://api.github.com/gists/{GIST_ID}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data["files"]["kaggle_url.txt"]["content"].strip()
    except Exception:
        pass
    return ""

kaggle_url = get_auto_kaggle_url()

st.title("🎬 ध्यानी AI — 3D Text-to-Video Studio")

if kaggle_url:
    st.success("🟢 AI GPU Video Engine कनेक्टेड है!")
else:
    st.warning("⚠️ Kaggle Engine कनेक्ट नहीं है। कृपया पहले Kaggle पर कोड रन करें।")

st.markdown("---")

col1, col2 = st.columns([1.2, 1])

with col1:
    story_text = st.text_area(
        "1. 📝 पूरी कहानी दर्ज करें:", 
        height=180, 
        placeholder="एक सुंदर गाँव में गोलू नाम का खरगोश खुशी से उछल-कूद कर रहा था..."
    )
    voice = st.selectbox("2. 🎙️ कथावाचक वॉयस", [
        "Natural Male (Madhur - कथावाचक)", 
        "Natural Female (Swara - स्पष्ट)"
    ])

with col2:
    char_desc = st.text_input(
        "3. 👤 3D कैरेक्टर और स्टाइल:", 
        value="Cute 3D fluffy baby bear cub, Pixar animation style"
    )

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural"
}

async def generate_voice(text, voice_code, out_path):
    import edge_tts
    comm = edge_tts.Communicate(text, voice_code)
    await comm.save(out_path)

if st.button("🚀 Generate Complete 3D Moving Video", type="primary", use_container_width=True):
    if not kaggle_url:
        st.error("❌ Kaggle बैकएंड कनेक्ट नहीं है! कृपया पहले Kaggle पर कोड चालू करें।")
    elif not story_text.strip():
        st.error("❌ कृपया पहले कहानी दर्ज करें!")
    else:
        status = st.status("🎬 3D वीडियो प्रोडक्शन शुरू हो रहा है...", expanded=True)
        os.makedirs("temp_render/scenes", exist_ok=True)

        sentences = [s.strip() for s in re.split(r'[।\n\.]+', story_text) if len(s.strip()) > 3]
        total = len(sentences)
        scene_clips = []

        for idx, sentence in enumerate(sentences):
            status.write(f"🎙️ **सीन {idx+1}/{total}:** आवाज़ तैयार हो रही है...")
            audio_path = f"temp_render/scenes/audio_{idx}.mp3"
            asyncio.run(generate_voice(sentence, VOICE_MAP[voice], audio_path))
            audio_clip = AudioFileClip(audio_path)
            dur = audio_clip.duration

            status.write(f"🎥 **सीन {idx+1}/{total}:** 3D मूविंग वीडियो रेंडर हो रहा है...")
            try:
                client = Client(kaggle_url)
                video_prompt = f"{char_desc}, {sentence}"
                video_res = client.predict(
                    prompt=video_prompt,
                    api_name="/predict"
                )
                
                # Gradio Dict आउटपुट से असली वीडियो पाथ निकालने का फिक्स
                if isinstance(video_res, dict):
                    raw_path = video_res.get("video") or video_res.get("path")
                else:
                    raw_path = str(video_res)
                
                clip = VideoFileClip(raw_path)
                if clip.duration < dur:
                    clip = clip.loop(duration=dur)
                else:
                    clip = clip.subclip(0, dur)
                
                clip = clip.set_audio(audio_clip)
                scene_clips.append(clip)
            except Exception as e:
                status.write(f"⚠️ सीन {idx+1} में समस्या: {e}")

        if scene_clips:
            status.write("🎞️ सभी क्लिप्स जोड़कर फाइनल 3D वीडियो बन रही है...")
            final_video = concatenate_videoclips(scene_clips, method="compose")
            out_file = "temp_render/dhyani_ai_master_video.mp4"
            final_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", logger=None)

            status.update(label="✅ 3D वीडियो तैयार!", state="complete")
            st.success("🎉 आपकी 3D वीडियो सफलतापूर्वक बन गई!")
            st.video(out_file)
            
            with open(out_file, "rb") as f:
                st.download_button("📥 Download Video (MP4)", f, file_name="dhyani_ai_3d_video.mp4", mime="video/mp4", use_container_width=True)
        else:
            status.update(label="❌ कोई सीन रेंडर नहीं हो सका", state="error")
