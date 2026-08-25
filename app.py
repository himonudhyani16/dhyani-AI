import asyncio
from io import BytesIO
import os
import re
import time
from PIL import Image
import requests
import streamlit as st

# MoviePy v1 और v2 दोनों के लिए सुरक्षित इम्पोर्ट
try:
  from moviepy.editor import (
      AudioFileClip,
      ImageClip,
      VideoFileClip,
      concatenate_videoclips,
  )
except Exception:
  from moviepy import (
      AudioFileClip,
      ImageClip,
      VideoFileClip,
      concatenate_videoclips,
  )

st.set_page_config(
    page_title="3D AI Story & Video Maker", page_icon="🎬", layout="centered"
)

st.title("🎬 3D AI Auto Video Generator")
st.write("कहानी दर्ज करें और 3D मोशन वीडियो तैयार करें।")

story_input = st.text_area(
    "1. 📝 पूरी कहानी / स्क्रिप्ट यहाँ पेस्ट करें:",
    height=150,
    placeholder="यहाँ कहानी लिखें...",
)

col1, col2 = st.columns(2)
with col1:
  ratio_input = st.selectbox(
      "2. 📐 वीडियो फॉर्मेट",
      ["16:9 (YouTube Video)", "9:16 (Shorts / Reels)"],
  )
with col2:
  voice_input = st.selectbox(
      "3. 🎙️ वॉयसओवर चुनें",
      [
          "Natural Male (Madhur - कथावाचक)",
          "Natural Female (Swara - स्पष्ट)",
      ],
  )

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural",
}


async def generate_voice(text, voice_code, output_path):
  import edge_tts

  communicate = edge_tts.Communicate(text, voice_code)
  await communicate.save(output_path)


def get_ai_scene_image(prompt, width, height):
  clean_prompt = requests.utils.quote(
      f"3D cinematic animated film scene, {prompt}, hyper realistic Pixar"
      " Disney style, 8k render, highly detailed"
  )
  url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&nologo=true&seed={int(time.time())}"
  for _ in range(3):
    try:
      res = requests.get(url, timeout=75)
      if res.status_code == 200:
        return Image.open(BytesIO(res.content))
    except Exception:
      time.sleep(1)
  return Image.new("RGB", (width, height), color=(20, 25, 45))


if st.button(
    "🚀 Generate 3D Motion Video", type="primary", use_container_width=True
):
  if not story_input.strip():
    st.error("कृपया पहले कहानी दर्ज करें!")
  else:
    with st.spinner("⏳ AI वीडियो, वॉयस और मोशन रेंडर हो रहा है..."):
      os.makedirs("temp_render", exist_ok=True)
      sentences = [
          s.strip()
          for s in re.split(r"[।\n\.]+", story_input)
          if len(s.strip()) > 3
      ]
      voice_code = VOICE_MAP[voice_input]
      w, h = (1280, 720) if "16:9" in ratio_input else (720, 1280)
      video_clips = []

      progress_bar = st.progress(0)
      total = len(sentences)

      for idx, sentence in enumerate(sentences):
        # 1. Voice
        audio_file = f"temp_render/audio_{idx}.mp3"
        asyncio.run(generate_voice(sentence, voice_code, audio_file))
        audio_clip = AudioFileClip(audio_file)
        duration = audio_clip.duration

        # 2. Scene Image
        img_path = f"temp_render/img_{idx}.png"
        img = get_ai_scene_image(sentence[:80], w, h)
        img.save(img_path)

        # 3. Motion Clip
        try:
          clip = (
              ImageClip(img_path).set_duration(duration).resize(newsize=(w, h))
          )
          clip = clip.resize(lambda t: 1 + 0.03 * t)
          clip = clip.set_audio(audio_clip)
        except Exception:
          clip = ImageClip(img_path).with_duration(duration).resized((w, h))
          clip = clip.with_audio(audio_clip)

        video_clips.append(clip)
        progress_bar.progress((idx + 1) / (total + 1))

      # 4. Assembly
      final_video = concatenate_videoclips(video_clips, method="compose")
      final_output = "temp_render/final_story.mp4"
      final_video.write_videofile(
          final_output, fps=24, codec="libx264", audio_codec="aac"
      )
      progress_bar.progress(1.0)

      st.success("✅ वीडियो सफलतापूर्वक तैयार हो गई!")
      st.video(final_output)
      with open(final_output, "rb") as f:
        st.download_button(
            "📥 Download Video",
            f,
            file_name="story_video.mp4",
            mime="video/mp4",
        )
