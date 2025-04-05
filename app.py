import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
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

# Constants
SAMPLE_RATE = 16000
MAX_DURATION = 30  # Maximum recording duration in seconds

# Configure page
st.set_page_config(page_title="Voice Assistant", page_icon="🎤")
st.title("Voice Assistant")

# Function to record audio
def record_audio():
    try:
        # Check if the audio device is available
        devices = sd.query_devices()
        if len(devices) == 0:
            st.error("No audio devices found. Please check your microphone.")
            return False
            
        # Clear any previous audio data
        st.session_state.audio_data = None
        
        # Start recording
        st.session_state.audio_data = sd.rec(
            int(SAMPLE_RATE * MAX_DURATION),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocking=False
        )
        return True
    except Exception as e:
        st.error(f"Error recording audio: {str(e)}")
        return False

# Function to stop recording
def stop_recording():
    try:
        sd.stop()
        
        # Add a small delay to ensure recording has stopped
        time.sleep(0.5)
        
        # Check if we have audio data
        if st.session_state.audio_data is None or len(st.session_state.audio_data) == 0:
            st.warning("No audio was recorded. Please try again.")
            return False
            
        return True
    except Exception as e:
        st.error(f"Error stopping recording: {str(e)}")
        return False

# Function to save audio to a temp file
def save_audio_to_file():
    if st.session_state.audio_data is not None:
        try:
            # Get the audio data and handle it safely
            audio_data = st.session_state.audio_data
            
            # Check if any audio was recorded
            if len(audio_data) == 0:
                st.error("No audio data was recorded.")
                return None
                
            # Make sure we have valid data with values
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
    return None

# Function to transcribe audio
def transcribe_audio(audio_file_path):
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
                language=st.session_state.language  # Use the selected language from session state
            )
        os.unlink(audio_file_path)  # Delete the temp file
        return transcription.text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
        return None

# Function to speak text using TTS
def speak_text(text, use_female_voice=True, voice_rate=0.75, voice_volume=0.9):
    try:
        print(f"Attempting to speak: {text[:30]}...")
        success = False
        
        # First try pyttsx3
        try:
            # Initialize TTS engine within the thread to avoid context issues
            tts_engine = pyttsx3.init()
            
            # Configure voice to be more feminine and slower
            voices = tts_engine.getProperty('voices')
            
            # On Windows, make sure to use SAPI5 driver
            if os.name == 'nt':  # Windows
                try:
                    # On some Windows systems, we need to reinitialize with SAPI5 explicitly
                    tts_engine = pyttsx3.init(driverName='sapi5')
                    voices = tts_engine.getProperty('voices')
                except:
                    # If that fails, continue with the original engine
                    pass
            
            # Find a female voice if requested
            if use_female_voice and voices:
                female_voice = None
                # Debug available voices
                print(f"Available voices: {len(voices)}")
                for voice in voices:
                    print(f"Voice: {voice.name}, ID: {voice.id}")
                    if "female" in voice.name.lower() or "fem" in voice.id.lower() or "zira" in voice.name.lower():
                        female_voice = voice.id
                        print(f"Selected female voice: {voice.name}")
                        break
                
                # Set the voice if a female voice was found
                if female_voice:
                    tts_engine.setProperty('voice', female_voice)
                    print(f"Set voice to: {female_voice}")
            
            # Get the current rate and adjust based on settings
            rate = tts_engine.getProperty('rate')
            tts_engine.setProperty('rate', rate * voice_rate)
            
            # Adjust volume based on settings
            tts_engine.setProperty('volume', voice_volume)
            
            print(f"Speaking text: {text[:30]}...")
            tts_engine.say(text)
            tts_engine.runAndWait()
            print("Speech completed")
            # Clean up
            tts_engine.stop()
            success = True
        except Exception as e:
            print(f"Primary TTS method failed: {str(e)}")
            success = False
        
        # If pyttsx3 failed, try platform-specific alternatives
        if not success:
            if os.name == 'nt':  # Windows
                try:
                    import win32com.client
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    print("Using Windows SAPI directly")
                    speaker.Speak(text)
                    print("Windows SAPI speech completed")
                    success = True
                except Exception as e:
                    print(f"Windows SAPI TTS failed: {str(e)}")
            elif os.name == 'posix':  # macOS or Linux
                try:
                    # For Mac, try using the say command
                    if os.system('which say >/dev/null 2>&1') == 0:
                        os.system(f'say "{text}"')
                        print("macOS 'say' command completed")
                        success = True
                    # For Linux, try using espeak
                    elif os.system('which espeak >/dev/null 2>&1') == 0:
                        os.system(f'espeak "{text}"')
                        print("Linux 'espeak' command completed")
                        success = True
                except Exception as e:
                    print(f"Platform-specific TTS failed: {str(e)}")
        
        if not success:
            print("WARNING: All TTS methods failed. Unable to speak text.")
            
    except Exception as e:
        # Can't use st.error here because of thread context issues
        print(f"Error during text-to-speech: {str(e)}")

