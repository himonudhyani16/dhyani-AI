import streamlit as st
import requests
import asyncio
import os
import re
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

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

st.title("🎬 ध्यानी AI — 3D Video Studio")

if kaggle_url:
    st.success("🟢 AI GPU Lip-Sync Video Engine कनेक्टेड है!")
else:
    st.warning("⚠️ Kaggle Engine कनेक्ट नहीं है। कृपया पहले Kaggle पर कोड रन करें।")

st.markdown("---")

col1, col2 = st.columns([1.2, 1])

with col1:
    story_text = st.text_area(
        "1. 📝 पूरी कहानी दर्ज करें:", 
        height=160, 
        placeholder="एक सुंदर गाँव में गोलू नाम का खरगोश खुशी से उछल-कूद कर रहा था..."
    )
    voice = st.selectbox("2. 🎙️ कथावाचक वॉयस", [
        "Natural Male (Madhur - कथावाचक)", 
        "Natural Female (Swara - स्पष्ट)"
    ])

with col2:
    char_desc = st.text_input(
        "3. 👤 कैरेक्टर विवरण / प्रॉम्प्ट:", 
        value="Cute fluffy baby squirrel in fairyland garden"
    )
    
    # 🖼️ इमेज अपलोड बॉक्स
    custom_img = st.file_uploader(
        "4. 🖼️ कैरेक्टर फोटो अपलोड करें (अनिवार्य):", 
        type=["png", "jpg", "jpeg"]
    )
    
    # 📐 आस्पेक्ट रेशियो बॉक्स
    aspect_ratio = st.selectbox(
        "5. 📐 वीडियो साइज़ / रेशियो चुनें:",
        ["16:9 (YouTube Landscape)", "9:16 (Shorts / Reels Portrait)", "1:1 (Square)"]
    )

if custom_img:
    st.image(custom_img, caption="✅ चुनी गई कैरेक्टर फोटो", width=220)

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural"
}

async def generate_voice(text, voice_code, out_path):
    import edge_tts
    comm = edge_tts.Communicate(text, voice_code)
    await comm.save(out_path)

def extract_valid_path(raw_res):
    if isinstance(raw_res, dict):
        for key in ["video", "path", "name", "data"]:
            if key in raw_res and raw_res[key]:
                return str(raw_res[key])
        return str(list(raw_res.values())[0])
    elif isinstance(raw_res, (list, tuple)):
        return str(raw_res[0])
    return str(raw_res)

def resize_to_ratio(clip, ratio_type):
    if ratio_type == "16:9 (YouTube Landscape)":
        return clip.resize(height=720).crop(x1=clip.w/2 - 640, width=1280, height=720) if clip.w >= 1280 else clip.resize((1280, 720))
    elif ratio_type == "9:16 (Shorts / Reels Portrait)":
        return clip.resize(height=1280).crop(x1=clip.w/2 - 360, width=720, height=1280) if clip.w >= 720 else clip.resize((720, 1280))
    else:
        return clip.resize((720, 720))

if st.button("🚀 Generate Complete 3D Lip-Sync Video", type="primary", use_container_width=True):
    if not kaggle_url:
        st.error("❌ Kaggle बैकएंड कनेक्ट नहीं है!")
    elif not story_text.strip():
        st.error("❌ कृपया पहले कहानी दर्ज करें!")
    elif not custom_img:
        st.error("❌ कृपया लिप-सिंक के लिए कैरेक्टर की फोटो (Box 4) जरूर अपलोड करें!")
    else:
        status = st.status("🎬 वीडियो प्रोडक्शन शुरू हो रहा है...", expanded=True)
        os.makedirs("temp_render/scenes", exist_ok=True)

        saved_img_path = "temp_render/character_input.png"
        with open(saved_img_path, "wb") as f:
            f.write(custom_img.getbuffer())

        sentences = [s.strip() for s in re.split(r'[।\n\.]+', story_text) if len(s.strip()) > 3]
        total = len(sentences)
        scene_clips = []

        for idx, sentence in enumerate(sentences):
            status.write(f"🎙️ **सीन {idx+1}/{total}:** आवाज़ रिकॉर्ड हो रही है...")
            audio_path = f"temp_render/scenes/audio_{idx}.mp3"
            asyncio.run(generate_voice(sentence, VOICE_MAP[voice], audio_path))

            status.write(f"👄 **सीन {idx+1}/{total}:** AI परफेक्ट लिप-सिंक रेंडर कर रहा है...")
            try:
                client = Client(kaggle_url)
                video_res = client.predict(
                    image_path=os.path.abspath(saved_img_path),
                    audio_path=os.path.abspath(audio_path),
                    api_name="/predict"
                )
                
                real_path = extract_valid_path(video_res)
                
                if os.path.exists(real_path):
                    clip = VideoFileClip(real_path)
                    clip = resize_to_ratio(clip, aspect_ratio)
                    scene_clips.append(clip)
                else:
                    status.write(f"⚠️ सीन {idx+1} रेंडर नहीं हो सका!")
            except Exception as e:
                status.write(f"⚠️ सीन {idx+1} एरर: {e}")

        if scene_clips:
            status.write("🎞️ सभी क्लिप्स जोड़कर फाइनल वीडियो बन रही है...")
            final_video = concatenate_videoclips(scene_clips, method="compose")
            out_file = "temp_render/master_lipsync_video.mp4"
            final_video.write_videofile(out_file, fps=25, codec="libx264", audio_codec="aac", logger=None)

            status.update(label="✅ वीडियो तैयार!", state="complete")
            st.success("🎉 आपकी लिप-सिंक वीडियो तैयार हो गई!")
            st.video(out_file)
            
            with open(out_file, "rb") as f:
                st.download_button("📥 Download Video (MP4)", f, file_name="final_lipsync_video.mp4", mime="video/mp4", use_container_width=True)
        else:
            status.update(label="❌ कोई सीन नहीं बन पाया", state="error")
