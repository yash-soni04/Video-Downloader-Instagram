from flask import Flask, request, render_template, send_from_directory, jsonify
import requests
import os
import re
import json
from urllib.parse import urlparse, unquote
import time

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Current browser headers to avoid detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1'
}

def extract_video_data(html):
    """Extract video URL using multiple fallback methods"""
    try:
        # Method 1: JSON-LD data (most reliable when available)
        ld_json = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        if ld_json:
            data = json.loads(ld_json.group(1))
            if isinstance(data, list):
                data = data[0]
            if data.get('video'):
                return unquote(data['video']['contentUrl'])
        
        # Method 2: Embedded GraphQL data
        graphql_data = re.search(r'window\.__additionalDataLoaded\(\'[^\']+\',(.*?)\);', html)
        if graphql_data:
            data = json.loads(graphql_data.group(1))
            if data.get('graphql'):
                video_url = data['graphql']['shortcode_media']['video_url']
                if video_url:
                    return unquote(video_url)
        
        # Method 3: Direct video URL search
        video_url = re.search(r'"video_url":"(https?://[^"]+)"', html)
        if video_url:
            return unquote(video_url.group(1))
        
        # Method 4: Newest Instagram fallback
        video_src = re.search(r'src="(https?://[^"]+\.mp4[^"]*)"', html)
        if video_src:
            return unquote(video_src.group(1))
    
    except Exception as e:
        app.logger.error(f"Extraction error: {e}")
    
    return None

def clean_filename(filename):
    """Remove invalid characters from filenames"""
    return re.sub(r'[^\w\-_. ]', '', filename)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        
        if not any(x in url for x in ('instagram.com/p/', 'instagram.com/reel/')):
            return render_template("error.html", message="Please provide a valid Instagram post or reel URL")
        
        try:
            # Add mobile parameter to simplify HTML
            parsed = urlparse(url)
            if not parsed.query:
                url = f"{url}?__a=1&__d=dis"
            
            # Throttle requests to avoid blocks
            time.sleep(2)
            
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            
            video_url = extract_video_data(response.text)
            if not video_url:
                return render_template("error.html", message="Video found but couldn't extract URL. Try another post.")
            
            shortcode = url.split("/")[-1].split("?")[0]
            filename = f"{shortcode}.mp4"
            filepath = os.path.join(DOWNLOAD_FOLDER, clean_filename(filename))
            
            # Stream download with progress
            with requests.get(video_url, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            return render_template("success.html", 
                               video_url=f"/download/{filename}",
                               shortcode=shortcode)
            
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Request failed: {e}")
            return render_template("error.html", message=f"Network error: {str(e)}")
        except Exception as e:
            app.logger.error(f"Unexpected error: {e}")
            return render_template("error.html", message=f"Processing error: {str(e)}")
    
    return render_template("index.html")

@app.route("/download/<filename>")
def download(filename):
    try:
        return send_from_directory(
            DOWNLOAD_FOLDER,
            clean_filename(filename),
            as_attachment=True,
            mimetype='video/mp4'
        )
    except FileNotFoundError:
        return render_template("error.html", message="File not found or expired")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
