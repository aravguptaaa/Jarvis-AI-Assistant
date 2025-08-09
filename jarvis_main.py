import pvporcupine
import pyaudio
import struct
import whisper
from TTS.api import TTS
import os
import wave
import time
import numpy as np # --- MODIFICATION: Added for audio processing ---
import audioop     # --- MODIFICATION: Added for RMS calculation ---
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

WAKE_WORDS = ["jarvis"]
SHUTDOWN_COMMAND = "goodbye"
COMMAND_FILENAME = "command.wav"
RESPONSE_FILENAME = "response.wav"
SAMPLE_RATE = 16000
TTS_MODEL = "tts_models/en/vctk/vits"

# --- MODIFICATION: New configuration for Voice Activity Detection (VAD) ---
# You may need to adjust this threshold based on your microphone and background noise
SILENCE_THRESHOLD = 300  # RMS value below which audio is considered silent
SILENCE_DURATION_S = 1.5 # How many seconds of silence triggers the end of recording
MAX_RECORDING_SECONDS = 15 # A failsafe to prevent recording forever

def speak(tts_instance, text):
    """Generates and plays speech, and cleans up special characters for TTS."""
    print(f"JARVIS: {text}")
    clean_text = text.replace('%', ' percent')
    tts_instance.tts_to_file(text=clean_text, file_path=RESPONSE_FILENAME, speaker="p236")
    os.system(f"afplay {RESPONSE_FILENAME} > /dev/null 2>&1")
    time.sleep(0.1)
    if os.path.exists(RESPONSE_FILENAME):
        os.remove(RESPONSE_FILENAME)

# --- MODIFICATION: New dynamic recording function with VAD ---
def record_command_vad(p, stream, sample_rate, chunk_size, filename):
    """
    Records audio dynamically, stopping after a period of silence.
    """
    print("Listening for your command...")

    if not stream.is_active():
        stream.start_stream()

    frames = []
    is_speaking = False
    silent_chunks = 0
    
    # Calculate how many silent chunks constitute the silence duration
    chunks_per_second = sample_rate / chunk_size
    num_silent_chunks_to_stop = int(SILENCE_DURATION_S * chunks_per_second)
    max_chunks = int(MAX_RECORDING_SECONDS * chunks_per_second)

    for i in range(max_chunks):
        data = stream.read(chunk_size, exception_on_overflow=False)
        frames.append(data)

        # Calculate RMS of the current chunk to detect volume
        rms = audioop.rms(data, 2)  # 2 is for 16-bit audio

        if rms > SILENCE_THRESHOLD:
            # If sound is detected, reset the silence counter
            is_speaking = True
            silent_chunks = 0
        elif is_speaking:
            # If we were speaking, but are now silent, start counting
            silent_chunks += 1

        # If silence duration is met after speaking, stop recording
        if is_speaking and silent_chunks > num_silent_chunks_to_stop:
            print("...end of speech detected.")
            break
            
    # If the loop finishes without detecting speech, treat it as silence
    if not is_speaking:
        print("...no speech detected.")
        stream.stop_stream()
        return None # Return None to indicate silence

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
    """Transcribes the recorded command."""
    # --- MODIFICATION: Handle the case where recording returned None (silence) ---
    if filename is None:
        return "" # Return an empty string immediately
        
    print("Transcribing...")
    # Use a smaller, faster model if speed is critical. "base" is a good balance.
    result = whisper_model.transcribe(filename, fp16=False) # Use FP32 on CPU
    if os.path.exists(filename):
        os.remove(filename)
    transcription = result['text'].lower().strip()
    print(f"YOU SAID: '{transcription}'")
    return transcription

# --- Main Execution ---
if __name__ == "__main__":
    porcupine = None
    pa = None
    audio_stream = None

    try:
        # --- Initialize Models ---
        print("Initializing models... (This might take a moment)")
        porcupine = pvporcupine.create(
            access_key=PICOVOICE_ACCESS_KEY,
            keywords=WAKE_WORDS
        )
        os.environ["COQUI_LOG_LEVEL"] = "error"
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
        
        # --- Main Loop: Waits for Wake Word ---
        while True:
            print("--------------------------------------------------")
            print(f"JARVIS is in standby, listening for '{WAKE_WORDS[0]}'")
            print("--------------------------------------------------")
            
            audio_stream.start_stream()
            while True:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                keyword_index = porcupine.process(pcm)
                if keyword_index >= 0:
                    print(f"Wake word '{WAKE_WORDS[0]}' detected!")
                    audio_stream.stop_stream()
                    break
            
            speak(tts, "Yes sir?")
            
            # --- Conversation Loop ---
            while True: 
                # --- MODIFICATION: Using the new VAD recording function ---
                command_audio_path = record_command_vad(
                    pa,
                    audio_stream, 
                    SAMPLE_RATE, 
                    porcupine.frame_length, 
                    COMMAND_FILENAME
                )
                command_text = transcribe_command(whisper_model, command_audio_path)

                # --- MODIFICATION: Re-ordered logic for clarity and correctness ---
                if not command_text:
                    # Requirement 3: If nothing was said, just listen again.
                    print("Silence detected, listening again...")
                    continue # Skips the rest of the loop and starts listening again
                elif SHUTDOWN_COMMAND in command_text:
                    # Requirement 1: Exit conversation loop and return to standby.
                    speak(tts, "Goodbye, sir. Returning to standby.")
                    break # This break exits the conversation loop
                else:
                    # Default behavior: process the command.
                    response = f"Command received... {command_text}"
                    speak(tts, response)

    except KeyboardInterrupt:
        print("\nUser interrupted. Shutting down.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Cleaning up resources.")
        if audio_stream is not None:
            if audio_stream.is_active():
                audio_stream.stop_stream()
            audio_stream.close()
        if pa is not None:
            pa.terminate()
        if porcupine is not None:
            porcupine.delete()
        if os.path.exists(COMMAND_FILENAME):
            os.remove(COMMAND_FILENAME)
        if os.path.exists(RESPONSE_FILENAME):
            os.remove(RESPONSE_FILENAME)