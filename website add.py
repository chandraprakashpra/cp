# ============================================================
# ANJU AI - HIGH LEVEL WINDOWS VOICE ASSISTANT
# ============================================================
# Python 3.13 compatible
# Features:
# - Hindi / Hinglish / English speech recognition
# - Female Windows TTS voice preference
# - OpenAI Responses API with conversation memory
# - Google search / YouTube
# - C:, D:, E: ... drive opening
# - This PC / File Explorer
# - Desktop / Documents / Downloads etc.
# - File/folder opening by name
# - Notepad / Calculator / Chrome
# - Safe screen clearing
# - Robust microphone + AI error handling
#
# IMPORTANT:
# Set OPENAI_API_KEY in Windows. Never put your API key in this file.
# ============================================================

import os
import sys
import re
import subprocess
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus

import speech_recognition as sr
import pyttsx3

# Indian F&O trading module
# The assistant can run even when india_fo_trading.py is not installed.
# Paper mode is used as a safe fallback; no real order is placed.
try:
    import india_fo_trading as trading

    TRADING_MODULE_AVAILABLE = True
except ModuleNotFoundError:
    TRADING_MODULE_AVAILABLE = False

    class _PaperTradingFallback:
        PAPER_MODE = True
        running = False

        def start_trading(self, speak_func=None):
            self.running = True
            message = "Trading module nahi mila. Safe paper-trading fallback start kar diya hai. Real order place nahi hoga."
            print_safe(message) if "print_safe" in globals() else print(message)
            if speak_func:
                speak_func(message)

        def stop_trading(self, speak_func=None):
            self.running = False
            message = "Paper trading fallback stop kar diya hai."
            print_safe(message) if "print_safe" in globals() else print(message)
            if speak_func:
                speak_func(message)

        def trading_status(self, speak_func=None):
            status = "RUNNING" if self.running else "STOPPED"
            message = f"Trading status: {status}. Mode: PAPER. Real trading disabled."
            print_safe(message) if "print_safe" in globals() else print(message)
            if speak_func:
                speak_func(message)

    trading = _PaperTradingFallback()
# To enable the real broker integration, place india_fo_trading.py
# in the same folder as this file and configure it separately.


# ============================================================
# WINDOWS CONSOLE / UNICODE FIX
# ============================================================

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# ============================================================
# SETTINGS
# ============================================================

ASSISTANT_NAME = "Anju"

# Current OpenAI model can be changed from environment:
# setx ANJU_AI_MODEL "gpt-5.6"
AI_MODEL = os.getenv("ANJU_AI_MODEL", "gpt-5.6").strip()

# Keep only a small recent conversation for voice use.
MAX_HISTORY_MESSAGES = 12

import shutil
import glob


# ============================================================
# 100+ APPS  (name -> list of possible launch targets)
# Each target can be: a real .exe path, a bare exe name (found via PATH),
# or a URI scheme (e.g. "spotify:", "ms-settings:").
# The launcher tries them in order and falls back gracefully.
# ============================================================

