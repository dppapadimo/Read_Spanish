import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import date
import io

st.set_page_config(page_title="Spanish Reader", page_icon="📖", layout="centered")

CSS = (
    "<style>"
    ".stButton button {"
    "width:100%;padding:0.75rem;font-size:1rem;border-radius:10px;}"
    ".stTextInput input,.stTextArea textarea {font-size:1rem;}"
    ".word-card {"
    "background:#1e3a5f;color:white;padding:2rem;border-radius:16px;"
    "text-align:center;font-size:2rem;font-weight:bold;margin:1rem 0;}"
    ".answer-card {"
    "background:#0f4c2a;color:#7dffb3;padding:1.5rem;border-radius:16px;"
    "text-align:center;font-size:1.5rem;margin:1rem 0;}"
    "</style>"
)
st.markdown(CSS, unsafe_allow_html=True)

EXPECTED_COLS = [
    "word", "translation", "lemma", "pos", "sentence",
    "difficulty", "date", "ease", "interval", "repetitions", "next_review"
]


def fix_columns(df):
    df.columns = [c.lower().strip() for c in df.columns]
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[EXPECTED_COLS]


def empty_words_df():
    return pd.DataFrame(columns=EXPECTED_COLS)


def empty_log_df():
    return pd.DataFrame(columns=["date", "count"])


def do_translate(word):
    return GoogleTranslator(source="auto", target="el").translate(word)


def word_exists(df, word):
    return word.strip().lower() in df["word"].str.lower().values


