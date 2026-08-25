import streamlit as st
import requests
import asyncio
import os
import re
import urllib.parse
from PIL import Image, ImageDraw, ImageFont

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
st.caption("Google Flow आर्किटेक्चर — अल्ट्रा फ़ास्ट रेंडरिंग एवं जीरो टाइमआउट")

st.markdown("---")

col1, col2 = st.columns([1.2, 1])

with col1:
    story_text = st.text_area(
        "1. 📝 पूरी कहानी दर्ज करें:", 
        height=180, 
        placeholder="एक प्राचीन जादुई जंगल के बीच बादलों से बातें करता एक सुंदर सोने का महल था।\nमहल के दरवाज़े पर नीले पंखों वाला एक नन्हा जादुई ड्रैगन उड़ रहा था।\nअचानक आसमान में तारों की चमकती हुई बारिश होने लगी और पूरा जंगल रोशन हो गया।"
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

def create_fallback_art(prompt, out_path, target_w, target_h):
    """सर्वर धीमा होने पर बैकअप हाई-क्वालिटी बैकग्राउंड तैयार करना"""
    img = Image.new('RGB', (target_w, target_h), color=(20, 24, 40))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (target_w - 20, target_h - 20)], outline=(100, 150, 255), width=4)
    img.save(out_path)
    return True

def generate_scene_art(prompt, style, out_path, seed, target_w, target_h):
    """जीरो-टाइमआउट और बैकअप इंजन के साथ इमेज जनरेटर"""
    clean_prompt = f"{style}, highly detailed, cinematic lighting, {prompt}, vibrant colors, 4k wallpaper"
    enc = urllib.parse.quote(clean_prompt)
    
    # 1. पहला प्रयास: Turbo मॉडल (सुपर फास्ट, 5-8 सेकंड)
    url_turbo = f"https://image.pollinations.ai/prompt/{enc}?width={target_w}&height={target_h}&nologo=true&seed={seed}&model=turbo"
    try:
        res = requests.get(url_turbo, timeout=18)
        if res.status_code == 200 and len(res.content) > 1000:
            with open(out_path, "wb") as f:
                f.write(res.content)
            return True
    except Exception:
        pass

    # 2. दूसरा बैकअप: स्टैंडर्ड इंजन
    url_standard = f"https://image.pollinations.ai/prompt/{enc}?width={target_w}&height={target_h}&nologo=true&seed={seed}"
    try:
        res = requests.get(url_standard, timeout=18)
        if res.status_code == 200 and len(res.content) > 1000:
            with open(out_path, "wb") as f:
                f.write(res.content)
            return True
    except Exception:
        pass

    # 3. तीसरा बैकअप: लोकल कैनवास (कभी क्रैश नहीं होने देगा)
    return create_fallback_art(prompt, out_path, target_w, target_h)

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
            status.write(f"🎙️ **सीन {idx+1}/{total}:** आवाज़ तैयार हो रही है...")
            audio_path = f"temp_render/scenes/audio_{idx}.mp3"
            asyncio.run(generate_voice(sentence, VOICE_MAP[voice], audio_path))
            
            audio_clip = AudioFileClip(audio_path)
            dur = audio_clip.duration + 0.3

            status.write(f"🎨 **सीन {idx+1}/{total}:** 8K विज़ुअल्स और मोशन रेंडर हो रहा है...")
            img_path = f"temp_render/scenes/art_{idx}.png"
            seed_val = 100 + idx * 43
            
            generate_scene_art(sentence, visual_style, img_path, seed_val, target_w, target_h)
            
            # सिनेमैटिक कैमरा मोशन
            img_clip = ImageClip(img_path).set_duration(dur)
            img_clip = img_clip.resize((target_w, target_h))
            
            zoomed = img_clip.resize(lambda t: 1 + 0.04 * (t / dur)).set_position(('center', 'center'))
            final_scene = CompositeVideoClip([zoomed], size=(target_w, target_h)).set_duration(dur)
            final_scene = final_scene.set_audio(audio_clip)
            
            scene_clips.append(final_scene)

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
