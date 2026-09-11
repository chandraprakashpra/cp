import speech_recognition as sr
import pyttsx3
from datetime import datetime

# Text-to-Speech engine
engine = pyttsx3.init()

engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)


def speak(text):
    print("Assistant:", text)
    engine.say(text)
    engine.runAndWait()


def listen():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("\n🎤 Sun raha hoon...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)

        try:
            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=8
            )

            print("🔄 Samajh raha hoon...")

            command = recognizer.recognize_google(
                audio,
                language="hi-IN"
            )

            print("You:", command)
            return command.lower()

        except sr.WaitTimeoutError:
            return ""

        except sr.UnknownValueError:
            speak("Mujhe samajh nahi aaya.")
            return ""

        except sr.RequestError:
            speak("Speech recognition service available nahi hai.")
            return ""


def show_time():
    current_time = datetime.now().strftime("%I:%M %p")
    speak(f"Abhi time hai {current_time}")


def show_date():
    current_date = datetime.now().strftime("%d-%m-%Y")
    speak(f"Aaj ki date hai {current_date}")


def assistant():
    speak("Hello! Main Anju Assistant hoon.")
    speak("Aap mujhe voice command de sakte hain.")

    while True:
        command = listen()

        if not command:
            continue

        if any(word in command for word in ["hello", "hi", "नमस्ते", "हेलो"]):
            speak("Hello! Kaise ho?")

        elif "time" in command or "समय" in command:
            show_time()

        elif "date" in command or "तारीख" in command:
            show_date()

        elif "your name" in command or "तुम्हारा नाम" in command:
            speak("Mera naam Anju Assistant hai.")

        elif "how are you" in command or "कैसी हो" in command:
            speak("Main bilkul theek hoon.")

        elif "thank" in command or "धन्यवाद" in command:
            speak("You're welcome!")

        elif "good morning" in command:
            speak("Good morning CP! Aapka din achha rahe.")

        elif "good night" in command:
            speak("Good night! Kal phir milte hain.")

        elif "stop" in command or "बंद" in command or "exit" in command:
            speak("Okay, Assistant band kar raha hoon.")
            break

        else:
            speak("Ye command abhi meri list mein nahi hai.")


if __name__ == "__main__":
    assistant()