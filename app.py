import streamlit as st
import requests
import asyncio
import os
import re
import urllib.parse
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import edge_tts
from moviepy.editor import (
    AudioFileClip, 
    ImageClip, 
    concatenate_videoclips, 
    CompositeVideoClip
)

st.set_page_config(page_title="ध्यानी AI — Universal Video Studio", page_icon="🎬", layout="wide")

st.title("🎬 ध्यानी AI — Universal Story & Video Studio")
st.caption("Google Flow आर्किटेक्चर पर आधारित — किसी भी विषय (जंगल, घर, शहर, अंतरिक्ष) पर फुल HD वीडियो")

st.markdown("---")

col1, col2 = st.columns([1.2, 1])

with col1:
    story_text = st.text_area(
        "1. 📝 पूरी कहानी दर्ज करें:", 
        height=180, 
        placeholder="एक घने जादुई जंगल में छोटा भालू सैर कर रहा था।\nअचानक उसे एक चमकता हुआ बड़ा महल दिखाई दिया।\nवह खुशी से दौड़ते हुए महल के अंदर चला गया।"
    )
    voice = st.selectbox("2. 🎙️ कथावाचक वॉयस", [
        "Natural Male (Madhur - कथावाचक)", 
        "Natural Female (Swara - स्पष्ट)"
    ])

with col2:
    visual_style = st.selectbox(
        "3. 🎨 विज़ुअल स्टाइल (Cinematic Style):",
        ["3D Pixar Disney Animation", "Hyper-Realistic 8K Cinematic", "Anime Studio Ghibli", "Fantasy Epic Concept Art"]
    )
    aspect_ratio = st.selectbox(
        "4. 📐 वीडियो फॉर्मेट / रेशियो:",
        ["16:9 (YouTube Landscape)", "9:16 (Shorts / Reels)", "1:1 (Square)"]
    )

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural"
}

RATIO_MAP = {
    "16:9 (YouTube Landscape)": (1280, 720),
    "9:16 (Shorts / Reels)": (720, 1280),
    "1:1 (Square)": (720, 720)
}

async def generate_voice(text, voice_code, out_path):
    comm = edge_tts.Communicate(text, voice_code)
    await comm.save(out_path)

def generate_scene_art(prompt, style, out_path, seed):
    """Google Flow स्टाइल यूनिवर्सल विज़ुअल जनरेटर"""
    full_prompt = f"{style}, cinematic masterpiece, highly detailed, vibrant colors, dynamic camera angle, {prompt}, 8k render, no blur, no text, no watermark"
    enc = urllib.parse.quote(full_prompt)
    url = f"https://image.pollinations.ai/prompt/{enc}?width=1280&height=720&nologo=true&seed={seed}&model=flux"
    
    res = requests.get(url, timeout=40)
    if res.status_code == 200:
        with open(out_path, "wb") as f:
            f.write(res.content)
        return True
    return False

if st.button("🚀 Generate Complete Cinematic Video", type="primary", use_container_width=True):
    if not story_text.strip():
        st.error("❌ कृपया पहले कहानी दर्ज करें!")
    else:
        status = st.status("🎬 यूनिवर्सल प्रोडक्शन शुरू हो रहा है...", expanded=True)
        os.makedirs("temp_render/scenes", exist_ok=True)

        target_w, target_h = RATIO_MAP[aspect_ratio]
        sentences = [s.strip() for s in re.split(r'[।\n\.]+', story_text) if len(s.strip()) > 3]
        total = len(sentences)
        scene_clips = []

        for idx, sentence in enumerate(sentences):
            status.write(f"🎙️ **सीन {idx+1}/{total}:** आवाज़ रिकॉर्ड हो रही है...")
            audio_path = f"temp_render/scenes/audio_{idx}.mp3"
            asyncio.run(generate_voice(sentence, VOICE_MAP[voice], audio_path))
            
            audio_clip = AudioFileClip(audio_path)
            dur = audio_clip.duration + 0.3 # शब्द कटने से बचाने के लिए बफर

            status.write(f"🎨 **सीन {idx+1}/{total}:** AI विज़ुअल्स और कैमरा मोशन तैयार हो रहा है...")
            img_path = f"temp_render/scenes/art_{idx}.png"
            seed_val = 100 + idx * 37
            success = generate_scene_art(sentence, visual_style, img_path, seed_val)
            
            if success:
                # स्मूथ डायनामिक कैमरा मोशन (Ken Burns Cinematic Effect)
                img_clip = ImageClip(img_path).set_duration(dur)
                img_clip = img_clip.resize((target_w, target_h))
                
                # हल्का स्मूथ ज़ूम इफ़ेक्ट (Google Flow स्टाइल)
                zoomed = img_clip.resize(lambda t: 1 + 0.04 * (t / dur)).set_position(('center', 'center'))
                final_scene = CompositeVideoClip([zoomed], size=(target_w, target_h)).set_duration(dur)
                final_scene = final_scene.set_audio(audio_clip)
                
                scene_clips.append(final_scene)
            else:
                status.write(f"⚠️ सीन {idx+1} विज़ुअल स्किप हुआ...")

        if scene_clips:
            status.write("🎞️ सभी सीन्स को जोड़कर मास्टर वीडियो तैयार हो रही है...")
            final_video = concatenate_videoclips(scene_clips, method="compose")
            out_file = "temp_render/dhyani_master_film.mp4"
            final_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", logger=None)

            status.update(label="✅ मास्टर वीडियो तैयार!", state="complete")
            st.success("🎉 आपकी सिनेमैटिक स्टोरी वीडियो पूरी तरह तैयार है!")
            st.video(out_file)
            
            with open(out_file, "rb") as f:
                st.download_button("📥 Download Film (MP4)", f, file_name="dhyani_cinematic_film.mp4", mime="video/mp4", use_container_width=True)
        else:
            status.update(label="❌ कोई सीन तैयार नहीं हुआ", state="error")
