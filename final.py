# main_jarvis.py

import pvporcupine
import pyaudio
import struct
import whisper
from TTS.api import TTS
import os
import wave
import time
import audioop
from dotenv import load_dotenv
import google.generativeai as genai
import json

# --- IMPORT OUR NEW ACTIONS MODULE ---
import actions

# --- Load Environment Variables ---
load_dotenv()
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Configure Google AI ---
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Google AI. Check your API key. Error: {e}")
    exit()

# --- Configuration ---
WAKE_WORDS = ["jarvis"]
SHUTDOWN_COMMAND = "goodbye"
COMMAND_FILENAME = "command.wav"
RESPONSE_FILENAME = "response.wav"
SAMPLE_RATE = 16000
TTS_MODEL = "tts_models/en/vctk/vits"
TTS_SPEAKER = "p236"
SILENCE_THRESHOLD = 300
SILENCE_DURATION_S = 1.5
MAX_RECORDING_SECONDS = 15

# --- Action Registry: Map tool names to functions ---
AVAILABLE_TOOLS = {
    "open_application": actions.open_application,
    "search_files_on_mac": actions.search_files_on_mac,
    "get_calendar_events": actions.get_calendar_events,
    "get_battery_level": actions.get_battery_level,
}

# --- Voice I/O Functions (Unchanged) ---
def speak(tts_instance, text, speaker_wav=None):
    print(f"JARVIS: {text}")
    try:
        # Clean text for TTS
        clean_text = text.replace('%', ' percent')
        tts_instance.tts_to_file(text=clean_text, file_path=RESPONSE_FILENAME, speaker=speaker_wav)
        os.system(f"afplay {RESPONSE_FILENAME} > /dev/null 2>&1")
    except Exception as e:
        print(f"Error during speech synthesis: {e}")
    finally:
        if os.path.exists(RESPONSE_FILENAME): os.remove(RESPONSE_FILENAME)

def record_command_vad(p, stream, sample_rate, chunk_size, filename):
    print("Listening...")
    if not stream.is_active(): stream.start_stream()
    frames, is_speaking, silent_chunks = [], False, 0
    num_silent_chunks_to_stop = int(SILENCE_DURATION_S * (sample_rate / chunk_size))
    max_chunks = int(MAX_RECORDING_SECONDS * (sample_rate / chunk_size))
    for _ in range(max_chunks):
        data = stream.read(chunk_size, exception_on_overflow=False)
        frames.append(data)
        if audioop.rms(data, 2) > SILENCE_THRESHOLD:
            is_speaking, silent_chunks = True, 0
        elif is_speaking:
            silent_chunks += 1
        if is_speaking and silent_chunks > num_silent_chunks_to_stop: break
    if not is_speaking:
        stream.stop_stream()
        return None
    stream.stop_stream()
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
    return filename

def transcribe_command(whisper_model, filename):
    if filename is None: return ""
    print("Transcribing...")
    result = whisper_model.transcribe(filename, fp16=False)
    if os.path.exists(filename): os.remove(filename)
    transcription = result['text'].strip()
    print(f"YOU SAID: '{transcription}'")
    return transcription

# --- AI Brain with Tool-Using Capability ---
def get_ai_response(command):
    """
    Gets a response from the AI and cleans it for tool use.
    """
    print("JARVIS is thinking...")
    system_prompt = f"""
    You are Jarvis, a witty and brilliant AI assistant. Analyze the user's command: "{command}"

    You have access to the following tools:
    1. open_application(app_name: str): Opens a specified application.
    2. search_files_on_mac(query: str): Searches for files on the user's Mac.
    3. get_calendar_events(): Retrieves today's events from the calendar.
    4. get_battery_level(): Checks the current battery level and status.

    - If the command matches a tool's capability, you MUST respond with ONLY a JSON object:
      {{"tool_name": "function_name", "parameters": {{"arg_name": "value"}}}}
    - For tools without arguments (like get_calendar_events or get_battery_level), use empty parameters:
      {{"tool_name": "function_name", "parameters": {{}}}}
    - If the command is conversational (e.g., a greeting, a random question), respond naturally and in character, without using JSON.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(system_prompt)
        
        # --- THIS IS THE CRITICAL FIX ---
        # Clean the response to remove markdown wrappers.
        ai_text = response.text.strip()
        if ai_text.startswith("```json"):
            ai_text = ai_text.strip("```json").strip("`").strip()

        return ai_text

    except Exception as e:
        print(f"AI Error: {e}")
        return "My apologies, sir. My cognitive circuits are experiencing a malfunction."

# --- Main Execution ---
if __name__ == "__main__":
    porcupine, pa, audio_stream = None, None, None
    try:
        print("Initializing models...")
        porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keywords=WAKE_WORDS)
        whisper_model = whisper.load_model("base")
        tts = TTS(model_name=TTS_MODEL, progress_bar=False)
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16,
                               input=True, frames_per_buffer=porcupine.frame_length)
        
        while True:
            print(f"\n--- JARVIS is in standby, listening for '{WAKE_WORDS[0]}' ---")
            audio_stream.start_stream()
            while True:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                if porcupine.process(struct.unpack_from("h" * porcupine.frame_length, pcm)) >= 0:
                    audio_stream.stop_stream()
                    break
            
            speak(tts, "Yes, sir?", speaker_wav=TTS_SPEAKER)
            
            while True: 
                command_path = record_command_vad(pa, audio_stream, SAMPLE_RATE, porcupine.frame_length, COMMAND_FILENAME)
                command_text = transcribe_command(whisper_model, command_path)
                
                if not command_text: continue
                if SHUTDOWN_COMMAND in command_text.lower():
                    speak(tts, "Goodbye, sir.", speaker_wav=TTS_SPEAKER)
                    break
                
                ai_output = get_ai_response(command_text)
                
                try:
                    # Attempt to parse the AI's output as a tool command
                    tool_call = json.loads(ai_output)
                    tool_name = tool_call.get("tool_name")
                    parameters = tool_call.get("parameters", {})
                    
                    if tool_name in AVAILABLE_TOOLS:
                        function_to_call = AVAILABLE_TOOLS[tool_name]
                        action_result = function_to_call(**parameters)
                        speak(tts, action_result, speaker_wav=TTS_SPEAKER)
                    else:
                        speak(tts, "An unknown tool was requested. I am unable to perform that action.", speaker_wav=TTS_SPEAKER)

                except (json.JSONDecodeError, TypeError):
                    # If it's not JSON, it's a conversational reply
                    speak(tts, ai_output, speaker_wav=TTS_SPEAKER)

    except KeyboardInterrupt:
        print("\nUser initiated shutdown. Goodbye.")
    except Exception as e:
        print(f"A critical error occurred: {e}")
    finally:
        print("Cleaning up resources...")
        if audio_stream: audio_stream.close()
        if pa: pa.terminate()
        if porcupine: porcupine.delete()
        if os.path.exists(COMMAND_FILENAME): os.remove(COMMAND_FILENAME)
        if os.path.exists(RESPONSE_FILENAME): os.remove(RESPONSE_FILENAME)