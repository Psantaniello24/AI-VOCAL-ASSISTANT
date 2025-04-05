import streamlit as st
import os
import sys

# Set the page config before anything else
st.set_page_config(
    page_title="Voice Assistant",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get OpenAI API key from Streamlit secrets if available
if 'openai' in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["openai"]["api_key"]

# Import the main app module
try:
    import app
except Exception as e:
    st.error(f"Error loading the application: {e}")
    st.error("Please make sure you've configured the OpenAI API key in Streamlit secrets.")
    
    # Display setup instructions if there's an error
    st.markdown("""
    ## Setup Instructions
    
    This application requires an OpenAI API key to function properly.
    
    ### For Streamlit Cloud:
    1. Go to your app settings in Streamlit Cloud
    2. Click on "Secrets"
    3. Add the following configuration:
    ```
    [openai]
    api_key = "your_openai_api_key_here"
    ```
    
    ### For local development:
    Create a `.env` file with:
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    ```
    
    ### Note:
    This application uses your browser's microphone access. Make sure to:
    1. Allow microphone access when prompted
    2. Use a recent version of Chrome, Firefox, or Edge
    """) 