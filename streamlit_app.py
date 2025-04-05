import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import numpy as np
import tempfile
import os
import time
import threading
import pyttsx3
from openai import OpenAI
from dotenv import load_dotenv
import json
import datetime
from datetime import datetime, timedelta
import requests
import httpx
import re
import random
import queue
import av
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if api_key and api_key != "your_openai_api_key_here":
    # Create a basic httpx client with no proxies
    http_client = httpx.Client()
    client = OpenAI(api_key=api_key, http_client=http_client)
else:
    client = None
    st.error("OpenAI API key not found. Please enter your API key in the sidebar.")

# Initialize text-to-speech engine
engine = pyttsx3.init()

# WebRTC configuration
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Audio queue for processing
audio_queue = queue.Queue()

# App state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recording" not in st.session_state:
    st.session_state.recording = False
if "audio_data" not in st.session_state:
    st.session_state.audio_data = None
if "calendar_events" not in st.session_state:
    st.session_state.calendar_events = []
if "api_key" not in st.session_state:
    st.session_state.api_key = None
if "voice_rate" not in st.session_state:
    st.session_state.voice_rate = 0.75  # 75% of normal speed (slower)
if "use_female_voice" not in st.session_state:
    st.session_state.use_female_voice = True  # Default to female voice
if "voice_volume" not in st.session_state:
    st.session_state.voice_volume = 0.9  # 90% volume
if "draft_emails" not in st.session_state:
    st.session_state.draft_emails = []
if "last_processed_input" not in st.session_state:
    st.session_state.last_processed_input = ""
if "language" not in st.session_state:
    st.session_state.language = "en"  # Default language is English
if "audio_frames" not in st.session_state:
    st.session_state.audio_frames = []

# Constants
SAMPLE_RATE = 16000

# Configure page
st.set_page_config(page_title="Voice Assistant", page_icon="🎤")
st.title("Voice Assistant")

# Audio processing callback for WebRTC
class AudioProcessor:
    def __init__(self):
        self.frames = []
        
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # Store audio data for processing
        audio_data = frame.to_ndarray()
        self.frames.append(audio_data)
        
        # Also put in queue for real-time processing if needed
        audio_queue.put(audio_data)
        
        return frame

# Function to save audio frames to a temp file
def save_audio_frames_to_file(frames: List[np.ndarray]) -> str:
    try:
        if not frames:
            st.error("No audio data was recorded.")
            return None
            
        # Concatenate all frames
        audio_data = np.concatenate(frames, axis=0)
        
        # Normalize and convert to int16
        if np.max(np.abs(audio_data)) > 0:
            audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
        else:
            audio_data = np.int16(audio_data * 0)  # Convert to silence if no sound
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        write(temp_file.name, SAMPLE_RATE, audio_data)
        return temp_file.name
    except Exception as e:
        st.error(f"Error saving audio: {str(e)}")
        return None

# Function to transcribe audio
def transcribe_audio(audio_file_path: str) -> str:
    try:
        if not client:
            st.error("OpenAI API key not set. Please add your API key in the sidebar.")
            if os.path.exists(audio_file_path):
                os.unlink(audio_file_path)
            return None
            
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=st.session_state.language
            )
        os.unlink(audio_file_path)  # Delete the temp file
        return transcription.text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
        return None

# Function to speak text using TTS
def speak_text(text: str, use_female_voice: bool = True, voice_rate: float = 0.75, voice_volume: float = 0.9):
    try:
        # Initialize TTS engine within the thread to avoid context issues
        tts_engine = pyttsx3.init()
        
        # Configure voice to be more feminine and slower
        voices = tts_engine.getProperty('voices')
        
        # On Windows, make sure to use SAPI5 driver
        if os.name == 'nt':  # Windows
            try:
                tts_engine = pyttsx3.init(driverName='sapi5')
                voices = tts_engine.getProperty('voices')
            except:
                pass
        
        # Find a female voice if requested
        if use_female_voice and voices:
            female_voice = None
            for voice in voices:
                if "female" in voice.name.lower() or "fem" in voice.id.lower() or "zira" in voice.name.lower():
                    female_voice = voice.id
                    break
            
            if female_voice:
                tts_engine.setProperty('voice', female_voice)
        
        # Adjust rate and volume
        rate = tts_engine.getProperty('rate')
        tts_engine.setProperty('rate', rate * voice_rate)
        tts_engine.setProperty('volume', voice_volume)
        
        tts_engine.say(text)
        tts_engine.runAndWait()
        tts_engine.stop()
    except Exception as e:
        print(f"Error during text-to-speech: {str(e)}")