# Available assistant functions
available_functions = {
    "schedule_event": lambda event_details: schedule_event(event_details),
    "draft_email": lambda email_details: draft_email(email_details),
    "web_search": lambda search_query: web_search(search_query)
}

# Function implementation for scheduling calendar events
def schedule_event(event_details):
    try:
        title = event_details.get("title", "Untitled Event")
        start_time_str = event_details.get("start_time")
        duration_minutes = event_details.get("duration_minutes", 60)
        location = event_details.get("location", "")
        
        # Parse the start time
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
        else:
            start_time = datetime.now() + timedelta(hours=1)
            start_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        # Calculate end time
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Generate meeting link if not provided
        meeting_link = ""
        if not location or "online" in location.lower() or "virtual" in location.lower() or "remote" in location.lower():
            # Generate a random meeting ID
            meeting_id = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            meeting_password = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6)])
            
            # Create a Zoom-like link
            meeting_link = f"https://meeting-link.example.com/j/{meeting_id}?pwd={meeting_password}"
            
            # Set location to the meeting link if not specified
            if not location:
                location = "Virtual Meeting"
        
        # Check for duplicate events
        is_duplicate = False
        for existing_event in st.session_state.calendar_events:
            if (existing_event.get("title") == title and 
                existing_event.get("start_time") == start_time.isoformat()):
                is_duplicate = True
                break
        
        # Only add if not a duplicate
        if not is_duplicate:
            # Add to calendar events
            event = {
                "title": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": duration_minutes,
                "location": location,
                "meeting_link": meeting_link
            }
            st.session_state.calendar_events.append(event)
        
        # Format response with meeting details
        response = f"Scheduled: {title} at {start_time.strftime('%Y-%m-%d %H:%M')}"
        if location:
            response += f"\nLocation: {location}"
        if meeting_link:
            response += f"\nMeeting Link: {meeting_link}"
        
        return response
    except Exception as e:
        return f"Failed to schedule event: {str(e)}"

# Function implementation for drafting emails
def draft_email(email_details):
    try:
        to = email_details.get("to", "")
        subject = email_details.get("subject", "")
        body = email_details.get("body", "")
        
        # Generate a random email ID
        email_id = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(8)])
        
        # Check for duplicate emails
        is_duplicate = False
        for existing_email in st.session_state.draft_emails:
            if (existing_email.get("to") == to and 
                existing_email.get("subject") == subject and
                existing_email.get("body") == body):
                is_duplicate = True
                # Use the existing email ID for consistency
                email_id = existing_email.get("id")
                break
        
        # Only add if not a duplicate
        if not is_duplicate:
            # Store the email draft
            email_draft = {
                "id": email_id,
                "to": to,
                "subject": subject,
                "body": body,
                "created_at": datetime.now().isoformat()
            }
            
            st.session_state.draft_emails.append(email_draft)
        
        # Format the response with the full email content
        response = f"Email drafted to {to} with subject '{subject}'\n\n"
        response += f"To: {to}\n"
        response += f"Subject: {subject}\n"
        response += f"Body:\n{body}\n\n"
        response += f"Email ID: {email_id} (Use this ID to reference this email later)"
        
        return response
    except Exception as e:
        return f"Failed to draft email: {str(e)}"

# Function implementation for web search
def web_search(search_query):
    try:
        query = search_query.get("query", "")
        
        # Use DuckDuckGo API for real web searches
        try:
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    abstract = result.get('Abstract', '')
                    related_topics = result.get('RelatedTopics', [])
                    
                    # Generate a direct answer instead of a list of links
                    search_results = []
                    
                    # Add abstract if available (this is typically the most direct answer)
                    if abstract:
                        return abstract
                    
                    # If no abstract, collect text from related topics and form a coherent answer
                    if related_topics:
                        combined_info = ""
                        for topic in related_topics[:5]:
                            if 'Text' in topic:
                                combined_info += topic['Text'] + " "
                        
                        if combined_info:
                            # Return a direct response without mentioning "search results"
                            return combined_info.strip()
                    
                    # If we still don't have results, try backup method
                    raise Exception("No results from primary search")
                except:
                    # If parsing fails, try backup search method
                    pass
            
            # Backup search method using a different approach
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            
            if response.status_code == 200:
                # Extract information from the HTML response
                content = response.text
                
                # Simple text extraction between result sections
                snippets = re.findall(r'<a class="result__snippet".*?>(.*?)</a>', content)
                
                if snippets:
                    # Combine snippets into a coherent response
                    combined_info = ""
                    for snippet in snippets[:3]:  # Limit to first 3 for conciseness
                        # Remove HTML tags
                        clean_snippet = re.sub(r'<.*?>', '', snippet)
                        if clean_snippet:
                            combined_info += clean_snippet + " "
                    
                    # Form a direct response without mentioning "search results"
                    if combined_info:
                        return combined_info.strip()
            
            # If no results found, return a more conversational response
            return f"Based on my knowledge, {query} is something I can tell you about, but I don't have specific current information. Can I help you with something else?"
            
        except Exception as e:
            print(f"Web search error: {str(e)}")
            # Provide a more direct response that doesn't mention search capabilities
            return f"Regarding {query}, I can tell you that it's something I have some information about, though my knowledge may not be completely up to date."
    except Exception as e:
        return f"I'm having trouble finding information about that right now. Is there something else I can help you with?"

