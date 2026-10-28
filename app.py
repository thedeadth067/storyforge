
from __future__ import annotations

import base64
import html
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    from google import genai
except ImportError:
    genai = None

APP_NAME = "StoryForge"
MODEL_NAME = "gemini-flash-latest"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
BACKGROUND_DIR = DATA_DIR / "backgrounds"
DB_PATH = DATA_DIR / "storyforge.db"
PREFS_PATH = DATA_DIR / "preferences.json"

for folder in (DATA_DIR, UPLOAD_DIR, BACKGROUND_DIR):
    folder.mkdir(parents=True, exist_ok=True)

SECTIONS = [
    "Home", "Create", "My Library", "Digital Reader",
    "Story Lab", "Character Studio", "Picture Stories",
    "Export Studio", "Settings", "About"
]

DEFAULT_COLORS = {
    "Home": "#302052",
    "Create": "#152E50",
    "My Library": "#49351D",
    "Digital Reader": "#332820",
    "Story Lab": "#202C48",
    "Character Studio": "#30304C",
    "Picture Stories": "#24483D",
    "Export Studio": "#493044",
    "Settings": "#252C38",
    "About": "#153C38",
}

DEFAULT_PREFS = {
    "mode": "Dark",
    "section_colors": DEFAULT_COLORS.copy(),
    "background_path": "",
    "background_mode": "Color",
    "font_size": 19,
    "narration_speed": 1.0,
    "sound_effects": True,
    "sound_volume": 0.55,
}


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS creations_v2 (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            profile TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    return conn


def current_user():
    if "guest_id" not in st.session_state:
        st.session_state.guest_id = "guest:" + str(uuid.uuid4())
    return st.session_state.guest_id


def save_creation(title, kind, content):
    with db_connect() as conn:
        conn.execute(
            """INSERT INTO creations_v2
            (id,user_id,title,kind,content,created_at)
            VALUES (?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()), current_user(),
                title.strip() or "Untitled",
                kind, content,
                datetime.now().isoformat(timespec="seconds")
            )
        )


def get_creations():
    with db_connect() as conn:
        return conn.execute(
            """SELECT * FROM creations_v2
            WHERE user_id=? ORDER BY created_at DESC""",
            (current_user(),)
        ).fetchall()


def get_creation(item_id):
    with db_connect() as conn:
        return conn.execute(
            "SELECT * FROM creations_v2 WHERE id=? AND user_id=?",
            (item_id, current_user())
        ).fetchone()


def update_creation(item_id, title, content):
    with db_connect() as conn:
        conn.execute(
            """UPDATE creations_v2 SET title=?,content=?
            WHERE id=? AND user_id=?""",
            (title.strip() or "Untitled", content, item_id, current_user())
        )


def delete_creation(item_id):
    with db_connect() as conn:
        conn.execute(
            "DELETE FROM creations_v2 WHERE id=? AND user_id=?",
            (item_id, current_user())
        )


def save_character(name, profile, character_id=None):
    with db_connect() as conn:
        if character_id:
            conn.execute(
                """UPDATE characters SET name=?,profile=?
                WHERE id=? AND user_id=?""",
                (name, profile, character_id, current_user())
            )
        else:
            conn.execute(
                """INSERT INTO characters
                (id,user_id,name,profile,created_at)
                VALUES (?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), current_user(), name,
                    profile, datetime.now().isoformat(timespec="seconds")
                )
            )


def get_characters():
    with db_connect() as conn:
        return conn.execute(
            "SELECT * FROM characters WHERE user_id=? ORDER BY name",
            (current_user(),)
        ).fetchall()


def delete_character(character_id):
    with db_connect() as conn:
        conn.execute(
            "DELETE FROM characters WHERE id=? AND user_id=?",
            (character_id, current_user())
        )


# ---------------------------------------------------------
# PREFERENCES AND APPEARANCE
# ---------------------------------------------------------

