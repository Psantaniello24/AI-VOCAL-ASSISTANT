#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies if needed
if [ ! -f "venv/.dependencies_installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.dependencies_installed
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your OpenAI API key."
    exit 1
fi

# Function to start components
start_components() {
    # Start API server
    echo "Starting API server..."
    python api.py &
    API_PID=$!
    
    # Wait a moment for API to start
    sleep 2
    
    # Start automation script
    echo "Starting automation script..."
    python automation.py &
    AUTOMATION_PID=$!
    
    # Start Streamlit app
    echo "Starting Streamlit app..."
    streamlit run app.py &
    STREAMLIT_PID=$!
    
    echo "All components started!"
    echo "API server PID: $API_PID"
    echo "Automation script PID: $AUTOMATION_PID"
    echo "Streamlit app PID: $STREAMLIT_PID"
    
    echo "Press Ctrl+C to stop all components."
    
    # Wait for user to press Ctrl+C
    trap "kill $API_PID $AUTOMATION_PID $STREAMLIT_PID; exit" INT
    wait
}

# Parse command line arguments
case "$1" in
    api)
        echo "Starting API server only..."
        python api.py
        ;;
    app)
        echo "Starting Streamlit app only..."
        streamlit run app.py
        ;;
    automation)
        echo "Starting automation script only..."
        python automation.py
        ;;
    *)
        start_components
        ;;
esac 