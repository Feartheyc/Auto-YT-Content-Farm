import os
import json
import random
import asyncio
import urllib.parse
import urllib.request
import time
from gtts import gTTS # NEW: Cloud-stable TTS
from dotenv import load_dotenv 
from google import genai
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

# --- YouTube API Libraries ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- 1. Security & Environment Setup ---
load_dotenv() 

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")

if not GEMINI_KEY or not PEXELS_KEY:
    print("❌ API Keys missing! Check your .env file or GitHub Secrets.")
    exit()

client = genai.Client(api_key=GEMINI_KEY)
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_full_package(topic, visual_theme):
    """Stage 1: Gemini generates Script, Montage Keywords, and SEO Metadata."""
    print(f"🧠 Engineering content for: {topic}...")
    
    prompt = (
        f"Create a YouTube Short package about '{topic}'. Style: {visual_theme}.\n\n"
        "1. A 45-second narration script (120 words).\n"
        "2. 8 unique Pexels search keywords.\n"
        "3. A clickbaity Title.\n"
        "4. A description with a summary and 5-10 hashtags.\n"
        "5. Comma-separated SEO tags.\n\n"
        "Format EXACTLY:\n"
        "[SCRIPT] text\n"
        "[KEYWORDS] k1, k2, k3, k4, k5, k6, k7, k8\n"
        "[TITLE] title text\n"
        "[DESC] description text\n"
        "[TAGS] tag1, tag2, tag3"
    )
    
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    raw = response.text.strip()
    
    data = {'script': '', 'keywords': [], 'title': '', 'desc': '', 'tags': []}
    current_key = None
    for line in raw.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith("[SCRIPT]"): data['script'] = line.replace("[SCRIPT]", "").strip(); current_key = 'script'
        elif line.startswith("[KEYWORDS]"): data['keywords'] = [k.strip() for k in line.replace("[KEYWORDS]", "").split(",")]; current_key = 'keywords'
        elif line.startswith("[TITLE]"): data['title'] = line.replace("[TITLE]", "").strip(); current_key = 'title'
        elif line.startswith("[DESC]"): data['desc'] = line.replace("[DESC]", "").strip(); current_key = 'desc'
        elif line.startswith("[TAGS]"): data['tags'] = [t.strip() for t in line.replace("[TAGS]", "").split(",")]; current_key = 'tags'
        elif current_key: data[current_key] += " " + line

    return data

def download_video_set(keywords, visual_theme):
    """Stage 2: Downloads a high-variety set of 9:16 background clips."""
    video_paths = []
    headers = {'Authorization': PEXELS_KEY, 'User-Agent': 'Mozilla/5.0'}
    BANNED_WORDS = ["birthday", "cake", "party", "balloon"]
    
    for i, query in enumerate(keywords):
        enhanced_query = f"{query} {visual_theme} -party -birthday"
        print(f"🎥 Scouting Scene {i+1}: '{enhanced_query}'...")
        
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(enhanced_query)}&orientation=portrait&per_page=10"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode())
                valid_videos = []
                for video in data.get('videos', []):
                    tags = [t.get('name', '').lower() for t in video.get('tags', [])]
                    if any(b in tags for b in BANNED_WORDS): continue
                    valid_videos.append(video)
                
                if valid_videos:
                    selected = random.choice(valid_videos)
                    path = f"scene_{i}.mp4"
                    dl_req = urllib.request.Request(selected['video_files'][0]['link'], headers=headers)
                    with urllib.request.urlopen(dl_req) as dl_res, open(path, 'wb') as f:
                        f.write(dl_res.read())
                    video_paths.append(path)
        except: continue
    return video_paths

async def generate_audio(text, output_filename="voiceover.mp3"):
    """Stage 3: Cloud-stable TTS generation using gTTS."""
    print("🎙️ Generating voiceover (Cloud-Safe)...")
    try:
        # We use a wrapper to make the synchronous gTTS work in our async loop
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_filename)
        print(f"✅ Voiceover saved as {output_filename}")
        return output_filename
    except Exception as e:
        print(f"❌ TTS Generation failed: {e}")
        return None

def assemble_montage(audio_path, video_paths, output_filename="final_video.mp4"):
    """Stage 4: Assembles video with 1080x1920 cropping to fix black bars."""
    print(f"🎬 Rendering 1080x1920 montage with {len(video_paths)} clips...")
    audio_clip = AudioFileClip(audio_path)
    target_w, target_h = 1080, 1920
    
    loaded_clips = []
    for p in video_paths:
        try:
            clip = VideoFileClip(p).without_audio()
            factor = max(target_w / clip.w, target_h / clip.h)
            clip = clip.resized(factor).cropped(
                x_center=clip.w*factor/2, 
                y_center=clip.h*factor/2, 
                width=target_w, 
                height=target_h
            )
            loaded_clips.append(clip)
        except: continue

    if not loaded_clips: return
    bg_video = concatenate_videoclips(loaded_clips, method="compose")
    
    if bg_video.duration < audio_clip.duration:
        loop_count = int(audio_clip.duration // bg_video.duration) + 1
        bg_video = concatenate_videoclips([bg_video] * loop_count)

    final_clip = bg_video.subclipped(0, audio_clip.duration).with_audio(audio_clip)
    final_clip.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
    
    final_clip.close(); audio_clip.close(); bg_video.close()
    for c in loaded_clips: c.close()
    time.sleep(2) 
    for p in video_paths:
        try: os.remove(p)
        except: pass

def upload_to_youtube(video_path, metadata):
    """Stage 5: Automated Upload using token refresh logic."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', YOUTUBE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token: token.write(creds.to_json())
    
    youtube = build('youtube', 'v3', credentials=creds)
    body = {
        'snippet': {
            'title': metadata['title'][:100], 
            'description': metadata['desc'],
            'tags': metadata['tags'],
            'categoryId': '23'
        },
        'status': {'privacyStatus': 'private'}
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
    print(f"🚀 Published: {metadata['title']}")

async def main():
    topic = "Funny cat stories"
    style = "funny videos about cat cinematic lighting"
    
    content = generate_full_package(topic, style)
    video_files = download_video_set(content['keywords'], style) 
    audio = await generate_audio(content['script'])
    
    if video_files and audio:
        assemble_montage(audio, video_files, "final_video.mp4")
        upload_to_youtube("final_video.mp4", content)

if __name__ == "__main__":
    asyncio.run(main())