def load_prefs():
    if "prefs" not in st.session_state:
        prefs = json.loads(json.dumps(DEFAULT_PREFS))
        try:
            if PREFS_PATH.exists():
                saved = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
                prefs.update(saved)
                prefs["section_colors"] = {
                    **DEFAULT_COLORS,
                    **saved.get("section_colors", {})
                }
        except (OSError, ValueError):
            pass
        st.session_state.prefs = prefs
    return st.session_state.prefs


def save_prefs():
    PREFS_PATH.write_text(
        json.dumps(st.session_state.prefs, indent=2),
        encoding="utf-8"
    )


def apply_appearance(section):
    prefs = load_prefs()
    color = prefs["section_colors"].get(section, "#202030")
    text_color = "#F5F5F7" if prefs["mode"] == "Dark" else "#211F2A"

    bg_path = prefs.get("background_path", "")
    background_css = ""

    if bg_path and Path(bg_path).is_file():
        suffix = Path(bg_path).suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg", ".webp"):
            raw = base64.b64encode(Path(bg_path).read_bytes()).decode()
            mime = "image/png" if suffix == ".png" else "image/jpeg"
            background_css = (
                f"background-image:linear-gradient("
                f"rgba(10,10,20,.76),rgba(10,10,20,.76)),"
                f"url('data:{mime};base64,{raw}');"
                "background-size:cover;background-position:center;"
                "background-attachment:fixed;"
            )

    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-color:{color}!important;
        {background_css}
        color:{text_color};
    }}
    [data-testid="stSidebar"] {{
        background-color:color-mix(in srgb,{color} 82%,black 18%);
    }}
    [data-testid="stHeader"] {{background:transparent;}}
    .stButton>button {{
        border-radius:10px;
        transition:transform .15s ease;
    }}
    .stButton>button:hover {{transform:translateY(-1px);}}
    .sf-title {{font-size:2.4rem;font-weight:800;}}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# GEMINI
# ---------------------------------------------------------

def get_api_key():
    try:
        key = st.secrets.get("gemini", {}).get("api_key", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip()


def generate_ai(prompt):
    key = get_api_key()
    if not key:
        raise RuntimeError(
            "Gemini API key missing. Add it to .streamlit/secrets.toml."
        )
    if genai is None:
        raise RuntimeError(
            "Install the Google Gen AI library: "
            "python -m pip install google-genai"
        )

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={"temperature": 0.85, "max_output_tokens": 8192}
    )
    result = getattr(response, "text", "")
    if not result or not result.strip():
        raise RuntimeError("The AI returned an empty response.")
    return result.strip()


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

def show_home():
    rows = get_creations()
    characters = get_characters()

    st.markdown('<div class="sf-title">Welcome to StoryForge ✨</div>',
                unsafe_allow_html=True)
    st.write("Your personal storytelling and illustrated-book studio.")

    a, b, c = st.columns(3)
    a.metric("Saved creations", len(rows))
    b.metric("Characters", len(characters))
    c.metric("Creative tools", 4)

    st.subheader("Your creative studio")
    tools = [
        ("Story Lab", "Plan plots, twists, and branching adventures."),
        ("Character Studio", "Design and save character profiles."),
        ("Picture Stories", "Build illustrated stories with captions."),
        ("Export Studio", "Download your work in useful formats."),
    ]

    cols = st.columns(2)
    for i, (name, description) in enumerate(tools):
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(name)
                st.write(description)
                if st.button("Open " + name, key="home_" + name):
                    st.session_state.page = name
                    st.rerun()

    st.subheader("Recent creations")
    for row in rows[:5]:
        with st.container(border=True):
            st.markdown("**" + html.escape(row["title"]) + "**")
            st.caption(row["kind"].title() + " · " + row["created_at"])
            st.write(row["content"][:220])


# ---------------------------------------------------------
# CREATE: STORIES AND POEMS
# ---------------------------------------------------------