APPS = {
    # --- Windows built-ins ---
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "paint 3d": ["mspaint.exe"],
    "snipping tool": ["SnippingTool.exe"],
    "task manager": ["taskmgr.exe"],
    "control panel": ["control.exe"],
    "settings": ["ms-settings:"],
    "registry editor": ["regedit.exe"],
    "device manager": ["devmgmt.msc"],
    "disk management": ["diskmgmt.msc"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "terminal": ["wt.exe", "powershell.exe"],
    "file explorer": ["explorer.exe"],
    "character map": ["charmap.exe"],
    "sticky notes": ["StikyNot.exe"],
    "magnifier": ["magnify.exe"],
    "on screen keyboard": ["osk.exe"],
    "remote desktop": ["mstsc.exe"],
    "event viewer": ["eventvwr.msc"],
    "services": ["services.msc"],
    "system information": ["msinfo32.exe"],
    # --- Browsers ---
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "chrome.exe",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        "firefox.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "msedge.exe",
    ],
    "brave": [
        os.path.expandvars(
            r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
        ),
        "brave.exe",
    ],
    "opera": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
        "opera.exe",
    ],
    # --- Office / documents ---
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "powerpoint": ["powerpnt.exe"],
    "outlook": ["outlook.exe"],
    "onenote": ["onenote.exe"],
    "access": ["msaccess.exe"],
    "adobe reader": [
        r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        "AcroRd32.exe",
    ],
    # --- Dev tools ---
    "vs code": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "code.exe",
    ],
    "visual studio": ["devenv.exe"],
    "sublime text": [
        r"C:\Program Files\Sublime Text\sublime_text.exe",
        "sublime_text.exe",
    ],
    "notepad++": [r"C:\Program Files\Notepad++\notepad++.exe", "notepad++.exe"],
    "pycharm": ["pycharm64.exe"],
    "android studio": ["studio64.exe"],
    "git bash": [r"C:\Program Files\Git\git-bash.exe"],
    "postman": [os.path.expandvars(r"%LOCALAPPDATA%\Postman\Postman.exe")],
    "docker desktop": [r"C:\Program Files\Docker\Docker\Docker Desktop.exe"],
    "xampp": [r"C:\xampp\xampp-control.exe"],
    # --- Communication ---
    "whatsapp": [
        "whatsapp:",
        os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
    ],
    "telegram": [os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe")],
    "discord": [os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")],
    "skype": [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Skype for Desktop\Skype.exe")
    ],
    "zoom": [os.path.expandvars(r"%APPDATA%\Zoom\bin\Zoom.exe")],
    "teams": [os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe")],
    "slack": [os.path.expandvars(r"%LOCALAPPDATA%\slack\slack.exe")],
    # --- Media ---
    "spotify": ["spotify:", os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")],
    "vlc": [r"C:\Program Files\VideoLAN\VLC\vlc.exe", "vlc.exe"],
    "itunes": [r"C:\Program Files\iTunes\iTunes.exe"],
    "windows media player": ["wmplayer.exe"],
    # --- Utilities / archivers ---
    "winrar": [r"C:\Program Files\WinRAR\WinRAR.exe"],
    "7zip": [r"C:\Program Files\7-Zip\7zFM.exe"],
    "ccleaner": [r"C:\Program Files\CCleaner\CCleaner64.exe"],
    # --- Adobe creative ---
    "photoshop": ["Photoshop.exe"],
    "illustrator": ["Illustrator.exe"],
    "premiere pro": ["Adobe Premiere Pro.exe"],
    "after effects": ["AfterFX.exe"],
    # --- Gaming ---
    "steam": [r"C:\Program Files (x86)\Steam\steam.exe"],
    "epic games": [
        os.path.expandvars(
            r"%LOCALAPPDATA%\EpicGamesLauncher\Portal\Binaries\Win64\EpicGamesLauncher.exe"
        )
    ],
    "battle net": [r"C:\Program Files (x86)\Battle.net\Battle.net Launcher.exe"],
}


# ============================================================
# 100+ WEBSITES  (name -> URL). Handled purely by webbrowser.open,
# so no installation / path lookup is needed at all.
# ============================================================

WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "google maps": "https://maps.google.com",
    "google photos": "https://photos.google.com",
    "google translate": "https://translate.google.com",
    "google news": "https://news.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "google calendar": "https://calendar.google.com",
    "google meet": "https://meet.google.com",
    "google forms": "https://forms.google.com",
    "google classroom": "https://classroom.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "pinterest": "https://www.pinterest.com",
    "whatsapp web": "https://web.whatsapp.com",
    "telegram web": "https://web.telegram.org",
    "discord web": "https://discord.com/app",
    "threads": "https://www.threads.net",
    "tiktok": "https://www.tiktok.com",
    "snapchat": "https://www.snapchat.com",
    "tumblr": "https://www.tumblr.com",
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "myntra": "https://www.myntra.com",
    "ajio": "https://www.ajio.com",
    "meesho": "https://www.meesho.com",
    "nykaa": "https://www.nykaa.com",
    "tatacliq": "https://www.tatacliq.com",
    "jiomart": "https://www.jiomart.com",
    "croma": "https://www.croma.com",
    "reliance digital": "https://www.reliancedigital.in",
    "olx": "https://www.olx.in",
    "ebay": "https://www.ebay.com",
    "etsy": "https://www.etsy.com",
    "netflix": "https://www.netflix.com",
    "prime video": "https://www.primevideo.com",
    "hotstar": "https://www.hotstar.com",
    "sonyliv": "https://www.sonyliv.com",
    "zee5": "https://www.zee5.com",
    "jio cinema": "https://www.jiocinema.com",
    "spotify web": "https://open.spotify.com",
    "soundcloud": "https://soundcloud.com",
    "twitch": "https://www.twitch.tv",
    "youtube music": "https://music.youtube.com",
    "imdb": "https://www.imdb.com",
    "rotten tomatoes": "https://www.rottentomatoes.com",
    "wikipedia": "https://www.wikipedia.org",
    "wikihow": "https://www.wikihow.com",
    "quora": "https://www.quora.com",
    "medium": "https://medium.com",
    "archive": "https://archive.org",
    "britannica": "https://www.britannica.com",
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",
    "stack overflow": "https://stackoverflow.com",
    "npm": "https://www.npmjs.com",
    "pypi": "https://pypi.org",
    "replit": "https://replit.com",
    "codepen": "https://codepen.io",
    "jsfiddle": "https://jsfiddle.net",
    "codesandbox": "https://codesandbox.io",
    "leetcode": "https://leetcode.com",
    "hackerrank": "https://www.hackerrank.com",
    "geeksforgeeks": "https://www.geeksforgeeks.org",
    "w3schools": "https://www.w3schools.com",
    "mdn": "https://developer.mozilla.org",
    "freecodecamp": "https://www.freecodecamp.org",
    "coursera": "https://www.coursera.org",
    "udemy": "https://www.udemy.com",
    "khan academy": "https://www.khanacademy.org",
    "edx": "https://www.edx.org",
    "nptel": "https://nptel.ac.in",
    "unacademy": "https://unacademy.com",
    "linkedin learning": "https://www.linkedin.com/learning",
    "duolingo": "https://www.duolingo.com",
    "canva": "https://www.canva.com",
    "figma": "https://www.figma.com",
    "notion": "https://www.notion.so",
    "trello": "https://trello.com",
    "asana": "https://asana.com",
    "dropbox": "https://www.dropbox.com",
    "wetransfer": "https://wetransfer.com",
    "onedrive": "https://onedrive.live.com",
    "outlook web": "https://outlook.com",
    "yahoo": "https://www.yahoo.com",
    "yahoo mail": "https://mail.yahoo.com",
    "icloud": "https://www.icloud.com",
    "speedtest": "https://www.speedtest.net",
    "weather": "https://weather.com",
    "bbc news": "https://www.bbc.com/news",
    "cnn": "https://edition.cnn.com",
    "ndtv": "https://www.ndtv.com",
    "times of india": "https://timesofindia.indiatimes.com",
    "hindustan times": "https://www.hindustantimes.com",
    "the hindu": "https://www.thehindu.com",
    "indian express": "https://indianexpress.com",
    "espn cricinfo": "https://www.espncricinfo.com",
    "cricbuzz": "https://www.cricbuzz.com",
    "espn": "https://www.espn.com",
    "nba": "https://www.nba.com",
    "fifa": "https://www.fifa.com",
    "paytm": "https://paytm.com",
    "phonepe": "https://www.phonepe.com",
    "google pay": "https://pay.google.com",
    "irctc": "https://www.irctc.co.in",
    "makemytrip": "https://www.makemytrip.com",
    "ease my trip": "https://www.easemytrip.com",
    "redbus": "https://www.redbus.in",
    "zomato": "https://www.zomato.com",
    "swiggy": "https://www.swiggy.com",
    "bookmyshow": "https://in.bookmyshow.com",
    "tradingview": "https://www.tradingview.com",
    "zerodha kite": "https://kite.zerodha.com",
    "upstox": "https://pro.upstox.com",
    "angel one": "https://trade.angelone.in",
    "groww": "https://groww.in",
    "moneycontrol": "https://www.moneycontrol.com",
    "nse india": "https://www.nseindia.com",
    "bse india": "https://www.bseindia.com",
    "coinmarketcap": "https://coinmarketcap.com",
    "coingecko": "https://www.coingecko.com",
    "binance": "https://www.binance.com",
    "coindcx": "https://coindcx.com",
    "delta exchange": "https://www.delta.exchange",
    "rbi": "https://www.rbi.org.in",
    "sbi": "https://sbi.co.in",
    "hdfc bank": "https://www.hdfcbank.com",
    "icici bank": "https://www.icicibank.com",
    "axis bank": "https://www.axisbank.com",
    "amazon aws": "https://aws.amazon.com",
    "microsoft": "https://www.microsoft.com",
    "microsoft 365": "https://www.microsoft365.com",
    "openai": "https://openai.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "perplexity": "https://www.perplexity.ai",
    "deepseek": "https://www.deepseek.com",
    "hugging face": "https://huggingface.co",
    "elevenlabs": "https://elevenlabs.io",
    "wordpress": "https://wordpress.com",
    "blogger": "https://www.blogger.com",
    "shopify": "https://www.shopify.com",
    "godaddy": "https://www.godaddy.com",
    "namecheap": "https://www.namecheap.com",
    "indeed": "https://www.indeed.com",
    "naukri": "https://www.naukri.com",
    "glassdoor": "https://www.glassdoor.com",
    "internshala": "https://internshala.com",
    "apna": "https://apna.co",
    "freelancer": "https://www.freelancer.com",
    "upwork": "https://www.upwork.com",
    "fiverr": "https://www.fiverr.com",
    "toptal": "https://www.toptal.com",
    "phonepe business": "https://www.phonepe.com/business/",
    "razorpay": "https://razorpay.com",
    "stripe": "https://stripe.com",
    "paypal": "https://www.paypal.com",
}


def find_installed_exe(exe_name):
    """Best-effort search: PATH, then common Program Files locations."""
    found = shutil.which(exe_name)
    if found:
        return found

    search_roots = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
    ]

    for root in search_roots:
        if not root or not os.path.exists(root):
            continue
        pattern = os.path.join(root, "**", exe_name)
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

    return None


def launch_app_by_name(name):
    """Try every known target for an app name until one works."""
    targets = APPS.get(name)
    if not targets:
        return False

    for target in targets:
        try:
            if target.endswith(":"):
                os.startfile(target)
                speak(f"{name} open kar rahi hoon.")
                return True

            if os.path.isabs(target) or os.sep in target:
                if os.path.exists(target):
                    subprocess.Popen([target])
                    speak(f"{name} open kar rahi hoon.")
                    return True
                continue

            resolved = find_installed_exe(target)
            if resolved:
                subprocess.Popen([resolved])
                speak(f"{name} open kar rahi hoon.")
                return True

        except Exception as error:
            print_safe(f"{name} launch error: {repr(error)}")
            continue

    speak(f"{name} is computer par installed nahi mila.")
    return True


def show_websites():
    """Print all website aliases available to the assistant."""
    clear_screen()
    print_safe(f"Available websites: {len(WEBSITES)}")
    for number, name in enumerate(WEBSITES, 1):
        print_safe(f"{number:3}. {name}")
    speak(f"Maine {len(WEBSITES)} websites ki list screen par dikha di hai.")


def open_website_by_name(name):
    url = WEBSITES.get(name)
    if not url:
        return False

    webbrowser.open(url)
    speak(f"{name} open kar rahi hoon.")
    return True


# ============================================================
# TEXT HELPERS
# ============================================================


def safe_text(value):
    """Convert any value to safe printable text."""
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return repr(value)


def print_safe(text=""):
    try:
        print(safe_text(text))
    except UnicodeEncodeError:
        # Last-resort ASCII fallback for old Windows consoles.
        try:
            print(safe_text(text).encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ============================================================
# VOICE ENGINE
# ============================================================

try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)
except Exception as error:
    engine = None
    print_safe("TTS initialization error: " + repr(error))


def select_female_voice():
    """Prefer a female Windows SAPI voice when one is installed."""
    if engine is None:
        return False

    preferred_words = [
        "zira",
        "hazel",
        "heera",
        "female",
        "susan",
        "samantha",
        "google",
    ]

    try:
        voices = engine.getProperty("voices") or []

        for voice in voices:
            name = safe_text(getattr(voice, "name", "")).lower()

            if any(word in name for word in preferred_words):
                engine.setProperty("voice", voice.id)
                print_safe("Voice selected: " + safe_text(voice.name))
                return True

        # If no female-name match exists, keep the Windows default.
        return False

    except Exception as error:
        print_safe("Voice selection error: " + repr(error))
        return False


select_female_voice()


def speak(text):
    text = safe_text(text).strip()

    if not text:
        return

    print_safe(f"{ASSISTANT_NAME}: {text}")

    if engine is None:
        return

    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as error:
        print_safe("Voice error: " + repr(error))


# ============================================================
# MICROPHONE
# ============================================================

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.5


def listen():
    """Listen safely without crashing the whole assistant."""
    try:
        with sr.Microphone() as source:
            print_safe("\n[Listening...]")

            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.7)
            except Exception as error:
                print_safe("Ambient-noise setup warning: " + repr(error))

            try:
                audio = recognizer.listen(
                    source,
                    timeout=7,
                    phrase_time_limit=10,
                )
            except sr.WaitTimeoutError:
                print_safe("No voice detected.")
                return ""

    except OSError as error:
        print_safe("Microphone/PyAudio error: " + repr(error))
        speak(
            "Microphone mein problem hai. Windows microphone permission aur input device check karo."
        )
        return ""

    except Exception as error:
        print_safe("Microphone error: " + repr(error))
        return ""

    try:
        # en-IN works well for English/Hinglish speech.
        command = recognizer.recognize_google(
            audio,
            language="en-IN",
        )

        command = safe_text(command).strip().lower()
        print_safe("You: " + command)
        return command

    except sr.UnknownValueError:
        speak("Sorry, mujhe samajh nahi aaya.")
        return ""

    except sr.RequestError as error:
        print_safe("Speech service error: " + repr(error))
        speak("Speech recognition service mein problem hai.")
        return ""

    except Exception as error:
        print_safe("Recognition error: " + repr(error))
        return ""


