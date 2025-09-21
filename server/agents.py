# server/agents.py
import random
import os
import base64
import requests
import json
from typing import Dict, List, Optional

def agent_analyze_video(video_path: str) -> Dict:
    """Analyze video using Gemini API for accident detection"""
    print(f"[DEBUG] Analyzing video at {video_path}")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _mock_video_analysis()
    
    try:
        # Read and encode video file
        with open(video_path, "rb") as video_file:
            video_data = base64.b64encode(video_file.read()).decode('utf-8')
        
        # Determine MIME type
        if video_path.endswith('.webm'):
            mime_type = "video/webm"
        elif video_path.endswith('.mp4'):
            mime_type = "video/mp4"
        else:
            mime_type = "video/webm"
        
        # Structured prompt for accident analysis
        prompt = """Analyze this video for accident-related information. Respond in this exact JSON format:

{
  "cars_involved": <number: 1 for solo accident, 2 for two-car, 3+ for multi-car>,
  "damages": <array of strings: ["tire damage", "front collision", "side damage", "broken glass", "scratches", "dents"]>,
  "severity": <string: "minor" | "major" | "severe">,
  "location_type": <string: "highway", "intersection", "parking lot", "residential street", "other">,
  "description": <string: brief description of what you observe>,
  "immediate_concerns": <array: safety issues that need attention>
}

Focus on:
- Vehicle damage visible
- Number of vehicles involved
- Severity assessment (minor = cosmetic/no injury risk, major = significant damage/potential injury, severe = emergency/life-threatening)
- Location context if visible
- Any immediate safety concerns"""

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": video_data
                        }
                    }
                ]
            }]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=45)
        
        if response.status_code == 200:
            result = response.json()
            analysis_text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response
            try:
                # Clean the response to extract JSON
                json_start = analysis_text.find('{')
                json_end = analysis_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = analysis_text[json_start:json_end]
                    analysis = json.loads(json_str)
                    print(f"[DEBUG] Gemini video analysis: {analysis}")
                    return analysis
                else:
                    print(f"[ERROR] Could not extract JSON from Gemini response: {analysis_text}")
                    return _mock_video_analysis()
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON decode error: {e}")
                print(f"[DEBUG] Raw response: {analysis_text}")
                return _mock_video_analysis()
                
        else:
            print(f"[ERROR] Gemini API error: {response.status_code} - {response.text}")
            return _mock_video_analysis()
            
    except Exception as e:
        print(f"[ERROR] Video analysis failed: {e}")
        return _mock_video_analysis()

def _mock_video_analysis() -> Dict:
    """Fallback mock analysis"""
    mock_response = {
        "cars_involved": random.choice([1, 2, 3]),
        "damages": random.choice([["tire damage"], ["front collision"], ["side damage", "broken glass"], ["scratches", "dents"]]),
        "severity": random.choice(["minor", "major", "severe"]),
        "location_type": random.choice(["highway", "intersection", "parking lot", "residential street"]),
        "description": "Mock analysis - could not process video with Gemini",
        "immediate_concerns": random.choice([[], ["check for injuries"], ["move to safety", "call emergency services"]])
    }
    print(f"[DEBUG] Mock video analysis: {mock_response}")
    return mock_response

def agent_analyze_text(text_input: str) -> Dict:
    """Analyze text input for additional context"""
    print(f"[DEBUG] Text received: {text_input}")
    return {
        "note": text_input,
        "length": len(text_input),
        "has_content": len(text_input.strip()) > 5 # Require more than a few chars
    }