def show_create():
    st.title("Create a Story or Poem")

    kind = st.radio("Creation type", ["Story", "Poem"], horizontal=True)
    title = st.text_input("Title")
    idea = st.text_area("Your idea", height=130)

    c1, c2, c3 = st.columns(3)
    genre = c1.selectbox(
        "Genre", ["Fantasy", "Mystery", "Adventure", "Science fiction",
                  "Comedy", "Horror", "Historical", "Any"]
    )
    mood = c2.selectbox(
        "Mood", ["Magical", "Suspenseful", "Hopeful", "Cozy",
                 "Funny", "Emotional", "Epic"]
    )
    ending = c3.selectbox(
        "Ending", ["Satisfying", "Happy", "Bittersweet", "Twist",
                   "Open-ended"]
    )

    if kind == "Story":
        chapters = st.slider("Chapters", 1, 10, 3)
        length = st.selectbox("Length", ["Short", "Medium", "Long"])
    else:
        chapters = 0
        length = ""
        st.slider("Stanzas", 2, 12, 4, key="poem_stanzas")

    cues = st.checkbox("Include sound-effect cues for narration")

    if st.button("Generate with AI", type="primary"):
        if not idea.strip():
            st.warning("Please enter an idea first.")
        else:
            if kind == "Story":
                prompt = (
                    f"Write an original {length.lower()} {genre} story in "
                    f"{chapters} labeled chapters. Mood: {mood}. Ending: "
                    f"{ending}. Idea: {idea}. Title: {title or 'Untitled'}."
                )
            else:
                prompt = (
                    f"Write an original poem with {st.session_state.poem_stanzas} "
                    f"stanzas. Theme: {genre}. Mood: {mood}. Idea: {idea}. "
                    f"Title: {title or 'Untitled'}."
                )

            if cues:
                prompt += (
                    " Add occasional cues in brackets, such as [thunder], "
                    "[rain], [glass breaks], [door slams], [footsteps], "
                    "or [knock]."
                )

            with st.spinner("Creating your draft..."):
                try:
                    st.session_state.draft = generate_ai(prompt)
                    st.session_state.draft_title = title or "Untitled"
                    st.session_state.draft_kind = kind.lower()
                except Exception as exc:
                    st.error(str(exc))

    if "draft" in st.session_state:
        st.subheader("Edit your draft")
        st.session_state.draft_title = st.text_input(
            "Draft title", st.session_state.get("draft_title", "Untitled")
        )
        st.session_state.draft = st.text_area(
            "Draft text", st.session_state.draft, height=350
        )
        if st.button("Save draft to My Library", type="primary"):
            save_creation(
                st.session_state.draft_title,
                st.session_state.get("draft_kind", "story"),
                st.session_state.draft
            )
            st.success("Saved to your library.")


# ---------------------------------------------------------
# STORY LAB
# ---------------------------------------------------------