# Available assistant functions (same as before)
available_functions = {
    "schedule_event": lambda event_details: schedule_event(event_details),
    "draft_email": lambda email_details: draft_email(email_details),
    "web_search": lambda search_query: web_search(search_query)
}

# Function implementations (same as before)
def schedule_event(event_details: Dict[str, Any]) -> str:
    try:
        title = event_details.get("title", "Untitled Event")
        start_time_str = event_details.get("start_time")
        duration_minutes = event_details.get("duration_minutes", 60)
        location = event_details.get("location", "")
        
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
        else:
            start_time = datetime.now() + timedelta(hours=1)
            start_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        meeting_link = ""
        if not location or "online" in location.lower() or "virtual" in location.lower() or "remote" in location.lower():
            meeting_id = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            meeting_password = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6)])
            meeting_link = f"https://meeting-link.example.com/j/{meeting_id}?pwd={meeting_password}"
            if not location:
                location = "Virtual Meeting"
        
        is_duplicate = False
        for existing_event in st.session_state.calendar_events:
            if (existing_event.get("title") == title and 
                existing_event.get("start_time") == start_time.isoformat()):
                is_duplicate = True
                break
        
        if not is_duplicate:
            event = {
                "title": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": duration_minutes,
                "location": location,
                "meeting_link": meeting_link
            }
            st.session_state.calendar_events.append(event)
        
        response = f"Scheduled: {title} at {start_time.strftime('%Y-%m-%d %H:%M')}"
        if location:
            response += f"\nLocation: {location}"
        if meeting_link:
            response += f"\nMeeting Link: {meeting_link}"
        
        return response
    except Exception as e:
        return f"Failed to schedule event: {str(e)}"

def draft_email(email_details: Dict[str, Any]) -> str:
    try:
        to = email_details.get("to", "")
        subject = email_details.get("subject", "")
        body = email_details.get("body", "")
        
        email_id = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(8)])
        
        is_duplicate = False
        for existing_email in st.session_state.draft_emails:
            if (existing_email.get("to") == to and 
                existing_email.get("subject") == subject and
                existing_email.get("body") == body):
                is_duplicate = True
                email_id = existing_email.get("id")
                break
        
        if not is_duplicate:
            email_draft = {
                "id": email_id,
                "to": to,
                "subject": subject,
                "body": body,
                "created_at": datetime.now().isoformat()
            }
            st.session_state.draft_emails.append(email_draft)
        
        response = f"Email drafted to {to} with subject '{subject}'\n\n"
        response += f"To: {to}\n"
        response += f"Subject: {subject}\n"
        response += f"Body:\n{body}\n\n"
        response += f"Email ID: {email_id} (Use this ID to reference this email later)"
        
        return response
    except Exception as e:
        return f"Failed to draft email: {str(e)}"

def web_search(search_query: Dict[str, Any]) -> str:
    try:
        query = search_query.get("query", "")
        
        try:
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    abstract = result.get('Abstract', '')
                    related_topics = result.get('RelatedTopics', [])
                    
                    if abstract:
                        return abstract
                    
                    if related_topics:
                        combined_info = ""
                        for topic in related_topics[:5]:
                            if 'Text' in topic:
                                combined_info += topic['Text'] + " "
                        
                        if combined_info:
                            return combined_info.strip()
                    
                    raise Exception("No results from primary search")
                except:
                    pass
            
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            
            if response.status_code == 200:
                content = response.text
                snippets = re.findall(r'<a class="result__snippet".*?>(.*?)</a>', content)
                
                if snippets:
                    combined_info = ""
                    for snippet in snippets[:3]:
                        clean_snippet = re.sub(r'<.*?>', '', snippet)
                        if clean_snippet:
                            combined_info += clean_snippet + " "
                    
                    if combined_info:
                        return combined_info.strip()
            
            return f"Based on my knowledge, {query} is something I can tell you about, but I don't have specific current information."
            
        except Exception as e:
            print(f"Web search error: {str(e)}")
            return f"Regarding {query}, I can tell you that it's something I have some information about."
    except Exception as e:
        return f"I'm having trouble finding information about that right now."

