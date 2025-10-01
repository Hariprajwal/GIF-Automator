import yt_dlp
import os
import math
import subprocess
import time
import webbrowser
import pyautogui
import pyperclip
import google.generativeai as genai
from tkinter import Tk, Label, Button, Frame, StringVar, simpledialog
import sys  # Added for Unix input handling
import re

def sanitize_filename(name):
    """
    Sanitize filename to remove invalid characters and limit length
    """
    # Remove invalid characters for Windows filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    # Limit length to avoid Windows path issues (max 255 chars, but be safe)
    if len(name) > 100:
        name = name[:100]
    
    # Remove any leading/trailing spaces or dots
    name = name.strip().strip('.')
    
    return name

def download_video_from_url(url):
    """
    Downloads the best quality video from a given URL using yt-dlp.
    Returns the path to the downloaded video file and the video title.
    """
    
    # 1. Define the directory to save the file
    download_dir = "D:\\downloads"  # Fixed: Use double backslashes
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # 2. Define the options for yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
        'outtmpl': os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s'),
        'noprogress': False, 
        'noplaylist': True,
    }

    print(f"Attempting to download: {url}")
    
    try:
        # Use YoutubeDL to get video info and download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info to get the filename and title
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            video_title = info.get('title', 'Unknown_Title')
        
        print("\n✅ Download complete!")
        return downloaded_file, video_title

    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌ An error occurred during download: {e}")
        return None, None
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        return None, None

def video_to_gifs(video_path, output_dir, clip_length=3, fps=15):
    """
    Converts a video file to multiple GIF clips.
    """
    # ✅ Ensure output folder exists (create if not present)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📂 Created output directory: {output_dir}")
    else:
        print(f"📂 Using existing output directory: {output_dir}")

    # Get video duration using ffprobe
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        print("❌ Could not read video duration. Check ffmpeg installation.")
        return

    print(f"Video length: {duration:.2f} seconds")

    # Number of GIFs to create
    num_clips = math.ceil(duration / clip_length)
    print(f"Creating {num_clips} GIF clips of {clip_length} seconds each...")

    for i in range(num_clips):
        start = i * clip_length
        output_path = os.path.join(output_dir, f"output_{i+1}.gif")

        # ffmpeg command
        command = [
            "ffmpeg", "-y",             
            "-ss", str(start),          
            "-t", str(clip_length),     
            "-i", video_path,           
            "-vf", f"fps={fps},scale=480:-1:flags=lanczos", 
            output_path
        ]

        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"✅ Saved: {output_path}")

def get_input_with_timeout(prompt, timeout=3, default=""):
    """
    Simple input with timeout that doesn't use threading
    """
    print(prompt)
    start_time = time.time()
    user_input = ""
    
    print(f"You have {timeout} seconds to type a custom name, or we'll use: '{default}'")
    print("Type your input and press Enter, or just wait...")
    
    # Simple input with timeout
    try:
        while (time.time() - start_time) < timeout:
            if os.name == 'nt':  # Windows
                import msvcrt
                if msvcrt.kbhit():
                    user_input = input()
                    break
            else:  # Unix/Linux/Mac
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = input()
                    break
            time.sleep(0.1)
    except:
        pass
    
    if user_input:
        return user_input.strip()
    else:
        print(f"Using default: '{default}'")
        return default