def show_story_lab():
    st.title("Story Lab 🧪")
    st.write("Plan a story or build an adventure with reader choices.")

    mode = st.radio(
        "Project type",
        ["Plot Planner", "Choose-Your-Own-Adventure"],
        horizontal=True
    )
    title = st.text_input("Project title", key="lab_title")
    premise = st.text_area("Story idea or premise", key="lab_premise")

    a, b = st.columns(2)
    genre = a.selectbox(
        "Genre", ["Fantasy", "Mystery", "Adventure", "Science fiction",
                  "Comedy", "Drama", "Horror"]
    )
    audience = b.selectbox(
        "Reading level", ["Children", "Young readers", "General audience"]
    )

    if mode == "Plot Planner":
        count = st.slider("Number of chapters", 3, 20, 8)
        extras = st.text_area(
            "Characters, themes, or twists to include",
            placeholder="A secret map, a rival, an unexpected discovery..."
        )
    else:
        count = st.slider("Number of story stages", 4, 12, 6)
        extras = st.text_area(
            "Choices or endings you want",
            placeholder="Include at least two endings and meaningful choices."
        )

    if st.button("Generate story plan", type="primary"):
        if not premise.strip():
            st.warning("Enter a premise first.")
        else:
            if mode == "Plot Planner":
                prompt = (
                    f"Create a detailed original {genre} story outline for "
                    f"{audience}. Title: {title}. Premise: {premise}. "
                    f"Organize it into {count} chapters. For each chapter, "
                    "give its purpose, key events, conflict, and hook. "
                    f"Additional details: {extras}"
                )
            else:
                prompt = (
                    f"Create an original choose-your-own-adventure story "
                    f"in the {genre} genre for {audience}. Title: {title}. "
                    f"Premise: {premise}. Use {count} stages. At each stage, "
                    "provide meaningful choices and show where each choice "
                    "leads. Include multiple endings and avoid broken links. "
                    f"Additional requirements: {extras}"
                )

            with st.spinner("Planning your story..."):
                try:
                    st.session_state.lab_result = generate_ai(prompt)
                except Exception as exc:
                    st.error(str(exc))

    if st.session_state.get("lab_result"):
        result = st.text_area(
            "Edit your plan", st.session_state.lab_result, height=400
        )
        if st.button("Save plan to library"):
            save_creation(title or "Story Lab Plan", "story plan", result)
            st.success("Plan saved.")


# ---------------------------------------------------------
# CHARACTER STUDIO
# ---------------------------------------------------------

def show_character_studio():
    st.title("Character Studio 🎭")
    st.write("Create character profiles that you can reuse in your stories.")

    with st.form("character_form"):
        name = st.text_input("Character name")
        role = st.selectbox(
            "Role", ["Hero", "Friend", "Rival", "Mentor", "Villain",
                     "Supporting character", "Other"]
        )
        appearance = st.text_area("Appearance")
        personality = st.text_area("Personality and habits")
        goals = st.text_area("Goals, strengths, and weaknesses")
        backstory = st.text_area("Backstory")
        relationships = st.text_area("Relationships with other characters")
        generate_profile = st.form_submit_button("Improve with AI")

    if generate_profile:
        if not name.strip():
            st.warning("Give your character a name.")
        else:
            prompt = (
                f"Create a clear character profile for an original fictional "
                f"character named {name}. Role: {role}. Appearance: {appearance}. "
                f"Personality: {personality}. Goals, strengths and weaknesses: "
                f"{goals}. Backstory: {backstory}. Relationships: {relationships}. "
                "Preserve the user's ideas, organize the profile, and suggest "
                "one character arc."
            )
            with st.spinner("Developing character..."):
                try:
                    st.session_state.character_profile = generate_ai(prompt)
                    st.session_state.character_name = name
                except Exception as exc:
                    st.error(str(exc))

    if st.session_state.get("character_profile"):
        st.session_state.character_profile = st.text_area(
            "Profile", st.session_state.character_profile, height=300
        )
        if st.button("Save character", type="primary"):
            save_character(
                st.session_state.get("character_name", "Unnamed"),
                st.session_state.character_profile
            )
            st.success("Character saved.")

    st.subheader("Saved characters")
    for char in get_characters():
        with st.expander(char["name"]):
            st.write(char["profile"])
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "Download profile",
                    char["profile"],
                    file_name=re.sub(
                        r"[^A-Za-z0-9_-]", "_", char["name"]
                    ) + ".txt",
                    key="char_dl_" + char["id"]
                )
            with c2:
                if st.button("Delete", key="char_del_" + char["id"]):
                    delete_character(char["id"])
                    st.rerun()


# ---------------------------------------------------------
# PICTURE STORIES
# ---------------------------------------------------------