# ============================================================
# OPENAI AI
# ============================================================

conversation_history = []
_openai_client = None


def get_openai_client():
    """Create the OpenAI client only when AI is actually requested."""
    global _openai_client

    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        return None

    try:
        from openai import OpenAI

        _openai_client = OpenAI(
            api_key=api_key,
            timeout=30.0,
            max_retries=2,
        )

        return _openai_client

    except Exception as error:
        print_safe("OpenAI client error: " + repr(error))
        return None


def ask_ai(question):
    """
    Send a voice question to OpenAI Responses API.
    Uses only recent turns to keep voice conversations responsive.
    """
    global conversation_history

    question = safe_text(question).strip()

    if not question:
        return

    client = get_openai_client()

    if client is None:
        speak(
            "OpenAI API key set nahi hai. "
            "Windows mein OPENAI_API_KEY set karke naya terminal kholo."
        )
        return

    conversation_history.append(
        {
            "role": "user",
            "content": question,
        }
    )

    # Prevent unlimited memory growth.
    conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]

    try:
        response = client.responses.create(
            model=AI_MODEL,
            instructions=(
                "You are Anju, a friendly female desktop voice assistant. "
                "The user speaks Hindi, Hinglish, or English. "
                "Answer in the same language. "
                "For voice replies, be concise and natural. "
                "Do not use markdown tables or emojis. "
                "If the user asks for a computer action, explain the action "
                "but do not claim an action happened unless this program "
                "actually executed it."
            ),
            input=conversation_history,
        )

        answer = safe_text(getattr(response, "output_text", "")).strip()

        if not answer:
            speak("AI se empty response mila.")
            return

        conversation_history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]

        speak(answer)

    except UnicodeEncodeError as error:
        # This specifically prevents the previous ASCII error from killing
        # the assistant. We also print only a safe diagnostic.
        print_safe("AI Unicode/encoding error: " + repr(error))
        speak(
            "AI response mein Windows encoding problem aayi. "
            "Terminal UTF 8 mode check karo."
        )

    except Exception as error:
        # repr() is intentional: it exposes the real exception safely.
        print_safe("AI ERROR: " + repr(error))

        error_text = safe_text(error).lower()

        if (
            "api key" in error_text
            or "authentication" in error_text
            or "401" in error_text
        ):
            speak("OpenAI API key invalid ya missing hai. API key check karo.")

        elif "429" in error_text or "rate" in error_text:
            speak("AI service ki request limit aa gayi hai. Thodi der baad try karo.")

        elif "model" in error_text and (
            "not found" in error_text or "404" in error_text
        ):
            speak(
                f"AI model {AI_MODEL} available nahi hai. "
                "ANJU_AI_MODEL environment variable check karo."
            )

        elif "connection" in error_text or "timeout" in error_text:
            speak("Internet ya OpenAI connection mein problem hai.")

        else:
            speak(
                "AI service se connect nahi ho pa raha hai. Terminal mein AI ERROR dekho."
            )


