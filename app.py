from flask import Flask, request, render_template, send_from_directory
import requests
import os
import re
import json
from urllib.parse import urlparse, unquote

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.instagram.com/',
    'DNT': '1'
}

def extract_video_url(html_content):
    """Improved video URL extraction for current Instagram layout"""
    try:
        # Method 1: Find JSON data in script tag
        script_data = re.search(r'<script type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL)
        if script_data:
            json_data = json.loads(script_data.group(1).get('video', [{}])[0]
            if json_data.get('contentUrl'):
                return unquote(json_data['contentUrl'])

        # Method 2: Find video URL in embedded JSON
        embedded_data = re.search(r'window\.__additionalDataLoaded\(\'[^\']+\',(.*?)\);', html_content)
        if embedded_data:
            video_info = json.loads(embedded_data.group(1))
            if video_info.get('items'):
                for item in video_info['items']:
                    if item.get('video_versions'):
                        return max(item['video_versions'], key=lambda x: x.get('width', 0))['url']

        # Method 3: Fallback to direct URL search
        video_url = re.search(r'"video_url":"(https?://[^"]+)"', html_content)
        if video_url:
            return unquote(video_url.group(1))

    except Exception as e:
        print(f"Extraction error: {e}")
    
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        
        if not any(x in url for x in ('instagram.com/p/', 'instagram.com/reel/')):
            return "Please provide a valid Instagram post/reel URL"
        
        try:
            # Add mobile version parameter to get simpler HTML
            if '?' in url:
                url += '&__a=1&__d=dis'
            else:
                url += '?__a=1&__d=dis'
            
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            
            video_url = extract_video_url(response.text)
            if not video_url:
                return "Found the post but couldn't extract video URL. Instagram may have changed their page structure."
            
            shortcode = url.split("/")[-1].split("?")[0]
            video_path = os.path.join(DOWNLOAD_FOLDER, f"{shortcode}.mp4")
            
            # Download with proper streaming
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
