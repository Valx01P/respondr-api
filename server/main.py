# server/main.py
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import shutil, os
from typing import Dict, List, Optional
from agents import (
    agent_analyze_video,
    agent_analyze_text,
    agent_decision_maker,
    agent_location_search,
    agent_transcribe_audio,
    agent_intelligent_query_analyzer,
    generate_chat_response
)

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Simple in-memory storage for chat sessions
chat_sessions: Dict[str, List[Dict]] = {}

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
    return {"status": "ok", "message": "Respondr backend running with Enhanced AI Analysis"}

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile):
    """Transcribe audio using Gemini"""
    save_path = f"uploads/audio_{audio.filename}"
    os.makedirs("uploads", exist_ok=True)
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    
    transcription = agent_transcribe_audio(save_path)
    
    # Clean up uploaded file
    try:
        os.remove(save_path)
    except:
        pass
    
    return {"transcription": transcription}

@app.post("/analyze")
async def analyze(
    video: UploadFile, 
    note: str = Form(""),
    session_id: str = Form("new"),
    user_location: str = Form("Miami, FL")
):
    """Comprehensive accident analysis with enhanced location services"""
    
    # Save video temporarily
    save_path = f"uploads/{video.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    try:
        # Run analysis agents
        video_analysis = agent_analyze_video(save_path)
        text_analysis = agent_analyze_text(note)
        
        # Generate decision and advice FIRST
        decision = agent_decision_maker(video_analysis, text_analysis, None)
        
        # Enhanced service search based on analysis
        location_services = {}
        all_services = []
        seen_services = set()
        
        # Determine what services to search for based on decision
        search_queries = []
        location_recommendations = decision.get("location_recommendations", [])
        
        # Primary service determination based on severity and damage
        final_damages = decision.get("damages", [])
        severity = decision.get("severity", "minor")
        
        if severity == "severe":
            search_queries.extend(["hospital", "tow_truck"])
        elif any("tire" in damage.lower() for damage in final_damages):
            search_queries.extend(["tire_shop", "tow_truck"])
        elif severity == "major":
            search_queries.extend(["auto_body_shop", "tow_truck"])
        else:
            search_queries.append("mechanic")
        
        # Add services from location recommendations
        for rec in location_recommendations:
            service_type = rec["type"]
            if service_type not in search_queries:
                search_queries.append(service_type)
        
        # Search for services with enhanced data
        for query in search_queries[:4]:  # Limit to 4 searches for performance
            location_info = agent_location_search(query, user_location)
            location_services[query] = location_info
            
            # Process services with contextual reasoning
            services_with_context = location_info.get("services", [])
            for service in services_with_context[:3]:  # Top 3 per category
                service_id = f"{service.get('name', '')}-{service.get('address', '')}"
                
                if service_id not in seen_services:
                    seen_services.add(service_id)
                    
                    # Add recommendation context
                    for rec in location_recommendations:
                        if rec["type"] == query:
                            service["recommendation_reason"] = rec["reason"]
                            service["priority"] = rec.get("priority", "normal")
                            break
                    
                    # Add AI-generated contextual advice
                    service["ai_advice"] = _generate_service_advice(service, decision)
                    
                    all_services.append(service)
        
        # Create session ID
        new_session_id = f"session_{len(chat_sessions)}" if session_id == "new" else session_id
        
        # Create comprehensive response
        response = {
            "session_id": new_session_id,
            "analysis": {
                "video": video_analysis,
                "text": text_analysis,
                "decision": decision,
                "final_assessment": {
                    "severity": decision.get("severity"),
                    "cars_involved": decision.get("cars_involved"),
                    "damages": decision.get("damages"),
                    "text_override_applied": decision.get("text_override_applied", False),
                    "overview_summary": decision.get("overview_summary"),
                    "detailed_explanation": decision.get("detailed_explanation")
                }
            },
            "location_services": location_services,
            "user_location": user_location,
            "recommendations": {
                "immediate_actions": decision.get("immediate_actions", []),
                "general_advice": decision.get("general_advice", []),
                "services": all_services[:6],  # Top 6 services across all categories
                "comprehensive_tips": decision.get("comprehensive_tips", [])
            },
            "priority": decision.get("priority", "medium"),
            "timestamp": "now",
            "context": {
                "search_queries_used": search_queries,
                "total_services_found": len(all_services)
            }
        }
        
        # Store in chat history with enhanced context
        if new_session_id not in chat_sessions:
            chat_sessions[new_session_id] = []
        
        chat_sessions[new_session_id].append({
            "type": "analysis",
            "user_input": {
                "video_filename": video.filename,
                "note": note,
                "location": user_location
            },
            "ai_response": response,
            "context": {
                "analysis_summary": decision.get("overview_summary"),
                "priority": decision.get("priority"),
                "service_needs": search_queries
            }
        })
        
        return response
    
    finally:
        # Clean up uploaded file
        try:
            os.remove(save_path)
        except:
            pass

