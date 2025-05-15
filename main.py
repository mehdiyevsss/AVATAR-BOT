import streamlit as st
import os
from utilss import speech_to_text, text_to_speech, autoplay_audio, get_rag_response
from audio_recorder_streamlit import audio_recorder
from streamlit_float import float_init
from streamlit.components.v1 import html

st.set_page_config(page_title="Voice Avatar Chatbot", layout="wide")
float_init()

st.title("🗣️ Voice Avatar Chatbot with RAG")

# Layout: Avatar left, chat right
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### Your Assistant")
    html("""
<div id="avatar-container">
  <model-viewer id="avatar" src="https://raw.githubusercontent.com/mehdiyevsss/glb-assets/main/brunette.glb" 
    autoplay camera-controls interaction-prompt="none"
    style="width: 100%; height: 400px;" background-color="#111111">
  </model-viewer>
</div>

<script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
""", height=420)


with col2:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you?"}]

    audio_bytes = audio_recorder()

    st.markdown("""
        <style>
        .chat-box {
            max-height: 450px;
            overflow-y: auto;
            padding-right: 10px;
            border: 1px solid #444;
            border-radius: 10px;
            background-color: #0e1117;
        }
        </style>
        <div class="chat-box">
    """, unsafe_allow_html=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    st.markdown("</div>", unsafe_allow_html=True)

    if audio_bytes:
        with st.spinner("Transcribing..."):
            with open("temp_input.mp3", "wb") as f:
                f.write(audio_bytes)
            transcript = speech_to_text("temp_input.mp3")

        if transcript:
            st.session_state.messages.append({"role": "user", "content": transcript})
            with st.chat_message("user"):
                st.write(transcript)

    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                user_message = st.session_state.messages[-1]["content"]
                response = get_rag_response(user_message)
                audio_file = text_to_speech(response)
                autoplay_audio(audio_file)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Avatar fake lip sync trigger
                st.markdown(f"""
                <script>
                  window.parent.postMessage({{
                    type: 'SPEAK',
                    duration: 2000
                  }}, '*');
                </script>
                """, unsafe_allow_html=True)

                os.remove(audio_file)
