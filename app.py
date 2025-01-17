import streamlit as st
import json
import io
from pydub import AudioSegment
from elevenlabs import ElevenLabs, VoiceSettings
import requests
import os
import base64

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
            'outro_text': '',
            'outro_voice': '',
            'intro_music': None,
            'podcasters': {},
            'voice_settings': {
                'stability': 0.5,
                'similarity_boost': 0.8,
                'style': 0.1,
            }
        }
    if 'audio_segments' not in st.session_state:
        st.session_state.audio_segments = []
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
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
        voice_settings=settings,
        model_id="eleven_multilingual_v2",
    )
    audio_data = b''.join(chunk for chunk in audio_stream)
    return AudioSegment.from_mp3(io.BytesIO(audio_data))

# Function to display masked API key
def display_masked_api_key():
    if st.session_state.api_key:
        masked_key = st.session_state.api_key[:4] + "*" * (len(st.session_state.api_key) - 8) + st.session_state.api_key[-4:]
        st.sidebar.text(f"API Key: {masked_key}")

# Step 0: Instructions
def step_0_instructions():
    st.header("Welcome to the Podcast Generator")
    st.write("""
    This application helps you create a podcast using AI-generated voices. Follow these steps to use the app:

    1. **Get an ElevenLabs API Key:**
       - Go to [ElevenLabs](https://elevenlabs.io/) and sign up for an account.
       - Navigate to your profile settings to find your API key.

    2. **Generate a Transcript:**
       - Use an AI assistant like ChatGPT, Claude, or Gemini to create your podcast script.
       - Use the following prompt to generate your script:
    """)
    
    st.code("""
    1. Extract key points, definitions, and interesting facts from the given financial press release.
    2. Transform the information into a lively, engaging, and informative podcast dialogue in the style of NPR.
    3. Format the script as a JSON file with alternating speakers (Alex and Sarah).
    4. Structure each dialogue entry as:
    {
    "speaker": "Name",
    "text": "Dialog"
    }
    5. Make the podcast sound like it's from Nordea Bank, with the speakers being part of Nordea's investor relations team.
    6. Define all terms used carefully for a broad audience of listeners.
    7. Add human touches to the dialogue, such as casual banter and pauses.
    8. Use ellipsis (...) to indicate pauses instead of XML-style break tags.
    9. Ensure the content is informative while remaining accessible to a general audience.
    10. Cover key financial metrics, explain their significance, and provide simple analogies to help listeners understand complex concepts.
    11. Maintain a balance between presenting positive results and acknowledging the need for cautious interpretation of financial data.
    """, language="markdown")

    st.write("""
    3. **Prepare Your JSON:**
       - The AI will generate a JSON-formatted script. It should look like this:
    """)

    st.code("""
    [
        {"speaker": "Alex", "text": "Welcome to Nordea's financial update..."},
        {"speaker": "Sarah", "text": "Thanks, Alex. Let's dive into the latest numbers..."},
        ...
    ]
    """, language="json")

    st.write("""
    4. **Navigate Through the App:**
       - Use the navigation panel on the left to move through each step of the podcast creation process.
       - Start by entering your ElevenLabs API key, then proceed through script input, editing, configuration, audio generation, and finalization.

    Click the 'Proceed to API Key Input' button below when you're ready to start creating your podcast!
    """)

    if st.button("Proceed to API Key Input"):
        st.session_state.current_step = 1

# Step 1: API Key Input
def step_1():
    st.header("Step 1: Enter Your ElevenLabs API Key")
    api_key = st.text_input("API Key", type="password")
    if st.button("Submit API Key"):
        st.session_state.api_key = api_key
        st.session_state.available_voices = get_available_voices()
        st.success("API Key submitted successfully!")
        st.session_state.current_step = 2

