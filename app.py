import os

import streamlit as st
from groq import Groq
from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)


# ============================================================
# APP CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Meta AI Study Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Change this one variable if you want to use another
# currently supported Groq chat model.
MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.7rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1.05rem;
            color: #6b7280;
            margin-bottom: 1.5rem;
        }

        .feature-card {
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            margin-bottom: 0.75rem;
        }

        .sidebar-title {
            font-size: 1.35rem;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key" not in st.session_state:
    st.session_state.api_key = ""


# ============================================================
# API KEY HANDLING
# ============================================================

def get_api_key():
    """
    Get the Groq API key securely.

    Priority:
    1. Streamlit Secrets
    2. Environment variable
    3. Temporary session input
    """

    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")

        if secret_key:
            return secret_key.strip()

    except Exception:
        pass

    environment_key = os.getenv("GROQ_API_KEY", "")

    if environment_key:
        return environment_key.strip()

    return st.session_state.api_key.strip()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">🤖 Meta AI Study Assistant</div>',
        unsafe_allow_html=True,
    )

    st.caption("Your AI-powered learning companion")

    st.divider()

    subject = st.selectbox(
        "📚 Subject",
        [
            "Computer Science",
            "Mathematics",
            "Physics",
            "Chemistry",
            "English",
            "General Knowledge",
            "Other",
        ],
    )

    explanation_style = st.selectbox(
        "🎯 Explanation Style",
        [
            "Simple",
            "Detailed",
            "Exam-focused",
        ],
    )

    task = st.selectbox(
        "🧠 AI Task",
        [
            "AI Tutor",
            "Notes Generator",
            "Summarizer",
            "Quiz Generator",
            "MCQ Generator",
            "Flashcard Generator",
            "Study Planner",
            "Coding Assistant",
        ],
    )

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):

        st.session_state.messages = []

        st.rerun()

    st.divider()

    st.markdown("### 🔐 API Key")

    try:
        secret_exists = bool(
            st.secrets.get("GROQ_API_KEY", "")
        )
    except Exception:
        secret_exists = False

    environment_exists = bool(
        os.getenv("GROQ_API_KEY", "")
    )

    if not secret_exists and not environment_exists:

        st.session_state.api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=st.session_state.api_key,
            placeholder="Paste your Groq API key",
            help="Your key is kept in the current session.",
        )

        st.caption(
            "For Streamlit Cloud, add GROQ_API_KEY "
            "to Streamlit Secrets."
        )

    else:

        st.success("Groq API key detected.")

    st.divider()

    st.markdown("### ✨ What I can do")

    st.markdown(
        """
        - 📖 Explain concepts
        - 📝 Generate notes
        - 🔎 Summarize text
        - 🧠 Create quizzes
        - ✅ Generate MCQs
        - 🗂️ Create flashcards
        - 📅 Build study plans
        - 💻 Explain code
        """
    )


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Meta AI Study Assistant, a helpful educational AI assistant.

Your main goal is to help students understand concepts instead of
simply giving unexplained answers.

Follow these rules:

1. Explain concepts clearly and accurately.
2. Adapt responses to the selected subject.
3. Adapt responses to the selected explanation style.
4. Use simple language whenever possible.
5. Break difficult topics into smaller steps.
6. Give examples when useful.
7. Use headings, bullet points, numbered steps, tables,
   and code blocks when appropriate.
8. For mathematics and science problems, show steps clearly.
9. For programming questions, explain both the code and
   the programming concept.
10. Never invent facts when uncertain.
11. Encourage understanding and learning.
12. Keep responses relevant.
13. Do not unnecessarily repeat the question.
14. For exam-focused responses, emphasize definitions,
    formulas, important points, common mistakes, and
    revision tips.
"""


# ============================================================
# TASK PROMPTS
# ============================================================

TASK_INSTRUCTIONS = {

    "AI Tutor": """
Act as a personal AI tutor.

Answer the student's question and teach the concept clearly.
Include explanations, steps, and examples when useful.
""",

    "Notes Generator": """
Create organized study notes about the requested topic.

Include:
- Definitions
- Important concepts
- Examples
- Key points
- Short revision summary
""",

    "Summarizer": """
Summarize the student's provided text.

Provide:
- Concise summary
- Main ideas
- Important facts
- Key terms when relevant

Do not change the original meaning.
""",

    "Quiz Generator": """
Create an educational quiz based on the student's topic
or provided text.

Generate approximately 5 questions unless another number
is requested.

Provide an answer key at the end.
""",

    "MCQ Generator": """
Generate approximately 5 multiple-choice questions unless
another number is requested.

Each question must have:

A.
B.
C.
D.

Clearly identify the correct answer and briefly explain it.
""",

    "Flashcard Generator": """
Create approximately 8 educational flashcards unless
another number is requested.

Use this format:

Flashcard 1
Question: ...
Answer: ...
""",

    "Study Planner": """
Create a realistic personalized study plan.