# Process user input with GPT-4 (same as before)
def process_with_gpt(user_input: str) -> str:
    try:
        if user_input == st.session_state.last_processed_input:
            for i in range(len(st.session_state.messages) - 1, -1, -1):
                if st.session_state.messages[i]["role"] == "assistant" and st.session_state.messages[i].get("content"):
                    return st.session_state.messages[i]["content"]
            return "I've already processed this request."
        
        st.session_state.last_processed_input = user_input
        
        if not client:
            st.error("OpenAI API key not set. Please add your API key in the sidebar.")
            return "Error: OpenAI API key not set."
            
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        functions = [
            {
                "type": "function",
                "function": {
                    "name": "schedule_event",
                    "description": "Schedule a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Title of the event"},
                            "start_time": {"type": "string", "description": "Start time in ISO format"},
                            "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
                            "location": {"type": "string", "description": "Location of the event"}
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "draft_email",
                    "description": "Draft an email with full content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Email recipient"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body content"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for real-time information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
        messages = []
        for msg in st.session_state.messages:
            if msg["role"] == "user" or (msg["role"] == "assistant" and msg.get("content") is not None):
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        system_message = {
            "role": "system",
            "content": "You are a helpful voice assistant that provides direct answers to questions."
        }
        
        messages = [system_message] + messages
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=functions,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            assistant_msg_with_tool_calls = {
                "role": "assistant",
                "content": None,
                "tool_calls": []
            }
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                assistant_msg_with_tool_calls["tool_calls"].append({
                    "function": {"name": function_name, "arguments": tool_call.function.arguments},
                    "id": tool_call.id
                })
                
                if function_name in available_functions:
                    function_response = available_functions[function_name](function_args)
                    
                    tool_response = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    }
            
            st.session_state.messages.append(assistant_msg_with_tool_calls)
            
            tool_messages = []
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name in available_functions:
                    function_response = available_functions[function_name](function_args)
                    
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    }
                    st.session_state.messages.append(tool_msg)
                    tool_messages.append(tool_msg)
            
            follow_up_messages = messages.copy()
            follow_up_messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in response_message.tool_calls
                ]
            })
            
            for tool_msg in tool_messages:
                follow_up_messages.append(tool_msg)
            
            second_response = client.chat.completions.create(
                model="gpt-4",
                messages=[system_message] + follow_up_messages
            )
            
            assistant_response = second_response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            return assistant_response
        else:
            assistant_response = response_message.content
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            return assistant_response
            
    except Exception as e:
        error_message = f"Error processing with GPT: {str(e)}"
        st.error(error_message)
        return f"I encountered an issue processing your request. {error_message}"

# UI Components
col1, col2 = st.columns([4, 1])

with col1:
    # Display conversation history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant" and msg.get("content"):
            st.chat_message("assistant").write(msg["content"])
        elif msg["role"] == "tool":
            with st.chat_message("system"):
                st.write(f"*{msg['content']}*")

