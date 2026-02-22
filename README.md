# 🚀 Auto‑YT‑Content‑Farm

AI-powered automation tool to generate YouTube Shorts from a single
topic idea.

------------------------------------------------------------------------

## 🧠 Overview

Auto‑YT‑Content‑Farm automatically:

1.  Generates a script using AI (Gemini)
2.  Extracts scene keywords
3.  Downloads relevant stock clips (Pexels API)
4.  Generates voiceover using Edge TTS
5.  Stitches everything into a 45-second Short using MoviePy
6.  (Optional) Uploads directly to YouTube via YouTube API

------------------------------------------------------------------------

## ✨ Features

-   🤖 AI Script & Keyword Generation\
-   🎥 Automatic Stock Video Fetching\
-   🎙 AI Voiceover Creation\
-   🎬 Smart Video Montage Creation\
-   📤 Optional Direct YouTube Upload

------------------------------------------------------------------------

## 📁 Project Structure

Auto‑YT‑Content‑Farm/ ├── generator.py\
├── requirements.txt\
├── background.png\
├── .gitignore\
└── README.md

------------------------------------------------------------------------

## 🛠 Requirements

-   Python 3.10+
-   Gemini API Key
-   Pexels API Key
-   YouTube API Credentials (optional)

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## 🔑 Environment Setup

Set your API keys:

Linux/macOS:

``` bash
export GEMINI_API_KEY="your_key"
export PEXELS_API_KEY="your_key"
```

Windows (PowerShell):

``` powershell
setx GEMINI_API_KEY "your_key"
setx PEXELS_API_KEY "your_key"
```

------------------------------------------------------------------------

## ▶ Usage

Edit the topic inside `generator.py`:

``` python
my_topic = "Funny cat stories"
```

Run:

``` bash
python generator.py
```

If YouTube credentials are configured, the video will upload
automatically as private.

------------------------------------------------------------------------

## ⚠ Notes

-   Respect API rate limits
-   Do not commit API keys
-   This is experimental automation
