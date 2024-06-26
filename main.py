from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
import wikipedia
import os
from pathlib import Path
import pyttsx3
import requests
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jarvis.db'  # SQLite database file path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load configuration from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

OPENAI_API_KEY = config.get('OPENAI_API_KEY')
GITHUB_API_TOKEN = config.get('GITHUB_API_TOKEN')
GITHUB_USERNAME = config.get('GITHUB_USERNAME')

client = OpenAI(api_key=OPENAI_API_KEY)

# Define a model for the database
class UserQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.String(255), nullable=False)
    response_text = db.Column(db.Text, nullable=False)

# Function to generate speech from text using pyttsx3
def generate_speech(text, output_file):
    engine = pyttsx3.init()
    engine.save_to_file(text, output_file)
    engine.runAndWait()

# GitHub API details (replace with your GitHub credentials)
github_token = GITHUB_API_TOKEN
github_username = GITHUB_USERNAME

# Function to create a new GitHub repository
def create_github_repo(repo_name, description):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    payload = {
        "name": repo_name,
        "description": description,
        "private": False  # Change to True for private repositories
    }
    response = requests.post(f'https://api.github.com/user/repos', headers=headers, json=payload)
    return response.json()

# Function to add file to GitHub repository
def add_file_to_repo(repo_name, file_name, file_content):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    payload = {
        "message": "Add file via Jarvis Jay's tool",
        "content": file_content,
        "committer": {
            "name": github_username,
            "email": f"{github_username}@users.noreply.github.com"
        }
    }
    response = requests.put(f'https://api.github.com/repos/{github_username}/{repo_name}/contents/{file_name}', headers=headers, json=payload)
    return response.json()

@app.route("/")
def hello_world():
    return app.send_static_file("index.html")

@app.route('/search')
def search():
    query = request.args.get('query', '')
    try:
        result = wikipedia.summary(query)
    except wikipedia.exceptions.DisambiguationError as e:
        result = "Multiple matches found. Please be more specific."
    except wikipedia.exceptions.PageError:
        result = "Sorry, I couldn't find any information on that topic."
    return result

@app.route('/reply', methods=['POST'])
def reply_to_user():
    data = request.get_json()
    user_query = data.get('query', '')

    # Check if user wants to create a GitHub repository
    if "create repository" in user_query.lower():
        repo_name = "MyNewRepo"  # Example repo name
        description = "This is a new repository created via Jarvis Jay's tool."

        # Create repository on GitHub
        repo_response = create_github_repo(repo_name, description)

        if 'html_url' in repo_response:
            response_text = f"Master Jay, successfully created repository: {repo_response['html_url']}"
        else:
            response_text = "Master Jay, failed to create repository on GitHub."

    # Check if user wants to add code to a GitHub repository
    elif "add code to repository" in user_query.lower():
        repo_name = "MyNewRepo"  # Example repo name
        file_name = "example.py"
        file_content = "# Example Python code\nprint('Hello, World!')"

        # Add file to GitHub repository
        add_file_response = add_file_to_repo(repo_name, file_name, file_content)

        if 'content' in add_file_response:
            response_text = f"Master Jay, successfully added code to repository: {add_file_response['content']['html_url']}"
        else:
            response_text = "Master Jay, failed to add code to repository on GitHub."

    else:
        # Default AI response handling
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{
                'role': 'user',
                'content': f"{user_query}"
            }],
            temperature=0,
        )

        response_text = "No response from OpenAI."
        if response and response.choices:
            response_text = " ".join(choice.message.get('content', '') for choice in response.choices if choice.message.get('content', ''))

        # Save user query and AI response to database
        new_query = UserQuery(query_text=user_query, response_text=response_text)
        db.session.add(new_query)
        db.session.commit()

    # Generate speech from response text
    mp3_file_path = Path(__file__).parent / "response.mp3"
    generate_speech(response_text, mp3_file_path)

    # Return JSON response with MP3 file path
    return jsonify({"response": response_text, "mp3_path": "/play_response"})

@app.route('/play_response')
def play_response():
    mp3_file_path = Path(__file__).parent / "response.mp3"
    return render_template('play_response.html', mp3_path=mp3_file_path)

@app.route('/generateimages/<prompt>')
def generate_images(prompt):
    response = client.images.generate(
        model="dall-e-2",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=2,
    )  
    images = [image.url for image in response.data]
    return jsonify({"images": images})

print ("main.hehe")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)