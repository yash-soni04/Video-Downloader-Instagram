from flask import Flask, request, render_template, send_from_directory
import requests
import os
import re
from urllib.parse import urlparse

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Modified headers to mimic browser behavior
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.instagram.com/',
    'DNT': '1'
}

def extract_video_url(html_content):
    """Extract video URL from Instagram page HTML"""
    # New regex pattern that works with current Instagram HTML structure
    pattern = r'"video_url":"(https?://[^"]+\.mp4[^"]*)"'
    match = re.search(pattern, html_content)
    return match.group(1) if match else None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        
        if not url.startswith(('https://www.instagram.com/', 'https://instagram.com/')):
            return "Invalid Instagram URL"
        
        try:
            # Fetch the Instagram page
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            
            # Extract video URL
            video_url = extract_video_url(response.text)
            if not video_url:
                return "Could not find video in this post"
            
            # Download the video
            shortcode = url.split("/")[-2]
            video_path = os.path.join(DOWNLOAD_FOLDER, f"{shortcode}.mp4")
            
            with requests.get(video_url, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            return render_template("success.html", 
                               video_url=f"/download/{shortcode}.mp4",
                               shortcode=shortcode)
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    return render_template("index.html")

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
