import os
import json
import random
import asyncio
import urllib.parse
import urllib.request
import urllib.error
import edge_tts
import time
from google import genai
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

# --- YouTube API Libraries ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- 1. API Keys ---
# Using get() so the script works with GitHub Secrets OR local Env variables
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "AIzaSyBIaSHg1HJ_eDsCZ1wSyvTsUNYKvPeVuGU")
os.environ["PEXELS_API_KEY"] = os.getenv("PEXELS_API_KEY", "O2yUSiq8AhhBZDR2YaCEnW4MGlRrUNGocNmGU60yWNsVS8ozpPScSUXs")

client = genai.Client()
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_content_and_keywords(topic):
    print(f"🧠 Engineering visuals for: {topic}...")
    prompt = (
        f"Write a 45-second narration script for a YouTube Short about '{topic}'. "
        "After the script, provide 5 unique visual SEARCH_KEYWORDS for Pexels. "
        "Format: [SCRIPT] text [KEYWORDS] k1, k2, k3, k4, k5"
    )
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    full_text = response.text.strip()
    if "[KEYWORDS]" in full_text:
        parts = full_text.split("[KEYWORDS]")
        script = parts[0].replace("[SCRIPT]", "").strip()
        keywords = [k.strip() for k in parts[1].split(",")]
    else:
        script, keywords = full_text, ["cinematic", "dark", "action"]
    return script, keywords

def download_video_set(keywords):
    video_paths = []
    headers = {'Authorization': os.environ["PEXELS_API_KEY"], 'User-Agent': 'Mozilla/5.0'}
    BANNED_WORDS = ["birthday", "cake", "party"]
    for i, query in enumerate(keywords):
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&orientation=portrait&per_page=5"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode())
                for video in data.get('videos', []):
                    tags = [t.get('name', '').lower() for t in video.get('tags', [])]
                    if any(b in tags for b in BANNED_WORDS): continue
                    path = f"scene_{i}.mp4"
                    dl_req = urllib.request.Request(video['video_files'][0]['link'], headers=headers)
                    with urllib.request.urlopen(dl_req) as dl_res, open(path, 'wb') as f:
                        f.write(dl_res.read())
                    video_paths.append(path)
                    break
        except: continue
    return video_paths

async def generate_audio(text, output_filename="voiceover.mp3"):
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_filename)
    return output_filename

def assemble_montage(audio_path, video_paths, output_filename="final_video.mp4"):
    audio_clip = AudioFileClip(audio_path)
    loaded_clips = [VideoFileClip(p).without_audio() for p in video_paths]
    bg_video = concatenate_videoclips(loaded_clips, method="compose")
    if bg_video.duration < audio_clip.duration:
        bg_video = concatenate_videoclips([bg_video] * (int(audio_clip.duration // bg_video.duration) + 1))
    final_clip = bg_video.subclipped(0, audio_clip.duration).with_audio(audio_clip)
    final_clip.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", temp_audiofile="temp.m4a", remove_temp=True, logger=None)
    final_clip.close(); audio_clip.close(); bg_video.close()
    for c in loaded_clips: c.close()
    time.sleep(1)
    for p in video_paths:
        if os.path.exists(p): os.remove(p)

def upload_to_youtube(video_path, title, description):
    """Stage 5: Automated Upload using token.json to avoid manual login."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', YOUTUBE_SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    youtube = build('youtube', 'v3', credentials=creds)
    body = {'snippet': {'title': title, 'description': description + "\n\n#Shorts #AI #Automation"},
            'status': {'privacyStatus': 'private'}}
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
    print("🚀 Video is live on YouTube!")

async def main():
    topics = ["Why corporate life is like a heist", "The secret life of bank vaults", "How to laugh at a robbery fail"]
    my_topic = random.choice(topics) # Randomize topic for daily variety
    
    script, keywords = generate_content_and_keywords(my_topic)
    video_files = download_video_set(keywords) 
    audio = await generate_audio(script)
    if video_files and audio:
        assemble_montage(audio, video_files, "final_video.mp4")
        upload_to_youtube("final_video.mp4", f"AI Story: {my_topic}", script)

if __name__ == "__main__":
    asyncio.run(main())