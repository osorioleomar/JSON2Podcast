import streamlit as st
import json
import io
from pydub import AudioSegment
from elevenlabs import ElevenLabs, VoiceSettings
import requests
import os

# Initialize session state for API key
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''

# Function to initialize ElevenLabs client
def init_elevenlabs_client():
    return ElevenLabs(api_key=st.session_state.api_key)

# Get available voices from ElevenLabs
def get_available_voices():
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": st.session_state.api_key
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        voices_data = response.json()
        return {voice["name"]: {"voice_id": voice["voice_id"], "samples": voice.get("samples", [])} for voice in voices_data["voices"]}
    else:
        st.error(f"Failed to fetch voices: {response.status_code}")
        return {}

# Function to get and play voice sample
def get_voice_sample(voice_id, sample_id):
    try:
        client = init_elevenlabs_client()
        audio_data = client.samples.get_audio(voice_id=voice_id, sample_id=sample_id)
        return audio_data
    except Exception as e:
        st.error(f"Failed to get voice sample: {str(e)}")
        return None

# Function to load or initialize session state
def init_session_state():
    if 'script' not in st.session_state:
        st.session_state.script = []
    if 'config' not in st.session_state:
        st.session_state.config = {
            'intro_text': '',
            'intro_voice': '',
            'intro_music': None,
            'podcasters': {},
            'voice_settings': {
                'stability': 0.7,
                'similarity_boost': 0.75,
                'style': 0.4,
            }
        }
    if 'audio_segments' not in st.session_state:
        st.session_state.audio_segments = []
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'available_voices' not in st.session_state:
        st.session_state.available_voices = {}

# Function to generate audio for a single line
def generate_audio(text, voice_id, voice_settings):
    client = init_elevenlabs_client()
    settings = VoiceSettings(
        stability=voice_settings['stability'],
        similarity_boost=voice_settings['similarity_boost'],
        style=voice_settings['style']
    )
    audio_stream = client.text_to_speech.convert(
        voice_id=voice_id,
        optimize_streaming_latency=0,
        output_format="mp3_44100_128",
        text=text,
        voice_settings=settings
    )
    audio_data = b''.join(chunk for chunk in audio_stream)
    return AudioSegment.from_mp3(io.BytesIO(audio_data))

# Step 0: API Key Input
def step_0():
    st.header("Enter Your ElevenLabs API Key")
    api_key = st.text_input("API Key", type="password")
    if st.button("Submit API Key"):
        st.session_state.api_key = api_key
        st.session_state.available_voices = get_available_voices()
        st.success("API Key submitted successfully!")
        st.session_state.current_step = 1

# Step 1: JSON Input
def step_1():
    st.header("Step 1: Input Script")
    json_input = st.text_area("Paste your JSON script here:", height=300)
    if st.button("Load Script"):
        try:
            script_data = json.loads(json_input)
            if isinstance(script_data, list) and all(isinstance(item, dict) and 'speaker' in item and 'text' in item for item in script_data):
                st.session_state.script = script_data
                st.success("Script loaded successfully!")
                st.session_state.current_step = 2
            else:
                st.error("Invalid script format. Please ensure your JSON is a list of objects with 'speaker' and 'text' keys.")
        except json.JSONDecodeError:
            st.error("Invalid JSON. Please check your input.")

# Step 2: Display and Edit Script
def step_2():
    st.header("Step 2: Edit Script")
    for i, line in enumerate(st.session_state.script):
        with st.expander(f"{line['speaker']}: {line['text'][:50]}...", expanded=True):
            st.session_state.script[i]['speaker'] = st.text_input(f"Speaker {i+1}", line['speaker'], key=f"speaker_{i}")
            st.session_state.script[i]['text'] = st.text_area(f"Edit {line['speaker']}'s line", line['text'], key=f"line_{i}")
    if st.button("Proceed to Configuration"):
        st.session_state.current_step = 3

# Step 3: Configuration
def step_3():
    st.header("Step 3: Configuration")
    st.session_state.config['intro_text'] = st.text_area("Intro Text:", st.session_state.config['intro_text'])
    st.session_state.config['intro_voice'] = st.selectbox("Intro Voice:", list(st.session_state.available_voices.keys()))
    
    # Play voice sample for intro voice
    if st.button("Play Intro Voice Sample"):
        voice_data = st.session_state.available_voices[st.session_state.config['intro_voice']]
        if voice_data['samples']:
            sample = get_voice_sample(voice_data['voice_id'], voice_data['samples'][0]['sample_id'])
            if sample:
                st.audio(sample, format="audio/mp3")
    
    st.subheader("Podcasters")
    podcasters = set(line['speaker'] for line in st.session_state.script)
    for podcaster in podcasters:
        st.session_state.config['podcasters'][podcaster] = st.selectbox(f"Voice for {podcaster}:", list(st.session_state.available_voices.keys()), key=f"voice_{podcaster}")
        # Play voice sample for each podcaster
        if st.button(f"Play {podcaster} Voice Sample"):
            voice_data = st.session_state.available_voices[st.session_state.config['podcasters'][podcaster]]
            if voice_data['samples']:
                sample = get_voice_sample(voice_data['voice_id'], voice_data['samples'][0]['sample_id'])
                if sample:
                    st.audio(sample, format="audio/mp3")
    
    st.subheader("Voice Settings")
    st.session_state.config['voice_settings']['stability'] = st.slider("Stability:", 0.0, 1.0, st.session_state.config['voice_settings']['stability'])
    st.session_state.config['voice_settings']['similarity_boost'] = st.slider("Similarity Boost:", 0.0, 1.0, st.session_state.config['voice_settings']['similarity_boost'])
    st.session_state.config['voice_settings']['style'] = st.slider("Style:", 0.0, 1.0, st.session_state.config['voice_settings']['style'])
    
    st.session_state.config['intro_music'] = st.file_uploader("Upload Intro Music (MP3)", type="mp3")
    
    if st.button("Proceed to Audio Generation"):
        st.session_state.current_step = 4

