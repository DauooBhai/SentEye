# -*- coding: utf-8 -*-
"""channelanalyser.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1LeCjL7PWng3JisLoAydK_qDN9bMeoA64
"""

# Install required libraries
!pip install flask yt-dlp google-api-python-client nltk pyngrok matplotlib

# Import necessary libraries
from flask import Flask, request, render_template_string
import googleapiclient.discovery
import googleapiclient.errors
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd
import re
import time
import yt_dlp
from pyngrok import ngrok
import matplotlib.pyplot as plt
import os

# Ensure nltk dependencies are downloaded
nltk.download("vader_lexicon")
sia = SentimentIntensityAnalyzer()

# Set up YouTube API
API_KEY = "AIzaSyCoib0zISu_-BpGzHmV8jq8WZhICLsR6GE"  # Replace with your API key
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

# Initialize Flask app
app = Flask(__name__)

# Function to get video transcript
def get_video_transcript(video_id):
    """Fetch transcript using yt_dlp."""
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            subtitles = info.get("automatic_captions", {}).get("en", [])
            if subtitles:
                transcript = subtitles[0].get("url")
                return transcript if transcript else None
    except Exception as e:
        print(f"Error fetching transcript: {e}")
    return None

# Function to analyze sentiment
def analyze_sentiment(text):
    """Analyze sentiment using VADER."""
    sentiment_score = sia.polarity_scores(text)
    if sentiment_score['compound'] >= 0.05:
        return "Positive"
    elif sentiment_score['compound'] <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# Function to get video comments
def get_video_comments(video_id):
    """Fetch top 5 comments of a video."""
    try:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=5,
            order="relevance"
        ).execute()
        comments = [item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in response.get("items", [])]
        return " ".join(comments)
    except Exception as e:
        print(f"Error fetching comments: {e}")
    return ""

# Function to get video likes and dislikes
def get_video_likes_dislikes(video_id):
    """Fetch like-dislike count of a video."""
    try:
        response = youtube.videos().list(
            part="statistics",
            id=video_id
        ).execute()
        stats = response["items"][0]["statistics"]
        likes = int(stats.get("likeCount", 0))
        dislikes = int(stats.get("dislikeCount", 1))  # Avoid division by zero
        ratio = likes / (likes + dislikes)
        return ratio
    except Exception as e:
        print(f"Error fetching like-dislike ratio: {e}")
    return 0.5  # Neutral default

# Function to get all video IDs from a channel
def get_channel_videos(channel_id):
    """Fetch all video IDs from a channel."""
    video_ids = []
    next_page_token = None
    while True:
        response = youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token,
            type="video"
        ).execute()
        video_ids.extend([item['id']['videoId'] for item in response.get("items", [])])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return video_ids

# Function to analyze all videos in a channel
def analyze_channel(channel_id):
    """Analyze all videos in a channel."""
    video_ids = get_channel_videos(channel_id)
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}

    for video_id in video_ids:
        transcript = get_video_transcript(video_id)
        if transcript:
            sentiment = analyze_sentiment(transcript)
        else:
            comments = get_video_comments(video_id)
            like_ratio = get_video_likes_dislikes(video_id)

            if comments:
                sentiment = analyze_sentiment(comments)
            else:
                sentiment = "Positive" if like_ratio > 0.7 else "Negative" if like_ratio < 0.3 else "Neutral"

        sentiment_counts[sentiment] += 1
        print(f"Processed video {video_id}: {sentiment}")
        time.sleep(1)  # Avoid hitting API rate limits

    return sentiment_counts

# Function to plot sentiment distribution as a pie chart
def plot_sentiment_distribution(sentiment_counts):
    """Plot sentiment distribution as a pie chart."""
    labels = sentiment_counts.keys()
    sizes = sentiment_counts.values()
    colors = ['gold', 'lightcoral', 'lightskyblue']
    explode = (0.1, 0, 0)  # Explode the 1st slice (Positive)

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title("Sentiment Distribution")
    plt.savefig('static/sentiment_pie_chart.png')  # Save the plot as an image
    plt.close()