# ============================================================
# BASIC COMMANDS
# ============================================================


def hello(user_name):
    speak(f"Hello {user_name}.")


def assistant_name():
    speak("Mera naam Anju Assistant hai.")


def how_are_you():
    speak("Main bilkul theek hoon. Aap batao?")


def show_time():
    speak("Abhi time hai " + datetime.now().strftime("%I:%M %p"))


def show_date():
    speak("Aaj ki date hai " + datetime.now().strftime("%d-%m-%Y"))


def good_morning(user_name):
    speak(f"Good morning {user_name}.")


def good_evening(user_name):
    speak(f"Good evening {user_name}.")


def good_night(user_name):
    speak(f"Good night {user_name}.")


def thanks():
    speak("You're welcome.")


def love_response():
    speak("Haan CP, main tumhari Anju Assistant hoon. Bolo, kya karna hai?")


def janu_response():
    speak("Ji CP, bolo. Main sun rahi hoon.")


# ============================================================
# WINDOWS APPS
# ============================================================


def launch(command, spoken_name):
    try:
        subprocess.Popen(command)
        speak(f"{spoken_name} open kar rahi hoon.")
        return True
    except Exception as error:
        print_safe(f"{spoken_name} error: {repr(error)}")
        speak(f"{spoken_name} open nahi ho paya.")
        return False