class GiphyUploader:
    def __init__(self, video_title, auto_start=False):
        self.root = Tk()
        self.root.title("GIPHY Upload Automation")
        self.root.geometry("500x450")
        self.root.configure(bg='#121212')
        
        # Status variable
        self.status = StringVar()
        self.status.set("Ready to start GIPHY upload process")
        
        # Store the video title for later use
        self.video_title = video_title
        
        # Configure Gemini AI
        self.setup_gemini()
        
        # Create UI
        self.create_ui()
        
        # Set up pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # Auto-start if requested
        if auto_start:
            self.root.after(2000, self.start_process)  # Start after 2 seconds
        
    def setup_gemini(self):
        """Configure the Gemini AI for tag generation"""
        try:
            genai.configure(api_key="YOUR API KEY ")
            
            # List available models properly
            def get_available_models():
                try:
                    models = list(genai.list_models())
                    names = [m.name for m in models]
                    print("Available models:", names)
                    return names
                except Exception as e:
                    print("❌ Could not list models:", e)
                    return []

            # Pick a working model
            available = get_available_models()
            preferred = ["gemini-2.0-flash-exp", "gemini-1.5-flash-002", "gemini-1.5-pro-002"]

            model_name = None
            for p in preferred:
                if any(p in m for m in available):
                    model_name = p
                    break

            if not model_name:
                print("⚠️ No preferred model found. Using fallback: gemini-1.5-flash-002")
                model_name = "gemini-1.5-flash-002"

            print("✅ Using model:", model_name)
            self.model = genai.GenerativeModel(model_name=model_name)
            self.gemini_available = True
            
        except Exception as e:
            print(f"❌ Gemini AI setup failed: {e}")
            self.gemini_available = False
        
    def create_ui(self):
        # Header
        header = Label(self.root, text="GIPHY Upload Automation", 
                      font=("Arial", 18, "bold"), fg="#00FF9D", bg="#121212")
        header.pack(pady=20)
        
        # Instructions
        instructions = Label(self.root, 
                           text="This program will:\n1. Open GIPHY\n2. Guide you through the upload process\n3. Automate the file selection\n4. Add your name and generate tags",
                           font=("Arial", 12), fg="white", bg="#121212", justify="left")
        instructions.pack(pady=10)
        
        # Video title display
        title_label = Label(self.root, 
                          text=f"Video Title: {self.video_title}",
                          font=("Arial", 11, "bold"), fg="#00D8FF", bg="#121212",
                          wraplength=400, justify="center")
        title_label.pack(pady=5)
        
        # Status display
        status_frame = Frame(self.root, bg="#1E1E1E", relief="solid", bd=1)
        status_frame.pack(pady=20, padx=40, fill="x")
        
        status_label = Label(status_frame, textvariable=self.status, 
                           font=("Arial", 11), fg="#00D8FF", bg="#1E1E1E", 
                           wraplength=400, justify="left", padx=10, pady=10)
        status_label.pack()
        
        # Button frame
        button_frame = Frame(self.root, bg="#121212")
        button_frame.pack(pady=20)
        
        # Start button
        start_btn = Button(button_frame, text="Start GIPHY Upload", 
                          font=("Arial", 12, "bold"), bg="#00FF9D", fg="black",
                          command=self.start_process, width=20, height=2)
        start_btn.pack(pady=10)
        
        # Gemini status
        gemini_status = "✅ Gemini AI Ready" if self.gemini_available else "❌ Gemini AI Not Available"
        gemini_label = Label(self.root, text=gemini_status,
                           font=("Arial", 10), fg="green" if self.gemini_available else "red", 
                           bg="#121212")
        gemini_label.pack(pady=5)
        
        # Warning
        warning = Label(self.root, 
                       text="Note: Do not move the mouse during automation!\nThe program will control your mouse and keyboard.",
                       font=("Arial", 10), fg="orange", bg="#121212", justify="center")
        warning.pack(pady=10)
        
    def update_status(self, message):
        self.status.set(message)
        self.root.update()
        
    def click_at_position(self, x, y, description):
        self.update_status(f"Step: {description}")
        pyautogui.click(x, y)
        time.sleep(1)
        
    def generate_and_paste_tags(self, topic):
        """Generate tags using Gemini AI and paste them"""
        if not self.gemini_available:
            self.update_status("Gemini AI not available - using default tags")
            default_tags = ["#gif", "#animation", "#funny", "#meme", "#trending", "#viral"]
            for tag in default_tags:
                pyperclip.copy(tag)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(0.3)
            return
            
        try:
            self.update_status("Generating tags with AI...")
            
            # Generate tags dynamically
            prompt = f"Generate 14 short, SEO-friendly hashtags for {topic}. First always include the name I have given. Only output the tags separated by commas. Include 1 tag for hero and another tag for heroine, and one dedicated tag which is most popular or viral."
            response = self.model.generate_content(prompt)
            text_response = response.text.strip()
            tags = [tag.strip() for tag in text_response.replace("\n", "").split(",") if tag.strip()]
            
            if not tags:
                tags = ["#gif", "#animation", "#fun", "#trending", "#viral", "#meme"]
                
            print("\n✅ Tags generated:", tags)
            
            # Wait a moment before pasting
            time.sleep(1)
            
            # Paste tags one by one
            for tag in tags:
                pyperclip.copy(tag)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(0.3)
                
            self.update_status("Tags successfully added!")
            
        except Exception as e:
            print(f"❌ Error generating tags: {e}")
            self.update_status("Error generating tags - using defaults")
            # Fallback to default tags
            default_tags = ["#gif", "#animation", "#fun", "#meme", "#trending", "#viral"]
            for tag in default_tags:
                pyperclip.copy(tag)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(0.3)
    
    def start_process(self):
        self.update_status("Starting GIPHY upload process...")
            
        try:
            # Step 0: Open GIPHY website
            self.update_status("Opening GIPHY website...")
            url = "https://giphy.com/"
            webbrowser.open(url)
            time.sleep(5)  # Wait for page to load
            
            # Step 1: Click on upload button
            self.click_at_position(1229, 191, "Clicking on upload button")
            
            # Step 2: Click on file selection area
            self.click_at_position(705, 714, "Clicking on file selection area")
            
            # Step 3: Click on path input and paste the file path
            self.click_at_position(445, 167, "Clicking on path input")
            
            # Create folder name from video title (sanitized)
            folder_name = sanitize_filename(self.video_title.replace(" ", "_") + "_gifs")
            gif_directory = os.path.join(r"C:\Users\harip\ALL TEST", folder_name)
            
            self.update_status(f"Pasting file path: {gif_directory}")
            pyautogui.write(gif_directory)
            pyautogui.press('enter')
            time.sleep(2)
            
            # Step 4: Click on search/name field and enter the name
            self.click_at_position(765, 165, "Clicking on name field")
            self.update_status(f"Entering name: {self.video_title}")
            pyautogui.write(self.video_title)
            time.sleep(5)  # Wait as specified
            
            # Step 5: Click at X=376, Y=234 and then press Ctrl+A to select all
            self.click_at_position(376, 234, "Clicking on file area to focus")
            pyautogui.hotkey('ctrl', 'a')  # Select all files
            time.sleep(1)
            
            # Step 6: Click on the upload confirmation (Open button)
            self.click_at_position(770, 628, "Confirming selection - Clicking Open")
            
            # Step 7: Wait for GIF to load with better timing
            self.update_status("Waiting for GIF to upload and process (45 seconds)...")
            for i in range(45, 0, -5):
                self.update_status(f"Processing... {i} seconds remaining")
                time.sleep(5)
            
            # Step 8: Click on tags area and generate/paste tags
            self.click_at_position(1211, 603, "Opening tags section")
            time.sleep(2)
            
            # Generate and paste tags using the video title
            self.generate_and_paste_tags(self.video_title)
            
            # Step 9: Final upload click
            self.click_at_position(1257, 1035, "Final upload")
            
            self.update_status("Upload process completed successfully!")
            
        except pyautogui.FailSafeException:
            self.update_status("Process was aborted by moving mouse to corner")
        except Exception as e:
            self.update_status(f"An error occurred: {str(e)}")
    
    def run(self):
        self.root.mainloop()

