# server/agents.py
import random
import os
import base64
import requests

def agent_analyze_video(video_path):
    print(f"[DEBUG] Received video at {video_path} for analysis")
    mock_response = {
        "cars_involved": random.choice([1, 2, 3]),
        "damages": random.choice([["popped tire"], ["front collision"], ["side body damage"], ["broken glass"]]),
        "severity": random.choice(["minor", "major", "severe"])
    }
    print("[DEBUG] Mock video analysis:", mock_response)
    return mock_response

def agent_analyze_text(text_input):
    print(f"[DEBUG] Text received: {text_input}")
    return {"note": text_input}

def agent_decision_maker(video_analysis, text_analysis):
    print(f"[DEBUG] Decision making with video={video_analysis}, text={text_analysis}")
    return {"advice": "Example advice based on mock analysis."}

def agent_location_search(query, location):
    print(f"[DEBUG] Location search for '{query}' near {location}")
    return {"shops": ["Tow Truck A - 1 mile", "Repair Shop B - 2 miles"]}

def agent_transcribe_audio(audio_path):
    """Transcribe audio using Gemini API"""
    print(f"[DEBUG] Transcribing audio at {audio_path}")
    
    # Check if we should use real Gemini API
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return transcribe_with_gemini_api(audio_path, api_key)
    else:
        # Mock transcription for testing
        mock_transcriptions = [
            "I just had a minor accident on 5th Street. My front bumper is dented but everyone is okay.",
            "There was a collision at the intersection. No injuries but my car won't start.",
            "I hit a pothole and now my tire is flat. I'm on the side of Highway 95.",
            "Fender bender in the parking lot. The other driver was very apologetic.",
            "Ice caused me to slide into a mailbox. Minor damage to the passenger side."
        ]
        transcription = random.choice(mock_transcriptions)
        print(f"[DEBUG] Mock transcription: {transcription}")
        return transcription

def transcribe_with_gemini_api(audio_path, api_key):
    """Real Gemini API transcription"""
    try:
        # Read and encode audio file
        with open(audio_path, "rb") as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
        
        # Determine MIME type
        if audio_path.endswith('.webm'):
            mime_type = "audio/webm"
        elif audio_path.endswith('.mp3'):
            mime_type = "audio/mp3"
        elif audio_path.endswith('.wav'):
            mime_type = "audio/wav"
        else:
            mime_type = "audio/webm"
        
        # API request
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Please transcribe this audio clearly and accurately:"},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": audio_data
                        }
                    }
                ]
            }]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            transcription = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"[DEBUG] Gemini transcription: {transcription}")
            return transcription.strip()
        else:
            print(f"[ERROR] Gemini API error: {response.status_code}")
            return "Error: Could not transcribe audio"
            
    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        return "Error: Transcription failed"