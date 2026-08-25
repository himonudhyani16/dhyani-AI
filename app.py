import asyncio
import os
import re
import requests
import streamlit as st
from PIL import Image
import fal_client

st.set_page_config(
    page_title="3D AI Story & Video Maker",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Story & Talking Character Video")
st.write("कहानी लिखें, Character Photo दें और बोलता हुआ वीडियो बनाएं।")

# -----------------------------
# INPUTS
# -----------------------------

story_input = st.text_area(
    "1. 📝 पूरी कहानी / स्क्रिप्ट:",
    height=180,
    placeholder="यहाँ अपनी कहानी लिखें..."
)

ratio_input = st.selectbox(
    "2. 📐 वीडियो फॉर्मेट",
    ["16:9 (YouTube Video)", "9:16 (Shorts / Reels)"]
)

character_file = st.file_uploader(
    "3. 🧑 Character Photo",
    type=["png", "jpg", "jpeg", "webp"],
    help="ऐसी साफ फोटो दें जिसमें character का चेहरा साफ दिखाई दे।"
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


# -----------------------------
# VOICE
# -----------------------------

async def generate_voice(text, voice_code, output_path):
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice_code
    )

    await communicate.save(output_path)


# -----------------------------
# FAL IMAGE UPLOAD
# -----------------------------

def upload_image_to_fal(image_path):
    return fal_client.upload_file(image_path)


def upload_audio_to_fal(audio_path):
    return fal_client.upload_file(audio_path)


# -----------------------------
# LIP-SYNC / TALKING VIDEO
# -----------------------------

def generate_talking_video(image_url, audio_url):

    result = fal_client.subscribe(
        "fal-ai/sync-lipsync/v3/image-to-video",
        arguments={
            "image_url": image_url,
            "audio_url": audio_url
        },
        with_logs=True
    )

    video_url = result["video"]["url"]

    return video_url


# -----------------------------
# DOWNLOAD FILE
# -----------------------------

def download_file(url, output_path):

    response = requests.get(
        url,
        timeout=180
    )

    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


# -----------------------------
# MAIN
# -----------------------------

if st.button(
    "🚀 Generate Talking Video",
    type="primary",
    use_container_width=True
):

    if not story_input.strip():
        st.error("कृपया पहले कहानी लिखें।")
        st.stop()

    if character_file is None:
        st.error("कृपया Character Photo upload करें।")
        st.stop()

    if not os.environ.get("FAL_KEY"):
        st.error(
            "FAL_KEY नहीं मिला। Streamlit Secrets में FAL_KEY जोड़ें।"
        )
        st.stop()

    os.makedirs("temp_render", exist_ok=True)

    # Character image save
    character_path = "temp_render/character.png"

    character_image = Image.open(character_file).convert("RGB")
    character_image.save(character_path)

    st.image(
        character_image,
        caption="Character Reference",
        width=300
    )

    # Story को छोटे scenes में बाँटना
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

    generated_videos = []

    # Character को एक बार upload करेंगे
    with st.spinner("Character upload हो रहा है..."):
        character_url = upload_image_to_fal(character_path)

    st.success("Character ready ✅")

    total = len(sentences)

    for idx, sentence in enumerate(sentences):

        st.write(
            f"🎬 Scene {idx + 1}/{total}: {sentence}"
        )

        # -------------------------
        # 1. Voice
        # -------------------------

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

        # -------------------------
        # 2. Upload Audio
        # -------------------------

        audio_url = upload_audio_to_fal(
            audio_path
        )

        # -------------------------
        # 3. Talking Character
        # -------------------------

        with st.spinner(
            f"Character बोल रहा है... Scene {idx + 1}"
        ):

            try:

                video_url = generate_talking_video(
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

    # -----------------------------
    # 4. JOIN ALL VIDEOS
    # -----------------------------

    st.write("🎞️ सभी scenes जोड़े जा रहे हैं...")

    try:

        from moviepy import (
            VideoFileClip,
            concatenate_videoclips
        )

        clips = []

        for video_path in generated_videos:
            clips.append(
                VideoFileClip(video_path)
            )

        final_video = concatenate_videoclips(
            clips,
            method="compose"
        )

        final_output = (
            "temp_render/final_video.mp4"
        )

        final_video.write_videofile(
            final_output,
            codec="libx264",
            audio_codec="aac"
        )

        st.success("🎉 वीडियो सफलतापूर्वक तैयार हो गया!")
        st.video(final_output)

        with open(final_output, "rb") as file:
            st.download_button(
                label="📥 Download Final Video",
                data=file,
                file_name="talking_character_video.mp4",
                mime="video/mp4",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Video merge करने में error: {e}")