# Step 4: Generate Audio
def step_4():
    st.header("Step 4: Generate Audio")
    if st.button("Generate All Audio"):
        st.session_state.audio_segments = []
        
        # Generate intro audio
        if st.session_state.config['intro_text']:
            intro_audio = generate_audio(
                st.session_state.config['intro_text'],
                st.session_state.available_voices[st.session_state.config['intro_voice']]['voice_id'],
                st.session_state.config['voice_settings']
            )
            st.session_state.audio_segments.append(("Intro", intro_audio))
        
        # Generate dialog audio
        for i, line in enumerate(st.session_state.script):
            audio = generate_audio(
                line['text'],
                st.session_state.available_voices[st.session_state.config['podcasters'][line['speaker']]]['voice_id'],
                st.session_state.config['voice_settings']
            )
            st.session_state.audio_segments.append((f"Line {i+1}", audio))
        
        st.success("Audio generated successfully!")
    
    # Display generated audio segments
    for i, (label, audio) in enumerate(st.session_state.audio_segments):
        st.subheader(label)
        st.audio(audio.export(format="mp3").read(), format="audio/mp3")
        
        if label == "Intro":
            new_text = st.text_area(f"Edit {label} text:", st.session_state.config['intro_text'], key=f"edit_{i}")
        else:
            line_index = int(label.split()[1]) - 1
            new_text = st.text_area(f"Edit {label} text:", st.session_state.script[line_index]['text'], key=f"edit_{i}")
        
        if st.button(f"Regenerate {label}", key=f"regen_{i}"):
            if label == "Intro":
                new_audio = generate_audio(
                    new_text,
                    st.session_state.available_voices[st.session_state.config['intro_voice']]['voice_id'],
                    st.session_state.config['voice_settings']
                )
                st.session_state.config['intro_text'] = new_text
            else:
                line_index = int(label.split()[1]) - 1
                new_audio = generate_audio(
                    new_text,
                    st.session_state.available_voices[st.session_state.config['podcasters'][st.session_state.script[line_index]['speaker']]]['voice_id'],
                    st.session_state.config['voice_settings']
                )
                st.session_state.script[line_index]['text'] = new_text
            st.session_state.audio_segments[i] = (label, new_audio)
            st.rerun()
    
    if st.button("Proceed to Finalization"):
        st.session_state.current_step = 5

# Step 5: Finalize
def step_5():
    st.header("Step 5: Finalize")
    if st.button("Finalize Podcast"):
        full_audio = AudioSegment.empty()
        
        # Add intro music if provided
        if st.session_state.config['intro_music']:
            intro_music = AudioSegment.from_mp3(st.session_state.config['intro_music'])
            full_audio += intro_music
        
        # Combine all audio segments
        for _, audio in st.session_state.audio_segments:
            full_audio += audio
            full_audio += AudioSegment.silent(duration=500)  # Add a short pause between segments
        
        # Export the full podcast
        output_path = "generated_podcast.mp3"
        full_audio.export(output_path, format="mp3")
        st.success("Podcast finalized successfully!")
        st.session_state.current_step = 6

# Step 6: Play and Download
def step_6():
    st.header("Step 6: Play and Download")
    output_path = "generated_podcast.mp3"
    st.audio(output_path, format="audio/mp3")
    with open(output_path, "rb") as file:
        st.download_button(
            label="Download Podcast",
            data=file,
            file_name="generated_podcast.mp3",
            mime="audio/mp3"
        )

# Main Streamlit app
def main():
    st.set_page_config(layout="wide", page_title="Podcast Generator")
    st.title("Podcast Generator")
    
    init_session_state()
    
    # Navigation
    st.sidebar.title("Navigation")
    step_buttons = [
        st.sidebar.button(f"Step {i}: {step}") for i, step in enumerate([
            "API Key Input", "Input Script", "Edit Script", "Configuration", 
            "Generate Audio", "Finalize", "Play and Download"
        ])
    ]
    
    if any(step_buttons):
        st.session_state.current_step = step_buttons.index(True)
    
    # Display current step
    if st.session_state.current_step == 0:
        step_0()
    elif st.session_state.current_step == 1:
        step_1()
    elif st.session_state.current_step == 2:
        step_2()
    elif st.session_state.current_step == 3:
        step_3()
    elif st.session_state.current_step == 4:
        step_4()
    elif st.session_state.current_step == 5:
        step_5()
    elif st.session_state.current_step == 6:
        step_6()

if __name__ == "__main__":
    main()