# Process user input with GPT-4
def process_with_gpt(user_input):
    try:
        # Check if this is a duplicate request
        if user_input == st.session_state.last_processed_input:
            print(f"Skipping duplicate request: {user_input[:30]}...")
            # Return the last assistant response instead of processing again
            for i in range(len(st.session_state.messages) - 1, -1, -1):
                if st.session_state.messages[i]["role"] == "assistant" and st.session_state.messages[i].get("content"):
                    return st.session_state.messages[i]["content"]
            return "I've already processed this request."
        
        # Store the input as the last processed input
        st.session_state.last_processed_input = user_input
        
        if not client:
            st.error("OpenAI API key not set. Please add your API key in the sidebar.")
            return "Error: OpenAI API key not set. Please add your API key in the sidebar."
            
        # Add user message to conversation history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Define available functions for the model to call
        functions = [
            {
                "type": "function",
                "function": {
                    "name": "schedule_event",
                    "description": "Schedule a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title of the event"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                            },
                            "duration_minutes": {
                                "type": "integer",
                                "description": "Duration of the event in minutes"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location of the event (physical address or 'virtual' for online meetings)"
                            }
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "draft_email",
                    "description": "Draft an email with full content that can be copied and sent later",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "Email recipient's address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject line"
                            },
                            "body": {
                                "type": "string",
                                "description": "Full email body content with proper formatting, greetings, and signature"
                            }
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for real-time information such as current events, weather, sports scores, or any other online information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
        # Create the message list from history - only include user and assistant messages
        messages = []
        for msg in st.session_state.messages:
            if msg["role"] == "user" or (msg["role"] == "assistant" and msg.get("content") is not None):
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add system message to provide direct answers rather than links
        system_message = {
            "role": "system",
            "content": "You are a helpful voice assistant that provides direct answers to questions. For web searches, weather, news, and similar queries, always respond with concise, direct information rather than providing links or search result citations. Make your responses conversational and natural, as if you have the information yourself rather than acting as a search interface. Focus on giving complete, factual answers in a friendly tone."
        }
        
        # Add the system message at the beginning of the messages list
        messages = [system_message] + messages
        
        # Call the OpenAI API with function calling capability
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=functions,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Check if the model wants to call a function
        if response_message.tool_calls:
            # Add the assistant's response with tool calls to our conversation
            assistant_msg_with_tool_calls = {
                "role": "assistant",
                "content": None,
                "tool_calls": []
            }
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Add tool call to assistant message
                assistant_msg_with_tool_calls["tool_calls"].append({
                    "function": {"name": function_name, "arguments": tool_call.function.arguments},
                    "id": tool_call.id
                })
                
                # Process the function call if it's available
                if function_name in available_functions:
                    function_response = available_functions[function_name](function_args)
                    
                    # We'll add the tool response after adding the assistant message
                    tool_response = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    }
            
            # First add the assistant message with tool calls
            st.session_state.messages.append(assistant_msg_with_tool_calls)
            
            # Then add all tool responses
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
            
            # Construct a clean message history for the follow-up
            follow_up_messages = messages.copy()  # Start with our original messages
            
            # Add the assistant tool call
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
            
            # Add tool responses
            for tool_msg in tool_messages:
                follow_up_messages.append(tool_msg)
            
            # Get a follow-up response from the assistant
            second_response = client.chat.completions.create(
                model="gpt-4",
                messages=[system_message] + follow_up_messages
            )
            
            # Add the assistant's final response to our conversation
            assistant_response = second_response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            return assistant_response
        else:
            # If no function call, just return the response content
            assistant_response = response_message.content
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            return assistant_response
            
    except Exception as e:
        error_message = f"Error processing with GPT: {str(e)}"
        st.error(error_message)
        return f"I encountered an issue processing your request. {error_message}"