def agent_intelligent_query_analyzer(message: str, context: Dict = None) -> Dict:
    """Analyze user query to determine what information and services they need"""
    message_lower = message.lower()
    
    analysis = {
        "needs_location_search": False,
        "search_types": [],
        "intent": "general",
        "urgency": "normal",
        "specific_requests": []
    }
    
    # Location-related keywords
    location_keywords = ["where", "nearby", "close", "location", "address", "directions", "map"]
    service_keywords = {
        "tire_shop": ["tire", "flat tire", "puncture", "rim", "wheel"],
        "tow_truck": ["tow", "towing", "can't drive", "won't start", "stuck"],
        "mechanic": ["mechanic", "repair", "fix", "engine", "car trouble"],
        "auto_body_shop": ["body shop", "collision", "dent", "scratch", "paint", "bumper"],
        "hospital": ["injured", "hurt", "pain", "emergency", "hospital", "doctor"],
        "police": ["police", "report", "officer", "law enforcement"]
    }
    
    # Check if they need location services
    if any(keyword in message_lower for keyword in location_keywords):
        analysis["needs_location_search"] = True
        analysis["intent"] = "location_request"
    
    # Determine what type of services they need
    for service_type, keywords in service_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis["search_types"].append(service_type)
            analysis["needs_location_search"] = True
    
    # If no specific service mentioned, infer from context
    if not analysis["search_types"] and context:
        final_assessment = context.get("analysis", {}).get("final_assessment", {})
        damages = final_assessment.get("damages", [])
        severity = final_assessment.get("severity", "minor")
        
        if any("tire" in str(damage).lower() for damage in damages):
            analysis["search_types"].append("tire_shop")
        elif severity == "severe":
            analysis["search_types"].extend(["hospital", "tow_truck"])
        elif severity == "major":
            analysis["search_types"].extend(["auto_body_shop", "tow_truck"])
        else:
            analysis["search_types"].append("mechanic")
    
    # Determine urgency
    urgent_keywords = ["emergency", "urgent", "asap", "immediately", "help", "stuck"]
    if any(keyword in message_lower for keyword in urgent_keywords):
        analysis["urgency"] = "urgent"
    
    # Check for specific requests
    if "cost" in message_lower or "price" in message_lower or "how much" in message_lower:
        analysis["specific_requests"].append("pricing_info")
    if "insurance" in message_lower:
        analysis["specific_requests"].append("insurance_guidance")
    if "next step" in message_lower or "what now" in message_lower:
        analysis["specific_requests"].append("next_steps")
    
    print(f"[DEBUG] Query analysis: {analysis}")
    return analysis

