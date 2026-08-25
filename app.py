import streamlit as st
import requests
import asyncio
import os
import re
import urllib.parse
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from gradio_client import Client, handle_file
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips

st.set_page_config(page_title="ध्यानी AI — 3D Lip-Sync Studio", page_icon="🎬", layout="wide")

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

st.title("🎬 ध्यानी AI — 3D Lip-Sync Studio")

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
        placeholder="एक सुंदर गाँव में चीकू नाम का एक नटखट बंदर रहता था..."
    )
    voice = st.selectbox("2. 🎙️ कथावाचक वॉयस", [
        "Natural Male (Madhur - कथावाचक)", 
        "Natural Female (Swara - स्पष्ट)"
    ])

with col2:
    char_desc = st.text_input(
        "3. 👤 कैरेक्टर विवरण (इमेज न होने पर AI इससे बनाएगा):", 
        value="Cute baby monkey cartoon face looking directly at camera, 3d pixar animation style"
    )
    custom_img = st.file_uploader(
        "4. 🖼️ कैरेक्टर फोटो अपलोड करें (वैकल्पिक):", 
        type=["png", "jpg", "jpeg"]
    )
    aspect_ratio = st.selectbox(
        "5. 📐 वीडियो साइज़ चुनें:",
        ["16:9 (YouTube Landscape)", "9:16 (Shorts / Reels Portrait)", "1:1 (Square)"]
    )

if custom_img:
    st.image(custom_img, caption="✅ अपलोड की गई फोटो", width=200)

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural"
}

async def generate_voice(text, voice_code, out_path):
    import edge_tts
    comm = edge_tts.Communicate(text, voice_code)
    await comm.save(out_path)

def generate_ai_character_image(prompt_text, save_path):
    """अगर यूजर फोटो न दे तो AI से साफ़ फ्रंट-फेसिंग कैरेक्टर इमेज बनाना"""
    clean_prompt = f"{prompt_text}, front-facing portrait, looking at camera, clear face and eyes, high quality"
    encoded_prompt = urllib.parse.quote(clean_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true&seed=42"
    
    response = requests.get(image_url, timeout=30)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    return False

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
        return clip.resize((1280, 720))
    elif ratio_type == "9:16 (Shorts / Reels Portrait)":
        return clip.resize((720, 1280))
    else:
        return clip.resize((720, 720))

if st.button("🚀 Generate Complete 3D Lip-Sync Video", type="primary", use_container_width=True):
    if not kaggle_url:
        st.error("❌ Kaggle बैकएंड कनेक्ट नहीं है!")
    elif not story_text.strip():
        st.error("❌ कृपया कहानी दर्ज करें!")
    else:
        status = st.status("🎬 वीडियो प्रोडक्शन शुरू हो रहा है...", expanded=True)
        os.makedirs("temp_render/scenes", exist_ok=True)

        saved_img_path = os.path.abspath("temp_render/character_input.png")
        
        # 1. इमेज चेक / ऑटो-जनरेशन
        if custom_img:
            status.write("🖼️ आपकी अपलोड की गई फोटो का इस्तेमाल हो रहा है...")
            with open(saved_img_path, "wb") as f:
                f.write(custom_img.getbuffer())
        else:
            status.write("🎨 फोटो नहीं मिली — AI नया कैरेक्टर बना रहा है...")
            success = generate_ai_character_image(char_desc, saved_img_path)
            if not success:
                st.error("❌ कैरेक्टर इमेज नहीं बन पाई!")
                st.stop()
            st.image(saved_img_path, caption="✨ AI द्वारा बनाया गया कैरेक्टर", width=200)

        sentences = [s.strip() for s in re.split(r'[।\n\.]+', story_text) if len(s.strip()) > 3]
        total = len(sentences)
        scene_clips = []

        for idx, sentence in enumerate(sentences):
            status.write(f"🎙️ **सीन {idx+1}/{total}:** आवाज़ रिकॉर्ड हो रही है...")
            audio_path = os.path.abspath(f"temp_render/scenes/audio_{idx}.mp3")
            asyncio.run(generate_voice(sentence, VOICE_MAP[voice], audio_path))

            status.write(f"👄 **सीन {idx+1}/{total}:** AI लिप-सिंक रेंडर कर रहा है...")
            try:
                client = Client(kaggle_url)
                video_res = client.predict(
                    handle_file(saved_img_path),
                    handle_file(audio_path),
                    api_name="/predict"
                )
                
                real_path = extract_valid_path(video_res)
                
                if real_path and os.path.exists(real_path):
                    clip = VideoFileClip(real_path)
                    clip = resize_to_ratio(clip, aspect_ratio)
                    scene_clips.append(clip)
                else:
                    status.write(f"⚠️ सीन {idx+1} फ़ाइल नहीं मिली: {real_path}")
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
