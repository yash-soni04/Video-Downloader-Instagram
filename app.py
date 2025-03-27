from flask import Flask, request, render_template, send_from_directory
import instaloader
import os

app = Flask(__name__)

# Configure paths for Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

loader = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_FOLDER,
    download_pictures=False,
    download_videos=True,
    download_video_thumbnails=False,
    save_metadata=False
)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        if not url or "instagram.com" not in url:
            return "Please enter a valid Instagram URL"
        
        try:
            shortcode = url.split("/")[-2]
            
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target=os.path.join(DOWNLOAD_FOLDER, shortcode))
            
            video_path = os.path.join(DOWNLOAD_FOLDER, shortcode, f"{shortcode}.mp4")
            return (
                f"Video downloaded successfully!"
            )
        except Exception as e:
            return f"Error: {str(e)}"
    return render_template("index.html")

@app.route("/download/<shortcode>")
def download_file(shortcode):
    return send_from_directory(
        os.path.join(DOWNLOAD_FOLDER, shortcode),
        f"{shortcode}.mp4",
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