def add_word(word, translation, text):
    df = st.session_state.words_df
    if word_exists(df, word):
        return False

    new_row = {
        "word": word.strip(),
        "translation": translation,
        "lemma": "",
        "pos": "",
        "sentence": text[:120] if text else "",
        "difficulty": "medium",
        "date": str(date.today()),
        "ease": 2.5,
        "interval": 1,
        "repetitions": 0,
        "next_review": str(date.today())
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.words_df = df

    log = st.session_state.log_df
    today = str(date.today())

    if today in log["date"].astype(str).values:
        log.loc[log["date"].astype(str) == today, "count"] += 1
    else:
        log = pd.concat([log, pd.DataFrame([{"date": today, "count": 1}])], ignore_index=True)

    st.session_state.log_df = log
    return True


def df_to_excel_bytes(df):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def word_card(word):
    st.markdown(f'<div class="word-card">ES {word}</div>', unsafe_allow_html=True)


def answer_card(translation):
    st.markdown(f'<div class="answer-card">GR {translation}</div>', unsafe_allow_html=True)


def read_or_audio_ui(text_key, word_key, save_key, spinner_text):
    text = st.text_area("Επικολλησε κειμενο:", height=200, key=text_key)
    word = st.text_input("Γραψε αγνωστη λεξη:", key=word_key)

    if word:
        word = word.strip()
        word_card(word)

        if "last_word" not in st.session_state or st.session_state.last_word != word:
            with st.spinner(spinner_text):
                st.session_state.last_translation = do_translate(word)
            st.session_state.last_word = word

        translation = st.session_state.last_translation
        answer_card(translation)

        if word_exists(st.session_state.words_df, word):
            st.warning("Η λεξη υπαρχει ηδη στη λιστα σου.")
        else:
            if st.button("Αποθηκευση λεξης", key=save_key):
                saved = add_word(word, translation, text)
                if saved:
                    st.success(f"Αποθηκευτηκε: {word} -> {translation}")
                    st.info(f"Συνολο: {len(st.session_state.words_df)} λεξεις")
                else:
                    st.warning("Η λεξη υπαρχει ηδη.")


# --- INIT SESSION STATE ---

if "words_df" not in st.session_state:
    st.session_state.words_df = empty_words_df()

if "log_df" not in st.session_state:
    st.session_state.log_df = empty_log_df()

if "fc_index" not in st.session_state:
    st.session_state.fc_index = 0

if "show_answer" not in st.session_state:
    st.session_state.show_answer = False

if "last_word" not in st.session_state:
    st.session_state.last_word = ""

if "last_translation" not in st.session_state:
    st.session_state.last_translation = ""


# --- SIDEBAR ---

with st.sidebar:
    st.header("Δεδομένα")

    uploaded_words = st.file_uploader("Φορτωσε Words Excel", type=["xlsx"], key="up_words")
    if uploaded_words:
        loaded = fix_columns(pd.read_excel(uploaded_words))
        st.session_state.words_df = loaded.copy()
        st.session_state.fc_index = 0
        st.session_state.show_answer = False
        st.success(f"Φορτωθηκαν {len(loaded)} λεξεις")

    uploaded_log = st.file_uploader("Φορτωσε Log Excel", type=["xlsx"], key="up_log")
    if uploaded_log:
        loaded_log = pd.read_excel(uploaded_log)
        st.session_state.log_df = loaded_log
        st.success(f"Φορτωθηκε log ({len(loaded_log)} εγγραφες)")

    st.divider()

    st.download_button(
        label="Κατεβασε Λεξεις",
        data=df_to_excel_bytes(st.session_state.words_df),
        file_name="spanish_words.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        label="Κατεβασε Log",
        data=df_to_excel_bytes(st.session_state.log_df),
        file_name="study_log.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()
    st.metric("Συνολικες λεξεις", len(st.session_state.words_df))


# --- MAIN ---

st.title("Spanish Reader")

mode = st.radio(
    "Λειτουργια:",
    ["Αναγνωση", "Audio", "Flashcards", "Ημερολογιο"],
    horizontal=True
)


# --- READ ---

if mode == "Αναγνωση":
    st.markdown("## Αναγνωση κειμενου")
    read_or_audio_ui("read_text", "read_word", "read_save", "Μεταφραση...")


# --- AUDIO ---

elif mode == "Audio":
    st.markdown("## Ακουστικο περιεχομενο")
    read_or_audio_ui("audio_text", "audio_word", "audio_save", "Μεταφραση...")


# --- FLASHCARDS ---

elif mode == "Flashcards":
    st.markdown("## Flashcards")

    df = st.session_state.words_df
    total = len(df)

    if total == 0:
        st.warning("Δεν υπαρχουν λεξεις. Προσθεσε απο Αναγνωση η Audio.")

    if total > 0:
        if st.session_state.fc_index >= total:
            st.session_state.fc_index = 0

        idx = st.session_state.fc_index
        row = df.iloc[idx]

        st.caption(f"Καρτα {idx + 1} απο {total}")
        word_card(row["word"])

        if row["sentence"]:
            st.caption(str(row["sentence"]))

        if st.session_state.show_answer:
            answer_card(row["translation"])

        if not st.session_state.show_answer:
            if st.button("Εμφανιση απαντησης", key="fc_show"):
                st.session_state.show_answer = True
                st.rerun()

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Επομενη", key="fc_next"):
                st.session_state.fc_index = (idx + 1) % total
                st.session_state.show_answer = False
                st.rerun()

        with col2:
            if st.button("Αρχη", key="fc_reset"):
                st.session_state.fc_index = 0
                st.session_state.show_answer = False
                st.rerun()


# --- CALENDAR ---

elif mode == "Ημερολογιο":
    st.markdown("## Ιστορικο μελετης")

    log = st.session_state.log_df

    if len(log) == 0:
        st.info("Δεν υπαρχει ιστορικο ακομα.")

    if len(log) > 0:
        log_display = log.copy()
        log_display.columns = ["Ημερομηνια", "Λεξεις"]
        log_display = log_display.sort_values("Ημερομηνια", ascending=False)
        st.dataframe(log_display, use_container_width=True, hide_index=True)
        st.metric("Συνολικες λεξεις", int(log["count"].sum()))
