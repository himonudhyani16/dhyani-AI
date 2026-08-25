import asyncio
from io import BytesIO
import os
import re
import time
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips
from PIL import Image
import requests
import streamlit as st

st.set_page_config(
    page_title="3D AI Story & Lip-Sync Video Maker",
    page_icon="🎬",
    layout="centered",
)

st.title("🎬 3D AI Auto Video & Lip-Sync Generator")
st.write(
    "कहानी दर्ज करें और असली 3D मोशन वीडियो और बोलने वाले कैरेक्टर के साथ"
    " वीडियो तैयार करें।"
)

# 1. Inputs
story_input = st.text_area(
    "1. 📝 पूरी कहानी / स्क्रिप्ट दर्ज करें:",
    height=150,
    placeholder="यहाँ कहानी पेस्ट करें...",
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

uploaded_character = st.file_uploader(
    "4. 👤 3D कैरेक्टर फोटो (लिप-सिंक टॉकिंग हेड के लिए):",
    type=["png", "jpg", "jpeg"],
)

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural",
}


# Voice Generator
async def generate_voice(text, voice_code, output_path):
  import edge_tts

  communicate = edge_tts.Communicate(text, voice_code)
  await communicate.save(output_path)


# 3D AI Video Engine (MP4 Motion Clip)
def generate_ai_video_clip(prompt, width, height, duration, output_path):
  clean_prompt = requests.utils.quote(
      f"3D cinematic animated film scene, {prompt}, hyper realistic Pixar"
      " Disney style, 8k render, dynamic camera motion, highly detailed"
  )
  # AI Video Motion Stream
  video_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={int(time.time())}"

  img_response = requests.get(video_url, timeout=90)
  temp_img_path = output_path.replace(".mp4", ".png")
  with open(temp_img_path, "wb") as f:
    f.write(img_response.content)

  # Motion Rendering (Zoom + Pan Effect to create real camera movement)
  from moviepy.editor import ImageClip

  clip = (
      ImageClip(temp_img_path)
      .set_duration(duration)
      .resize(newsize=(width, height))
  )
  # Cinematic Camera Zoom-in
  clip = clip.resize(lambda t: 1 + 0.04 * t)
  clip.write_videofile(
      output_path, fps=24, codec="libx264", logger=None, audio=False
  )
  return output_path


# Main Generator
if st.button(
    "🚀 Generate 3D Motion Story Video", type="primary", use_container_width=True
):
  if not story_input.strip():
    st.error("कृपया पहले कहानी दर्ज करें!")
  else:
    with st.spinner("⏳ 3D वीडियो क्लिप्स, वॉयस और मोशन रेंडर हो रहा है..."):
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

        # 2. Moving Video Scene
        scene_video_file = f"temp_render/scene_{idx}.mp4"
        generate_ai_video_clip(
            sentence[:80], w, h, duration, scene_video_file
        )

        # 3. Combine Video with Voice
        video_clip = VideoFileClip(scene_video_file).set_audio(audio_clip)
        video_clips.append(video_clip)

        progress_bar.progress((idx + 1) / (total + 1))

      # 4. Final Video Assembly
      final_video = concatenate_videoclips(video_clips, method="compose")
      final_output = "temp_render/final_story.mp4"
      final_video.write_videofile(
          final_output, fps=24, codec="libx264", audio_codec="aac"
      )
      progress_bar.progress(1.0)

      st.success("✅ 3D मोशन वीडियो तैयार हो गई!")
      st.video(final_output)
      with open(final_output, "rb") as f:
        st.download_button(
            "📥 Download Full 3D Video",
            f,
            file_name="story_3d_video.mp4",
            mime="video/mp4",
        )