# Step 2: JSON Input
def step_2():
    st.header("Step 2: Input Script")
    json_input = st.text_area("Paste your JSON script here (format: [{'speaker': 'name', 'text': 'content'}, ...]):", height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Load Script"):
            try:
                script_data = json.loads(json_input)
                if isinstance(script_data, list) and all(isinstance(item, dict) and 'speaker' in item and 'text' in item for item in script_data):
                    st.session_state.script = script_data
                    st.success("Script loaded successfully!")
                    st.session_state.current_step = 3
                else:
                    st.error("Invalid script format. Please ensure your JSON is a list of objects with 'speaker' and 'text' keys.")
            except json.JSONDecodeError:
                st.error("Invalid JSON. Please check your input.")
    
    with col2:
        if st.button("Export Script"):
            script_json = json.dumps(st.session_state.script, indent=2)
            b64 = base64.b64encode(script_json.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="podcast_script.json">Download JSON</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Import Script from JSON", type="json")
    if uploaded_file is not None:
        try:
            imported_script = json.load(uploaded_file)
            if isinstance(imported_script, list) and all(isinstance(item, dict) and 'speaker' in item and 'text' in item for item in imported_script):
                st.session_state.script = imported_script
                st.success("Script imported successfully!")
                st.session_state.current_step = 3
            else:
                st.error("Invalid script format in the imported file.")
        except json.JSONDecodeError:
            st.error("Invalid JSON in the imported file.")

# Step 3: Display and Edit Script
def step_3():
    st.header("Step 3: Edit Script")
    for i, line in enumerate(st.session_state.script):
        with st.expander(f"Dialog {i+1}", expanded=True):
            st.session_state.script[i]['speaker'] = st.text_input("Speaker", line['speaker'], key=f"speaker_{i}")
            st.session_state.script[i]['text'] = st.text_area("Dialog", line['text'], key=f"line_{i}", height=100)
    if st.button("Proceed to Configuration"):
        st.session_state.current_step = 4

# Step 4: Configuration
def step_4():
    st.header("Step 4: Configuration")
    
    st.subheader("Intro Configuration")
    st.session_state.config['intro_text'] = st.text_area("Intro Text:", st.session_state.config['intro_text'])
    st.session_state.config['intro_voice'] = st.selectbox("Intro Voice:", list(st.session_state.available_voices.keys()), key="intro_voice")
    
    if st.button("Play Intro Voice Sample", key="intro_sample"):
        voice_data = st.session_state.available_voices[st.session_state.config['intro_voice']]
        if voice_data['samples']:
            sample = get_voice_sample(voice_data['voice_id'], voice_data['samples'][0]['sample_id'])
            if sample:
                st.audio(sample, format="audio/mp3")
    
    st.subheader("Outro Configuration")
    st.session_state.config['outro_text'] = st.text_area("Outro Text:", st.session_state.config['outro_text'])
    st.session_state.config['outro_voice'] = st.selectbox("Outro Voice:", list(st.session_state.available_voices.keys()), key="outro_voice")
    
    if st.button("Play Outro Voice Sample", key="outro_sample"):
        voice_data = st.session_state.available_voices[st.session_state.config['outro_voice']]
        if voice_data['samples']:
            sample = get_voice_sample(voice_data['voice_id'], voice_data['samples'][0]['sample_id'])
            if sample:
                st.audio(sample, format="audio/mp3")
    
    st.markdown("You can check the voice samples on [ElevenLabs](https://elevenlabs.io/).")
    
    st.subheader("Podcasters")
    podcasters = set(line['speaker'] for line in st.session_state.script)
    for podcaster in podcasters:
        st.session_state.config['podcasters'][podcaster] = st.selectbox(f"Voice for {podcaster}:", list(st.session_state.available_voices.keys()), key=f"voice_{podcaster}")
        if st.button(f"Play {podcaster} Voice Sample", key=f"sample_{podcaster}"):
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
    
    st.markdown("### Upload Intro Music")
    st.markdown("You can download royalty-free intro music from the following sites:")
    st.markdown("- [Chosic](https://www.chosic.com/free-music/intro/)")
    st.markdown("- [Pixabay](https://pixabay.com/music/search/intro/)")
    
    if st.button("Proceed to Audio Generation"):
        st.session_state.current_step = 5

# Step 5: Generate Audio
def step_5():
    st.header("Step 5: Generate Audio")
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
            speaker = line['speaker']
            voice_name = st.session_state.config['podcasters'][speaker]
            audio = generate_audio(
                line['text'],
                st.session_state.available_voices[voice_name]['voice_id'],
                st.session_state.config['voice_settings']
            )
            st.session_state.audio_segments.append((f"Line {i+1}", audio))
        
# Generate outro audio
        if st.session_state.config['outro_text']:
            outro_audio = generate_audio(
                st.session_state.config['outro_text'],
                st.session_state.available_voices[st.session_state.config['outro_voice']]['voice_id'],
                st.session_state.config['voice_settings']
            )
            st.session_state.audio_segments.append(("Outro", outro_audio))
        
        st.success("Audio generated successfully!")
    
    # Display generated audio segments
    for i, (label, audio) in enumerate(st.session_state.audio_segments):
        st.subheader(label)
        st.audio(audio.export(format="mp3").read(), format="audio/mp3")
        
        if label == "Intro":
            new_text = st.text_area(f"Edit {label} text:", st.session_state.config['intro_text'], key=f"edit_{i}")
        elif label == "Outro":
            new_text = st.text_area(f"Edit {label} text:", st.session_state.config['outro_text'], key=f"edit_{i}")
        else:
            line_index = int(label.split()[1]) - 1
            speaker = st.session_state.script[line_index]['speaker']
            new_text = st.text_area(f"Edit {label} text:", st.session_state.script[line_index]['text'], key=f"edit_{i}")
        
        if st.button(f"Regenerate {label}", key=f"regen_{i}"):
            if label == "Intro":
                new_audio = generate_audio(
                    new_text,
                    st.session_state.available_voices[st.session_state.config['intro_voice']]['voice_id'],
                    st.session_state.config['voice_settings']
                )
                st.session_state.config['intro_text'] = new_text
            elif label == "Outro":
                new_audio = generate_audio(
                    new_text,
                    st.session_state.available_voices[st.session_state.config['outro_voice']]['voice_id'],
                    st.session_state.config['voice_settings']
                )
                st.session_state.config['outro_text'] = new_text
            else:
                line_index = int(label.split()[1]) - 1
                speaker = st.session_state.script[line_index]['speaker']
                voice_name = st.session_state.config['podcasters'][speaker]
                new_audio = generate_audio(
                    new_text,
                    st.session_state.available_voices[voice_name]['voice_id'],
                    st.session_state.config['voice_settings']
                )
                st.session_state.script[line_index]['text'] = new_text
            st.session_state.audio_segments[i] = (label, new_audio)
            st.rerun()
    
    if st.button("Proceed to Finalization"):
        st.session_state.current_step = 6

# Step 6: Finalize
def step_6():
    st.header("Step 6: Finalize")
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
        st.session_state.current_step = 7

# Step 7: Play and Download
def step_7():
    st.header("Step 7: Play and Download")
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
    display_masked_api_key()
    
    # Navigation
    st.sidebar.title("Navigation")
    step_buttons = [
        st.sidebar.button(f"Step {i}: {step}") for i, step in enumerate([
            "Instructions", "API Key Input", "Input Script", "Edit Script", "Configuration", 
            "Generate Audio", "Finalize", "Play and Download"
        ])
    ]
    
    if any(step_buttons):
        st.session_state.current_step = step_buttons.index(True)
    
    # Display current step
    if st.session_state.current_step == 0:
        step_0_instructions()
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
    elif st.session_state.current_step == 7:
        step_7()

if __name__ == "__main__":
    main()