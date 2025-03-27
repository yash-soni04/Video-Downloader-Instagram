from flask import Flask, request, render_template, send_from_directory
import instaloader
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Configure Instaloader for public access only
loader = instaloader.Instaloader(
    download_pictures=False,       # Disable image downloads
    download_videos=True,         # Enable video downloads
    download_video_thumbnails=False,
    save_metadata=False,          # Don't save metadata files
    compress_json=False,
    post_metadata_txt_pattern="", # Disable metadata files
    max_connection_attempts=1     # Faster failure
)

# Set download directory
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def is_valid_instagram_url(url):
    """Check if URL is a valid Instagram post URL"""
    parsed = urlparse(url)
    return (parsed.netloc in ['www.instagram.com', 'instagram.com'] 
            and '/p/' in url or '/reel/' in url)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        
        if not is_valid_instagram_url(url):
            return "Please enter a valid Instagram post URL"
        
        try:
            # Extract shortcode from URL (works for both /p/ and /reel/)
            shortcode = url.split("/")[-2]
            
            # Download the post
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target=os.path.join(DOWNLOAD_FOLDER, shortcode))
            
            # Find the downloaded video
            video_dir = os.path.join(DOWNLOAD_FOLDER, shortcode)
            for file in os.listdir(video_dir):
                if file.endswith('.mp4'):
                    return render_template("success.html", 
                                       video_url=f"/download/{shortcode}/{file}",
                                       shortcode=shortcode)
            
            return "No video found - this might be an image post"
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    return render_template("index.html")

@app.route("/download/<shortcode>/<filename>")
def download(shortcode, filename):
    return send_from_directory(
        os.path.join(DOWNLOAD_FOLDER, shortcode),
        filename,
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