# HTML templates as strings
index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Channel Sentiment Analysis</title>
    <style>
        /* Import JetBrains Mono font from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

        body {
            font-family: 'JetBrains Mono', monospace;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            background: rgb(238,174,202);
            background: radial-gradient(circle, rgba(238,174,202,1) 0%, rgba(148,187,233,1) 100%);
            position: relative;
            overflow: hidden;
        }

        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            text-align: center;
            position: relative;
            z-index: 2;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
        }

        form {
            display: flex;
            flex-direction: column;
            gap: 15px;
            align-items: center;
        }

        label {
            font-size: 1.2rem;
            font-style: italic;
            color: #444;
        }

        input[type="text"] {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            padding: 10px;
            border: 2px solid #555;
            border-radius: 5px;
            width: 300px;
            outline: none;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus {
            border-color: #007BFF;
        }

        button {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            font-weight: bold;
            padding: 10px 20px;
            background-color: #007BFF;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        button:hover {
            background-color: #0056b3;
        }

        button:active {
            background-color: #004080;
        }

        /* Random SVG Designs */
        .random-svg {
            position: absolute;
            z-index: 1;
            opacity: 0.3;
            font-size: 4rem; /* Increased size */
            color: #555;
            animation: float 6s infinite ease-in-out;
        }

        @keyframes float {
            0%, 100% {
                transform: translateY(0) rotate(0deg) scale(1);
            }
            25% {
                transform: translateY(-30px) rotate(-15deg) scale(1.1);
            }
            50% {
                transform: translateY(20px) rotate(15deg) scale(0.9);
            }
            75% {
                transform: translateY(-20px) rotate(-10deg) scale(1.05);
            }
        }

        /* Birds Animation */
        .bird {
            position: absolute;
            font-size: 3rem;
            color: #555;
            opacity: 0.4;
            animation: fly 8s linear infinite;
        }

        @keyframes fly {
            0% {
                transform: translateX(-100%) translateY(0) rotate(0deg);
            }
            100% {
                transform: translateX(100vw) translateY(-50px) rotate(360deg);
            }
        }

        /* Clouds Animation */
        .cloud {
            position: absolute;
            font-size: 5rem;
            color: #fff;
            opacity: 0.2;
            animation: drift 10s linear infinite;
        }

        @keyframes drift {
            0% {
                transform: translateX(-100%);
            }
            100% {
                transform: translateX(100vw);
            }
        }

        /* Stars Animation */
        .star {
            position: absolute;
            font-size: 2rem;
            color: #fff;
            opacity: 0.3;
            animation: twinkle 3s infinite ease-in-out;
        }

        @keyframes twinkle {
            0%, 100% {
                opacity: 0.3;
                transform: scale(1);
            }
            50% {
                opacity: 0.8;
                transform: scale(1.2);
            }
        }

        /* Hearts Animation */
        .heart {
            position: absolute;
            font-size: 2rem;
            color: #ff6b6b;
            opacity: 0.4;
            animation: float 5s infinite ease-in-out;
        }

        /* Snail Animation */
        .snail {
            position: absolute;
            bottom: -50px;
            left: -50px;
            font-size: 5rem; /* Increased size */
            animation: crawl 12s linear infinite;
            z-index: 1;
        }

        @keyframes crawl {
            0% {
                transform: translateX(-100%) rotate(0deg);
            }
            100% {
                transform: translateX(100vw) rotate(360deg);
            }
        }
    </style>
</head>
<body>
    <!-- Random SVG Elements -->
    <div class="random-svg" style="top: 10%; left: 5%; font-size: 5rem; transform: rotate(-15deg);">#</div>
    <div class="random-svg" style="top: 20%; right: 10%; font-size: 4.5rem; transform: rotate(25deg);">{}</div>
    <div class="random-svg" style="top: 40%; left: 15%; font-size: 4rem; transform: rotate(-10deg);">*</div>
    <div class="random-svg" style="bottom: 20%; right: 5%; font-size: 5.5rem; transform: rotate(15deg);">~</div>
    <div class="random-svg" style="bottom: 10%; left: 20%; font-size: 4rem; transform: rotate(-20deg);">/</div>
    <div class="random-svg" style="top: 5%; right: 20%; font-size: 4.2rem; transform: rotate(30deg);">@</div>

    <!-- Birds -->
    <div class="bird" style="top: 15%; left: 10%;">🐦</div>
    <div class="bird" style="top: 25%; right: 15%;">🦅</div>

    <!-- Clouds -->
    <div class="cloud" style="top: 5%; left: 20%;">☁️</div>
    <div class="cloud" style="top: 15%; right: 5%;">☁️</div>

    <!-- Stars -->
    <div class="star" style="top: 30%; left: 30%;">⭐</div>
    <div class="star" style="top: 40%; right: 40%;">🌟</div>

    <!-- Hearts -->
    <div class="heart" style="top: 50%; left: 10%;">❤️</div>
    <div class="heart" style="top: 60%; right: 20%;">💖</div>

    <!-- Moving Snail -->
    <div class="snail">🐌</div>

    <div class="container">
        <h1>YouTube Channel Sentiment Analysis</h1>
        <form method="POST">
            <label for="channel_id"><strong>Enter YouTube Channel ID:</strong></label>
            <input type="text" id="channel_id" name="channel_id" required placeholder="e.g., UC_x5XG1OV2P6uZZ5FSM9Ttw">
            <button type="submit">Analyze</button>
        </form>
    </div>