def show_picture_stories():
    st.title("Picture Stories 🖼️")
    st.write(
        "Create a picture book with captions. You can upload your own "
        "illustrations; generating new images requires a separate image "
        "generation service."
    )

    title = st.text_input("Picture book title", key="picture_title")
    idea = st.text_area(
        "What happens in your picture story?",
        placeholder="A small fox discovers a glowing garden...",
        key="picture_idea"
    )
    page_count = st.slider("Number of pages", 2, 12, 5)
    style = st.selectbox(
        "Illustration style",
        ["Watercolor", "Cartoon", "Storybook", "Paper collage",
         "Pixel art", "Realistic", "Let me choose later"]
    )

    if st.button("Write picture-book scenes", type="primary"):
        if not idea.strip():
            st.warning("Enter a story idea first.")
        else:
            prompt = (
                f"Create an original picture book titled {title or 'Untitled'}. "
                f"Premise: {idea}. Illustration direction: {style}. "
                f"Make exactly {page_count} pages. For each page, provide "
                "a short scene description, a concise caption suitable for "
                "a picture book, and an illustration prompt. Keep characters "
                "visually consistent across pages. Clearly label each page."
            )
            with st.spinner("Writing scenes..."):
                try:
                    st.session_state.picture_scenes = generate_ai(prompt)
                except Exception as exc:
                    st.error(str(exc))

    if st.session_state.get("picture_scenes"):
        scenes = st.text_area(
            "Edit scenes and captions",
            st.session_state.picture_scenes,
            height=350
        )

        st.subheader("Add your illustrations")
        uploaded_images = st.file_uploader(
            "Upload pictures in page order",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="picture_uploads"
        )

        if uploaded_images:
            for i, img in enumerate(uploaded_images):
                st.image(img, caption=f"Page illustration {i + 1}",
                         use_container_width=True)

        if st.button("Save picture story", type="primary"):
            saved_images = []
            for img in uploaded_images or []:
                ext = Path(img.name).suffix.lower()
                safe_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
                safe_path.write_bytes(img.getvalue())
                saved_images.append(str(safe_path))

            project = {
                "scenes": scenes,
                "images": saved_images,
                "style": style
            }
            save_creation(
                title or "Picture Story",
                "picture story",
                json.dumps(project, ensure_ascii=False, indent=2)
            )
            st.success("Picture story saved to My Library.")


# ---------------------------------------------------------
# LIBRARY
# ---------------------------------------------------------

def show_library():
    st.title("My Library")
    rows = get_creations()
    if not rows:
        st.info("Your library is empty. Create something first.")
        return

    query = st.text_input("Search titles and content")
    for row in rows:
        if query.lower() not in (
            row["title"] + " " + row["content"]
        ).lower():
            continue

        with st.container(border=True):
            st.subheader(row["title"])
            st.caption(row["kind"].title() + " · " + row["created_at"])
            preview = row["content"]
            st.write(preview[:300] + ("…" if len(preview) > 300 else ""))

            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button(
                    "Download TXT",
                    row["content"],
                    file_name=re.sub(
                        r"[^A-Za-z0-9_-]", "_", row["title"]
                    ) + ".txt",
                    key="lib_dl_" + row["id"]
                )
            with c2:
                if st.button("Read", key="lib_read_" + row["id"]):
                    st.session_state.reader_id = row["id"]
                    st.session_state.page = "Digital Reader"
                    st.rerun()
            with c3:
                if st.button("Delete", key="lib_del_" + row["id"]):
                    delete_creation(row["id"])
                    st.rerun()

            with st.expander("Edit"):
                new_title = st.text_input(
                    "Title", row["title"], key="edit_title_" + row["id"]
                )
                new_content = st.text_area(
                    "Content", row["content"],
                    height=200, key="edit_content_" + row["id"]
                )
                if st.button("Save edits", key="edit_save_" + row["id"]):
                    update_creation(row["id"], new_title, new_content)
                    st.success("Updated.")
                    st.rerun()


# ---------------------------------------------------------
# DIGITAL READER
# ---------------------------------------------------------

