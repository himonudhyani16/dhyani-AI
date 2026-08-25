import asyncio
import os
import re
import requests
import streamlit as st
from PIL import Image
import fal_client

st.set_page_config(
    page_title="AI Story & Talking Character Video",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Story & Talking Character Video")
st.write("कहानी लिखें, Character Photo दें और talking video बनाएं।")

story_input = st.text_area(
    "1. 📝 पूरी कहानी / स्क्रिप्ट:",
    height=180,
    placeholder="यहाँ कहानी लिखें..."
)

ratio_input = st.selectbox(
    "2. 📐 वीडियो फॉर्मेट",
    ["16:9 (YouTube Video)", "9:16 (Shorts / Reels)"]
)

character_file = st.file_uploader(
    "3. 🧑 Character Photo",
    type=["png", "jpg", "jpeg", "webp"]
)

voice_input = st.selectbox(
    "4. 🎙️ Voice",
    [
        "Natural Male (Madhur - कथावाचक)",
        "Natural Female (Swara - स्पष्ट)"
    ]
)

VOICE_MAP = {
    "Natural Male (Madhur - कथावाचक)": "hi-IN-MadhurNeural",
    "Natural Female (Swara - स्पष्ट)": "hi-IN-SwaraNeural",
}


async def generate_voice(text, voice_code, output_path):
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice_code
    )

    await communicate.save(output_path)


def upload_file(path):
    return fal_client.upload_file(path)


def make_talking_video(image_url, audio_url):
    result = fal_client.subscribe(
        "fal-ai/sync-lipsync/v3/image-to-video",
        arguments={
            "image_url": image_url,
            "audio_url": audio_url
        }
    )

    return result["video"]["url"]


def download_file(url, path):
    response = requests.get(url, timeout=180)
    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)


if st.button(
    "🚀 Generate Talking Video",
    type="primary",
    use_container_width=True
):

    if not story_input.strip():
        st.error("कृपया कहानी लिखें।")
        st.stop()

    if character_file is None:
        st.error("कृपया Character Photo upload करें।")
        st.stop()

    if not os.environ.get("FAL_KEY"):
        st.error("FAL_KEY सेट नहीं है।")
        st.stop()

    os.makedirs("temp_render", exist_ok=True)

    character_path = "temp_render/character.png"

    character = Image.open(character_file).convert("RGB")
    character.save(character_path)

    st.image(
        character,
        caption="Character Reference",
        width=300
    )

    sentences = [
        s.strip()
        for s in re.split(r"[।\n.!?]+", story_input)
        if len(s.strip()) > 3
    ]

    if not sentences:
        st.error("कहानी बहुत छोटी है।")
        st.stop()

    voice_code = VOICE_MAP[voice_input]

    progress = st.progress(0)

    character_url = upload_file(character_path)

    generated_videos = []

    total = len(sentences)

    for idx, sentence in enumerate(sentences):

        st.write(
            f"🎬 Scene {idx + 1}/{total}: {sentence}"
        )

        audio_path = (
            f"temp_render/audio_{idx}.mp3"
        )

        asyncio.run(
            generate_voice(
                sentence,
                voice_code,
                audio_path
            )
        )

        audio_url = upload_file(audio_path)

        with st.spinner(
            f"Character बोल रहा है... Scene {idx + 1}"
        ):

            try:
                video_url = make_talking_video(
                    character_url,
                    audio_url
                )

                video_path = (
                    f"temp_render/scene_{idx}.mp4"
                )

                download_file(
                    video_url,
                    video_path
                )

                generated_videos.append(
                    video_path
                )

            except Exception as e:
                st.error(
                    f"Scene {idx + 1} में error: {e}"
                )
                st.stop()

        progress.progress(
            (idx + 1) / total
        )

    st.write("🎞️ Final video तैयार हो रही है...")

    from moviepy import (
        VideoFileClip,
        concatenate_videoclips
    )

    clips = [
        VideoFileClip(path)
        for path in generated_videos
    ]

    final_video = concatenate_videoclips(
        clips,
        method="compose"
    )

    final_output = (
        "temp_render/final_story.mp4"
    )

    final_video.write_videofile(
        final_output,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    for clip in clips:
        clip.close()

    final_video.close()

    st.success("✅ Talking Character Video तैयार है!")

    st.video(final_output)

    with open(final_output, "rb") as f:
        st.download_button(
            "📥 Download Video",
            f,
            file_name="talking_character_video.mp4",
            mime="video/mp4",
            use_container_width=True
        )
