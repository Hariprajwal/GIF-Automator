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
import sys
import re

# Global variables
N = 0  # Will be set dynamically based on number of GIFs created
TAGS = []  # Will store generated tags
CURRENT_VIDEO_INDEX = 0  # Track current video being processed
ALL_VIDEO_URLS = []  # Store all video URLs

def extract_urls_from_input(user_input):
    """
    Extract multiple URLs from user input using space or comma separation
    AND handle continuous links without separators
    """
    urls = []
    
    # First, try to find URLs using regex pattern
    url_pattern = r'https?://[^\s,]+'
    found_urls = re.findall(url_pattern, user_input)
    
    if found_urls:
        # If regex found URLs, use them
        urls = found_urls
    else:
        # Fallback: split by both commas and spaces
        raw_urls = re.split(r'[,\s]+', user_input)
        
        for url in raw_urls:
            url = url.strip()
            # Basic URL validation
            if url and (url.startswith('http://') or url.startswith('https://')):
                urls.append(url)
    
    return urls

def check_existing_gifs(output_dir):
    """
    Check if GIF files already exist in the output directory
    Returns: (bool_exists, int_count)
    """
    if not os.path.exists(output_dir):
        return False, 0
    
    try:
        gif_files = [f for f in os.listdir(output_dir) if f.endswith('.gif') and f.startswith('output_')]
        
        if gif_files:
            print(f"📁 Found {len(gif_files)} existing GIF files in directory")
            return True, len(gif_files)
        
        return False, 0
    except Exception as e:
        print(f"⚠️  Error checking existing GIFs: {e}")
        return False, 0

def sanitize_filename(name):
    """
    Sanitize filename to remove invalid characters and limit length
    MORE ROBUST HANDLING FOR COMPLEX FILENAMES
    """
    if not name:
        return "Unknown_Video"
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Remove invalid characters for Windows filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    # Limit length to avoid Windows path issues - INCREASED FOR LONG NAMES
    if len(name) > 150:  # Increased from 100 to 150
        # Try to keep important parts of the name
        name = name[:150]
    
    # Remove any leading/trailing spaces, dots, or hyphens
    name = name.strip().strip('.').strip('-')
    
    # If name becomes empty after sanitization, use default
    if not name:
        name = "Unknown_Video"
    
    return name

