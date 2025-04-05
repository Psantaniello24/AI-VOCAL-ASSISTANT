import streamlit as st
import av
import numpy as np
import tempfile
import os
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from typing import List, Callable

# WebRTC Configuration - uses Google's free STUN servers
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

class AudioProcessor:
    def __init__(self):
        self.audio_buffer = []
        self.recording = False
        self.sample_rate = 16000
        
    def start_recording(self):
        """Start recording audio"""
        self.audio_buffer = []
        self.recording = True
        
    def stop_recording(self):
        """Stop recording audio"""
        self.recording = False
        
    def process_audio(self, frame):
        """Process incoming audio frames"""
        if self.recording:
            sound = frame.to_ndarray()
            sound = np.mean(sound, axis=1).astype(np.float32)
            self.audio_buffer.append(sound)
        return frame
        
    def get_audio_data(self):
        """Get the recorded audio data as a numpy array"""
        if not self.audio_buffer:
            return None
        audio_data = np.concatenate(self.audio_buffer)
        return audio_data
        
    def save_to_wav_file(self):
        """Save the recorded audio to a temporary WAV file"""
        import scipy.io.wavfile as wav_file
        
        audio_data = self.get_audio_data()
        if audio_data is None:
            return None
            
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            file_path = temp_file.name
            
        # Normalize and convert to int16
        if np.max(np.abs(audio_data)) > 0:
            audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
        else:
            audio_data = np.int16(audio_data * 0)
            
        # Save to file
        wav_file.write(file_path, self.sample_rate, audio_data)
        return file_path

def create_webrtc_audio_recorder():
    """Create and return a WebRTC audio recorder component"""
    audio_processor = AudioProcessor()
    
    # Create WebRTC streamer
    webrtc_ctx = webrtc_streamer(
        key="voice-recorder",
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=RTC_CONFIGURATION,
        audio_receiver_size=1024,
        media_stream_constraints={"video": False, "audio": True},
    )
    
    # Set up recording controls
    col1, col2 = st.columns(2)
    
    with col1:
        if webrtc_ctx.state.playing:
            if st.button("Start Recording", key="start_rec"):
                audio_processor.start_recording()
                st.session_state.recording_webrtc = True
    
    with col2:
        if webrtc_ctx.state.playing and st.session_state.get("recording_webrtc", False):
            if st.button("Stop Recording", key="stop_rec"):
                audio_processor.stop_recording()
                st.session_state.recording_webrtc = False
                st.session_state.audio_file_path = audio_processor.save_to_wav_file()
                st.success("Recording completed!")
    
    # Process audio frames when available
    if webrtc_ctx.audio_receiver:
        if webrtc_ctx.state.playing and st.session_state.get("recording_webrtc", False):
            st.info("Recording in progress...")
            
        try:
            audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
            for frame in audio_frames:
                audio_processor.process_audio(frame)
        except Exception as e:
            st.error(f"Error processing audio: {e}")
            
    return webrtc_ctx.state.playing and st.session_state.get("audio_file_path")

if __name__ == "__main__":
    st.title("WebRTC Audio Recorder Test")
    audio_file_ready = create_webrtc_audio_recorder()
    
    if audio_file_ready:
        st.audio(st.session_state.audio_file_path)
        st.success(f"Audio saved to: {st.session_state.audio_file_path}") 