def agent_location_search(query: str, location: str = "Miami, FL") -> Dict:
    """Enhanced location search with properly structured map data for frontend consumption"""
    print(f"[DEBUG] Location search for '{query}' near {location}")
    
    # Comprehensive service database with precise coordinates for mapping
    miami_services_db = {
        "tire_shop": [
            {
                "id": "tire_kingdom_sw8", "name": "Tire Kingdom", "distance": "1.8 miles", "rating": 4.2,
                "coordinates": {"lat": 25.789, "lng": -80.210}, "type": "tire_shop",
                "phone": "(305) 555-0123", "address": "2500 SW 8th St, Miami, FL 33135",
                "hours": "Mon-Sat 8AM-6PM, Sun 9AM-5PM",
                "services": ["tire replacement", "wheel alignment", "tire repair"],
                "price_range": "$80-$300", "wait_time": "30-60 minutes",
                "map_ready": True
            },
            {
                "id": "costco_tire_flagler", "name": "Costco Tire Center", "distance": "3.2 miles", "rating": 4.5,
                "coordinates": {"lat": 25.750, "lng": -80.255}, "type": "tire_shop",
                "phone": "(305) 555-0456", "address": "7795 W Flagler St, Miami, FL 33144",
                "hours": "Mon-Fri 10AM-8PM, Sat 9:30AM-6PM, Sun 10AM-6PM",
                "services": ["tire installation", "road hazard warranty", "tire rotation"],
                "price_range": "$100-$400", "wait_time": "45-90 minutes",
                "map_ready": True
            },
            {
                "id": "discount_tire_sw40", "name": "Discount Tire", "distance": "4.1 miles", "rating": 4.3,
                "coordinates": {"lat": 25.731, "lng": -80.268}, "type": "tire_shop",
                "phone": "(305) 555-0789", "address": "8901 SW 40th St, Miami, FL 33165",
                "hours": "Mon-Fri 8AM-6PM, Sat 8AM-5PM",
                "services": ["tire replacement", "flat repair", "tire balancing"],
                "price_range": "$90-$350", "wait_time": "20-45 minutes",
                "map_ready": True
            }
        ],
        "tow_truck": [
            {
                "id": "tremont_towing_dispatch", "name": "Tremont Towing", "distance": "2.1 miles", "rating": 4.0,
                "coordinates": {"lat": 25.774, "lng": -80.193}, "type": "tow_truck",
                "phone": "(305) 555-0789", "address": "Dispatch: 1520 NW 7th St, Miami, FL 33125",
                "hours": "24/7 Emergency Service",
                "services": ["emergency towing", "roadside assistance", "jump start"],
                "price_range": "$75-$150", "wait_time": "15-30 minutes",
                "map_ready": True
            },
            {
                "id": "usa_towing_nw36", "name": "USA Towing", "distance": "3.5 miles", "rating": 3.8,
                "coordinates": {"lat": 25.810, "lng": -80.208}, "type": "tow_truck", 
                "phone": "(305) 555-1234", "address": "3501 NW 36th St, Miami, FL 33142",
                "hours": "24/7",
                "services": ["heavy duty towing", "accident recovery", "lockout service"],
                "price_range": "$85-$200", "wait_time": "20-45 minutes",
                "map_ready": True
            }
        ],
        "auto_body_shop": [
            {
                "id": "caliber_collision_nw27", "name": "Caliber Collision", "distance": "2.8 miles", "rating": 4.4,
                "coordinates": {"lat": 25.795, "lng": -80.224}, "type": "auto_body_shop",
                "phone": "(305) 555-2468", "address": "2900 NW 27th Ave, Miami, FL 33142",
                "hours": "Mon-Fri 7:30AM-5:30PM",
                "services": ["collision repair", "paint work", "insurance claims"],
                "price_range": "$500-$5000+", "wait_time": "3-7 days",
                "map_ready": True
            },
            {
                "id": "joes_auto_body_sw40", "name": "Joe's Auto Body", "distance": "4.1 miles", "rating": 4.1,
                "coordinates": {"lat": 25.728, "lng": -80.261}, "type": "auto_body_shop",
                "phone": "(305) 555-3691", "address": "6700 SW 40th St, Miami, FL 33155",
                "hours": "Mon-Fri 8AM-5PM, Sat 9AM-1PM",
                "services": ["dent repair", "frame straightening", "custom paint"],
                "price_range": "$300-$4000+", "wait_time": "2-5 days",
                "map_ready": True
            }
        ],
        "mechanic": [
            {
                "id": "pep_boys_sw22", "name": "Pep Boys", "distance": "1.2 miles", "rating": 3.9,
                "coordinates": {"lat": 25.761, "lng": -80.218}, "type": "mechanic",
                "phone": "(305) 555-4812", "address": "1250 SW 22nd St, Miami, FL 33145",
                "hours": "Mon-Sat 8AM-8PM, Sun 9AM-6PM",
                "services": ["oil change", "brake service", "engine diagnostics"],
                "price_range": "$50-$800", "wait_time": "30 minutes-2 hours",
                "map_ready": True
            },
            {
                "id": "gus_garage_sw32", "name": "Gus's Garage", "distance": "2.8 miles", "rating": 4.6,
                "coordinates": {"lat": 25.739, "lng": -80.245}, "type": "mechanic",
                "phone": "(305) 555-5925", "address": "3050 SW 32nd Ave, Miami, FL 33133",
                "hours": "Mon-Fri 7AM-6PM, Sat 8AM-4PM",
                "services": ["engine repair", "transmission", "electrical work"],
                "price_range": "$75-$1200", "wait_time": "1-3 hours",
                "map_ready": True
            }
        ],
        "hospital": [
            {
                "id": "jackson_memorial_main", "name": "Jackson Memorial Hospital", "distance": "3.8 miles", "rating": 4.2,
                "coordinates": {"lat": 25.798, "lng": -80.214}, "type": "hospital",
                "phone": "911 or (305) 585-1111", "address": "1611 NW 12th Ave, Miami, FL 33136",
                "hours": "24/7 Emergency Room",
                "services": ["emergency care", "trauma center", "surgery"],
                "price_range": "Contact insurance", "wait_time": "Varies by severity",
                "map_ready": True
            },
             {
                "id": "mercy_hospital_south", "name": "Mercy Hospital", "distance": "4.5 miles", "rating": 4.0,
                "coordinates": {"lat": 25.742, "lng": -80.212}, "type": "hospital",
                "phone": "911 or (305) 854-4400", "address": "3663 S Miami Ave, Miami, FL 33133",
                "hours": "24/7 Emergency Department",
                "services": ["emergency medicine", "urgent care", "imaging"],
                "price_range": "Insurance dependent", "wait_time": "Based on triage",
                "map_ready": True
            }
        ]
    }
    
    # Map query to service type with better matching
    query_lower = query.lower()
    service_key = "mechanic"  # Default
    
    if any(word in query_lower for word in ["tire", "flat", "puncture", "wheel"]):
        service_key = "tire_shop"
    elif any(word in query_lower for word in ["tow", "towing", "stuck", "won't start", "can't drive"]):
        service_key = "tow_truck"
    elif any(word in query_lower for word in ["body", "collision", "dent", "scratch", "paint", "bumper"]):
        service_key = "auto_body_shop"
    elif any(word in query_lower for word in ["emergency", "hospital", "injured", "hurt", "medical"]):
        service_key = "hospital"
    elif any(word in query_lower for word in ["mechanic", "repair", "engine", "brake", "oil"]):
        service_key = "mechanic"

    services = miami_services_db.get(service_key, miami_services_db["mechanic"])
    
    # Calculate map bounds for frontend
    if services:
        lats = [s["coordinates"]["lat"] for s in services]
        lngs = [s["coordinates"]["lng"] for s in services]
        bounds = {
            "north": max(lats) + 0.01,
            "south": min(lats) - 0.01,
            "east": max(lngs) + 0.01,
            "west": min(lngs) - 0.01
        }
        center_lat = (max(lats) + min(lats)) / 2
        center_lng = (max(lngs) + min(lngs)) / 2
    else:
        bounds = {
            "north": 25.85, "south": 25.65,
            "east": -80.1, "west": -80.3
        }
        center_lat, center_lng = 25.7617, -80.1918
    
    return {
        "query": query,
        "location": location,
        "service_type": service_key,
        "services": services,
        "total_found": len(services),
        "search_successful": True,
        "map_config": {
            "center": {"lat": center_lat, "lng": center_lng},
            "bounds": bounds,
            "zoom_level": 12 if len(services) > 1 else 14,
            "show_markers": True,
            "cluster_markers": len(services) > 5
        },
        "search_metadata": {
            "radius": "10 miles",
            "sort_by": "distance",
            "last_updated": "2025-01-01",
            "query_type": service_key,
            "frontend_ready": True
        }
    }