def robust_directory_creation(directory_path):
    """
    More robust directory creation that handles various edge cases
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            print(f"📂 Created directory: {directory_path}")
        else:
            print(f"📂 Using existing directory: {directory_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create directory {directory_path}: {e}")
        # Fallback: try to create in a simpler location
        try:
            fallback_dir = r"C:\Users\harip\ALL TEST\Fallback_GIFs"
            os.makedirs(fallback_dir, exist_ok=True)
            print(f"📂 Using fallback directory: {fallback_dir}")
            return fallback_dir
        except:
            print("❌ Critical: Could not create any directory")
            return False

def download_video_from_url(url):
    """
    Downloads the best quality video from a given URL using yt-dlp.
    Returns the path to the downloaded video file and the video title.
    """
    
    # Define the directory to save the file
    download_dir = "D:\\downloads"
    if not robust_directory_creation(download_dir):
        return None, None, None, None

    # Define the options for yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
        'outtmpl': os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s'),
        'noprogress': False, 
        'noplaylist': True,
    }

    print(f"🎥 Attempting to download: {url}")
    
    try:
        # Use YoutubeDL to get video info and download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info to get the filename and title
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            video_title = info.get('title', 'Unknown_Title')
            video_description = info.get('description', '')
            video_tags = info.get('tags', [])
        
        print("✅ Download complete!")
        return downloaded_file, video_title, video_description, video_tags

    except yt_dlp.utils.DownloadError as e:
        print(f"❌ An error occurred during download: {e}")
        return None, None, None, None
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None, None, None, None

def video_to_gifs(video_path, output_dir, clip_length=3, fps=15):
    """
    Converts a video file to multiple GIF clips.
    Returns the number of GIFs created.
    """
    global N
    
    # Ensure output folder exists with robust creation
    if not robust_directory_creation(output_dir):
        return 0

    # Get video duration using ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        duration = float(result.stdout.strip())
    except (ValueError, subprocess.SubprocessError) as e:
        print(f"❌ Could not read video duration: {e}")
        return 0

    print(f"⏱ Video length: {duration:.2f} seconds")
    
    # SKIP FIRST 5 SECONDS AND LAST 5 SECONDS
    usable_duration = duration - 10  # Subtract 10 seconds (5 from start + 5 from end)
    
    if usable_duration <= 0:
        print("❌ Video is too short after skipping first and last 5 seconds")
        return 0
        
    print(f"🎯 Usable duration (after skipping first/last 5s): {usable_duration:.2f} seconds")

    # Number of GIFs to create
    num_clips = math.ceil(usable_duration / clip_length)
    N = num_clips  # Set global N
    print(f"🔄 Creating {num_clips} GIF clips of {clip_length} seconds each...")

    successful_conversions = 0
    for i in range(num_clips):
        start = (i * clip_length) + 5  # ADD 5 SECONDS TO SKIP THE BEGINNING
        output_path = os.path.join(output_dir, f"output_{i+1}.gif")

        # ffmpeg command with error handling
        command = [
            "ffmpeg", "-y",             
            "-ss", str(start),          
            "-t", str(clip_length),     
            "-i", video_path,           
            "-vf", f"fps={fps},scale=480:-1:flags=lanczos", 
            output_path
        ]

        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                print(f"✅ Saved: output_{i+1}.gif")
                successful_conversions += 1
            else:
                print(f"⚠️  Failed to create: output_{i+1}.gif - {result.stderr[:100]}") 
        except Exception as e:
            print(f"❌ Error creating output_{i+1}.gif: {e}")
    
    print(f"📊 Successfully created {successful_conversions}/{num_clips} GIFs")
    return successful_conversions

def setup_gemini(video_title, video_description, video_tags):
    """Configure the Gemini AI for tag generation using gemini-2.0-flash-exp based on YouTube video content"""
    global TAGS
    
    try:
        genai.configure(api_key="AIzaSyCA_zjgfMu3nCEg0IA2ws57lICRYyggnsw")
        
        # Use the specified model
        model_name = "gemini-2.0-flash-exp"
        print(f"✅ Using model: {model_name}")
        model = genai.GenerativeModel(model_name=model_name)
        
        # Generate tags based on YouTube video content
        print("🤖 Generating tags with Gemini AI based on YouTube video content...")
        
        # Prepare context from YouTube video
        context = f"Video Title: {video_title}"
        if video_description:
            # Limit description length to avoid token limits
            short_description = video_description[:500] + "..." if len(video_description) > 500 else video_description
            context += f"\nVideo Description: {short_description}"
        if video_tags:
            context += f"\nVideo Tags: {', '.join(video_tags[:10])}"  # Limit to first 10 tags
        
        prompt = f"""
        Based on this YouTube video content:
        {context}
        
        Generate 14 short, SEO-friendly hashtags specifically relevant to this video's content. 
        Focus on tags that would be appropriate for GIF clips from this video.
        Include a mix of:
        - Specific tags related to the video content
        - Trending/viral tags
        - Entertainment/comedy tags
        - Popular culture tags
        
        Only output the tags separated by commas, no other text.
        """
        
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        TAGS = [tag.strip() for tag in text_response.replace("\n", "").split(",") if tag.strip()]
        
        # Ensure we have exactly 14 tags
        if len(TAGS) < 14:
            print(f"⚠️  Generated only {len(TAGS)} tags, adding some defaults...")
            default_tags = ["#gif", "#animation", "#funny", "#meme", "#trending", "#viral", "#entertainment", "#comedy", "#dance", "#viralvideo", "#fun", "#lol", "#popular", "#fyp"]
            # Add defaults without duplicates
            for tag in default_tags:
                if tag not in TAGS and len(TAGS) < 14:
                    TAGS.append(tag)
        else:
            TAGS = TAGS[:14]
            
        print("✅ Tags generated based on YouTube content:", TAGS)
        return True
        
    except Exception as e:
        print(f"❌ Gemini AI setup failed: {e}")
        # Fallback to video-based tags or defaults
        if video_tags:
            TAGS = [f"#{tag.replace(' ', '')}" for tag in video_tags[:14]]
            if len(TAGS) < 14:
                TAGS.extend(["#gif", "#animation", "#funny", "#meme", "#trending", "#viral"])
                TAGS = TAGS[:14]
        else:
            TAGS = ["#gif", "#animation", "#funny", "#meme", "#trending", "#viral", "#entertainment", "#comedy", "#dance", "#viralvideo", "#fun", "#lol", "#popular", "#fyp"]
        print("✅ Using fallback tags:", TAGS)
        return False

class GiphyUploader:
    def __init__(self, video_title, video_description, video_tags, auto_start=False):
        self.root = Tk()
        self.root.title("GIPHY Upload Automation")
        self.root.geometry("500x450")
        self.root.configure(bg='#121212')
        
        # Status variable
        self.status = StringVar()
        self.status.set("Ready to start GIPHY upload process")
        
        # Store the video info for later use
        self.video_title = video_title
        self.video_description = video_description
        self.video_tags = video_tags
        
        # Configure Gemini AI with YouTube video context
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
        """Configure the Gemini AI for tag generation using YouTube video content"""
        try:
            genai.configure(api_key="YOUR API TAG ")
            
            # Use the specified model
            model_name = "gemini-2.0-flash-exp"
            print(f"✅ Using model: {model_name}")
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
        
    def generate_and_paste_tags(self):
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
            
            # Generate tags based on YouTube video content
            context = f"Video Title: {self.video_title}"
            if self.video_description:
                short_description = self.video_description[:500] + "..." if len(self.video_description) > 500 else self.video_description
                context += f"\nVideo Description: {short_description}"
            if self.video_tags:
                context += f"\nVideo Tags: {', '.join(self.video_tags[:10])}"
            
            prompt = f"""
            Based on this YouTube video content:
            {context}
            
            Generate 14 short, SEO-friendly hashtags specifically relevant to this video's content. 
            Focus on tags that would be appropriate for GIF clips from this video.
            Include a mix of:
            - Specific tags related to the video content
            - Trending/viral tags
            - Entertainment/comedy tags
            - Popular culture tags
            
            Only output the tags separated by commas, no other text.
            """
            
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
    
    def select_gif_files(self, gif_directory):
        """
        Enhanced file selection system from Tenor code
        Handles file selection in the file dialog
        """
        try:
            # Wait for file dialog to open
            time.sleep(2)
            
            # Click on address bar to focus and paste the path
            self.update_status("Selecting GIF directory in file dialog...")
            pyautogui.click(445, 60)  # Address bar position
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'a')  # Select all
            time.sleep(0.2)
            pyautogui.write(gif_directory)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(2)
            
            # Wait for directory to load
            self.update_status("Loading directory contents...")
            time.sleep(2)
            
            # Click in the file list area to focus
            pyautogui.click(400, 300)
            time.sleep(0.5)
            
            # Select all GIF files using Ctrl+A
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)
            
            # CHANGED: Press ENTER instead of clicking coordinates
            self.update_status("Pressing Enter to select files...")
            pyautogui.press('enter')
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self.update_status(f"Error in file selection: {str(e)}")
            return False
    
    def start_process(self):
        self.update_status("Starting GIPHY upload process...")
            
        try:
            # Step 0: Open GIPHY website
            self.update_status("Opening GIPHY website...")
            url = "https://giphy.com/upload"
            webbrowser.open(url)
            time.sleep(5)  # Wait for page to load
            
            # Step 1: Click on upload button
            self.click_at_position(1229, 191, "Clicking on upload button")
            
            # Step 2: Click on file selection area
            self.click_at_position(705, 714, "Clicking on file selection area")
            
            # Create folder name from video title (sanitized)
            folder_name = sanitize_filename(self.video_title.replace(" ", "")) + ".gifs"
            gif_directory = os.path.join(r"C:\Users\harip\ALL TEST", folder_name)
            
            # Check if GIF files already exist
            gifs_exist, existing_gif_count = check_existing_gifs(gif_directory)
            if not gifs_exist:
                self.update_status("❌ No GIF files found. Please run conversion first.")
                self.root.quit()  # Close window if no GIFs found
                return
            
            self.update_status(f"✅ GIF files found in: {gif_directory}")
            
            # Step 3: Use enhanced file selection system
            if not self.select_gif_files(gif_directory):
                self.update_status("File selection failed. Exiting.")
                self.root.quit()  # Close window on failure
                return
            
            # Step 4: Wait for GIF to load with better timing
            self.update_status("Waiting for GIF to upload and process (45 seconds)...")
            for i in range(45, 0, -5):
                self.update_status(f"Processing... {i} seconds remaining")
                time.sleep(5)
            
            # Step 5: Click on tags area and generate/paste tags
            self.click_at_position(1211, 603, "Opening tags section")
            time.sleep(2)
            
            # Generate and paste tags using the YouTube video context
            self.generate_and_paste_tags()
            
            # Step 6: Final upload click
            self.click_at_position(1257, 1035, "Final upload")
            
            self.update_status("Upload process completed successfully!")
            
            # Wait a bit and then close the window automatically
            time.sleep(3)
            self.root.quit()
            
        except pyautogui.FailSafeException:
            self.update_status("Process was aborted by moving mouse to corner")
            self.root.quit()
        except Exception as e:
            self.update_status(f"An error occurred: {str(e)}")
            self.root.quit()
    
    def run(self):
        self.root.mainloop()

def process_single_video(url, total_videos, current_index):
    """Process a single video: download, convert to GIFs, and upload to GIPHY"""
    global N, CURRENT_VIDEO_INDEX
    
    print(f"\n{'='*60}")
    print(f"🎬 PROCESSING VIDEO {current_index + 1} OF {total_videos}")
    print(f"🔗 URL: {url}")
    print(f"{'='*60}")
    
    # Step 1: Download video from URL
    print("🎥 VIDEO DOWNLOADER & GIF CONVERTER")
    print("=" * 40)
    
    # Download the video and get the title, description, and tags
    downloaded_video_path, video_title, video_description, video_tags = download_video_from_url(url)
    
    if not downloaded_video_path or not os.path.exists(downloaded_video_path):
        print("❌ Video download failed. Skipping to next video.")
        return False

    print(f"📁 Downloaded video: {downloaded_video_path}")
    print(f"🎬 Video title: {video_title}")
    if video_description:
        print(f"📝 Video description: {video_description[:100]}...")
    if video_tags:
        print(f"🏷 Video tags: {', '.join(video_tags[:5])}...")
    
    # Step 2: Convert to GIFs
    print("\n" + "=" * 40)
    print("🔄 CONVERTING TO GIFS")
    print("=" * 40)
    
    # Create folder name from video title (sanitized) - without underscores, with .gifs extension
    folder_name = sanitize_filename(video_title.replace(" ", "")) + ".gifs"
    final_output_dir = os.path.join(r"C:\Users\harip\ALL TEST", folder_name)
    
    print(f"🎯 Creating GIFs in: {final_output_dir}")
    
    # CHECK IF GIFs ALREADY EXIST
    gifs_exist, existing_gif_count = check_existing_gifs(final_output_dir)
    
    if gifs_exist:
        print(f"✅ GIFs already exist! Found {existing_gif_count} GIF files.")
        print("🚀 Proceeding directly to GIPHY upload...")
        N = existing_gif_count  # Set global N to existing count
    else:
        # Convert the downloaded video to GIFs
        successful_gifs = video_to_gifs(downloaded_video_path, final_output_dir)
        if successful_gifs == 0:
            print("❌ GIF creation failed. Skipping to next video.")
            return False
        print(f"📊 Total GIFs created: {N}")
    
    # Step 3: Automatic GIPHY upload start after 10 seconds
    print("\n" + "=" * 50)
    print("🤖 GIPHY UPLOAD AUTOMATION")
    print("=" * 50)
    
    print("⚠  WARNING: Do not move mouse or keyboard during automation!")
    print("🚀 Starting GIPHY automation in 10 seconds...")
    
    # Countdown
    for i in range(10, 0, -1):
        print(f"Starting in {i} seconds...")
        time.sleep(1)
    
    print("🎬 Starting automation NOW!")
    
    # Safety settings for pyautogui
    pyautogui.FAILSAFE = True
    
    try:
        # Start GIPHY upload automation with YouTube video context
        app = GiphyUploader(video_title, video_description, video_tags, auto_start=True)
        app.run()  # This will block until the window closes
        
        print(f"\n🎉 Video {current_index + 1} processing completed successfully!")
        print(f"📁 Video downloaded to: {downloaded_video_path}")
        print(f"📁 GIFs saved to: {final_output_dir}")
        print(f"📊 Total GIFs created: {N}")
        return True
            
    except KeyboardInterrupt:
        print("\n🛑 Automation interrupted by user!")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during automation: {e}")
        print("💡 Tip: If automation failed, check if all required packages are installed.")
        return False

# --- Main Program Execution ---
if __name__ == "__main__":
    
    print("🎥 MULTI-VIDEO DOWNLOADER & GIF CONVERTER")
    print("=" * 50)
    
    # Get multiple video links from user
    video_links_input = input("Paste video URL(s) (separated by spaces or commas) and press Enter: ").strip()

    if not video_links_input:
        print("No URL provided. Exiting.")
        exit()

    # Extract multiple URLs from input - WITH CONTINUOUS LINK SUPPORT
    ALL_VIDEO_URLS = extract_urls_from_input(video_links_input)
    
    if not ALL_VIDEO_URLS:
        print("❌ No valid URLs found. Please provide valid YouTube links.")
        exit()
    
    print(f"📋 Found {len(ALL_VIDEO_URLS)} video URL(s) to process:")
    for i, url in enumerate(ALL_VIDEO_URLS):
        print(f"  {i+1}. {url}")
    
    # Process each video one by one
    successful_processed = 0
    
    for i, url in enumerate(ALL_VIDEO_URLS):
        CURRENT_VIDEO_INDEX = i
        
        if process_single_video(url, len(ALL_VIDEO_URLS), i):
            successful_processed += 1
            
        # If there are more videos, wait before starting next one
        if i < len(ALL_VIDEO_URLS) - 1:
            next_video_num = i + 2
            print(f"\n⏳ Preparing for next video ({next_video_num}/{len(ALL_VIDEO_URLS)}) in 5 seconds...")
            time.sleep(5)
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {successful_processed}/{len(ALL_VIDEO_URLS)} videos")
    print(f"❌ Failed: {len(ALL_VIDEO_URLS) - successful_processed}/{len(ALL_VIDEO_URLS)} videos")
    print("🎉 All operations completed!")