# --- Main Program Execution ---
if __name__ == "__main__":
    
    # Step 1: Download video from URL
    print("🎥 VIDEO DOWNLOADER & GIF CONVERTER")
    print("=" * 40)
    
    video_link = input("Paste the video URL and press Enter: ").strip()

    if not video_link:
        print("No URL provided. Exiting.")
        exit()

    # Download the video and get the title
    downloaded_video_path, video_title = download_video_from_url(video_link)
    
    if not downloaded_video_path or not os.path.exists(downloaded_video_path):
        print("❌ Video download failed. Exiting.")
        exit()

    print(f"📁 Downloaded video: {downloaded_video_path}")
    print(f"🎬 Video title: {video_title}")
    
    # Step 2: Convert to GIFs
    print("\n" + "=" * 40)
    print("🔄 CONVERTING TO GIFS")
    print("=" * 40)
    
    # Create folder name from video title (sanitized)
    folder_name = sanitize_filename(video_title.replace(" ", "_") + "_gifs")
    final_output_dir = os.path.join(r"C:\Users\harip\ALL TEST", folder_name)
    
    print(f"🎯 Creating GIFs in: {final_output_dir}")
    
    # Convert the downloaded video to GIFs
    video_to_gifs(downloaded_video_path, final_output_dir)
    
    print("\n✅ GIF conversion completed!")
    print(f"📁 Video downloaded to: {downloaded_video_path}")
    print(f"📁 GIFs saved to: {final_output_dir}")
    
    # Step 3: 10-second cooldown before auto-starting GIPHY uploader
    print("\n" + "=" * 40)
    print("🚀 STARTING GIPHY UPLOADER IN 10 SECONDS")
    print("=" * 40)
    
    print("⏳ 10-second cooldown before starting automation...")
    for i in range(10, 0, -1):
        print(f"⏰ Starting in {i} seconds...")
        time.sleep(1)
    
    print("🎯 Auto-starting GIPHY uploader now!")
    
    # Check if required modules are installed
    try:
        import pyautogui
        import pyperclip
        # Auto-start the upload process
        app = GiphyUploader(video_title, auto_start=True)
        app.run()
    except ImportError as e:
        print(f"Please install the required modules: pip install pyautogui pyperclip")
        print(f"Missing module: {e}")
        input("Press Enter to exit...")
