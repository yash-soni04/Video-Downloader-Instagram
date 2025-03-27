from flask import Flask, request, render_template
import instaloader
import os

app = Flask(__name__)

loader = instaloader.Instaloader(
    download_pictures=False,
    download_geotags=False,
    download_comments=False,
    download_video_thumbnails=False,
    save_metadata=False,
)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        shortcode = url.split("/")[-2]
        try:
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target="downloads")
            return f'<a href="/downloads/{shortcode}.mp4" download>Click here to download</a>'
        except Exception as e:
            return f"Error: {e}"
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