# UI Components
col1, col2 = st.columns([4, 1])  # Change ratio to give more space to the conversation

with col1:
    # Display conversation history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant" and msg.get("content"):
            st.chat_message("assistant").write(msg["content"])
        elif msg["role"] == "tool":
            # Display function results in a more subtle way
            with st.chat_message("system"):
                st.write(f"*{msg['content']}*")

with col2:
    # Voice recording controls
    if not st.session_state.recording:
        if st.button("🎤 Start Recording"):
            st.session_state.recording = True
            if record_audio():
                st.info("Recording... Press 'Stop' when done.")
                st.rerun()
    else:
        if st.button("⏹️ Stop Recording"):
            st.session_state.recording = False
            if stop_recording():
                audio_file = save_audio_to_file()
                if audio_file:
                    with st.spinner("Transcribing..."):
                        transcription = transcribe_audio(audio_file)
                        if transcription:
                            st.success("Transcription complete!")
                            
                            # Process the transcription with GPT
                            with st.spinner("Processing your request..."):
                                response = process_with_gpt(transcription)
                            
                            # Speak the response in a background thread
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
                            
                            # Don't rerun immediately to avoid interrupting the TTS
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Failed to transcribe audio.")
                else:
                    st.error("Failed to save audio.")

    # Display calendar events if there are any
    if st.session_state.calendar_events:
        st.subheader("Calendar Events")
        st.write(f"*{len(st.session_state.calendar_events)} event(s) found*")
        
        for event in st.session_state.calendar_events:
            start_time = datetime.fromisoformat(event["start_time"])
            
            # Create an expandable card for each event
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
            
            # Create an expandable card for each email
            with st.expander(f"✉️ To: {email['to']} - Subject: {email['subject']}"):
                st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**To:** {email['to']}")
                st.write(f"**Subject:** {email['subject']}")
                st.text_area("Body", email['body'], height=150, key=f"email_{email['id']}", disabled=True)
                st.write(f"**Email ID:** {email['id']}")
                
                # Add a copy button for the email body
                if st.button("Copy Email Content", key=f"copy_{email['id']}"):
                    # Create a string with the full email content
                    full_email = f"To: {email['to']}\nSubject: {email['subject']}\n\n{email['body']}"
                    st.code(full_email)
                    st.success("Email content copied to clipboard! You can now paste it into your email client.")

# Text input as an alternative to voice
user_input = st.text_input("Or type your command:", "")
if user_input:
    with st.spinner("Processing your request..."):
        response = process_with_gpt(user_input)
        
        # Speak the response in a background thread
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
    
    # Wait a moment for TTS to start before rerunning
    time.sleep(0.5)
    st.rerun()

# Show language selector in sidebar
with st.sidebar:
    # Create a language dropdown
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
    
    # Update language if changed
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        # Clear conversation when language changes
        if st.session_state.messages:
            if st.button(f"Change to {languages[selected_language]} and clear conversation"):
                st.session_state.messages = []
                st.rerun()
    
    # Add voice settings
    st.divider()
    st.subheader("Voice Settings")
    
    # Voice gender selection
    st.session_state.use_female_voice = st.checkbox("Use female voice", value=st.session_state.use_female_voice)
    
    # Voice rate slider (speed)
    st.session_state.voice_rate = st.slider(
        "Voice Speed", 
        min_value=0.5, 
        max_value=1.5, 
        value=st.session_state.voice_rate,
        step=0.1
    )
    
    # Voice volume slider
    st.session_state.voice_volume = st.slider(
        "Voice Volume", 
        min_value=0.1, 
        max_value=1.0, 
        value=st.session_state.voice_volume,
        step=0.1
    )
    
    # Test voice button
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
    
    # Add instructions without header
    st.divider()
    st.markdown("""
    ### Features:
    - **Real-time Web Search**: Ask about current events, weather, news, etc.
    - **Calendar Management**: Schedule meetings and events with automatic meeting links
    - **Email Drafting**: Create complete email drafts that you can copy and send
    
    ### Voice Commands Examples:
    - "Schedule a virtual meeting with John tomorrow at 2pm"
    - "Draft an email to sarah@example.com about the project update with a detailed message"
    - "Search the web for today's weather in New York"
    - "What's happening in the world right now?"
    
    ### Tips:
    - Use the calendar and email sections to view your scheduled events and drafted emails
    - For virtual meetings, a meeting link will be automatically generated
    - You can copy email content with the "Copy Email Content" button
    - Speak clearly and in a quiet environment
    """) 
