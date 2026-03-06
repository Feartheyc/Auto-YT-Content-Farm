import os
import json
import random
import asyncio
import urllib.parse
import urllib.request
import time
from gtts import gTTS 
from dotenv import load_dotenv 
from google import genai
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip, TextClip, afx

# --- Security Setup ---
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

# --- NEW: ADVANCED VIDEO FX FUNCTIONS ---

def create_text_overlay(text, duration, width):
    """Creates a bold 'Hook' title for the top of the video."""
    # Using a simple color clip + text overlay for high compatibility
    return TextClip(
        text=text.upper(),
        font_size=70,
        color='white',
        method='caption',
        size=(width * 0.8, None),
        text_align='center',
        stroke_color='black',
        stroke_width=2
    ).with_duration(duration).with_position(('center', 200))

def create_progress_bar(duration, width, height=10):
    """Creates a growing progress bar at the bottom of the screen."""
    bar = ColorClip(size=(width, height), color=(255, 0, 0)) # Red bar
    # Animate the bar width from 0 to 100%
    return bar.with_duration(duration).with_position(('left', 'bottom')).map_effects(
        lambda clip: clip.resized(lambda t: [max(1, int(width * (t/duration))), height])
    )

def assemble_pro_montage(audio_path, video_paths, metadata, output_filename="final_video.mp4"):
    print(f"🎬 Rendering PRO montage with Overlays & Branding...")
    audio_clip = AudioFileClip(audio_path)
    target_w, target_h = 1080, 1920
    
    loaded_clips = []
    for p in video_paths:
        try:
            clip = VideoFileClip(p).without_audio()
            factor = max(target_w / clip.w, target_h / clip.h)
            clip = clip.resized(factor).cropped(
                x_center=clip.w*factor/2, y_center=clip.h*factor/2, 
                width=target_w, height=target_h
            )
            loaded_clips.append(clip)
        except: continue

    main_video = concatenate_videoclips(loaded_clips, method="compose")
    if main_video.duration < audio_clip.duration:
        main_video = concatenate_videoclips([main_video] * (int(audio_clip.duration // main_video.duration) + 1))
    main_video = main_video.subclipped(0, audio_clip.duration)

    # 1. Add Hook Title (First 5 seconds)
    hook_text = metadata['title']
    title_overlay = create_text_overlay(hook_text, 5, target_w)

    # 2. Add Branding (@Feartheyc)
    branding = TextClip(
        text="@Feartheyc", font_size=40, color='white', opacity=0.6
    ).with_duration(main_video.duration).with_position(('center', 1700))

    # 3. Add Progress Bar
    p_bar = create_progress_bar(main_video.duration, target_w)

    # 4. Mix Background Music (If you have a music.mp3 in root)
    final_audio = audio_clip
    if os.path.exists("background_music.mp3"):
        bg_music = AudioFileClip("background_music.mp3").with_effects([afx.AudioVolumex(0.1)]) # 10% volume
        bg_music = bg_music.subclipped(0, audio_clip.duration)
        from moviepy.audio.AudioClip import CompositeAudioClip
        final_audio = CompositeAudioClip([audio_clip, bg_music])

    # Combine everything
    final_video = CompositeVideoClip([main_video, title_overlay, branding, p_bar]).with_audio(final_audio)
    
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
    
    # Cleanup
    final_video.close(); main_video.close(); audio_clip.close()
    for c in loaded_clips: c.close()
    time.sleep(2)
    for p in video_paths: os.remove(p)

# --- (Rest of your generate_full_package and upload logic remains the same) ---