def open_notepad():
    return launch(["notepad.exe"], "Notepad")


def open_calculator():
    return launch(["calc.exe"], "Calculator")


def open_file_explorer():
    return launch(["explorer.exe"], "File Explorer")


def open_chrome():
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]

    for path in chrome_paths:
        if os.path.exists(path):
            try:
                subprocess.Popen([path])
                speak("Chrome open kar rahi hoon.")
                return True
            except Exception as error:
                print_safe("Chrome error: " + repr(error))

    webbrowser.open("https://www.google.com")
    speak("Default browser mein Google open kar rahi hoon.")
    return True


# ============================================================
# WEB
# ============================================================


def open_google():
    webbrowser.open("https://www.google.com")
    speak("Google open kar rahi hoon.")


def open_youtube():
    webbrowser.open("https://www.youtube.com")
    speak("YouTube open kar rahi hoon.")


def google_search(command):
    prefixes = [
        "search for ",
        "search ",
        "google ",
    ]

    search_text = ""

    for prefix in prefixes:
        if command.startswith(prefix):
            search_text = command[len(prefix) :].strip()
            break

    if not search_text:
        return False

    url = "https://www.google.com/search?q=" + quote_plus(search_text)
    webbrowser.open(url)
    speak(f"Google par {search_text} search kar rahi hoon.")
    return True


