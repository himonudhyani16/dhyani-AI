import streamlit as st
import asyncio
import edge_tts
import os
import re
import requests
from io import BytesIO
from PIL import Image
import moviepy.editor as mp

st.set_page_config(page_title="24/7 AI Story Video Maker", page_icon="🎬", layout="centered")

st.title("🎬 24/7 AI Auto Story Video Generator")
st.write("अपनी कहानी लिखें और तुरंत पूरी वीडियो तैयार करें।")

story_input = st.text_area("1. 📝 अपनी पूरी कहानी / स्क्रिप्ट यहाँ पेस्ट करें:", height=150, placeholder="यहाँ अपनी कहानी लिखें...")

col1, col2 = st.columns(2)
with col1:
    ratio_input = st.selectbox("2. 📐 वीडियो का अनुपात (Ratio)", ["16:9 (YouTube Video)", "9:16 (Shorts / Reels)", "1:1 (Square)"])
with col2:
    timer_input = st.slider("3. ⏱️ सीन की अवधि (Timer - 0 = ऑटो वॉयस अनुसार)", min_value=0, max_value=15, value=0)

col3, col4 = st.columns(2)
with col3:
    uploaded_img = st.file_uploader("4. 🖼️ कैरेक्टर फोटो (Optional)", type=["png", "jpg", "jpeg"])
with col4:
    voice_input = st.selectbox("5. 🎙️ वॉयस चुनें", ["Natural Male (Madhur - कथावाचक)", "Natural Female (Swara - स्पष्ट)"])

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural"
}

async def generate_voice(text, voice_code, output_path):
    communicate = edge_tts.Communicate(text, voice_code)
    await communicate.save(output_path)

def get_ai_image(prompt, width, height):
    clean_prompt = requests.utils.quote(f"3D mythological cinematic animated scene, {prompt}, 8k highly detailed Disney Pixar aesthetic")
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&nologo=true"
    response = requests.get(url, timeout=30)
    return Image.open(BytesIO(response.content))

if st.button("🚀 Generate Full Video", type="primary", use_container_width=True):
    if not story_input.strip():
        st.error("कृपया पहले कहानी दर्ज करें!")
    else:
        with st.spinner("⏳ AI वीडियो तैयार कर रहा है..."):
            os.makedirs("temp_files", exist_ok=True)
            sentences = [s.strip() for s in re.split(r'[।\n\.]+', story_input) if len(s.strip()) > 3]
            voice_code = VOICE_MAP[voice_input]
            w, h = (1280, 720) if "16:9" in ratio_input else (720, 1280) if "9:16" in ratio_input else (720, 720)
            video_clips = []
            
            for idx, sentence in enumerate(sentences):
                audio_path = f"temp_files/audio_{idx}.mp3"
                asyncio.run(generate_voice(sentence, voice_code, audio_path))
                audio_clip = mp.AudioFileClip(audio_path)
                duration = max(float(timer_input), audio_clip.duration) if timer_input > 0 else audio_clip.duration
                
                img_path = f"temp_files/img_{idx}.png"
                if uploaded_img is not None and idx == 0:
                    user_image = Image.open(uploaded_img)
                    user_image.save(img_path)
                else:
                    img = get_ai_image(sentence[:60], w, h)
                    img.save(img_path)
                
                img_clip = mp.ImageClip(img_path).set_duration(duration).resize(newsize=(w, h))
                clip = img_clip.set_audio(audio_clip.set_duration(duration))
                video_clips.append(clip)
                
            final_video = mp.concatenate_videoclips(video_clips, method="compose")
            output_path = "temp_files/final_output.mp4"
            final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
            
            st.success("✅ वीडियो तैयार हो गई!")
            st.video(output_path)
            with open(output_path, "rb") as f:
                st.download_button("📥 Download Video", f, file_name="story_video.mp4", mime="video/mp4")
