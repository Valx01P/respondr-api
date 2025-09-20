from fastapi import FastAPI, UploadFile, Form
import shutil, os
from agents import (
    agent_analyze_video,
    agent_analyze_text,
    agent_decision_maker,
    agent_location_search
)

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Respondr backend running"}

@app.post("/analyze")
async def analyze(video: UploadFile, note: str = Form("")):
    # Save video temporarily
    save_path = f"uploads/{video.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # Run through placeholder agents
    video_analysis = agent_analyze_video(save_path)
    text_analysis = agent_analyze_text(note)
    decision = agent_decision_maker(video_analysis, text_analysis)
    location_info = agent_location_search("tow truck", "Miami")  # hardcoded for now

    return {
        "video_analysis": video_analysis,
        "text_analysis": text_analysis,
        "decision": decision,
        "location_info": location_info,
    }
