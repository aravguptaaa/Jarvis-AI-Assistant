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
import google.generativeai as genai
import datetime   # <-- ADDED for getting time
import subprocess # <-- ADDED for opening apps

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Google AI: {e}\nPlease ensure your GOOGLE_API_KEY is correct.")
    exit()

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

# --- NEW: Define Python Functions as "Tools" ---

def get_current_time():
    """Returns the current time in a human-readable format."""
    print("TOOL: Getting current time.")
    now = datetime.datetime.now()
    return now.strftime("%I:%M %p") # Example: 04:30 PM

def open_application(app_name: str):
    """Opens a specified application on the Mac."""
    print(f"TOOL: Opening application '{app_name}'.")
    try:
        # Use subprocess for better control and security
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Successfully opened {app_name}."
    except Exception as e:
        return f"An error occurred while trying to open {app_name}: {e}"

# --- NEW: Describe the Tools for the AI Model ---

# --- NEW: Describe the Tools for the AI Model ---

tools_list = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="get_current_time",
                description="Use this function to get the current time.",
                # THE FIX IS HERE: Define an empty object schema
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={}
                )
            ),
            genai.protos.FunctionDeclaration(
                name="open_application",
                description="Use this function to open any application on the user's Mac.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "app_name": genai.protos.Schema(type=genai.protos.Type.STRING, description="The name of the application to open (e.g., 'Safari', 'WhatsApp').")
                    },
                    required=["app_name"]
                )
            )
        ]
    )
]

# --- NEW: A dictionary to map tool names to the actual Python functions ---
available_tools = {
    "get_current_time": get_current_time,
    "open_application": open_application,
}


# --- Voice I/O Functions (Unchanged from jarvis_main2.py) ---

def speak(tts_instance, text, speaker_wav=None):
    print(f"JARVIS: {text}")
    try:
        tts_instance.tts_to_file(text=text, file_path=RESPONSE_FILENAME, speaker=speaker_wav)
        os.system(f"afplay {RESPONSE_FILENAME} > /dev/null 2>&1")
    except Exception as e:
        print(f"Error during speech synthesis: {e}")
    finally:
        if os.path.exists(RESPONSE_FILENAME):
            os.remove(RESPONSE_FILENAME)

def record_command_vad(p, stream, sample_rate, chunk_size, filename):
    print("Listening...")
    if not stream.is_active(): stream.start_stream()
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
    if filename is None: return ""
    print("Transcribing...")
    result = whisper_model.transcribe(filename, fp16=False)
    if os.path.exists(filename): os.remove(filename)
    transcription = result['text'].strip()
    print(f"YOU SAID: '{transcription}'")
    return transcription

# --- REVISED: The AI Brain now handles conversations and tools ---

def run_conversation(command, ai_model):
    """Handles the full conversation logic, including function calling."""
    print("JARVIS is thinking...")
    
    prompt = f"""
    You are Jarvis, a witty and brilliant AI assistant. The user has said: '{command}'.
    Analyze the request. 
    1. If it's a general question (e.g., 'what is a black hole?'), formulate a helpful, in-character response directly.
    2. If it requires a computer action (like getting time or opening an app), use the available tools.
    """
    
    try:
        response = ai_model.generate_content(prompt, tools=tools_list)
        response_part = response.candidates[0].content.parts[0]

        if response_part.function_call.name:
            function_name = response_part.function_call.name
            function_args = {key: value for key, value in response_part.function_call.args.items()}
            
            print(f"AI wants to use tool: {function_name} with args: {function_args}")
            
            function_to_call = available_tools[function_name]
            function_result = function_to_call(**function_args)
            
            print(f"Tool Result: '{function_result}'")

            # Send the result back to the model to get a natural language response
            final_response = ai_model.generate_content(
                [
                    genai.Part(text=prompt),
                    response.candidates[0].content,
                    genai.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={"result": str(function_result)}
                        )
                    )
                ],
                tools=tools_list
            )
            return final_response.text.strip()
        else:
            return response.text.strip()
            
    except Exception as e:
        print(f"AI Error: {e}")
        return "My apologies, sir. I've encountered a cognitive dissonance."

# --- Main Execution ---

if __name__ == "__main__":
    porcupine = None
    pa = None
    audio_stream = None

    try:
        print("Initializing models... (This might take a moment)")
        porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keywords=WAKE_WORDS)
        whisper_model = whisper.load_model("base")
        tts = TTS(model_name=TTS_MODEL, progress_bar=False)
        
        # --- NEW: Initialize the AI model once, using a version that supports tool use ---
        ai_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=porcupine.frame_length
        )
        
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
            
            while True: 
                command_path = record_command_vad(pa, audio_stream, SAMPLE_RATE, porcupine.frame_length, COMMAND_FILENAME)
                command_text = transcribe_command(whisper_model, command_path)

                if not command_text: continue
                
                if SHUTDOWN_COMMAND in command_text.lower():
                    speak(tts, "Goodbye, sir. Returning to standby.", speaker_wav=TTS_SPEAKER)
                    break
                
                # --- CORE LOGIC CHANGE: Use the new conversation handler ---
                ai_reply = run_conversation(command_text, ai_model)
                speak(tts, ai_reply, speaker_wav=TTS_SPEAKER)

    except KeyboardInterrupt:
        print("\nUser interrupted. Shutting down.")
    except Exception as e:
        print(f"A critical error occurred: {e}")
    finally:
        print("Cleaning up resources.")
        if audio_stream: audio_stream.close()
        if pa: pa.terminate()
        if porcupine: porcupine.delete()
        if os.path.exists(COMMAND_FILENAME): os.remove(COMMAND_FILENAME)
        if os.path.exists(RESPONSE_FILENAME): os.remove(RESPONSE_FILENAME)