import os
import logging
import threading
import time
import json
import pyaudio
import websocket
from urllib.parse import urlencode
from datetime import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Load API key from environment
api_key = os.getenv('ASSEMBLYAI_API_KEY')
if not api_key:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable is required")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio Configuration
FRAMES_PER_BUFFER = 800  # 50ms of audio
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16

# Connection parameters
CONNECTION_PARAMS = {
    "sample_rate": SAMPLE_RATE,
    "format_turns": True,
}
API_ENDPOINT_BASE_URL = "wss://streaming.assemblyai.com/v3/ws"
API_ENDPOINT = f"{API_ENDPOINT_BASE_URL}?{urlencode(CONNECTION_PARAMS)}"

class TranscriptionManager:
    def __init__(self):
        self.ws_app = None
        self.audio = None
        self.stream = None
        self.audio_thread = None
        self.ws_thread = None
        self.stop_event = threading.Event()
        self.is_streaming = False
        
    def on_ws_open(self, ws):
        """Called when the WebSocket connection is established."""
        logger.info("WebSocket connection opened")
        socketio.emit('session_started', {'session_id': 'connected'})
        
        # Start sending audio data in a separate thread
        def stream_audio():
            logger.info("Starting audio streaming...")
            while not self.stop_event.is_set():
                try:
                    audio_data = self.stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                    # Send audio data as binary message
                    ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
                except Exception as e:
                    logger.error(f"Error streaming audio: {e}")
                    break
            logger.info("Audio streaming stopped.")

        self.audio_thread = threading.Thread(target=stream_audio)
        self.audio_thread.daemon = True
        self.audio_thread.start()

    def on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == "Begin":
                session_id = data.get('id')
                expires_at = data.get('expires_at')
                logger.info(f"Session began: ID={session_id}")
                socketio.emit('session_started', {'session_id': session_id})
                
            elif msg_type == "Turn":
                transcript = data.get('transcript', '')
                formatted = data.get('turn_is_formatted', False)
                
                if transcript:
                    logger.info(f"Transcript: {transcript}")
                    socketio.emit('transcript_update', {
                        'transcript': transcript,
                        'is_final': formatted
                    })
                    
            elif msg_type == "Termination":
                audio_duration = data.get('audio_duration_seconds', 0)
                logger.info(f"Session terminated: {audio_duration}s")
                socketio.emit('session_terminated', {'duration': audio_duration})
                self.is_streaming = False
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def on_ws_error(self, ws, error):
        """Called when a WebSocket error occurs."""
        logger.error(f"WebSocket Error: {error}")
        socketio.emit('error', {'message': str(error)})
        self.stop_event.set()
        self.is_streaming = False

    def on_ws_close(self, ws, close_status_code, close_msg):
        """Called when the WebSocket connection is closed."""
        logger.info(f"WebSocket Disconnected: Status={close_status_code}")
        self.stop_event.set()
        self.is_streaming = False
        
        # Clean up audio resources
        if self.stream:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.audio:
            self.audio.terminate()
            self.audio = None

transcription_manager = TranscriptionManager()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_transcription')
def handle_start_transcription():
    if transcription_manager.is_streaming:
        emit('error', {'message': 'Transcription already in progress'})
        return
        
    try:
        # Initialize PyAudio
        transcription_manager.audio = pyaudio.PyAudio()
        
        # Open microphone stream
        transcription_manager.stream = transcription_manager.audio.open(
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            channels=CHANNELS,
            format=FORMAT,
            rate=SAMPLE_RATE,
        )
        
        # Create WebSocketApp
        transcription_manager.ws_app = websocket.WebSocketApp(
            API_ENDPOINT,
            header={"Authorization": api_key},
            on_open=transcription_manager.on_ws_open,
            on_message=transcription_manager.on_ws_message,
            on_error=transcription_manager.on_ws_error,
            on_close=transcription_manager.on_ws_close,
        )
        
        transcription_manager.is_streaming = True
        transcription_manager.stop_event.clear()
        emit('transcription_started', {'status': 'success'})
        
        # Run WebSocketApp in a separate thread
        transcription_manager.ws_thread = threading.Thread(
            target=transcription_manager.ws_app.run_forever
        )
        transcription_manager.ws_thread.daemon = True
        transcription_manager.ws_thread.start()
        
    except Exception as e:
        logger.error(f"Failed to start transcription: {e}")
        emit('error', {'message': str(e)})
        transcription_manager.is_streaming = False

@socketio.on('stop_transcription')
def handle_stop_transcription():
    if transcription_manager.ws_app and transcription_manager.is_streaming:
        try:
            # Send termination message
            if transcription_manager.ws_app.sock and transcription_manager.ws_app.sock.connected:
                terminate_message = {"type": "Terminate"}
                transcription_manager.ws_app.send(json.dumps(terminate_message))
            
            # Close the WebSocket connection
            transcription_manager.ws_app.close()
            transcription_manager.is_streaming = False
            emit('transcription_stopped', {'status': 'success'})
        except Exception as e:
            logger.error(f"Error stopping transcription: {e}")
            emit('error', {'message': str(e)})
    else:
        emit('error', {'message': 'No active transcription session'})

@socketio.on('disconnect')
def handle_disconnect():
    if transcription_manager.ws_app and transcription_manager.is_streaming:
        try:
            transcription_manager.ws_app.close()
            transcription_manager.is_streaming = False
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5002)
