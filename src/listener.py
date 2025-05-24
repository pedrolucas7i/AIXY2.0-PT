"""
===============================================================================================================================================================
===============================================================================================================================================================

                                                                   _      ___  __  __ __   __  ____         ___  
                                                                  / \    |_ _| \ \/ / \ \ / / |___ \       / _ \ 
                                                                 / _ \    | |   \  /   \ V /    __) |     | | | |
                                                                / ___ \   | |   /  \    | |    / __/   _  | |_| |
                                                               /_/   \_\ |___| /_/\_\   |_|   |_____| (_)  \___/ 

                                                               
                                                                            COMPUTER LISTENER CODE
                                                                            by Pedro Ribeiro Lucas
                                                                                                                  
===============================================================================================================================================================
===============================================================================================================================================================
"""

import numpy as np
import sounddevice as sd
import tempfile
import wave
import requests
import os
import time
import env

# Audio configuration
SAMPLE_RATE = 44100
CHANNELS = 1
BLOCK_SIZE = 1024
SILENCE_THRESHOLD = 500  # Lower threshold for silence detection
SILENCE_TIME = 1.5  # seconds (how long to wait before stopping)

SERVER_URL = env.WHISPER_HOST

def detect_silence(audio):
    """Returns True if the average volume is below the threshold."""
    volume = np.abs(audio).mean()
    # print(f"Volume: {volume}")  # Debugging: Print volume level
    return volume < SILENCE_THRESHOLD

def record_until_silence():
    """Records audio until the user stops speaking for a few seconds, only if speech is detected."""
    buffer = []
    silence_start = None
    speech_detected = False

    def callback(indata, frames, time_info, status):
        nonlocal buffer, silence_start, speech_detected
        if status:
            print(status)

        samples = indata.copy().flatten()
        buffer.append(samples)

        volume = np.abs(samples).mean()

        if volume >= SILENCE_THRESHOLD:
            speech_detected = True
            silence_start = None  # reset silence timer
        else:
            if speech_detected:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_TIME:
                    print("Silence detected after speech. Stopping recording.")
                    raise sd.CallbackStop

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=np.int16,
                        blocksize=BLOCK_SIZE, callback=callback) as stream:
        print("Listening...")
        try:
            while stream.active:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Interrupted by user.")
        except sd.CallbackStop:
            pass

    if not speech_detected:
        print("⚠️ No speech detected during the session.")
        return np.array([], dtype=np.int16)

    return np.concatenate(buffer)

def transcribe_speech():
    """Records and sends audio to the server, returning the transcribed text."""
    print("Recording...")  # Show that we're starting
    audio = record_until_silence()

    if len(audio) == 0:
        print("⚠️ No audio captured.")
        return ""

    print("✅ Audio captured. Length:", len(audio))

    # Save to temporary WAV
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    print("📤 Sending audio to server...")

    try:
        with open(path, "rb") as f:
            response = requests.post(SERVER_URL, files={"audio": f})
        os.remove(path)

        print("📥 Response received.")

        # Logar a resposta bruta
        print(f"⚠️ Raw Response: {response.text}")  # Adicionando log para visualizar a resposta

        if response.status_code == 200:
            text = response.json().get("text", "").strip()
            print(f"📝 Transcribed Text: {text}")
            if ((text != "you") and (text != "Thanks for watching!") and (text != "Thank you.") and (text != "Thank you for watching!")):
                return text
            else:
                return None
        else:
            print(f"❌ Server error {response.status_code}: {response.text}")

            return ""
    except Exception as e:
        print(f"⚠️ Exception during request: {e}")
        return ""



if __name__ == "__main__":
    text = transcribe_speech()
