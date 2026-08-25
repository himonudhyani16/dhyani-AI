import asyncio
from io import BytesIO
import os
import re
from gradio_client import Client, handle_file
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image
import requests
import streamlit as st

st.set_page_config(
    page_title="ध्यानी AI — 3D Video Studio",
    page_icon="🎬",
    layout="wide",
)

# Gist ID सेट है, अब लिंक अपने आप फेच होगा
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

st.title("🎬 ध्यानी AI — Auto 3D Video Studio")

if kaggle_url:
  st.success("🟢 AI GPU Engine कनेक्टेड है!")
else:
  st.warning(
      "⚠️ Kaggle Engine कनेक्ट नहीं है। कृपया पहले Kaggle पर कोड रन करें।"
  )

st.markdown("---")

col1, col2 = st.columns([1.2, 1])

with col1:
  story_text = st.text_area(
      "1. 📝 पूरी कहानी दर्ज करें:",
      height=180,
      placeholder="एक समय की बात है, एक नटखट बालक गाँव की गलियों में घूम रहा था...",
  )
  col_a, col_b = st.columns(2)
  with col_a:
    ratio = st.selectbox(
        "2. 📐 वीडियो फॉर्मेट",
        ["16:9 Landscape (YouTube)", "9:16 Shorts (Reels)"],
    )
  with col_b:
    voice = st.selectbox(
        "3. 🎙️ कथावाचक वॉयस",
        [
            "Natural Male (Madhur - कथावाचक)",
            "Natural Female (Swara - स्पष्ट)",
        ],
    )

with col2:
  char_desc = st.text_input(
      "4. 👤 3D कैरेक्टर और स्टाइल विवरण:",
      value="Cute Indian boy, yellow kurta, peacock feather crown, 3D Pixar animation style",
  )
  custom_avatar = st.file_uploader(
      "5. 🎭 कैरेक्टर फोटो (वैकल्पिक):", type=["png", "jpg", "jpeg"]
  )

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural",
}


async def generate_voice(text, voice_code, out_path):
  import edge_tts

  comm = edge_tts.Communicate(text, voice_code)
  await comm.save(out_path)


def generate_3d_image(prompt, seed=100, w=1024, h=576):
  clean = requests.utils.quote(
      f"3D Pixar Disney animation style, {prompt}, highly detailed, 8k"
      " render, cinematic lighting"
  )
  url = f"https://image.pollinations.ai/prompt/{clean}?width={w}&height={h}&model=flux&nologo=true&seed={seed}"
  for _ in range(3):
    try:
      res = requests.get(url, timeout=60)
      if res.status_code == 200:
        return Image.open(BytesIO(res.content)).convert("RGB")
    except Exception:
      pass
  return Image.new("RGB", (w, h), color=(25, 30, 45))


def create_motion_clip(img_path, duration, w, h):
  clip = (
      ImageClip(img_path).set_duration(duration).resize(newsize=(w, h))
  )
  return clip.resize(lambda t: 1 + 0.025 * t)


if st.button(
    "🚀 Generate Complete 3D Story Video",
    type="primary",
    use_container_width=True,
):
  if not kaggle_url:
    st.error(
        "❌ Kaggle बैकएंड कनेक्ट नहीं हो सका! सुनिश्चित करें कि Kaggle चल रहा"
        " है।"
    )
  elif not story_text.strip():
    st.error("❌ कृपया पहले कहानी दर्ज करें!")
  else:
    status = st.status(
        "🎬 वीडियो प्रोडक्शन शुरू हो रहा है...", expanded=True
    )
    os.makedirs("temp_render/scenes", exist_ok=True)
    w, h = (1024, 576) if "16:9" in ratio else (576, 1024)

    status.write("👤 3D कैरेक्टर तैयार हो रहा है...")
    avatar_path = "temp_render/master_avatar.png"
    if custom_avatar:
      with open(avatar_path, "wb") as f:
        f.write(custom_avatar.getbuffer())
    else:
      avatar_img = generate_3d_image(
          f"Centered portrait of {char_desc}, looking at camera, neutral face",
          seed=42,
          w=512,
          h=512,
      )
      avatar_img.save(avatar_path)

    sentences = [
        s.strip()
        for s in re.split(r"[।\n\.]+", story_text)
        if len(s.strip()) > 3
    ]
    total = len(sentences)
    scene_clips = []

    for idx, sentence in enumerate(sentences):
      status.write(f"🎬 **सीन {idx+1}/{total}:** आवाज़ और दृश्य निर्माण...")

      audio_path = f"temp_render/scenes/audio_{idx}.mp3"
      asyncio.run(
          generate_voice(sentence, VOICE_MAP[voice], audio_path)
      )
      audio_clip = AudioFileClip(audio_path)
      dur = audio_clip.duration

      bg_img = generate_3d_image(
          f"{char_desc}, scene action: {sentence}",
          seed=100 + idx,
          w=w,
          h=h,
      )
      bg_path = f"temp_render/scenes/bg_{idx}.png"
      bg_img.save(bg_path)
      bg_clip = create_motion_clip(bg_path, dur, w, h)

      status.write(
          f"🗣️ **सीन {idx+1}:** GPU लिप-सिंक रेंडरिंग जारी है..."
      )
      try:
        client = Client(kaggle_url)
        lipsync_result = client.predict(
            source_image=handle_file(avatar_path),
            source_audio=handle_file(audio_path),
            api_name="/predict",
        )
        char_clip = (
            VideoFileClip(str(lipsync_result))
            .resize(height=int(h * 0.45))
            .set_position(("right", "bottom"))
        )
        scene_final = CompositeVideoClip([bg_clip, char_clip]).set_audio(
            audio_clip
        )
      except Exception as e:
        status.write(f"⚠️ सीन {idx+1} में बैकग्राउंड मोशन का उपयोग: {e}")
        scene_final = bg_clip.set_audio(audio_clip)

      scene_clips.append(scene_final)

    status.write("🎞️ फाइनल MP4 वीडियो तैयार किया जा रहा है...")
    final_video = concatenate_videoclips(scene_clips, method="compose")
    out_file = "temp_render/dhyani_ai_master_video.mp4"
    final_video.write_videofile(
        out_file, fps=24, codec="libx264", audio_codec="aac", logger=None
    )

    status.update(
        label="✅ 3D AI वीडियो सफलतापूर्वक तैयार!", state="complete"
    )
    st.success("🎉 आपकी 3D AI वीडियो तैयार हो गई!")
    st.video(out_file)

    with open(out_file, "rb") as f:
      st.download_button(
          "📥 Download Video (MP4)",
          f,
          file_name="dhyani_ai_video.mp4",
          mime="video/mp4",
          use_container_width=True,
      )
