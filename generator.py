import os
import json
import random
import asyncio
import urllib.parse
import urllib.request
import urllib.error
import edge_tts
from google import genai
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

# --- YouTube API Libraries ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# --- 1. API Keys & Scopes ---
os.environ["GEMINI_API_KEY"] = "AIzaSyBIaSHg1HJ_eDsCZ1wSyvTsUNYKvPeVuGU"
os.environ["PEXELS_API_KEY"] = "O2yUSiq8AhhBZDR2YaCEnW4MGlRrUNGocNmGU60yWNsVS8ozpPScSUXs"

client = genai.Client()
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_content_and_keywords(topic):
    """Stage 1: Gemini provides the script and a list of keywords for multiple scenes."""
    print(f"🧠 Engineering montage visuals for: {topic}...")
    
    prompt = (
        f"Write a 45-second narration script for a YouTube Short about '{topic}'. "
        "After the script, provide 5 unique 'SEARCH_KEYWORDS' for different scenes. "
        "Format: [SCRIPT] ... [KEYWORDS] term1, term2, term3, term4, term5"
    )
    
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    full_text = response.text.strip()
    
    if "[KEYWORDS]" in full_text:
        parts = full_text.split("[KEYWORDS]")
        script = parts[0].replace("[SCRIPT]", "").strip()
        keywords = [k.strip() for k in parts[1].split(",")]
    else:
        script = full_text
        keywords = [topic, "cinematic", "action", "dark", "technology"]
        
    return script, keywords

def download_video_set(keywords):
    """Stage 2: Downloads a unique clip for each keyword provided by Gemini."""
    video_paths = []
    headers = {
        'Authorization': os.environ["PEXELS_API_KEY"],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    BANNED_WORDS = ["birthday", "cake", "party", "celebration"]

    for i, query in enumerate(keywords):
        print(f"🎥 Scouting Scene {i+1}: '{query}'...")
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&orientation=portrait&per_page=5"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                videos = data.get('videos', [])
                
                for video in videos:
                    video_tags = [tag.get('name', '').lower() for tag in video.get('tags', [])]
                    if any(bad in video_tags for bad in BANNED_WORDS):
                        continue 
                    
                    video_files = video['video_files']
                    hd_file = next((f for f in video_files if f['quality'] == 'hd'), video_files[0])
                    
                    path = f"scene_{i}.mp4"
                    dl_req = urllib.request.Request(hd_file['link'], headers={'User-Agent': headers['User-Agent']})
                    with urllib.request.urlopen(dl_req) as dl_res, open(path, 'wb') as out_file:
                        out_file.write(dl_res.read())
                    video_paths.append(path)
                    break 
        except Exception as e:
            print(f"⚠️ Scene {i+1} failed: {e}")

    return video_paths

async def generate_audio(text, output_filename="voiceover.mp3"):
    """Stage 3: Local TTS."""
    print("🎙️ Generating voiceover...")
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_filename)
    return output_filename

def assemble_montage(audio_path, video_paths, output_filename="final_video.mp4"):
    """Stage 4: Stitches multiple clips together and CLOSES them to prevent WinError 32."""
    print("🎬 Assembling the montage...")
    audio_clip = AudioFileClip(audio_path)
    
    loaded_clips = []
    for p in video_paths:
        try:
            clip = VideoFileClip(p).without_audio()
            loaded_clips.append(clip)
        except:
            continue

    if not loaded_clips:
        audio_clip.close() # Clean up even on failure
        return None

    bg_video = concatenate_videoclips(loaded_clips, method="compose")
    
    if bg_video.duration < audio_clip.duration:
        loop_count = int(audio_clip.duration // bg_video.duration) + 1
        bg_video = concatenate_videoclips([bg_video] * loop_count)

    final_clip = bg_video.subclipped(0, audio_clip.duration).with_audio(audio_clip)
    
    final_clip.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", 
                               temp_audiofile="temp-audio.m4a", remove_temp=True, logger=None)
    
    # --- CRITICAL FIX FOR WINDOWS PERMISSION ERROR ---
    print("🧹 Cleaning up media handles...")
    final_clip.close()
    audio_clip.close()
    bg_video.close()
    for clip in loaded_clips:
        clip.close()

    # Delay slightly to ensure Windows OS releases the file lock
    import time
    time.sleep(1)

    for p in video_paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            print(f"⚠️ Could not delete {p}: {e}")

def upload_to_youtube(video_path, title, description):
    """Stage 5: Final Upload."""
    if not os.path.exists('client_secret.json'): 
        print("❌ client_secret.json not found. Skipping upload.")
        return
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', YOUTUBE_SCOPES)
    credentials = flow.run_local_server(port=0)
    youtube = build('youtube', 'v3', credentials=credentials)
    body = {'snippet': {'title': title, 'description': description + "\n\n#Shorts #AI #Automation", 'categoryId': '23'},
            'status': {'privacyStatus': 'private'}}
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
    print("🚀 Montage is live on YouTube!")

async def main():
    # --- TOPIC ---
    my_topic = "Funny cat stories"
    
    script, keywords = generate_content_and_keywords(my_topic)
    video_files = download_video_set(keywords) 
    audio = await generate_audio(script)
    
    if video_files and audio:
        final_video = "final_video.mp4"
        assemble_montage(audio, video_files, final_video)
        upload_to_youtube(final_video, f"AI Story: {my_topic}", script)

if __name__ == "__main__":
    asyncio.run(main())