# ============================================================
# DRIVES / FILES / FOLDERS
# ============================================================


def open_path(path):
    path = os.path.expandvars(os.path.expanduser(path))

    try:
        if not os.path.exists(path):
            speak("Ye file ya folder nahi mila.")
            return False

        os.startfile(path)
        speak("Open kar rahi hoon.")
        return True

    except Exception as error:
        print_safe("Open path error: " + repr(error))
        speak("File ya folder open nahi ho paya.")
        return False


def available_drives():
    drives = []

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:\\"

        if os.path.exists(drive):
            drives.append(drive)

    return drives


def open_main_drive():
    speak("Main C drive open kar rahi hoon.")
    return open_path(r"C:\\")


def open_drive(command):
    match = re.search(
        r"(?:open\s+)?(?:drive|disk)\s*([a-z])\b|"
        r"\b([a-z])\s*(?:drive|disk)\b",
        command,
        re.IGNORECASE,
    )

    if not match:
        return False

    letter = (match.group(1) or match.group(2)).upper()
    drive = f"{letter}:\\"

    if not os.path.exists(drive):
        speak(f"Drive {letter} available nahi hai.")
        return True

    speak(f"Drive {letter} open kar rahi hoon.")
    return open_path(drive)


def open_this_pc():
    try:
        subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
        speak("This PC open kar rahi hoon.")
        return True
    except Exception as error:
        print_safe("This PC error: " + repr(error))
        return False


def open_folder(folder_name):
    home = os.path.expanduser("~")

    folders = {
        "desktop": os.path.join(home, "Desktop"),
        "documents": os.path.join(home, "Documents"),
        "document": os.path.join(home, "Documents"),
        "downloads": os.path.join(home, "Downloads"),
        "download": os.path.join(home, "Downloads"),
        "pictures": os.path.join(home, "Pictures"),
        "music": os.path.join(home, "Music"),
        "videos": os.path.join(home, "Videos"),
    }

    path = folders.get(folder_name.lower().strip())

    if not path:
        return False

    if not os.path.exists(path):
        speak(f"{folder_name} folder nahi mila.")
        return True

    speak(f"{folder_name} folder open kar rahi hoon.")
    return open_path(path)