with col2:
    # WebRTC audio recorder
    webrtc_ctx = webrtc_streamer(
        key="audio-recorder",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=256,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"audio": True, "video": False},
        audio_processor_factory=AudioProcessor
    )
    
    if webrtc_ctx.audio_receiver:
        st.info("Recording... Speak now. Press 'Stop' when done.")
        
        # Process audio when stop is pressed
        if st.button("Process Recording"):
            if hasattr(webrtc_ctx, 'audio_processor') and webrtc_ctx.audio_processor.frames:
                with st.spinner("Processing audio..."):
                    audio_file = save_audio_frames_to_file(webrtc_ctx.audio_processor.frames)
                    if audio_file:
                        transcription = transcribe_audio(audio_file)
                        if transcription:
                            st.success("Transcription complete!")
                            
                            with st.spinner("Processing your request..."):
                                response = process_with_gpt(transcription)
                            
                            threading.Thread(
                                target=speak_text, 
                                args=(
                                    response, 
                                    st.session_state.use_female_voice, 
                                    st.session_state.voice_rate, 
                                    st.session_state.voice_volume
                                ), 
                                daemon=True
                            ).start()
                            
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Failed to transcribe audio.")
                    else:
                        st.error("Failed to save audio.")
            else:
                st.warning("No audio was recorded. Please try again.")

    # Display calendar events if there are any
    if st.session_state.calendar_events:
        st.subheader("Calendar Events")
        st.write(f"*{len(st.session_state.calendar_events)} event(s) found*")
        
        for event in st.session_state.calendar_events:
            start_time = datetime.fromisoformat(event["start_time"])
            
            with st.expander(f"📅 {event['title']} - {start_time.strftime('%Y-%m-%d %H:%M')}"):
                st.write(f"**Start:** {start_time.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Duration:** {event['duration_minutes']} minutes")
                
                if event.get('location'):
                    st.write(f"**Location:** {event['location']}")
                
                if event.get('meeting_link'):
                    st.markdown(f"**Meeting Link:** [Click to join]({event['meeting_link']})")

    # Display drafted emails if there are any
    if st.session_state.draft_emails:
        st.subheader("Email Drafts")
        st.write(f"*{len(st.session_state.draft_emails)} email draft(s) found*")
        
        for email in st.session_state.draft_emails:
            created_at = datetime.fromisoformat(email["created_at"])
            
            with st.expander(f"✉️ To: {email['to']} - Subject: {email['subject']}"):
                st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**To:** {email['to']}")
                st.write(f"**Subject:** {email['subject']}")
                st.text_area("Body", email['body'], height=150, key=f"email_{email['id']}", disabled=True)
                st.write(f"**Email ID:** {email['id']}")
                
                if st.button("Copy Email Content", key=f"copy_{email['id']}"):
                    full_email = f"To: {email['to']}\nSubject: {email['subject']}\n\n{email['body']}"
                    st.code(full_email)
                    st.success("Email content copied to clipboard!")

# Text input as an alternative to voice
user_input = st.text_input("Or type your command:", "")
if user_input:
    with st.spinner("Processing your request..."):
        response = process_with_gpt(user_input)
        
        threading.Thread(
            target=speak_text, 
            args=(
                response, 
                st.session_state.use_female_voice, 
                st.session_state.voice_rate, 
                st.session_state.voice_volume
            ), 
            daemon=True
        ).start()
    
    time.sleep(0.5)
    st.rerun()

# Sidebar with settings (same as before)
with st.sidebar:
    languages = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "nl": "Nederlands",
        "ru": "Русский",
        "zh": "中文",
        "ja": "日本語",
        "ko": "한국어",
        "ar": "العربية",
        "hi": "हिन्दी",
        "sl": "Slovenščina"
    }
    
    selected_language = st.selectbox(
        "Select Language",
        options=list(languages.keys()),
        format_func=lambda x: languages[x],
        index=list(languages.keys()).index(st.session_state.language) if st.session_state.language in languages else 0
    )
    
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        if st.session_state.messages:
            if st.button(f"Change to {languages[selected_language]} and clear conversation"):
                st.session_state.messages = []
                st.rerun()
    
    st.divider()
    st.subheader("Voice Settings")
    
    st.session_state.use_female_voice = st.checkbox("Use female voice", value=st.session_state.use_female_voice)
    
    st.session_state.voice_rate = st.slider(
        "Voice Speed", 
        min_value=0.5, 
        max_value=1.5, 
        value=st.session_state.voice_rate,
        step=0.1
    )
    
    st.session_state.voice_volume = st.slider(
        "Voice Volume", 
        min_value=0.1, 
        max_value=1.0, 
        value=st.session_state.voice_volume,
        step=0.1
    )
    
    if st.button("Test Voice"):
        test_text = "This is a test of the voice settings."
        threading.Thread(
            target=speak_text, 
            args=(
                test_text, 
                st.session_state.use_female_voice, 
                st.session_state.voice_rate, 
                st.session_state.voice_volume
            ), 
            daemon=True
        ).start()
    
    st.divider()
    st.markdown("""
    ### Features:
    - **Real-time Web Search**: Ask about current events, weather, news, etc.
    - **Calendar Management**: Schedule meetings and events with automatic meeting links
    - **Email Drafting**: Create complete email drafts that you can copy and send
    
    ### Voice Commands Examples:
    - "Schedule a virtual meeting with John tomorrow at 2pm"
    - "Draft an email to sarah@example.com about the project update"
    - "What's the weather in New York today?"
    - "What's happening in the world right now?"
    
    ### Tips:
    - Press 'Start' to begin recording and 'Stop' when done
    - Use the calendar and email sections to view your scheduled events and drafts
    - Speak clearly and in a quiet environment
    """)