def _generate_service_advice(service: Dict, decision: Dict) -> str:
    """Generate contextual advice for each service based on the accident analysis"""
    service_type = service.get("type", "")
    severity = decision.get("severity", "minor")
    damages = decision.get("damages", [])
    
    advice_templates = {
        "tire_shop": {
            "minor": "Check if they can inspect your wheel alignment - impacts often affect it.",
            "major": "Ask about emergency tire service and if they can check for suspension damage.",
            "severe": "Call ahead - you may need emergency roadside tire replacement."
        },
        "tow_truck": {
            "minor": "If driving safely, you may not need a tow. Get an estimate first.",
            "major": "Request a flatbed tow to prevent further damage to your vehicle.",
            "severe": "Priority emergency towing - mention if there are injuries involved."
        },
        "auto_body_shop": {
            "minor": "Get a free estimate first before deciding on repairs vs. insurance claim.",
            "major": "Ask about insurance direct billing and rental car arrangements.",
            "severe": "Focus on certified collision centers experienced with major damage."
        },
        "mechanic": {
            "minor": "Request a post-accident inspection even if damage looks minimal.",
            "major": "Ask for a comprehensive diagnostic to check for hidden damage.",
            "severe": "Ensure they're equipped to handle extensive mechanical damage."
        },
        "hospital": {
            "minor": "Visit urgent care if you experience delayed pain or discomfort.",
            "major": "Get checked even if you feel fine - adrenaline can mask injuries.",
            "severe": "Call 911 or go to emergency room immediately."
        }
    }
    
    # Get specific advice based on service type and severity
    service_advice = advice_templates.get(service_type, {})
    advice = service_advice.get(severity, f"Contact them about your {severity} accident situation.")
    
    # Add damage-specific advice
    if "tire" in str(damages).lower() and service_type == "tire_shop":
        advice += " Mention the tire damage when calling."
    elif "engine" in str(damages).lower() and service_type == "mechanic":
        advice += " Specifically mention potential engine issues."
    
    return advice

@app.post("/chat")
async def chat_followup(
    session_id: str = Form(...),
    message: str = Form(...),
    audio: Optional[UploadFile] = None
):
    """Enhanced chat handler with intelligent location search and context awareness"""
    
    if session_id not in chat_sessions:
        return {"error": "Session not found"}
    
    # Process audio if provided
    transcribed_text = ""
    if audio:
        save_path = f"uploads/chat_audio_{audio.filename}"
        os.makedirs("uploads", exist_ok=True)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        transcribed_text = agent_transcribe_audio(save_path)
        
        # Clean up uploaded file
        try:
            os.remove(save_path)
        except:
            pass
    
    # Combine message and transcription
    full_message = f"{message} {transcribed_text}".strip()
    
    # Get chat history and context
    chat_history = chat_sessions[session_id]
    
    # Find the most recent analysis for context
    last_analysis = None
    analysis_context = None
    for entry in reversed(chat_history):
        if entry["type"] == "analysis":
            last_analysis = entry["ai_response"]["analysis"]
            analysis_context = entry.get("context", {})
            break
    
    # Use intelligent query analyzer to understand what user needs
    query_analysis = agent_intelligent_query_analyzer(full_message, {"analysis": last_analysis})
    
    # Initialize response components
    location_data = None
    response_text = ""
    
    # Handle location requests with the enhanced system
    if query_analysis["needs_location_search"] and query_analysis["search_types"]:
        search_results = {}
        all_found_services = []
        
        # Search for each requested service type
        for service_type in query_analysis["search_types"][:3]:  # Limit to 3 service types
            location_info = agent_location_search(service_type, "Miami, FL")
            search_results[service_type] = location_info
            
            # Collect services for map display
            services = location_info.get("services", [])[:3]  # Top 3 per type
            for service in services:
                service["search_context"] = f"User requested {service_type.replace('_', ' ')}"
                all_found_services.append(service)
        
        # Create structured location data for frontend
        location_data = {
            "services": all_found_services,
            "search_types": query_analysis["search_types"],
            "query_intent": query_analysis["intent"],
            "map_center": {"lat": 25.7617, "lng": -80.1918},
            "zoom_level": 12,
            "search_metadata": {
                "total_results": len(all_found_services),
                "search_successful": True,
                "user_query": full_message
            }
        }
    
    # Generate contextual response using enhanced agent
    response_text = generate_chat_response(full_message, last_analysis, chat_history)
    
    # If we found location data but response doesn't mention it, enhance the response
    if location_data and not any(word in response_text.lower() for word in ["found", "located", "here are"]):
        service_count = len(location_data["services"])
        service_types = ", ".join([t.replace("_", " ") for t in location_data["search_types"]])
        response_text += f"\n\nI found {service_count} nearby {service_types} options for you. You can see them on the map below."
    
    # Store enhanced chat exchange
    chat_entry = {
        "type": "chat",
        "user_message": full_message,
        "ai_response": response_text,
        "location_data": location_data,
        "query_analysis": query_analysis,
        "timestamp": "now"
    }
    
    chat_sessions[session_id].append(chat_entry)
    
    # Return enhanced response
    return {
        "session_id": session_id,
        "response": response_text,
        "location_data": location_data,
        "chat_history": chat_sessions[session_id],
        "query_analysis": query_analysis  # For debugging/frontend optimization
    }

@app.get("/chat/{session_id}")
async def get_chat_history(session_id: str):
    """Retrieve chat history for a session"""
    if session_id not in chat_sessions:
        return {"error": "Session not found"}
    
    return {
        "session_id": session_id,
        "chat_history": chat_sessions[session_id]
    }

@app.get("/sessions")
async def list_active_sessions():
    """List all active chat sessions (for debugging)"""
    return {
        "active_sessions": list(chat_sessions.keys()),
        "total_sessions": len(chat_sessions)
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific chat session"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"message": f"Session {session_id} deleted"}
    else:
        return {"error": "Session not found"}

@app.get("/health")
async def health_detailed():
    """Detailed health check with environment info"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    return {
        "status": "healthy",
        "services": {
            "gemini_api": "available" if gemini_key else "mock_mode",
            "file_upload": "enabled",
            "chat_storage": "in_memory",
            "location_search": "enhanced_mock_data",
            "intelligent_query_analysis": "enabled"
        },
        "stats": {
            "active_sessions": len(chat_sessions),
            "upload_directory": "uploads/"
        },
        "features": {
            "smart_location_search": True,
            "contextual_chat": True,
            "enhanced_recommendations": True
        }
    }