def find_and_open_file(filename):
    filename = filename.strip().strip('"').strip("'")

    if not filename:
        speak("Kaunsi file open karni hai?")
        return True

    # Direct path first.
    expanded = os.path.expandvars(os.path.expanduser(filename))

    if os.path.exists(expanded):
        return open_path(expanded)

    home = os.path.expanduser("~")

    roots = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Pictures"),
        os.path.join(home, "Videos"),
        os.path.join(home, "Music"),
    ]

    target = filename.lower()

    for root in roots:
        if not os.path.exists(root):
            continue

        try:
            for current_root, dirs, files in os.walk(root):
                dirs[:] = [
                    d
                    for d in dirs
                    if d.lower()
                    not in {
                        ".git",
                        "__pycache__",
                        "node_modules",
                    }
                ]

                for file_name in files:
                    if file_name.lower() == target:
                        full_path = os.path.join(current_root, file_name)
                        speak(f"{file_name} mil gayi. Open kar rahi hoon.")
                        return open_path(full_path)

        except (PermissionError, OSError):
            continue

    speak(f"{filename} common folders mein nahi mili.")
    return True


# ============================================================
# COMMAND HELP
# ============================================================


def help_menu():
    clear_screen()

    print_safe(
        """
============================================================
                    ANJU COMMANDS
============================================================

VOICE / AI
  Anju Python kya hai
  Anju explain artificial intelligence
  Anju tum kya kar sakti ho

WINDOWS
  open notepad
  open calculator
  open file explorer
  open chrome

DRIVES
  open main drive
  open C drive
  open D drive
  open E drive
  open this PC

FOLDERS
  open desktop
  open documents
  open downloads
  open pictures
  open videos

FILES
  open file resume.pdf
  file open photo.jpg
  open folder downloads

WEB
  open google
  open youtube
  search python
  google latest technology

UTILITY
  time
  date
  clear screen
  female voice

APPS & WEBSITES (166 websites, say "open <name>")
  open whatsapp / open spotify / open vs code / open steam ...
  open youtube / open amazon / open tradingview / open binance ...
[L]   show websites   (list all website shortcuts)

TRADING (paper mode by default; safe fallback if module is missing)
  start trading
  stop trading
  trading status

EXIT
  stop
  exit
  quit
  bye
============================================================
"""
    )

    speak("Command list screen par dikha di hai.")


# ============================================================
# WAKE WORD
# ============================================================

WAKE_WORDS = ["anju", "anjou", "jarvis"]


def wake_word_detected(command):
    return any(word in command for word in WAKE_WORDS)


def remove_wake_word(command):
    for word in WAKE_WORDS:
        command = command.replace(word, " ")

    return re.sub(r"\s+", " ", command).strip()


# ============================================================
# PROCESS COMMAND
# ============================================================