</body>
</html>
"""

result_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentiment Analysis Results</title>
    <style>
        /* Import JetBrains Mono font from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

        body {
            font-family: 'JetBrains Mono', monospace;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            background: rgb(238,174,202);
            background: radial-gradient(circle, rgba(238,174,202,1) 0%, rgba(148,187,233,1) 100%);
            position: relative;
            overflow: hidden;
        }

        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            text-align: center;
            position: relative;
            z-index: 2;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
        }

        p {
            font-size: 1.2rem;
            color: #444;
            margin: 5px 0;
        }

        img {
            max-width: 100%;
            height: auto;
            margin-top: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }

        a {
            font-size: 1rem;
            color: #007BFF;
            text-decoration: none;
            margin-top: 20px;
            transition: color 0.3s ease;
        }

        a:hover {
            color: #0056b3;
        }

        /* Math-related Moving Objects */
        .math-object {
            position: absolute;
            z-index: 1;
            opacity: 0.3;
            font-size: 3rem;
            color: #555;
            animation: float 6s infinite ease-in-out;
        }

        @keyframes float {
            0%, 100% {
                transform: translateY(0) rotate(0deg) scale(1);
            }
            25% {
                transform: translateY(-30px) rotate(-15deg) scale(1.1);
            }
            50% {
                transform: translateY(20px) rotate(15deg) scale(0.9);
            }
            75% {
                transform: translateY(-20px) rotate(-10deg) scale(1.05);
            }
        }

        /* Graphs and Charts */
        .graph {
            position: absolute;
            font-size: 4rem;
            color: #555;
            opacity: 0.4;
            animation: drift 10s linear infinite;
        }

        @keyframes drift {
            0% {
                transform: translateX(-100%);
            }
            100% {
                transform: translateX(100vw);
            }
        }

        /* Loading Bar */
        .loading-bar {
            position: fixed;
            top: 50%; /* Centered vertically */
            left: 50%; /* Centered horizontally */
            width: 50%; /* Adjust width */
            height: 5px;
            background: #007BFF;
            z-index: 9999;
            transform: translate(-50%, -50%) scaleX(0); /* Center the bar */
            transform-origin: left;
            animation: loading 2s ease-in-out;
        }

        @keyframes loading {
            0% {
                transform: translate(-50%, -50%) scaleX(0);
            }
            50% {
                transform: translate(-50%, -50%) scaleX(1);
            }
            100% {
                transform: translate(-50%, -50%) scaleX(0);
            }
        }

        /* Hide content until loaded */
        .content {
            display: none;
        }

        .loaded .content {
            display: block;
        }

        .loaded .loading-bar {
            display: none;
        }
    </style>
</head>
<body>
    <!-- Loading Bar -->
    <div class="loading-bar"></div>

    <!-- Math-related Moving Objects -->
    <div class="math-object" style="top: 10%; left: 5%; font-size: 4rem; transform: rotate(-15deg);">+</div>
    <div class="math-object" style="top: 20%; right: 10%; font-size: 4rem; transform: rotate(25deg);">-</div>
    <div class="math-object" style="top: 40%; left: 15%; font-size: 4rem; transform: rotate(-10deg);">×</div>
    <div class="math-object" style="bottom: 20%; right: 5%; font-size: 4rem; transform: rotate(15deg);">÷</div>
    <div class="math-object" style="bottom: 10%; left: 20%; font-size: 4rem; transform: rotate(-20deg);">()</div>
    <div class="math-object" style="top: 5%; right: 20%; font-size: 4rem; transform: rotate(30deg);">[]</div>

    <!-- Graphs and Charts -->
    <div class="graph" style="top: 15%; left: 10%;">📈</div>
    <div class="graph" style="top: 25%; right: 15%;">📉</div>

    <!-- Centered Content -->
    <div class="container content">
        <h1>Sentiment Analysis Results</h1>
        <p>Positive: {{ sentiment_counts['Positive'] }}</p>
        <p>Negative: {{ sentiment_counts['Negative'] }}</p>
        <p>Neutral: {{ sentiment_counts['Neutral'] }}</p>
        <img src="{{ url_for('static', filename='sentiment_pie_chart.png') }}" alt="Sentiment Distribution">
        <br>
        <a href="/">Back to Home</a>
    </div>

    <script>
        // Simulate page load for demonstration
        setTimeout(() => {
            document.body.classList.add('loaded');
        }, 2000); // Adjust this timeout to match your actual page load time
    </script>
</body>
</html>
"""

# Home route to display the input form
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        channel_id = request.form['channel_id']
        sentiment_counts = analyze_channel(channel_id)

        # Plot sentiment distribution
        plot_sentiment_distribution(sentiment_counts)

        # Render the result template with sentiment counts
        return render_template_string(result_html, sentiment_counts=sentiment_counts)
    return render_template_string(index_html)

# Run the Flask app with ngrok
if __name__ == '__main__':
    # Create static folder if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')

    # Kill any existing ngrok tunnels
    ngrok.kill()

    # Authenticate ngrok
    ngrok.set_auth_token("2t5sOIGkHQ4BTRxaOopDYphXY5Z_5QxnPCfSixPf4RuR7AQRv")  # Replace with your ngrok authtoken

    # Start ngrok tunnel
    public_url = ngrok.connect(5000)
    print("Public URL:", public_url)

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)