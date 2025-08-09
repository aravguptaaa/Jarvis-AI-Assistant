import pvporcupine
import pyaudio
import struct
import whisper
from TTS.api import TTS
import os
import wave
import time
import numpy as np
import audioop
from dotenv import load_dotenv
import google.generativeai as genai # <-- NEW: Import Google AI

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # <-- NEW: Load Google API Key

# --- NEW: Configure the Google AI client ---
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Google AI: {e}")
    print("Please ensure your GOOGLE_API_KEY is correct in the .env file.")
    exit()

WAKE_WORDS = ["jarvis"]
SHUTDOWN_COMMAND = "goodbye"
COMMAND_FILENAME = "command.wav"
RESPONSE_FILENAME = "response.wav"
SAMPLE_RATE = 16000

# Use a high-quality voice model (ensure you have run `brew install espeak`)
TTS_MODEL = "tts_models/en/vctk/vits"
TTS_SPEAKER = "p236" # A good male voice from the VCTK dataset

# Voice Activity Detection (VAD) configuration
SILENCE_THRESHOLD = 300
SILENCE_DURATION_S = 1.5
MAX_RECORDING_SECONDS = 15

# --- Voice I/O Functions ---

def speak(tts_instance, text, speaker_wav=None):
    """Generates and plays speech using the specified TTS model and speaker."""
    print(f"JARVIS: {text}")
    try:
        # Use the speaker argument if the model supports it (like VCTK)
        tts_instance.tts_to_file(text=text, file_path=RESPONSE_FILENAME, speaker=speaker_wav)
        os.system(f"afplay {RESPONSE_FILENAME} > /dev/null 2>&1")
    except Exception as e:
        print(f"Error during speech synthesis: {e}")
    finally:
        if os.path.exists(RESPONSE_FILENAME):
            os.remove(RESPONSE_FILENAME)

def record_command_vad(p, stream, sample_rate, chunk_size, filename):
    """Records audio dynamically, stopping after a period of silence."""
    print("Listening...")
    if not stream.is_active():
        stream.start_stream()

    frames = []
    is_speaking = False
    silent_chunks = 0
    num_silent_chunks_to_stop = int(SILENCE_DURATION_S * (sample_rate / chunk_size))
    max_chunks = int(MAX_RECORDING_SECONDS * (sample_rate / chunk_size))

    for _ in range(max_chunks):
        data = stream.read(chunk_size, exception_on_overflow=False)
        frames.append(data)
        rms = audioop.rms(data, 2)

        if rms > SILENCE_THRESHOLD:
            is_speaking = True
            silent_chunks = 0
        elif is_speaking:
            silent_chunks += 1
        
        if is_speaking and silent_chunks > num_silent_chunks_to_stop:
            print("...end of speech detected.")
            break
    
    if not is_speaking:
        print("...silence detected.")
        stream.stop_stream()
        return None

    print("...recording complete.")
    stream.stop_stream()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    return filename

def transcribe_command(whisper_model, filename):
    """Transcribes the recorded audio file."""
    if filename is None:
        return ""
    print("Transcribing...")
    result = whisper_model.transcribe(filename, fp16=False)
    if os.path.exists(filename):
        os.remove(filename)
    transcription = result['text'].strip()
    print(f"YOU SAID: '{transcription}'")
    return transcription

# --- NEW: AI Brain Function ---

def get_ai_response(command):
    """Sends the user's command to the Gemini AI and gets an intelligent response."""
    try:
        print("JARVIS is thinking...")
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        # This prompt defines JARVIS's personality.
        prompt = f"You are Jarvis, a witty, brilliant, and slightly sarcastic AI assistant, inspired by the one from the movies. A user has said this to you: '{command}'. Formulate a concise and in-character response."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        return "My apologies, sir. I seem to be having trouble connecting to my cognitive servers."

# --- Main Execution ---

if __name__ == "__main__":
    porcupine = None
    pa = None
    audio_stream = None

    try:
        # --- Initialize Models ---
        print("Initializing models... (This might take a moment)")
        porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keywords=WAKE_WORDS)
        whisper_model = whisper.load_model("base")
        tts = TTS(model_name=TTS_MODEL, progress_bar=False)
        pa = pyaudio.PyAudio()

        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        
        # --- Main Loop ---
        while True:
            print("\n--------------------------------------------------")
            print(f"JARVIS is in standby, listening for '{WAKE_WORDS[0]}'")
            print("--------------------------------------------------")
            
            audio_stream.start_stream()
            while True:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    print(f"Wake word '{WAKE_WORDS[0]}' detected!")
                    audio_stream.stop_stream()
                    break
            
            speak(tts, "Yes, sir?", speaker_wav=TTS_SPEAKER)
            
            # --- Conversation Loop ---
            while True: 
                command_path = record_command_vad(pa, audio_stream, SAMPLE_RATE, porcupine.frame_length, COMMAND_FILENAME)
                command_text = transcribe_command(whisper_model, command_path)

                if not command_text:
                    continue # If silence, listen again immediately
                
                # Use .lower() for robust command checking
                if SHUTDOWN_COMMAND in command_text.lower():
                    speak(tts, "Goodbye, sir. Returning to standby.", speaker_wav=TTS_SPEAKER)
                    break # Exit conversation loop
                
                # --- CORE LOGIC CHANGE: Call the AI Brain ---
                ai_reply = get_ai_response(command_text)
                speak(tts, ai_reply, speaker_wav=TTS_SPEAKER)

    except KeyboardInterrupt:
        print("\nUser interrupted. Shutting down.")
    except Exception as e:
        print(f"A critical error occurred: {e}")
    finally:
        print("Cleaning up resources.")
        if audio_stream is not None: audio_stream.close()
        if pa is not None: pa.terminate()
        if porcupine is not None: porcupine.delete()
        if os.path.exists(COMMAND_FILENAME): os.remove(COMMAND_FILENAME)
        if os.path.exists(RESPONSE_FILENAME): os.remove(RESPONSE_FILENAME)