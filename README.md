# Jarvis: Your Personal AI Assistant for macOS

<p align="center">
  <img src="https://i.imgur.com/vHqQz5F.gif" alt="Jarvis in Action" width="800"/>
  <em>A voice-powered AI assistant to command your macOS universe, inspired by the one and only.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/OS-macOS-lightgrey?style=for-the-badge&logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

---

## Overview

Ever wanted your own Jarvis? This project makes it a reality. It's a sophisticated, voice-controlled AI assistant that lives on your Mac. It's not just a chatbot; it's an integrated tool that can understand your commands, hold intelligent conversations, and perform real actions on your computer—like opening apps, searching for files, and checking your schedule.

This project is built on a powerful three-part architecture:

1.  **The Voice (Input/Output):** Captures your voice commands and speaks back responses in real-time.
2.  **The "Brain" (Intelligence):** Uses Google's Gemini API to understand requests and decide on the best course of action.
3.  **The Actions (Control):** Executes scripts to control your Mac, bringing the AI's decisions to life.

## Features

-   🗣️ **Voice Activation:** Wakes up to the hotword "Jarvis" using Picovoice Porcupine.
-   🧠 **Intelligent Conversation:** Powered by Google's `gemini-1.5-flash` model for witty, context-aware, and natural dialogue.
-   ⚡ **Real-time Transcription:** Uses OpenAI's Whisper for fast and accurate speech-to-text.
-   🔊 **High-Quality TTS:** Generates clear, human-like speech using Coqui TTS.
-   💻 **macOS System Control:**
    -   Open any application on command.
    -   Search your entire system for files using Spotlight's command-line interface.
    -   Check your Calendar for today's events.
    -   Get the current battery status.
-   🛠️ **Easily Extensible:** Designed from the ground up to be simple to add new custom actions and abilities.

## How It Works

The magic of Jarvis lies in its logical flow, where the AI acts as a decision-maker.

User Voice -> [Wake Word] -> Record Command -> [Transcribe to Text] -> "The Brain" (Gemini AI)

Once the "Brain" has the text, it makes a crucial choice:

1.  **Is this a command?** → If the request matches a known tool (e.g., "open Spotify"), the AI generates a structured **JSON object**.
2.  **Is this a conversation?** → If it's a general question or greeting, the AI generates a **natural language response**.

This output is then processed:
AI Output -> [Parse: JSON or Text?] -> Execute Action / Speak Response -> User


## Tech Stack

| Component              | Technology                                                                                           |
| ---------------------- | ---------------------------------------------------------------------------------------------------- |
| **Core Language**      | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)          |
| **AI Brain**           | ![Google Gemini](https://img.shields.io/badge/Google-Gemini_API-4285F4?style=flat&logo=google)        |
| **Speech-to-Text**     | ![OpenAI Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?style=flat&logo=openai)          |
| **Wake Word Engine**   | ![Picovoice](https://img.shields.io/badge/Picovoice-Porcupine-377DFF?style=flat)                      |
| **Text-to-Speech**     | ![Coqui TTS](https://img.shields.io/badge/Coqui-TTS-FDB13D?style=flat)                                 |
| **System Control**     | ![AppleScript](https://img.shields.io/badge/AppleScript-1E1E1E?style=flat&logo=apple&logoColor=white) |

---

## 🚀 Setup and Installation

Follow these steps to get your own Jarvis running.

### 1. Clone the Repository

```bash
git clone https://github.com/aravguptaaa/Jarvis.git
cd Jarvis

python3 final.py

Jarvis will initialize and go into standby mode. Say "Jarvis" to activate it, and then give your command.

Things to Try:

"Jarvis, what's my battery level?"
"Jarvis, open Spotify for me."
"Jarvis, what are my events for today?"
"Jarvis, search my computer for a file called 'project proposal'."
"Jarvis, what is the theory of relativity?"

To stop the assistant completely, press Ctrl + C in the terminal.

🛠️ Extending Jarvis's Abilities
Want to teach Jarvis a new trick? It's easy!

Create the Function: Open actions.py and write a new Python function that performs the desired action (e.g., set_volume, send_email).
Register the Tool: In final.py, import your new function and add it to the AVAILABLE_TOOLS dictionary.
Teach the AI: In the system_prompt inside the get_ai_response function, add a new line describing your new tool, its name, and its parameters.
That's it! The AI will now know about its new ability and will call it when your command matches its description.

This project is a demonstration of how modern AI APIs can be combined with local scripts to create powerful, personalized tools. Feel free to fork, modify, and build upon it!

---

## License

MIT License

---

## Contact

If you have any questions or suggestions, please open an issue on the [GitHub repository](https://github.com/aravguptaaa/Jarvis).

---

## Acknowledgments

-   [Picovoice](https://picovoice.ai/)
-   [Google Gemini](https://gemini.google.com/)
-   [OpenAI Whisper](https://github.com/openai/whisper)
-   [Coqui TTS](https://github.com/coqui-ai/TTS)
-   [AppleScript](https://developer.apple.com/applescript/)
-   [Spotlight](https://support.apple.com/en-us/HT204012)
-   [Calendar](https://support.apple.com/en-us/HT204012)
-   [Battery](https://support.apple.com/en-us/HT204012)
-   [System Events](https://support.apple.com/en-us/HT204012)
-   [Automator](https://support.apple.com/en-us/HT204012)
