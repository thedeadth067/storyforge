STORYFORGE UPDATED BUILD

1. Install Python 3.11 or newer from https://www.python.org/downloads/ . During installation, tick "Add Python to PATH".
2. Extract this folder to C:\Users\DELL\Desktop\storyforge (or another folder).
3. Open Command Prompt in that folder and run:
   python -m pip install -r requirements.txt
4. Create a Gemini API key at https://aistudio.google.com/ .
5. Create a folder named .streamlit next to app.py.
6. Inside .streamlit, create secrets.toml with:
   [gemini]
   api_key = "PASTE_YOUR_GEMINI_API_KEY_HERE"
   Never share this key or commit it to a public repository.
7. Double-click run.bat, or run: python -m streamlit run app.py
8. Open the local URL printed in the terminal (usually http://localhost:8501).

Backgrounds:
- Open Settings > Background picture or video.
- Select Color, Picture, or Video.
- Choose Whole app or Per section. For Per section, select the section and upload its background.
- Supported images: PNG, JPG, JPEG, WebP. Supported videos: MP4, WebM, MOV. File size limit: 100 MB.
- Uploaded assets and preferences are stored under data/.

Sound effects:
- In Create, tick "Include occasional sound-effect cues" before generating a story.
- Or edit a saved story so it contains supported cues in square brackets, e.g. [glass breaks], [thunder], [door slams], [door creaks], [footsteps], [knock], [wind], [rain], [heartbeat], [crowd gasps].
- Open Digital Reader and press Play narration. Sound effects are synthesized in the browser and occur when narration reaches the cue.
- Browser audio requires the user to press Play. Use Chrome or Edge for best support.

Notes:
- This build uses local SQLite storage and a local guest session. It does not configure Google OAuth sign-in.
- Background videos are muted and looped; video backgrounds can use significant memory. Prefer short, compressed clips.
- This is a Streamlit app running locally in your browser, not a fully standalone EXE. The included run.bat is the simplest launcher.

Optional Google sign-in:
- In .streamlit/secrets.toml, you may also configure the Streamlit auth section with your Google OAuth client credentials. See https://docs.streamlit.io/develop/concepts/connections/authentication .
- If not configured, use Continue as Guest. The app still works with a Gemini API key for AI generation.
