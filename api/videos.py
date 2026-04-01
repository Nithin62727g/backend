from flask import Blueprint, request, jsonify
from core.config import settings
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)
videos_bp = Blueprint("videos", __name__)

@videos_bp.get("/search")
def search_videos():
    topic = request.args.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "topic parameter is required"}), 400

    api_key = settings.YOUTUBE_API_KEY
    if not api_key or api_key == "YOUR_FREE_YOUTUBE_API_KEY_HERE":
        # Return mock data if no real API key is provided
        return jsonify({
            "topic": topic,
            "videos": [
                {
                    "title": f"Learn {topic} in 100 Seconds",
                    "channel": "Fireship",
                    "thumbnail": "https://i.ytimg.com/vi/placeholder/hqdefault.jpg",
                    "url": "https://youtube.com/watch?v=placeholder"
                },
                {
                    "title": f"{topic} Full Course for Beginners",
                    "channel": "Programming with Mosh",
                    "thumbnail": "https://i.ytimg.com/vi/placeholder2/hqdefault.jpg",
                    "url": "https://youtube.com/watch?v=placeholder2"
                }
            ],
            "is_mock": True
        })

    try:
        query = urllib.parse.quote(topic + " tutorial for beginners")
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults=5&key={api_key}"
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        videos = []
        for item in data.get("items", []):
            video_id = item["id"].get("videoId")
            if video_id:
                videos.append({
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                })
                
        return jsonify({"topic": topic, "videos": videos})
        
    except Exception as e:
        logger.error(f"YouTube API Error: {e}")
        return jsonify({"error": "Failed to fetch videos from YouTube"}), 500
