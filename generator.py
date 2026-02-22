import os
import asyncio
import urllib.parse
import urllib.request
import edge_tts
from google import genai
from moviepy import ImageClip, AudioFileClip # <-- FIXED THIS LINE

# --- 1. API Keys ---
# Generate a NEW key and paste it here
os.environ["GEMINI_API_KEY"] = "AIzaSyDx-8YsH98grAF9ttdqAr47L8Oe6HntoKk"
client = genai.Client()

def generate_script_and_prompt(topic):
    """Stage 1: Gemini 2.5 Flash writes the narration and a vertical image prompt."""
    print(f"🧠 Writing script and image prompt for: {topic}...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"You are a video producer. For the topic '{topic}', write a 2-sentence narration script for a YouTube Short. Then, on a new line, write 'PROMPT:' followed by a highly detailed, 9:16 portrait aspect ratio image generation prompt that perfectly matches the narration."
    )
    
    text_blocks = response.text.split("PROMPT:")
    script = text_blocks[0].strip()
    image_prompt = text_blocks[1].strip() if len(text_blocks) > 1 else "A beautiful cinematic scene, vertical orientation"
    
    print(f"\n📝 Script: {script}")
    print(f"🎨 Image Prompt: {image_prompt}\n")
    return script, image_prompt

def generate_image(prompt, output_filename="background.png"):
    """Temporary Stage 2: Grabs a random 9:16 placeholder image to test the pipeline."""
    print("🎨 Grabs a random placeholder image to keep the build moving...")
    
    # Random 720x1280 image
    url = "https://picsum.photos/720/1280"
    
    try:
        urllib.request.urlretrieve(url, output_filename)
        print(f"✅ Placeholder saved as {output_filename}")
        return output_filename
    except Exception as e:
        print(f"❌ Failed to grab placeholder: {e}")
        return None
async def generate_audio(text, output_filename="voiceover.mp3"):
    """Stage 3: edge-tts generates a highly realistic, free voiceover locally."""
    print("🎙️ Generating free voiceover...")
    
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_filename)
    
    print(f"✅ Voiceover saved as {output_filename}")
    return output_filename

def assemble_video(audio_path, image_path, output_filename="final_video.mp4"):
    """Stage 4: MoviePy stitches the vertical image over the audio track."""
    print("🎬 Assembling the final vertical video...")
    
    audio_clip = AudioFileClip(audio_path)
    
    image_clip = ImageClip(image_path).with_duration(audio_clip.duration)
    final_clip = image_clip.with_audio(audio_clip)
    
    # The crucial fix: explicitly define the temp audio file as .m4a
    final_clip.write_videofile(
        output_filename, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        temp_audiofile="temp-audio.m4a", # Forces FFmpeg to use the correct audio container
        remove_temp=True, # Cleans up the temp file after rendering is done
        logger=None
    )
    print(f"\n🎉 Success! Final video rendered as {output_filename}")

async def main():
    # --- 2. Execution ---
    test_topic = "Funny tiktok skits"
    
    script, img_prompt = generate_script_and_prompt(test_topic)
    image_file = generate_image(img_prompt)
    audio_file = await generate_audio(script)
    
    if image_file and audio_file:
        assemble_video(audio_file, image_file)

if __name__ == "__main__":
    asyncio.run(main())