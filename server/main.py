# server/main.py
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import shutil, os
from agents import (
    agent_analyze_video,
    agent_analyze_text,
    agent_decision_maker,
    agent_location_search,
    agent_transcribe_audio
)

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Respondr backend running with Gemini STT"}

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile):
    """Transcribe audio using Gemini"""
    save_path = f"uploads/audio_{audio.filename}"
    os.makedirs("uploads", exist_ok=True)
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    
    transcription = agent_transcribe_audio(save_path)
    
    return {"transcription": transcription}

@app.post("/analyze")
async def analyze(video: UploadFile, note: str = Form("")):
    # Save video temporarily
    save_path = f"uploads/{video.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    # Run through agents
    video_analysis = agent_analyze_video(save_path)
    text_analysis = agent_analyze_text(note)
    decision = agent_decision_maker(video_analysis, text_analysis)
    location_info = agent_location_search("tow truck", "Miami")
    
    return {
        "video_analysis": video_analysis,
        "text_analysis": text_analysis,
        "decision": decision,
        "location_info": location_info,
    }