Consider:
- Subjects
- Available study time
- Student goals
- Revision
- Practice
- Breaks
- Active recall

Avoid unrealistic schedules.
""",

    "Coding Assistant": """
Act as a programming tutor.

Help the student understand:
- What the code does
- How it works
- Errors or bugs
- How to improve it
- The programming concept involved

When useful, provide corrected code and explain the correction.
"""
}


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(
    user_input,
    selected_subject,
    selected_style,
    selected_task,
):

    task_instruction = TASK_INSTRUCTIONS[selected_task]

    return f"""
Selected subject:
{selected_subject}

Selected explanation style:
{selected_style}

Selected AI task:
{selected_task}

Task instructions:
{task_instruction}

Student request:
{user_input}

Response requirements:

- Match the selected explanation style.
- Keep the response educational and student-friendly.
- Use Markdown formatting where useful.
- For Simple style, explain for a beginner.
- For Detailed style, provide deeper explanations and examples.
- For Exam-focused style, emphasize important definitions,
  formulas, key points, common mistakes, and revision tips.
"""


# ============================================================
# GROQ AI FUNCTION
# ============================================================

def get_ai_response(
    user_input,
    selected_subject,
    selected_style,
    selected_task,
):

    api_key = get_api_key()

    if not api_key:

        return None, (
            "🔐 Groq API key is missing.\n\n"
            "For testing, enter your Groq API key in the sidebar.\n\n"
            "For Streamlit Cloud, add GROQ_API_KEY "
            "under the application's Secrets."
        )

    try:

        client = Groq(api_key=api_key)

        user_prompt = build_prompt(
            user_input,
            selected_subject,
            selected_style,
            selected_task,
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.4,
            max_tokens=2500,
        )

        answer = response.choices[0].message.content

        if not answer:

            return None, (
                "The AI returned an empty response. "
                "Please try again."
            )

        return answer, None

    except AuthenticationError:

        return None, (
            "❌ The Groq API key appears to be invalid. "
            "Please check your key and try again."
        )

    except RateLimitError:

        return None, (
            "⏳ Groq's API rate limit was reached. "
            "Please wait and try again."
        )

    except APIConnectionError:

        return None, (
            "🌐 Could not connect to Groq. "
            "Please check your internet connection."
        )

    except APIStatusError as error:

        return None, (
            f"⚠️ Groq returned an API error "
            f"(status {error.status_code}). "
            "Please try again later."
        )

    except Exception:

        return None, (
            "⚠️ Something went wrong while contacting "
            "the AI service. Please try again."
        )


# ============================================================
# MAIN PAGE
# ============================================================

st.markdown(
    '<div class="main-title">'
    'Meta AI Study Assistant 🤖📚'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Your AI-powered study companion for learning, "
    "revision, and exam preparation."
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# WELCOME SCREEN
# ============================================================

if not st.session_state.messages:

    st.info(
        "👋 Welcome! Select a subject and AI task from the "
        "sidebar, then ask your first question below."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            <div class="feature-card">
                <h4>📖 Learn</h4>
                <p>
                Understand difficult concepts through
                clear explanations and examples.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:

        st.markdown(
            """
            <div class="feature-card">
                <h4>📝 Revise</h4>
                <p>
                Generate notes, summaries, quizzes,
                MCQs, and flashcards.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:

        st.markdown(
            """
            <div class="feature-card">
                <h4>💻 Build</h4>
                <p>
                Learn programming and understand code
                with an AI coding tutor.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# CHAT INPUT
# ============================================================

placeholder_text = {

    "AI Tutor":
        "Ask me a question about your subject...",

    "Notes Generator":
        "Enter a topic for study notes...",

    "Summarizer":
        "Paste the text you want to summarize...",

    "Quiz Generator":
        "Enter a topic for your quiz...",

    "MCQ Generator":
        "Enter a topic for MCQs...",

    "Flashcard Generator":
        "Enter a topic for flashcards...",

    "Study Planner":
        "Tell me your subjects, study time, and goal...",

    "Coding Assistant":
        "Paste your code or ask a programming question...",
}


user_input = st.chat_input(
    placeholder_text.get(
        task,
        "Ask Meta AI Study Assistant...",
    )
)


# ============================================================
# PROCESS USER INPUT
# ============================================================

if user_input:

    user_input = user_input.strip()

    if not user_input:

        st.warning(
            "Please enter some text before sending."
        )

        st.stop()

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):

        st.markdown(user_input)

    with st.chat_message("assistant"):

        with st.spinner("🤔 Thinking..."):

            answer, error = get_ai_response(
                user_input=user_input,
                selected_subject=subject,
                selected_style=explanation_style,
                selected_task=task,
            )

            if error:

                st.error(error)

                assistant_response = error

            else:

                st.markdown(answer)

                assistant_response = answer

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_response,
        }
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Meta AI Study Assistant • Built with Python, "
    "Streamlit, and Groq"
)
