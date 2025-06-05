import os
import uuid
import base64
import tempfile
import json
from dotenv import load_dotenv
from openai import OpenAI
from utils.embedder import load_index
from utils.retriever import retrieve
from utils.prompt_helper import build_prompt

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Load vectors and chunks for retrieval
vectors, chunks = load_index()

def get_rag_response(user_input):
    results = retrieve(user_input, vectors, chunks)
    prompt = build_prompt(user_input, results)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def speech_to_text(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            response_format="text",
            file=audio_file
        )
    return transcript

def generate_viseme_data(text):
    """Generate viseme data based on text content that matches the frontend viseme map.
    This is a simplified version - in production, you'd want to use a proper TTS service
    that provides accurate viseme timings."""
    # Viseme mapping based on phonemes that matches the frontend viseme map
    visemes = []
    duration_per_char = 0.07  # seconds per character (faster speech rate)
    
    # Add a neutral/closed mouth at the beginning
    visemes.append({
        'start': 0,
        'end': 0.1,
        'value': 'X'  # Neutral/closed mouth
    })
    
    current_time = 0.1  # Start after the initial neutral position
    
    for i, char in enumerate(text.lower()):
        # Map characters to visemes that match the frontend viseme map
        if char in 'a':
            viseme = 'A'  # 'ah' sound
        elif char in 'e':
            viseme = 'E'  # 'eh' sound
        elif char in 'i':
            viseme = 'I'  # 'ee' sound
        elif char in 'o':
            viseme = 'O'  # 'oh' sound
        elif char in 'u':
            viseme = 'U'  # 'oo' sound
        elif char in 'bp':
            viseme = 'B'  # Bilabial plosives
        elif char in 'fv':
            viseme = 'F'  # Labiodental fricatives
        elif char in 'th':
            viseme = 'T'  # Dental fricatives
        elif char in 'dt':
            viseme = 'D'  # Alveolar plosives
        elif char in 'kg':
            viseme = 'K'  # Velar plosives
        elif char in 'szj':
            viseme = 'S'  # Sibilants
        elif char in 'n':
            viseme = 'N'  # Nasals
        elif char in 'r':
            viseme = 'R'  # Alveolar approximants
        elif char in ' ,.!?;:':
            # For punctuation and spaces, add a brief neutral mouth shape
            viseme = 'X'  # Neutral/closed mouth
        else:
            # Default for other characters
            viseme = 'X'  # Neutral/closed mouth
        
        # Only add viseme if it's not a space or punctuation
        start_time = current_time
        end_time = start_time + duration_per_char
        
        visemes.append({
            'start': start_time,
            'end': end_time,
            'value': viseme
        })
        
        current_time = end_time
    
    # Add a neutral/closed mouth at the end
    visemes.append({
        'start': current_time,
        'end': current_time + 0.1,
        'value': 'X'  # Neutral/closed mouth
    })
    
    return visemes

def text_to_speech(text):
    # Generate speech
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )
    
    # Create audio directory if it doesn't exist
    os.makedirs("audio", exist_ok=True)
    
    # Generate unique ID for this audio file
    audio_id = uuid.uuid4().hex
    audio_path = f"audio/{audio_id}.mp3"
    
    # Save audio file
    response.stream_to_file(audio_path)
    
    # Estimate audio duration based on text length and speaking rate
    # Average speaking rate is about 150 words per minute or 2.5 words per second
    # Assuming average word length of 5 characters + 1 space = 6 characters per word
    # This gives us approximately 15 characters per second
    estimated_duration = len(text) / 15  # in seconds
    
    # Generate viseme data with timing scaled to match estimated duration
    viseme_cues = generate_viseme_data(text)
    
    # Scale the timing of viseme cues to match the estimated audio duration
    # First, find the original duration of the viseme sequence
    original_end_time = viseme_cues[-1]['end']
    
    # Calculate scaling factor
    scaling_factor = estimated_duration / original_end_time
    
    # Scale all timings
    for cue in viseme_cues:
        cue['start'] *= scaling_factor
        cue['end'] *= scaling_factor
    
    # Generate and save viseme data
    viseme_data = {
        'text': text,
        'duration': estimated_duration,
        'mouthCues': viseme_cues
    }
    
    # Save viseme data as JSON with pretty formatting for easier debugging
    viseme_path = f"audio/{audio_id}.json"
    with open(viseme_path, 'w') as f:
        json.dump(viseme_data, f, indent=2)
    
    print(f"Generated viseme data with {len(viseme_cues)} cues for audio {audio_id}")
    return audio_path
