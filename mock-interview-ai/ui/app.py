import sys
import os
import requests
import streamlit as st

# Ensure project root is in Python path for direct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="AI Mock Interview Coach",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling - Premium Pink / Purple Theme
st.markdown("""
<style>
    /* Header Styling */
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 1.15rem;
        color: #64748B;
        font-weight: 400;
        margin-bottom: 1.8rem;
        line-height: 1.5;
    }

    /* Candidate Information Summary Card */
    .summary-card {
        background-color: #FFFFFF;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 1.8rem;
    }
    .summary-item {
        display: flex;
        flex-direction: column;
    }
    .summary-label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #94A3B8;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .summary-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0F172A;
    }

    /* Difficulty Badges */
    .badge-junior {
        background-color: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-mid {
        background-color: #EFF6FF;
        color: #2563EB;
        border: 1px solid #BFDBFE;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-senior {
        background-color: #FFF7ED;
        color: #EA580C;
        border: 1px solid #FFEDD5;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-staff {
        background-color: #FDF2F8;
        color: #DB2777;
        border: 1px solid #FBCFE8;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }

    /* Chat & Message Styling */
    .stChatMessage {
        border-radius: 14px !important;
        padding: 18px 22px !important;
        line-height: 1.65 !important;
        margin-bottom: 1.2rem !important;
    }
    
    /* Primary Action Button */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.2s ease;
    }
    div.stButton > button:first-child:hover {
        opacity: 0.92;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)


def check_backend_health() -> bool:
    """Checks whether the FastAPI REST backend server is responsive."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_difficulty_badge_html(difficulty: str) -> str:
    """Returns color-coded HTML badge for candidate difficulty state."""
    diff_lower = difficulty.lower()
    if "junior" in diff_lower:
        return f'<span class="badge-junior">🟢 {difficulty}</span>'
    elif "senior" in diff_lower:
        return f'<span class="badge-senior">🟠 {difficulty}</span>'
    elif "staff" in diff_lower:
        return f'<span class="badge-staff">🔴 {difficulty}</span>'
    else:
        return f'<span class="badge-mid">🟢 {difficulty}</span>'


def score_to_stars(score: int) -> str:
    """Converts 1-10 numerical score to 5-star representation."""
    stars = max(1, min(5, round(score / 2)))
    return "⭐" * stars + "☆" * (5 - stars)


def main() -> None:
    # 1. Header Presence
    st.markdown('<div class="main-header">🎯 AI Mock Interview Coach</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Practice realistic interviews powered by multiple AI agents using LangGraph.</div>', unsafe_allow_html=True)

    # Initialize Streamlit Session State
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "evaluations" not in st.session_state:
        st.session_state.evaluations = []
    if "current_difficulty" not in st.session_state:
        st.session_state.current_difficulty = "Mid-Level"
    if "is_completed" not in st.session_state:
        st.session_state.is_completed = False
    if "final_report" not in st.session_state:
        st.session_state.final_report = None

    # Sidebar Form Controls
    with st.sidebar:
        st.header("📋 Candidate Setup")
        st.markdown("<br>", unsafe_allow_html=True)
        
        target_role = st.text_input("Target Role", value="Senior AI Engineer")
        st.markdown("<br>", unsafe_allow_html=True)
        
        focus_area = st.selectbox("Interview Focus", ["Technical", "Behavioral", "Mixed", "Case"])
        st.markdown("<br>", unsafe_allow_html=True)
        
        resume_summary = st.text_area(
            "Resume Summary",
            value="5 years experience in Python, LangChain, RAG architecture, vector databases, and distributed system design.",
            height=160
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        max_turns = st.slider("Interview Turns", min_value=1, max_value=10, value=5)

        st.divider()

        is_backend_live = check_backend_health()
        if is_backend_live:
            st.success("🟢 FastAPI Backend Connected")
        else:
            st.info("🟡 Running in Standalone Graph Mode")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Start New Interview", use_container_width=True):
            with st.spinner("Planner & Interviewer Agents initializing strategy..."):
                start_new_interview(target_role, resume_summary, focus_area, max_turns, is_backend_live)

    # Welcome State View
    if not st.session_state.session_id and not st.session_state.messages:
        st.info("👈 Fill in your Target Role and Resume Summary in the sidebar, then click **Start New Interview** to begin.")
        st.markdown("""
        ### Multi-Agent LangGraph Architecture:
        - **Planner Agent**: Builds a customized interview strategy matching your target role.
        - **Interviewer Agent**: Asks dynamic, realistic scenario questions one at a time.
        - **Evaluator Agent**: Scores your answers (1-10) and extracts key strengths & weaknesses.
        - **Reflection Agent**: Routes interview flow dynamically (probes deeper or pivots topics).
        - **Difficulty Controller**: Escalates difficulty after strong answers and lowers it if you struggle.
        - **Coach Agent**: Synthesizes a comprehensive final coaching report upon completion.
        """)
        return

    # Candidate Summary Card
    diff_badge_html = get_difficulty_badge_html(st.session_state.current_difficulty)
    st.markdown(f"""
    <div class="summary-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div class="summary-item">
                <div class="summary-label">🎯 Target Role</div>
                <div class="summary-value">{target_role}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">📌 Focus Area</div>
                <div class="summary-value">{focus_area}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">⚡ Difficulty</div>
                <div>{diff_badge_html}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Chat Transcript Rendering
    for index, message in enumerate(st.session_state.messages):
        speaker_role = message.get("role")
        content = message.get("content")
        
        if speaker_role == "interviewer":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("**🤖 Interviewer**")
                st.markdown(content)
        elif speaker_role == "candidate":
            with st.chat_message("user", avatar="👤"):
                st.markdown("**👤 Candidate**")
                st.markdown(content)
                
                # Render associated coaching feedback breakdown for candidate answers
                evaluation_index = (index - 1) // 2
                if evaluation_index < len(st.session_state.evaluations):
                    eval_data = st.session_state.evaluations[evaluation_index]
                    score_num = eval_data.get("score", 6)
                    stars = score_to_stars(score_num)
                    
                    with st.expander("💡 Question Feedback & Analysis"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Communication:** {stars}")
                        with col2:
                            st.markdown(f"**Technical Depth:** {stars}")
                        with col3:
                            st.markdown(f"**Reasoning:** {stars}")
                            
                        st.markdown(f"**Critique:** {eval_data.get('feedback')}")
                        
                        strong_col, weak_col = st.columns(2)
                        with strong_col:
                            st.markdown("**Strengths:**")
                            for strength in eval_data.get("strong_points", []):
                                st.markdown(f"• {strength}")
                        with weak_col:
                            st.markdown("**Areas for Growth:**")
                            for weakness in eval_data.get("weak_points", []):
                                st.markdown(f"• {weakness}")

    # Completion View or Response Input Form
    if st.session_state.is_completed:
        st.success("🎉 Interview Completed!")
        if st.session_state.final_report:
            st.divider()
            report_data = st.session_state.final_report
            overall_score = report_data.get("overall_score", 8.0)
            
            # Recruiter-Style Clean Final Coaching Report
            st.markdown("## 🏆 Final Coaching Report")
            st.markdown(f"### Overall Score: **{overall_score} / 10**")
            st.divider()

            col_s, col_w, col_p = st.columns(3)
            with col_s:
                st.markdown("### Strengths")
                for s in report_data.get("strong_areas", ["Clear technical communication"]):
                    st.markdown(f"• {s}")

            with col_w:
                st.markdown("### Weaknesses")
                for w in report_data.get("weak_areas", ["Needs deeper trade-off analysis"]):
                    st.markdown(f"• {w}")

            with col_p:
                st.markdown("### Practice Next")
                st.markdown("• Review system design trade-offs for latency vs consistency")
                st.markdown("• Practice framing responses using the STAR method")
                st.markdown("• Deep dive into failure recovery and edge cases")

            st.divider()
            with st.expander("📄 View Complete Executive Report"):
                st.markdown(report_data.get("markdown_report", ""))
            
            st.download_button(
                label="📥 Download Full Report (.md)",
                data=report_data.get("markdown_report", ""),
                file_name="interview_coaching_report.md",
                mime="text/markdown",
                use_container_width=True
            )
    else:
        candidate_response_text = st.chat_input("Type your response here...")
        if candidate_response_text:
            with st.spinner("Evaluator, Reflection & Interviewer Agents processing response..."):
                submit_candidate_response(candidate_response_text, is_backend_live)


def start_new_interview(target_role: str, resume_summary: str, focus_area: str, max_turns: int, is_backend_live: bool) -> None:
    """Initializes new interview state and clears past history."""
    st.session_state.messages = []
    st.session_state.evaluations = []
    st.session_state.is_completed = False
    st.session_state.final_report = None

    if is_backend_live:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/interview/start",
                json={
                    "target_role": target_role,
                    "resume_summary": resume_summary,
                    "focus_area": focus_area,
                    "max_turns": max_turns
                },
                timeout=10
            )
            if response.status_code in [200, 201]:
                response_data = response.json()
                st.session_state.session_id = response_data["session_id"]
                st.session_state.current_difficulty = response_data["current_difficulty"]
                st.session_state.messages.append({"role": "interviewer", "content": response_data["initial_question"]})
                st.rerun()
                return
        except Exception as err:
            st.error(f"Failed to communicate with FastAPI backend: {err}")

    # Standalone Direct Execution Fallback
    from main import start_interview, StartInterviewRequest
    request_obj = StartInterviewRequest(
        target_role=target_role,
        resume_summary=resume_summary,
        focus_area=focus_area,
        max_turns=max_turns
    )
    api_response = start_interview(request_obj)
    st.session_state.session_id = api_response.session_id
    st.session_state.current_difficulty = api_response.current_difficulty
    st.session_state.messages.append({"role": "interviewer", "content": api_response.initial_question})
    st.rerun()


def submit_candidate_response(candidate_response_text: str, is_backend_live: bool) -> None:
    """Submits candidate response and updates state with evaluation, next question, or final report."""
    st.session_state.messages.append({"role": "candidate", "content": candidate_response_text})

    if is_backend_live:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/interview/respond",
                json={
                    "session_id": st.session_state.session_id,
                    "candidate_response": candidate_response_text
                },
                timeout=10
            )
            if response.status_code == 200:
                response_data = response.json()
                st.session_state.evaluations.append(response_data["latest_evaluation"])
                st.session_state.current_difficulty = response_data["current_difficulty"]
                st.session_state.is_completed = response_data["is_completed"]

                if response_data["is_completed"]:
                    st.session_state.final_report = response_data["final_report"]
                elif response_data["next_question"]:
                    st.session_state.messages.append({"role": "interviewer", "content": response_data["next_question"]})

                st.rerun()
                return
        except Exception as err:
            st.error(f"Failed to submit response to backend API: {err}")

    # Standalone Direct Execution Fallback
    from main import respond_to_interview, SubmitResponseRequest
    request_obj = SubmitResponseRequest(
        session_id=st.session_state.session_id,
        candidate_response=candidate_response_text
    )
    api_response = respond_to_interview(request_obj)
    st.session_state.evaluations.append(api_response.latest_evaluation)
    st.session_state.current_difficulty = api_response.current_difficulty
    st.session_state.is_completed = api_response.is_completed

    if api_response.is_completed:
        st.session_state.final_report = api_response.final_report
    elif api_response.next_question:
        st.session_state.messages.append({"role": "interviewer", "content": api_response.next_question})

    st.rerun()


if __name__ == "__main__":
    main()
