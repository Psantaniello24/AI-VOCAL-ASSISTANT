# Voice-Controlled Personal Assistant

A powerful voice-controlled personal assistant built with Python that can process spoken commands, schedule events, draft emails, perform web searches, and more. Easily connects with Google Mail and integrates with various social media platforms.

## Video example : 

![Demo GIF](./assistant_demo.gif)


## Features

- **Voice Recognition**: Records audio using sounddevice and transcribes with OpenAI's Whisper API
- **Natural Language Processing**: Processes commands using OpenAI GPT-4 with function calling
- **Command Capabilities**:
  - Calendar scheduling with automatic meeting link generation
  - Email drafting with seamless Google Mail connectivity
  - Web searches with direct answers (no links)
  - Social media integration potential
- **Multilingual Support**: Switch between 14+ languages in the interface
- **Customizable Voice**: Adjust gender, speed, and volume of the assistant's voice
- **Memory**: Maintains conversation history for context-aware responses
- **Streamlit Interface**: User-friendly web interface with recording controls and conversation display
- **Text-to-Speech**: Speaks responses using pyttsx3
- **Error Handling**:
  - Background noise detection
  - API rate limit management
  - Invalid command handling

## System Requirements

- Python 3.8 or higher
- OpenAI API key
- Internet connection for API access
- Microphone for voice input
- Speakers for voice output

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/voice-assistant.git
   cd voice-assistant
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Running the Application

To run the Streamlit web interface:

```
streamlit run app.py
```

This will launch a local web server and open the application in your default browser.

## Usage

1. In the web interface, click the "Start Recording" button.
2. Speak your command clearly (e.g., "Schedule a meeting with John tomorrow at 2 PM").
3. Click "Stop Recording" when finished.
4. The application will process your command and provide a spoken and written response.
5. You can also select your preferred language from the sidebar.
6. Adjust voice settings in the sidebar to customize the assistant's speech.

### Example Commands

- "Schedule a meeting with Sarah on Friday at 3 PM for 30 minutes"
- "Draft an email to john@example.com about the project update"
- "Search the web for the weather forecast for New York"
- "What events do I have scheduled for tomorrow?"
- "Post an update to my Twitter account" (with social media integration)
- "Check my Gmail inbox for unread messages"

## Integration Capabilities

The assistant is designed for easy integration with various services:

- **Google Mail**: Connect your Gmail account for email drafting, reading, and management
- **Google Calendar**: Sync with your Google Calendar for event scheduling and management
- **Social Media**: Framework in place for connecting with Twitter, Facebook, LinkedIn, and other platforms
- **Messaging Apps**: Can be extended to connect with WhatsApp, Telegram, and other messaging services

## Customization

You can customize the assistant's behavior by modifying the app.py file.

To connect with Google services and social media:
1. Create API credentials for the desired service
2. Add the credentials to your `.env` file
3. Uncomment the relevant code sections in the application files

## Troubleshooting

Common issues and solutions:

1. **Microphone not working**:
   - Ensure your microphone is properly connected and set as the default input device.
   - Check that your browser has permission to access your microphone.

2. **API Key issues**:
   - Verify your OpenAI API key is correct in the `.env` file.
   - Check that you have sufficient credits in your OpenAI account.

3. **Background noise**:
   - Use the assistant in a quiet environment for better voice recognition.


## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for their Whisper and GPT APIs
- Streamlit for the amazing web framework 