def process_command(command, user_name):
    if not command:
        return True

    # Exit
    if command in ["stop", "exit", "quit", "bye", "close assistant"]:
        speak("Okay CP, Anju Assistant band kar rahi hoon.")
        return False

    # Clear
    if command in [
        "clear",
        "clear screen",
        "screen clear",
        "screen saaf karo",
        "sab saaf karo",
    ]:
        clear_screen()
        speak("Screen clear kar di hai.")
        return True

    # Greetings
    if command in ["hello", "hi", "hey"]:
        hello(user_name)
        return True

    if "good morning" in command:
        good_morning(user_name)
        return True

    if "good evening" in command:
        good_evening(user_name)
        return True

    if "good night" in command:
        good_night(user_name)
        return True

    # Personal
    if command in ["name", "your name", "what is your name", "what's your name"]:
        assistant_name()
        return True

    if command in ["how are you", "how r u", "hru"]:
        how_are_you()
        return True

    if "thank you" in command or "thanks" in command:
        thanks()
        return True

    if "sorry" in command:
        speak("Koi baat nahi.")
        return True

    if (
        "love you" in command
        or "i love you" in command
        or "pyar" in command
        or "pyaar" in command
    ):
        love_response()
        return True

    if "janu" in command or "jaan" in command or "darling" in command:
        janu_response()
        return True

    # Time / date
    if "time" in command or "samay" in command:
        show_time()
        return True

    if "date" in command or "today date" in command or "tarikh" in command:
        show_date()
        return True

    # Windows apps
    if "open notepad" in command or "notepad kholo" in command:
        open_notepad()
        return True

    if (
        "open calculator" in command
        or "calculator kholo" in command
        or "calc kholo" in command
    ):
        open_calculator()
        return True

    if (
        "open file explorer" in command
        or "file explorer kholo" in command
        or "explorer kholo" in command
    ):
        open_file_explorer()
        return True

    if "open chrome" in command or "chrome kholo" in command:
        open_chrome()
        return True

    # Drives / This PC
    if command in [
        "open main drive",
        "main drive kholo",
        "open c drive",
        "c drive kholo",
        "open c disk",
    ]:
        open_main_drive()
        return True

    if command in [
        "open this pc",
        "this pc kholo",
        "open my computer",
        "my computer kholo",
        "open all files",
        "all files kholo",
    ]:
        open_this_pc()
        return True

    if open_drive(command):
        return True

    # Folders
    folder_aliases = [
        ("open desktop", "desktop"),
        ("desktop kholo", "desktop"),
        ("open documents", "documents"),
        ("documents kholo", "documents"),
        ("open downloads", "downloads"),
        ("downloads kholo", "downloads"),
        ("open pictures", "pictures"),
        ("pictures kholo", "pictures"),
        ("open videos", "videos"),
        ("videos kholo", "videos"),
        ("open music", "music"),
        ("music kholo", "music"),
    ]

    for phrase, folder_name in folder_aliases:
        if command == phrase:
            open_folder(folder_name)
            return True

    # File / folder by name
    if command.startswith("open file "):
        find_and_open_file(command[len("open file ") :])
        return True

    if command.startswith("file open "):
        find_and_open_file(command[len("file open ") :])
        return True

    if command.startswith("open folder "):
        open_folder(command[len("open folder ") :])
        return True

    # Web
    if command == "open google" or command == "google kholo":
        open_google()
        return True

    if command == "open youtube" or command == "youtube kholo":
        open_youtube()
        return True

    if google_search(command):
        return True

    # Website list
    if command in [
        "show websites",
        "website list",
        "websites list",
        "100 websites",
        "100 plus websites",
    ]:
        show_websites()
        return True

    # Generic 100+ apps / websites: "open <name>", "<name> kholo", or bare name
    generic_target = command
    for prefix in ("open ", "launch ", "start "):
        if generic_target.startswith(prefix):
            generic_target = generic_target[len(prefix) :].strip()
            break
    if generic_target.endswith(" kholo"):
        generic_target = generic_target[: -len(" kholo")].strip()

    if generic_target:
        if generic_target in APPS:
            return launch_app_by_name(generic_target)
        if generic_target in WEBSITES:
            return open_website_by_name(generic_target)

    # Voice
    if command in ["female voice", "female voice karo", "ladki ki voice", "girl voice"]:
        if select_female_voice():
            speak("Preferred female voice select kar di hai.")
        else:
            speak("Preferred female voice Windows mein available nahi mili.")
        return True

    # Help
    if command in ["help", "help me", "commands", "command list"]:
        help_menu()
        return True

    # Autonomous futures trading (paper mode by default)
    if command in ["start trading", "trading shuru karo", "trading start karo"]:
        trading.start_trading(speak)
        return True

    if command in ["stop trading", "trading band karo", "trading rok do"]:
        trading.stop_trading(speak)
        return True

    if command in ["trading status", "trading ka status batao"]:
        trading.trading_status(speak)
        return True

    # Everything else -> AI
    ask_ai(command)
    return True


# ============================================================
# MAIN
# ============================================================


def main():
    clear_screen()

    print_safe("=" * 60)
    print_safe("              ANJU AI VOICE ASSISTANT")
    print_safe("=" * 60)
    print_safe("AI model: " + AI_MODEL)

    user_name = input("Apna name batao: ").strip()

    if not user_name:
        user_name = "CP"

    speak(f"Hello {user_name}.")
    speak("Main Anju Assistant hoon. Aap mujhse baat kar sakte hain.")
    speak("Anju ya Jarvis bolkar command de sakte hain.")

    while True:
        command = listen()

        if not command:
            continue

        if wake_word_detected(command):
            command = remove_wake_word(command)

            if not command:
                speak("Ji CP, main sun rahi hoon.")
                continue

        should_continue = process_command(command, user_name)

        if not should_continue:
            break


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_safe("\nAssistant stopped.")
    except Exception as error:
        print_safe("PROGRAM ERROR: " + repr(error))
        speak("Program mein unexpected error aa gaya.")
