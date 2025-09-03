# Real-Time Call Transcription App

## Exponent Labs LLC

A simple, up-to-date, real-time audio transcription application using AssemblyAI's streaming API with a modern web interface.

## Features

- 🎤 Real-time audio transcription from microphone
- 🌐 Web-based interface with live updates
- 📱 Mobile-responsive design
- ⚡ WebSocket communication for instant updates
- 🎨 Modern, clean UI with status indicators
- 📊 Session tracking and duration display

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and add your AssemblyAI API key (**use the transcription API key NOT the generic API key I made that mistake so you don't have to**):

```bash
cp env.example .env
```

Edit `.env` and add your AssemblyAI API key:
```
ASSEMBLYAI_API_KEY=your_actual_api_key_here
```

Get your API key from [AssemblyAI Dashboard](https://www.assemblyai.com/dashboard/signup)

### 3. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5002`

## Usage

1. Open your browser and navigate to `http://localhost:5002`
2. Click "Start Transcription" to begin recording
3. Speak into your microphone - transcription will appear in real-time
4. Click "Stop Transcription" to end the session
5. Use "Clear" to reset the transcription display

## Technical Details

- **Backend**: Flask with Flask-SocketIO for WebSocket communication
- **Frontend**: Vanilla JavaScript with Socket.IO client
- **Audio Processing**: AssemblyAI streaming v3 WebSocket API with PyAudio
- **Real-time Updates**: Direct WebSocket connection to AssemblyAI for instant transcription

## File Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── templates/
│   └── index.html        # Main web interface
└── static/
    ├── css/
    │   └── style.css     # Styling
    └── js/
        └── app.js        # Frontend JavaScript
```

## Browser Compatibility

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge

## Troubleshooting

### Microphone Access
- Ensure your browser has microphone permissions
- Check system audio settings

### API Key Issues
- Verify your AssemblyAI API key is correct
- Ensure you have sufficient credits in your AssemblyAI account

### Audio Issues
- Check that PyAudio is properly installed
- On macOS, you may need to install portaudio: `brew install portaudio`
- On Linux, install: `sudo apt-get install portaudio19-dev`

## License

MIT License