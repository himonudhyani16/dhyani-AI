import streamlit as st
import asyncio
import os
import re
import urllib.parse
from PIL import Image
from gradio_client import Client, handle_file
import edge_tts
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips

st.set_page_config(page_title="ध्यानी AI — 3D Motion Studio", page_icon="🎬", layout="wide")
st.title("🎬 ध्यानी AI — 3D Motion Story Studio")
st.caption("Kaggle SVD Engine Powered | True 3D Motion Video")
st.markdown("---")

# 🔗 यहाँ है Kaggle URL डालने का बॉक्स (सबसे ऊपर)
kaggle_url = st.text_input("🔗 Kaggle Public URL (उदा. https://xxxx.gradio.live):", placeholder="https://xxxx.gradio.live")

col1, col2 = st.columns([1.2, 1])
with col1:
    story_text = st.text_area(
        "1. 📝 कहानी लिखें:", 
        height=160, 
        placeholder="एक घने जंगल में छोटा भालू सैर कर रहा था।\nअचानक उसे एक चमकता हुआ बड़ा सेब दिखाई दिया।"
    )
    voice = st.selectbox("2. 🎙️ वॉयस चुनें", ["Natural Male (Madhur)", "Natural Female (Swara)"])

with col2:
    visual_style = st.selectbox("3. 🎨 विज़ुअल स्टाइल", ["3D Pixar Animation", "8K Hyper-Realistic", "Fantasy Anime"])

VOICE_MAP = {
    "Natural Male (Madhur)": "hi-IN-MadhurNeural",
    "Natural Female (Swara)": "hi-IN-SwaraNeural"
}

def generate_base_image(prompt, style, out_path):
    enc = urllib.parse.quote(f"{style}, cinematic 3D character, {prompt}, 4k render, masterpiece")
    url = f"https://image.pollinations.ai/prompt/{enc}?width=1024&height=576&model=flux&nologo=true"
    import requests
    try:
        r = requests.get(url, timeout=35)
        if r.status_code == 200 and len(r.content) > 3000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def call_kaggle_svd(image_path, out_path, server_url):
    try:
        client = Client(server_url)
        res = client.predict(
            image=handle_file(image_path),
            motion_bucket_id=127,
            api_name="/predict"
        )
        if res and os.path.exists(res):
            import shutil
            shutil.copy(res, out_path)
            return True
    except Exception as e:
        st.write(f"⚠️ Kaggle Engine Error: {e}")
    return False

if st.button("🚀 Generate 3D Motion Video", type="primary", use_container_width=True):
    if not kaggle_url.strip():
        st.error("❌ कृपया पहले Kaggle का Gradio URL ऊपर वाले बॉक्स में डालें!")
        st.stop()
    if not story_text.strip():
        st.error("❌ कृपया कहानी लिखें!")
        st.stop()

    status = st.status("🎬 वीडियो जनरेशन प्रोसेस शुरू...", expanded=True)
    os.makedirs("temp_render/scenes", exist_ok=True)
    
    sentences = [s.strip() for s in re.split(r'[।\n\.]+', story_text) if len(s.strip()) > 3]
    scene_clips = []
    
    for idx, sentence in enumerate(sentences):
        scene_no = idx + 1
        total = len(sentences)
        
        # 1. Voice
        status.write(f"🎙️ **सीन {scene_no}/{total}:** आवाज़ बन रही है...")
        aud_path = f"temp_render/scenes/audio_{idx}.mp3"
        comm = edge_tts.Communicate(sentence, VOICE_MAP[voice])
        asyncio.run(comm.save(aud_path))
        audio_clip = AudioFileClip(aud_path)
        audio_dur = audio_clip.duration
        
        # 2. Image
        status.write(f"🎨 **सीन {scene_no}/{total}:** 3D बेस इमेज तैयार हो रही है...")
        img_path = f"temp_render/scenes/img_{idx}.png"
        img_ok = generate_base_image(sentence, visual_style, img_path)
        
        if not img_ok:
            status.write(f"⚠️ सीन {scene_no} इमेज फेल!")
            audio_clip.close()
            continue
            
        # 3. Motion via Kaggle SVD
        status.write(f"🎥 **सीन {scene_no}/{total}:** Kaggle GPU द्वारा SVD मोशन रेंडर हो रहा है...")
        vid_path = f"temp_render/scenes/vid_{idx}.mp4"
        
        success = call_kaggle_svd(img_path, vid_path, kaggle_url.strip())
        
        if success and os.path.exists(vid_path):
            v_clip = VideoFileClip(vid_path)
            if v_clip.duration < audio_dur:
                reps = int(audio_dur / v_clip.duration) + 1
                v_clip = concatenate_videoclips([v_clip] * reps)
            v_clip = v_clip.subclip(0, audio_dur).set_audio(audio_clip)
            scene_clips.append(v_clip)
            status.write(f"✅ सीन {scene_no} मोशन क्लिप तैयार!")
        else:
            status.write(f"⚠️ सीन {scene_no} वीडियो जनरेशन में समस्या आई।")
            audio_clip.close()

    if scene_clips:
        status.write("🎞️ सभी क्लिप्स को जोड़कर मास्टर मूवी बनाई जा रही है...")
        final_path = "temp_render/master_movie.mp4"
        final_video = concatenate_videoclips(scene_clips, method="compose")
        final_video.write_videofile(final_path, fps=7, codec="libx264", audio_codec="aac", logger=None)
        
        status.update(label="✅ पूरी 3D मूवी तैयार!", state="complete")
        st.success("🎉 आपकी असली 3D मोशन वीडियो तैयार है!")
        st.video(final_path)
        
        with open(final_path, "rb") as f:
            st.download_button("📥 Download Master Movie (MP4)", f, file_name="dhyani_master_film.mp4", mime="video/mp4", use_container_width=True)
    else:
        status.update(label="❌ कोई वीडियो नहीं बन सकी", state="error")