def agent_decision_maker(video_analysis: Dict, text_analysis: Dict, location_info: Dict = None) -> Dict:
    """Enhanced decision maker that prioritizes text input and provides comprehensive recommendations"""
    print(f"[DEBUG] Enhanced decision making with video={video_analysis}, text={text_analysis}")
    
    # Extract data
    video_severity = video_analysis.get("severity", "minor")
    video_cars_involved = video_analysis.get("cars_involved", 1)
    video_damages = video_analysis.get("damages", [])
    
    text_content = text_analysis.get("note", "").lower()
    text_has_content = text_analysis.get("has_content", False)
    
    # TEXT TAKES PRECEDENCE
    final_severity = video_severity
    final_cars_involved = video_cars_involved
    final_damages = list(video_damages)
    text_override_applied = False
    
    if text_has_content:
        # Text severity indicators
        if any(word in text_content for word in ["emergency", "911", "ambulance", "serious injury", "bleeding", "unconscious", "severe", "hospital"]):
            final_severity = "severe"
            text_override_applied = True
        elif any(word in text_content for word in ["major damage", "can't drive", "won't start", "tow", "significant", "airbag"]):
            final_severity = "major"
            text_override_applied = True
        elif any(word in text_content for word in ["minor", "small", "tiny", "little", "scratch", "fender bender"]):
            final_severity = "minor"
            text_override_applied = True
        
        # Text car involvement indicators
        if any(word in text_content for word in ["other driver", "their car", "two car", "multi", "hit by", "collision with"]):
            final_cars_involved = max(2, final_cars_involved)
            text_override_applied = True
        elif any(word in text_content for word in ["solo", "alone", "just me", "by myself", "hit a pole", "hit a curb"]):
            final_cars_involved = 1
            text_override_applied = True
        
        # Text damage indicators (add to video damages)
        text_damage_indicators = {
            "tire damage": ["tire", "flat", "puncture", "rim", "blew out"],
            "engine damage": ["won't start", "engine", "smoke", "steam", "overheating"],
            "body damage": ["dent", "scratch", "bumper", "door", "fender", "body"],
            "glass damage": ["windshield", "window", "glass", "cracked"],
            "fluid leak": ["leak", "oil", "coolant", "fluid"]
        }
        
        for damage_type, keywords in text_damage_indicators.items():
            if any(keyword in text_content for keyword in keywords):
                if damage_type not in final_damages:
                    final_damages.append(damage_type)
                    text_override_applied = True

    # Generate summaries and explanations
    overview_summary = f"I've analyzed a {final_severity} incident involving {final_cars_involved} vehicle(s)."
    if text_override_applied:
        overview_summary += " My assessment prioritized your text description."
    
    detailed_explanation = f"Based on the combined video and text analysis, this appears to be a {final_severity} situation. "
    if final_cars_involved > 1:
        detailed_explanation += f"With {final_cars_involved} vehicles involved, it's crucial to handle information exchange properly. "
    else:
        detailed_explanation += "As a solo-vehicle incident, the primary focus is on your safety and vehicle condition. "
    
    if final_damages:
        damages_str = ", ".join(final_damages)
        detailed_explanation += f"The detected damages include: {damages_str}. This suggests attention may be needed for these specific areas."
    else:
        detailed_explanation += "No specific external damages were immediately obvious, but internal issues could still exist."

    # Determine priority, advice, and recommendations
    priority = "low"
    location_recommendations = []
    immediate_actions = []
    general_advice = []
    
    if final_severity == "severe":
        priority = "emergency"
        immediate_actions = [
            "CALL 911 IMMEDIATELY if not already done.",
            "Check for injuries on yourself and others. Do not move anyone who is seriously injured unless they are in immediate danger.",
            "Move to a safe location away from traffic if possible.",
            "Turn on your vehicle's hazard lights to warn other drivers."
        ]
        general_advice = [
            "Cooperate with police and emergency responders.",
            "Avoid discussing fault at the scene.",
            "Once safe, take photos of the scene and vehicle damage.",
            "Contact your insurance company after the immediate emergency is handled."
        ]
        location_recommendations = [{"type": "hospital", "reason": "Severe accidents require immediate medical evaluation.", "priority": "immediate"}]

    elif final_severity == "major":
        priority = "high"
        immediate_actions = [
            "Ensure you and any passengers are in a safe location away from traffic.",
            "Call the police to file an official report, which is crucial for insurance.",
            "Exchange contact and insurance information with any other drivers involved.",
            "Take extensive photos of all vehicle damage, license plates, and the accident scene."
        ]
        general_advice = [
            "Do not drive your vehicle if it seems unsafe; call for a tow.",
            "Notify your insurance provider about the accident promptly.",
            "Begin the process of getting repair estimates from certified shops.",
            "Keep detailed records of all communication and expenses."
        ]
        location_recommendations = [
            {"type": "auto_body_shop", "reason": "Major damage requires a professional collision center.", "priority": "urgent"},
            {"type": "tow_truck", "reason": "Vehicle may be unsafe to operate.", "priority": "immediate"}
        ]
    else: # minor
        priority = "medium"
        has_tire_damage = any("tire" in str(d).lower() for d in final_damages)
        
        if has_tire_damage:
            immediate_actions = [
                "Pull over to a safe, level location away from traffic.",
                "Assess the tire damage. If it's flat, prepare to use your spare or call for assistance.",
                "Turn on your hazard lights while you are on the roadside."
            ]
            location_recommendations.append({"type": "tire_shop", "reason": "A damaged tire needs immediate repair or replacement.", "priority": "urgent"})
        else:
             immediate_actions = [
                "Move your vehicle out of traffic if it is safe and legal to do so.",
                "Inspect your vehicle thoroughly for any damage you may have missed.",
                "If another driver is involved, exchange insurance and contact information."
            ]
        
        general_advice = [
            "Take photos of the damage, even if it seems minor.",
            "Decide whether to file an insurance claim based on the repair cost and your deductible.",
            "Get a professional estimate to understand the full extent of the damage.",
            "Even for minor damage, filing a police report can be beneficial."
        ]
        location_recommendations.append({"type": "mechanic", "reason": "Even minor incidents can cause hidden damage.", "priority": "soon"})
    
    comprehensive_tips = _generate_comprehensive_tips(final_severity, final_damages, final_cars_involved)

    return {
        "priority": priority,
        "severity": final_severity,
        "cars_involved": final_cars_involved,
        "damages": list(set(final_damages)), # a unique list
        "text_override_applied": text_override_applied,
        "overview_summary": overview_summary,
        "detailed_explanation": detailed_explanation,
        "immediate_actions": immediate_actions,
        "general_advice": general_advice,
        "location_recommendations": location_recommendations,
        "comprehensive_tips": comprehensive_tips
    }