def reader_html(title, content, prefs):
    data = json.dumps(content)
    title_safe = html.escape(title)
    font_size = int(prefs.get("font_size", 19))
    speed = float(prefs.get("narration_speed", 1.0))
    effects = "true" if prefs.get("sound_effects", True) else "false"
    volume = float(prefs.get("sound_volume", 0.55))

    return f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">
    <style>
      body {{font-family:Georgia,serif;background:#171725;color:#f5f1e8;
             padding:18px;}}
      .page {{max-width:850px;margin:auto;background:#242438;padding:24px;
              border-radius:16px;}}
      #story {{font-size:{font_size}px;line-height:1.7;white-space:pre-wrap;}}
      button {{padding:9px 14px;margin:4px;border-radius:8px;cursor:pointer;}}
      .cue {{color:#d9b6ff;font-size:.85em;font-family:Arial,sans-serif;}}
    </style></head>
    <body><div class="page">
    <h2>{title_safe}</h2>
    <button id="play">▶ Play</button>
    <button id="pause">Ⅱ Pause</button>
    <button id="stop">■ Stop</button>
    <label>Speed <select id="speed">
      <option value="0.75">0.75x</option>
      <option value="1">1x</option>
      <option value="1.25">1.25x</option>
      <option value="1.5">1.5x</option>
    </select></label>
    <label><input id="fx" type="checkbox" {"checked" if effects == "true" else ""}>
      Sound cues</label>
    <label>Volume <input id="vol" type="range" min="0" max="1"
      step="0.05" value="{volume}"></label>
    <div id="story"></div>
    <script>
      const raw={data};
      const el=document.getElementById('story');
      const supported=['thunder','rain','wind','glass breaks','door slams',
                       'door creaks','footsteps','knock','heartbeat'];
      const aliases={{'glass breaking':'glass breaks',
                      'glass was breaked':'glass breaks'}};
      const regex=/\\[([^\\]]+)\\]/g;
      let segments=[],index=0,stopped=true,paused=false;

      function esc(s) {{
        return s.replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;',
          '>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
      }}
      function parse() {{
        let last=0,m;
        while((m=regex.exec(raw))!==null) {{
          if(m.index>last) segments.push({{type:'text',text:raw.slice(last,m.index)}});
          let cue=m[1].trim().toLowerCase();
          cue=aliases[cue]||cue;
          if(supported.includes(cue)) segments.push({{type:'cue',text:cue}});
          else segments.push({{type:'text',text:m[0]}});
          last=regex.lastIndex;
        }}
        if(last<raw.length) segments.push({{type:'text',text:raw.slice(last)}});
        el.innerHTML=segments.map(s=>s.type==='cue'
          ? '<span class="cue">['+esc(s.text)+']</span>'
          : esc(s.text)).join('');
      }}
      function sound(name) {{
        if(!document.getElementById('fx').checked) return;
        try {{
          const ctx=new (window.AudioContext||window.webkitAudioContext)();
          const vol=Number(document.getElementById('vol').value);
          const o=ctx.createOscillator(),g=ctx.createGain();
          const now=ctx.currentTime;
          const freq=name==='thunder'?65:
                     name==='knock'?180:
                     name==='heartbeat'?70:
                     name==='glass breaks'?1300:
                     name==='door slams'?90:240;
          o.type=name==='thunder'?'sawtooth':'triangle';
          o.frequency.setValueAtTime(freq,now);
          o.frequency.exponentialRampToValueAtTime(Math.max(35,freq*.5),now+.35);
          g.gain.setValueAtTime(.001,now);
          g.gain.linearRampToValueAtTime(.22*vol,now+.025);
          g.gain.exponentialRampToValueAtTime(.001,now+.45);
          o.connect(g);g.connect(ctx.destination);
          o.start(now);o.stop(now+.5);
          setTimeout(()=>ctx.close(),800);
        }} catch(e) {{}}
      }}
      function next() {{
        if(stopped||paused) return;
        if(index>=segments.length) {{stopped=true;return;}}
        const s=segments[index++];
        if(s.type==='cue') {{sound(s.text);setTimeout(next,400);return;}}
        const t=s.text.trim();
        if(!t) {{setTimeout(next,10);return;}}
        const u=new SpeechSynthesisUtterance(t);
        u.rate=Number(document.getElementById('speed').value);
        u.onend=()=>setTimeout(next,50);
        u.onerror=()=>{{if(!stopped&&!paused)setTimeout(next,100);}};
        speechSynthesis.speak(u);
      }}
      document.getElementById('play').onclick=()=>{{
        if(paused) {{paused=false;speechSynthesis.resume();return;}}
        if(stopped) {{stopped=false;index=0;next();}}
      }};
      document.getElementById('pause').onclick=()=>{{
        paused=true;speechSynthesis.pause();
      }};
      document.getElementById('stop').onclick=()=>{{
        stopped=true;paused=false;index=0;speechSynthesis.cancel();
      }};
      document.getElementById('speed').value=String({speed});
      parse();
    </script></div></body></html>
    """


def show_reader():
    st.title("Digital Reader")
    rows = get_creations()
    if not rows:
        st.info("Save a creation first.")
        return

    ids = [r["id"] for r in rows]
    titles = {r["id"]: f'{r["title"]} · {r["kind"]}' for r in rows}
    default = st.session_state.get("reader_id", ids[0])
    if default not in ids:
        default = ids[0]

    selected = st.selectbox(
        "Choose a creation", ids, index=ids.index(default),
        format_func=lambda x: titles[x]
    )
    row = get_creation(selected)
    if row:
        components.html(
            reader_html(row["title"], row["content"], load_prefs()),
            height=620, scrolling=True
        )
        st.download_button(
            "Download text",
            row["content"],
            file_name="story.txt",
            mime="text/plain"
        )


# ---------------------------------------------------------
# EXPORT STUDIO
# ---------------------------------------------------------

def show_export_studio():
    st.title("Export Studio 📦")
    st.write("Download saved creations in formats supported by this app.")

    rows = get_creations()
    if not rows:
        st.info("Save a story, plan, or picture book first.")
        return

    ids = [r["id"] for r in rows]
    titles = {r["id"]: r["title"] for r in rows}
    selected = st.selectbox(
        "Choose a project", ids, format_func=lambda x: titles[x]
    )
    row = get_creation(selected)
    if not row:
        return

    st.subheader(row["title"])
    st.caption("Type: " + row["kind"])

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", row["title"])
    st.download_button(
        "Download TXT",
        row["content"],
        file_name=safe_name + ".txt",
        mime="text/plain",
        use_container_width=True
    )

    markdown = f"# {row['title']}\n\n{row['content']}\n"
    st.download_button(
        "Download Markdown",
        markdown,
        file_name=safe_name + ".md",
        mime="text/markdown",
        use_container_width=True
    )

    if st.button("Prepare PDF"):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer
            )
            from xml.sax.saxutils import escape

            from io import BytesIO
            output = BytesIO()
            doc = SimpleDocTemplate(output, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [
                Paragraph(escape(row["title"]), styles["Title"]),
                Spacer(1, 16)
            ]
            for paragraph in row["content"].splitlines():
                if paragraph.strip():
                    story.append(
                        Paragraph(escape(paragraph), styles["BodyText"])
                    )
                    story.append(Spacer(1, 8))
            doc.build(story)
            st.session_state.export_pdf = output.getvalue()
        except ImportError:
            st.error("Install PDF support with: python -m pip install reportlab")
        except Exception as exc:
            st.error("Could not create PDF: " + str(exc))

    if st.session_state.get("export_pdf"):
        st.download_button(
            "Download PDF",
            st.session_state.export_pdf,
            file_name=safe_name + ".pdf",
            mime="application/pdf"
        )

    st.caption(
        "Picture-book PDF export currently exports the saved project text. "
        "It does not yet embed uploaded images into the PDF."
    )


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

def show_settings():
    prefs = load_prefs()
    st.title("Settings & Appearance")

    prefs["mode"] = st.selectbox(
        "Contrast mode", ["Dark", "Light"],
        index=0 if prefs["mode"] == "Dark" else 1
    )

    st.subheader("Section colours")
    for section in SECTIONS:
        prefs["section_colors"][section] = st.color_picker(
            section + " background",
            prefs["section_colors"].get(section, "#202030"),
            key="color_" + section
        )

    st.subheader("Background picture")
    uploaded = st.file_uploader(
        "Upload a background image",
        type=["png", "jpg", "jpeg", "webp"]
    )
    if uploaded:
        ext = Path(uploaded.name).suffix.lower()
        path = BACKGROUND_DIR / f"{uuid.uuid4().hex}{ext}"
        path.write_bytes(uploaded.getvalue())
        prefs["background_path"] = str(path.resolve())
        st.success("Background uploaded.")

    if prefs.get("background_path") and Path(
        prefs["background_path"]
    ).is_file():
        st.image(prefs["background_path"], caption="Current background")
        if st.button("Remove background"):
            prefs["background_path"] = ""
            save_prefs()
            st.rerun()

    st.subheader("Reader")
    prefs["font_size"] = st.slider(
        "Reader font size", 14, 30, int(prefs["font_size"])
    )
    prefs["narration_speed"] = st.slider(
        "Narration speed", 0.75, 1.5, float(prefs["narration_speed"]), 0.05
    )
    prefs["sound_effects"] = st.checkbox(
        "Enable sound effects", value=bool(prefs["sound_effects"])
    )
    prefs["sound_volume"] = st.slider(
        "Sound volume", 0.0, 1.0, float(prefs["sound_volume"]), 0.05
    )

    if st.button("Save settings", type="primary"):
        save_prefs()
        st.success("Settings saved.")
        st.rerun()

    if st.button("Reset settings"):
        st.session_state.prefs = json.loads(json.dumps(DEFAULT_PREFS))
        save_prefs()
        st.rerun()


# ---------------------------------------------------------
# ABOUT AND NAVIGATION
# ---------------------------------------------------------

def show_about():
    st.title("About StoryForge")
    st.write(
        "StoryForge helps you create stories, poems, story plans, "
        "characters, and illustrated story projects."
    )
    st.markdown("""
    **Included sections**
    - Create: AI-assisted stories and poems
    - My Library: search, edit, download, and delete creations
    - Digital Reader: browser narration and synthesized sound cues
    - Story Lab: outlines and branching adventure plans
    - Character Studio: saved fictional character profiles
    - Picture Stories: scene descriptions, captions, and uploaded pictures
    - Export Studio: TXT, Markdown, and PDF text exports
    - Settings: section colours, background image, and reader controls

    Sound effects are simplified synthesized effects, not real recordings.
    """)


def main():
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    load_prefs()
    db_connect().close()

    with st.sidebar:
        st.markdown("# ✨ StoryForge")
        st.caption("Your storytelling studio")
        if "page" not in st.session_state:
            st.session_state.page = "Home"
        selected = st.radio(
            "Navigate", SECTIONS, key="page",
            label_visibility="collapsed"
        )
        st.divider()
        st.caption("Your creations are stored locally.")

    apply_appearance(selected)

    pages = {
        "Home": show_home,
        "Create": show_create,
        "My Library": show_library,
        "Digital Reader": show_reader,
        "Story Lab": show_story_lab,
        "Character Studio": show_character_studio,
        "Picture Stories": show_picture_stories,
        "Export Studio": show_export_studio,
        "Settings": show_settings,
        "About": show_about,
    }
    pages[selected]()


if __name__ == "__main__":
    main()
