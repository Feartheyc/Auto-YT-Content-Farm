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
# PASTE YOUR KEYS HERE
os.environ["GEMINI_API_KEY"] = "AIzaSyBIaSHg1HJ_eDsCZ1wSyvTsUNYKvPeVuGU"
os.environ["PEXELS_API_KEY"] = "O2yUSiq8AhhBZDR2YaCEnW4MGlRrUNGocNmGU60yWNsVS8ozpPScSUXs"

client = genai.Client()
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_script_and_prompt(topic):
    """Stage 1: Gemini 2.5 Flash writes a longer, engaging narration script."""
    print(f"🧠 Writing extended script for: {topic}...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"You are a video producer. For the topic '{topic}', write a highly engaging, 45-second narration script for a YouTube Short (roughly 120 words). Focus on retention. Do not include brackets or visual directions, just the spoken text."
    )
    
    script = response.text.strip()
    print(f"\n📝 Script: {script}\n")
    return script

def get_pexels_video(query, output_filename="background.mp4"):
    """Stage 2: Fetches a free, royalty-free vertical video from Pexels with anti-bot headers."""
    print(f"🎥 Searching Pexels for a vertical video about: '{query}'...")
    
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&orientation=portrait&size=medium&per_page=15"
    
    headers = {
        'Authorization': os.environ["PEXELS_API_KEY"],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            if not data.get('videos'):
                print("❌ No videos found on Pexels.")
                return None
                
            video = random.choice(data['videos'])
            video_files = video['video_files']
            hd_file = next((file for file in video_files if file['quality'] == 'hd'), video_files[0])
            download_link = hd_file['link']
            
            print("⬇️ Downloading video file securely...")
            dl_req = urllib.request.Request(download_link, headers={'User-Agent': headers['User-Agent']})
            with urllib.request.urlopen(dl_req) as dl_response, open(output_filename, 'wb') as out_file:
                out_file.write(dl_response.read())
                
            print(f"✅ Video background saved as {output_filename}")
            return output_filename
            
    except Exception as e:
        print(f"❌ Failed to fetch Pexels video: {e}")
        return None

async def generate_audio(text, output_filename="voiceover.mp3"):
    """Stage 3: edge-tts generates a realistic voiceover locally."""
    print("🎙️ Generating free voiceover...")
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_filename)
    print(f"✅ Voiceover saved as {output_filename}")
    return output_filename

def assemble_video(audio_path, video_bg_path, output_filename="final_video.mp4"):
    """Stage 4: MoviePy loops the background and stitches the audio."""
    print("🎬 Assembling the final extended vertical video...")
    
    audio_clip = AudioFileClip(audio_path)
    video_clip = VideoFileClip(video_bg_path)
    
    # LOOP LOGIC: If the voiceover is longer than the stock video, loop the video
    if audio_clip.duration > video_clip.duration:
        print("🔄 Looping background video to match audio length...")
        loop_count = int(audio_clip.duration // video_clip.duration) + 1
        video_clip = concatenate_videoclips([video_clip] * loop_count)
    
    # Trim to exact length and add audio (MoviePy v2.0 syntax)
    final_clip = video_clip.subclipped(0, audio_clip.duration).with_audio(audio_clip)
    
    final_clip.write_videofile(
        output_filename, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        temp_audiofile="temp-audio.m4a", 
        remove_temp=True, 
        logger=None
    )
    print(f"\n🎉 Success! Final video rendered as {output_filename}")

def upload_to_youtube(video_path, title, description):
    """Stage 5: Authenticate and push to your channel."""
    print("🚀 Authenticating with YouTube...")
    
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', YOUTUBE_SCOPES)
    credentials = flow.run_local_server(port=0)
    youtube = build('youtube', 'v3', credentials=credentials)

    print("📤 Uploading to YouTube Shorts...")
    body = {
        'snippet': {
            'title': title,
            'description': description + "\n\n#Shorts #Comedy #AIAutomation",
            'tags': ['funny', 'skit', 'shorts', 'automation'],
            'categoryId': '23'
        },
        'status': {
            'privacyStatus': 'private'
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    
    response = request.execute()
    print(f"\n✅ Video uploaded successfully! Video ID: {response.get('id')}")
    print(f"🔗 View it here: https://studio.youtube.com/video/{response.get('id')}/edit")

async def main():
    # --- 2. Execution ---
    test_topic = "a masked man robbing a bank but fails miserably"
    
    # 1. Write it (Now ~45 seconds)
    script = generate_script_and_prompt(test_topic)
    
    # 2. Get Visuals (using "funny office" as search term)
    bg_video_file = get_pexels_video("funny office") 
    
    # 3. Get Audio
    audio_file = await generate_audio(script)
    
    # 4. Assemble and Upload
    if bg_video_file and audio_file:
        final_video_path = "final_video.mp4"
        assemble_video(audio_file, bg_video_file, final_video_path)
        
        upload_to_youtube(
            video_path=final_video_path,
            title="AI Corporate Comedy Skit",
            description=script
        )

if __name__ == "__main__":
    asyncio.run(main())