def _generate_comprehensive_tips(severity: str, damages: List[str], cars_involved: int) -> List[str]:
    """Generate comprehensive, actionable tips based on the full situation analysis"""
    tips = []
    
    # Documentation tips
    tips.extend([
        "Use your phone to document everything: photos of damage, the scene, license plates, and insurance cards.",
        "Write down your own account of what happened as soon as possible while it's fresh in your mind."
    ])

    if cars_involved > 1:
        tips.extend([
            "Avoid admitting fault. Stick to the facts when speaking with other drivers and the police.",
            "Get contact information for any witnesses who saw the accident."
        ])

    if any("tire" in d.lower() for d in damages):
        tips.append("When getting a tire replaced, ask the shop to check your vehicle's alignment as well, as impacts can throw it off.")

    if severity in ["major", "severe"]:
        tips.append("Keep a detailed log of all medical visits, expenses, and days missed from work if you are injured.")
    
    # Insurance and financial tips
    tips.extend([
        "Notify your insurance company quickly, even if you're not at fault.",
        "Understand your insurance coverage, especially your deductible and rental car policy.",
        "Get at least two independent repair estimates before committing to a shop."
    ])
        
    return tips[:8] # Limit to most important tips

def agent_transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using Gemini API"""
    print(f"[DEBUG] Transcribing audio at {audio_path}")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        mock_transcriptions = [
            "I just had a minor accident on 5th Street. My front bumper is dented but everyone is okay.",
            "There was a collision at the intersection. No injuries but my car won't start.",
            "I hit a pothole and now my tire is flat. I'm on the side of Highway 95.",
        ]
        transcription = random.choice(mock_transcriptions)
        print(f"[DEBUG] Mock transcription: {transcription}")
        return transcription

    try:
        with open(audio_path, "rb") as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
        
        mime_type = "audio/webm"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Please transcribe this audio clearly and accurately. Focus on accident-related details:"},
                    {"inline_data": {"mime_type": mime_type, "data": audio_data}}
                ]
            }]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            transcription = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"[DEBUG] Gemini transcription: {transcription}")
            return transcription.strip()
        else:
            print(f"[ERROR] Gemini API error: {response.status_code} - {response.text}")
            return "Error: Could not transcribe audio"
            
    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        return "Error: Transcription failed"

def generate_chat_response(message: str, last_analysis: Optional[Dict], session_history: List[Dict] = None) -> str:
    """Enhanced chat response generation with intelligent location search triggering"""
    
    message_lower = message.lower()
    
    if not last_analysis:
        return "I don't have any previous analysis to reference. Please start a new analysis with a video."
    
    # Analyze the user's query
    query_analysis = agent_intelligent_query_analyzer(message, {"analysis": last_analysis})
    
    # Get context from last analysis
    severity = last_analysis.get("final_assessment", {}).get("severity", "unknown")
    damages = last_analysis.get("final_assessment", {}).get("damages", [])
    
    # Build contextual response
    response_parts = []
    
    # Handle specific requests first
    if "pricing_info" in query_analysis["specific_requests"]:
        if "tire" in str(damages).lower():
            response_parts.append("Tire replacement costs in Miami typically range from $100-$400 including installation, depending on your vehicle and tire quality. Budget tires run $80-150, while premium tires can cost $200-400 each.")
        elif severity == "major":
            response_parts.append("For major collision damage, repair costs can vary significantly from $2,000 to $15,000+ depending on the extent of damage. Body work typically costs $500-5,000, while structural repairs can be much higher.")
        else:
            response_parts.append("Minor repairs like small dents or scratches typically cost $300-$1,500. Touch-up paint jobs run $200-800, while small dent repair can be $150-500.")
    
    if "insurance_guidance" in query_analysis["specific_requests"]:
        response_parts.append("When contacting your insurance, have your policy number, driver's license, and photos ready. Report the claim within 24-48 hours if possible. Your insurance will assign a claims adjuster and guide you through their specific process.")
    
    if "next_steps" in query_analysis["specific_requests"]:
        if severity == "severe":
            response_parts.append("Your immediate priority should be medical attention and cooperating with emergency responders. Document everything once you're safe, and contact insurance after immediate needs are handled.")
        elif severity == "major":
            response_parts.append("Next steps: 1) Get a police report number, 2) Contact your insurance, 3) Get multiple repair estimates, 4) Arrange towing if needed, 5) Consider rental car coverage.")
        else:
            response_parts.append("For your situation: 1) Take detailed photos, 2) Get a repair estimate, 3) Decide on insurance claim vs. paying out of pocket, 4) Monitor for any delayed issues or pain.")
    
    # Handle location requests with enhanced responses
    if query_analysis["needs_location_search"]:
        if query_analysis["search_types"]:
            service_type = query_analysis["search_types"][0]  # Use first/primary type
            location_info = agent_location_search(service_type, "Miami, FL")
            
            # Create rich location response
            services = location_info.get("services", [])[:3]  # Top 3 services
            service_display_name = service_type.replace("_", " ").title()
            
            location_response = f"I found several {service_display_name.lower()} options near you:\n\n"
            
            for i, service in enumerate(services, 1):
                location_response += f"{i}. **{service['name']}** ({service['distance']})\n"
                location_response += f"   📍 {service['address']}\n"
                location_response += f"   📞 {service['phone']}\n"
                location_response += f"   ⏰ {service.get('hours', 'Call for hours')}\n"
                location_response += f"   💰 {service.get('price_range', 'Call for pricing')}\n"
                if service.get('wait_time'):
                    location_response += f"   ⏱️ Typical wait: {service['wait_time']}\n"
                location_response += "\n"
            
            response_parts.append(location_response)
            
            # Add contextual advice based on service type
            if service_type == "tire_shop":
                response_parts.append("💡 Pro tip: Call ahead to confirm they have your tire size in stock and ask about road hazard warranties.")
            elif service_type == "tow_truck":
                response_parts.append("💡 When calling for a tow, provide your exact location, vehicle make/model, and specify if you need flatbed service for AWD vehicles.")
            elif service_type == "auto_body_shop":
                response_parts.append("💡 Ask about insurance direct billing and get a written estimate. Reputable shops should provide warranties on their work.")
            elif service_type == "mechanic":
                response_parts.append("💡 For post-accident inspections, ask them to specifically check alignment, suspension, and frame integrity even if damage looks minor.")
        else:
            response_parts.append("I can help you find local services. What type of service do you need? (mechanic, tire shop, body shop, towing, etc.)")
    
    # General conversational responses
    if not response_parts:
        if any(word in message_lower for word in ["thank", "thanks"]):
            response_parts.append("You're welcome! I'm here to help you through this situation. Do you have any other questions about next steps or need help finding local services?")
        elif any(word in message_lower for word in ["help", "what", "how"]):
            response_parts.append("I can help you with next steps, finding local services, insurance guidance, or cost estimates. What specific information would be most helpful right now?")
        else:
            response_parts.append("I understand you're dealing with the aftermath of your accident. I can provide more details about next steps, help you find local services, or answer questions about the repair process. What would be most helpful?")
    
    return "\n".join(response_parts)