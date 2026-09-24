import sys
import os
import json
import urllib.parse
import requests
import streamlit as st

# Ensure project root is in Python path for direct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))

st.set_page_config(
    page_title="HirePractice AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Minimalist SaaS Design System
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #F8FAFC;
        color: #0F172A;
    }

    /* Minimalist Top Bar */
    .top-header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        padding: 14px 24px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        margin-bottom: 24px;
    }
    .top-brand-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.01em;
    }
    .top-brand-subtitle {
        font-size: 0.8rem;
        color: #64748B;
        font-weight: 500;
    }
    .top-user-badge {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.85rem;
        color: #475569;
        font-weight: 500;
        background: #F1F5F9;
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid #E2E8F0;
    }

    /* SaaS Card Container */
    .saas-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 20px;
    }
    .card-heading {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 12px;
    }

    /* Clean Skill Badges */
    .badge-matched {
        display: inline-block;
        background: #F0FDF4;
        color: #166534;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid #DCFCE7;
    }
    .badge-related {
        display: inline-block;
        background: #FFFBEB;
        color: #92400E;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid #FEF3C7;
    }
    .badge-missing {
        display: inline-block;
        background: #FEF2F2;
        color: #991B1B;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid #FEE2E2;
    }

    /* Primary Clean Action Button */
    div.stButton > button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        font-size: 0.95rem !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #4338CA !important;
    }

    /* Hide redundant Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# Initialize Session State Variables
if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = None
if "resume_analysis" not in st.session_state:
    st.session_state.resume_analysis = None
if "job_profile" not in st.session_state:
    st.session_state.job_profile = None
if "match_analysis" not in st.session_state:
    st.session_state.match_analysis = None
if "cold_email" not in st.session_state:
    st.session_state.cold_email = None

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0
if "current_difficulty" not in st.session_state:
    st.session_state.current_difficulty = "Junior"
if "is_completed" not in st.session_state:
    st.session_state.is_completed = False
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "interview_blueprint" not in st.session_state:
    st.session_state.interview_blueprint = None
if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = []


# TOP HEADER BAR
c_prof = st.session_state.candidate_profile or {}
c_name = c_prof.get("name") or "Candidate"
c_role = c_prof.get("target_roles", ["Software Engineer"])[0] if c_prof.get("target_roles") else "Software Engineer"

st.markdown(f"""
<div class="top-header-bar">
    <div>
        <div class="top-brand-title">HirePractice AI</div>
        <div class="top-brand-subtitle">Interview Practice & Preparation Platform</div>
    </div>
    <div class="top-user-badge">
        <span>Target Role: <strong>{c_role}</strong></span>
        <span>|</span>
        <span>Candidate: <strong>{c_name}</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)


# SIDEBAR NAVIGATION
with st.sidebar:
    st.subheader("HirePractice AI")
    st.caption("Workspace Navigation")
    
    nav_selection = st.radio(
        "Navigation Menu",
        [
            "Dashboard",
            "Resume & JD",
            "Match Analysis",
            "Interview Blueprint",
            "Active Interview",
            "History",
            "Progress",
            "Settings"
        ],
        index=0,
        label_visibility="collapsed",
        key="sidebar_nav_menu"
    )

    st.divider()
    st.caption("System Status")
    st.markdown("- **Engine**: ReAct Tool-Calling Agent\n- **Graph**: LangGraph Orchestrator\n- **RAG Store**: ChromaDB Vector DB")


# Helper function to trigger match analysis & cold email generation
def run_live_match_analysis():
    if st.session_state.candidate_profile and st.session_state.job_profile:
        try:
            m_resp = requests.post(
                f"{API_BASE_URL}/api/match/analyze",
                json={
                    "candidate_profile": st.session_state.candidate_profile,
                    "job_profile": st.session_state.job_profile
                },
                timeout=HTTP_TIMEOUT
            )
            if m_resp.status_code == 200:
                st.session_state.match_analysis = m_resp.json()["match_analysis"]

            e_resp = requests.post(
                f"{API_BASE_URL}/api/cold-email/generate",
                json={
                    "candidate_profile": st.session_state.candidate_profile,
                    "job_profile": st.session_state.job_profile
                },
                timeout=HTTP_TIMEOUT
            )
            if e_resp.status_code == 200:
                st.session_state.cold_email = e_resp.json()["cold_email"]
        except Exception as err:
            st.warning(f"Match engine status: {err}")


# PAGE 1: DASHBOARD
if nav_selection == "Dashboard":
    st.title("Dashboard")
    st.caption("Overview of candidate profile, target job, match score, and interview readiness.")

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Resume Profile",
            value="Uploaded" if st.session_state.candidate_profile else "Not Added"
        )
    with col2:
        st.metric(
            label="Job Description",
            value="Analyzed" if st.session_state.job_profile else "Not Added"
        )
    with col3:
        score_display = f"{st.session_state.match_analysis.get('match_score', 0)}%" if st.session_state.match_analysis else "N/A"
        st.metric(
            label="Resume Match Score",
            value=score_display
        )
    with col4:
        session_status = "In Progress" if st.session_state.session_id and not st.session_state.is_completed else ("Completed" if st.session_state.is_completed else "Not Started")
        st.metric(
            label="Active Session",
            value=session_status
        )

    st.divider()

    d_col1, d_col2 = st.columns([1.2, 1])

    with d_col1:
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Candidate Summary</div>', unsafe_allow_html=True)
        if st.session_state.candidate_profile:
            cp = st.session_state.candidate_profile
            st.write(f"**Name:** {cp.get('name', 'Candidate')}")
            st.write(f"**Skills:** {', '.join(cp.get('skills', [])[:8])}")
            if cp.get("projects"):
                st.write(f"**Key Projects:** {', '.join(cp.get('projects', []))}")
        else:
            st.info("No candidate resume uploaded. Navigate to **Resume & JD** to upload your resume.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Target Role Details</div>', unsafe_allow_html=True)
        if st.session_state.job_profile:
            jp = st.session_state.job_profile
            st.write(f"**Role:** {jp.get('role', 'Software Engineer')}")
            st.write(f"**Company:** {jp.get('company', 'Target Company')}")
            st.write(f"**Required Tech:** {', '.join(jp.get('required_skills', [])[:8])}")
        else:
            st.info("No job description added. Navigate to **Resume & JD** to add target job requirements.")
        st.markdown('</div>', unsafe_allow_html=True)

    with d_col2:
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Quick Actions</div>', unsafe_allow_html=True)
        
        if not st.session_state.candidate_profile or not st.session_state.job_profile:
            st.write("Complete setup to unlock mock interviews.")
            st.button("Upload Resume & Job Description", type="primary", use_container_width=True)
        else:
            st.write("Ready to start adaptive technical evaluation.")
            st.button("View Interview Blueprint", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# PAGE 2: RESUME & JD
elif nav_selection == "Resume & JD":
    st.title("Resume & Job Description Analysis")
    st.caption("Upload candidate resume and paste job description text to parse requirements.")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">1. Candidate Resume</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Upload PDF or DOCX file", type=["pdf", "docx"], key="page_resume_uploader")
        if uploaded_file and st.button("Parse Uploaded File", key="btn_parse_file"):
            with st.spinner("Parsing document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    resp = requests.post(f"{API_BASE_URL}/api/resume/upload", files=files, timeout=HTTP_TIMEOUT)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.candidate_profile = data["candidate_profile"]
                        st.session_state.resume_analysis = data["resume_analysis"]
                        st.success("Resume parsed successfully.")
                        run_live_match_analysis()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error parsing file: {e}")

        st.markdown("---")
        resume_text_input = st.text_area("Or Paste Plain Text Resume", height=140, placeholder="Paste resume raw text here...", key="txt_resume")
        if resume_text_input and st.button("Parse Resume Text", key="btn_parse_txt"):
            with st.spinner("Parsing text..."):
                try:
                    resp = requests.post(f"{API_BASE_URL}/api/resume/parse-text", json={"text": resume_text_input}, timeout=HTTP_TIMEOUT)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.candidate_profile = data["candidate_profile"]
                        st.session_state.resume_analysis = data["resume_analysis"]
                        st.success("Resume text parsed successfully.")
                        run_live_match_analysis()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error parsing resume text: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">2. Target Job Description</div>', unsafe_allow_html=True)
        jd_input = st.text_area("Paste Posting Requirements", height=240, placeholder="Paste target job description text here...", key="page_jd_text")
        if jd_input and st.button("Analyze Job Description", key="btn_parse_jd"):
            with st.spinner("Parsing requirements..."):
                try:
                    resp = requests.post(f"{API_BASE_URL}/api/jd/analyze", json={"jd_text": jd_input}, timeout=HTTP_TIMEOUT)
                    if resp.status_code == 200:
                        st.session_state.job_profile = resp.json()["job_profile"]
                        st.success("Job description analyzed.")
                        run_live_match_analysis()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error analyzing job description: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.candidate_profile or st.session_state.job_profile:
        st.divider()
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            if st.session_state.candidate_profile:
                st.subheader("Parsed Candidate Profile")
                st.json(st.session_state.candidate_profile)
        with res_col2:
            if st.session_state.job_profile:
                st.subheader("Parsed Job Requirements")
                st.json(st.session_state.job_profile)


# PAGE 3: MATCH ANALYSIS
elif nav_selection == "Match Analysis":
    st.title("Match Analysis & Skill Gap Audit")
    st.caption("Requirement-level skill matching, evidence evaluation, and gap detection.")

    if not st.session_state.candidate_profile or not st.session_state.job_profile:
        st.info("Upload a resume and add a job description in the **Resume & JD** section to run match analysis.")
    else:
        if not st.session_state.match_analysis:
            if st.button("Run Skill Match Engine", type="primary"):
                with st.spinner("Evaluating candidate fit..."):
                    run_live_match_analysis()
                    st.rerun()

        if st.session_state.match_analysis:
            ma = st.session_state.match_analysis
            score_val = ma.get("match_score", 0)
            breakdown = ma.get("breakdown", {})
            req_evidences = ma.get("requirement_evidences", [])

            col1, col2 = st.columns([1, 1.2])

            with col1:
                st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                st.markdown('<div class="card-heading">Match Score Breakdown</div>', unsafe_allow_html=True)
                st.metric("Overall Match Score", f"{score_val}%")
                
                req_score = breakdown.get("required_skills_score", 0)
                ev_score = breakdown.get("evidence_strength_score", 80.0)
                pref_score = breakdown.get("preferred_skills_score", 0)
                
                st.progress(min(1.0, req_score / 100.0), text=f"Required Skills Match: {req_score:.0f}%")
                st.progress(min(1.0, ev_score / 100.0), text=f"Evidence Strength: {ev_score:.0f}%")
                st.progress(min(1.0, pref_score / 100.0), text=f"Preferred Skills Match: {pref_score:.0f}%")
                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                st.markdown('<div class="card-heading">Skill Audit Summary</div>', unsafe_allow_html=True)
                
                st.write("**Strong Matches:**")
                st.markdown("".join([f'<span class="badge-matched">{s}</span>' for s in ma.get("strong_matches", [])]) or "_None_", unsafe_allow_html=True)
                
                st.write("**Related Evidence:**")
                st.markdown("".join([f'<span class="badge-related">{s}</span>' for s in ma.get("partial_matches", [])]) or "_None_", unsafe_allow_html=True)
                
                st.write("**Missing Requirements:**")
                st.markdown("".join([f'<span class="badge-missing">{s}</span>' for s in ma.get("skill_gaps", [])]) or "_None_", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if req_evidences:
                st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                st.markdown('<div class="card-heading">Requirement Verification Details</div>', unsafe_allow_html=True)
                for ev in req_evidences:
                    status = ev.get("status", "missing")
                    req = ev.get("requirement", "")
                    exp = ev.get("explanation", "")
                    
                    if status == "strong_match":
                        st.markdown(f"- **{req}**: <span class='badge-matched'>Matched</span> ({exp})", unsafe_allow_html=True)
                    elif status in ["partial_match", "related_evidence"]:
                        st.markdown(f"- **{req}**: <span class='badge-related'>Related Evidence</span> ({exp})", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- **{req}**: <span class='badge-missing'>Missing</span> ({exp})", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.cold_email:
            st.divider()
            ce = st.session_state.cold_email
            st.markdown('<div class="saas-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-heading">Application Outreach Email</div>', unsafe_allow_html=True)
            st.write(f"**Subject:** {ce.get('subject', 'Application')}")
            st.text_area("Generated Outreach Email", value=ce.get("body", ""), height=180, key="txt_email_body")
            st.markdown('</div>', unsafe_allow_html=True)


# PAGE 4: INTERVIEW BLUEPRINT
elif nav_selection == "Interview Blueprint":
    st.title("Interview Blueprint")
    st.caption("Pre-interview technical plan, level calibration, and evaluation roadmap.")

    default_role = st.session_state.job_profile.get("role", "Software Engineer") if st.session_state.job_profile else "Software Engineer"
    
    col1, col2 = st.columns(2)
    with col1:
        target_role = st.text_input("Target Position Title", value=default_role, key="bp_target_role")
        focus_area = st.selectbox("Evaluation Focus", ["Auto (Balanced)", "Technical", "System Design", "Behavioral", "Project Deep Dive"], index=0)
    with col2:
        difficulty_level = st.selectbox("Interview Level", ["Auto (Calibrated)", "Junior", "Mid-Level", "Senior", "Staff"], index=0)
        max_turns = st.slider("Interview Rounds / Turns", min_value=1, max_value=10, value=5)

    st.divider()

    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("Candidate Level", "Entry-Level" if not st.session_state.candidate_profile else "Calibrated")
    with b2:
        st.metric("Job Level", "Junior" if "junior" in target_role.lower() else ("Senior" if "senior" in target_role.lower() else "Mid-Level"))
    with b3:
        st.metric("Interview Calibration", "Junior" if "junior" in target_role.lower() else "Mid-Level")

    if st.session_state.match_analysis:
        ma = st.session_state.match_analysis
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-heading">Targeted Skill Verification Plan</div>', unsafe_allow_html=True)
        
        st.write("**Strong Candidate Skills (To Deep Dive):**")
        st.markdown("".join([f'<span class="badge-matched">{s}</span>' for s in ma.get("strong_matches", [])[:8]]) or "_None_", unsafe_allow_html=True)
        
        st.write("**Missing / Gap Skills (To Evaluate & Bridge):**")
        st.markdown("".join([f'<span class="badge-missing">{s}</span>' for s in ma.get("skill_gaps", [])[:6]]) or "_None_", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Start Interview Session", type="primary", use_container_width=True):
        with st.spinner("Initializing LangGraph state and executing initial tool call..."):
            try:
                payload = {
                    "target_role": target_role,
                    "resume_summary": json.dumps(st.session_state.candidate_profile) if st.session_state.candidate_profile else "",
                    "candidate_profile": st.session_state.candidate_profile,
                    "job_profile": st.session_state.job_profile,
                    "match_analysis": st.session_state.match_analysis,
                    "focus_area": "Mixed" if "Auto" in focus_area else focus_area,
                    "max_turns": max_turns
                }
                resp = requests.post(f"{API_BASE_URL}/api/interview/start", json=payload, timeout=HTTP_TIMEOUT)
                if resp.status_code == 201:
                    data = resp.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.current_question = data["initial_question"]
                    st.session_state.current_difficulty = data["current_difficulty"]
                    st.session_state.interview_blueprint = data.get("interview_blueprint")
                    st.session_state.tool_calls = data.get("tool_calls", [])
                    st.session_state.turn_count = 1
                    st.session_state.chat_history = [{"role": "interviewer", "content": data["initial_question"]}]
                    st.session_state.is_completed = False
                    st.session_state.final_report = None
                    st.rerun()
                else:
                    st.error(f"Failed to start interview session: {resp.text}")
            except Exception as err:
                st.error(f"Error connecting to backend: {err}")


# PAGE 5: ACTIVE INTERVIEW
elif nav_selection == "Active Interview":
    st.title("Technical Interview")
    st.caption("Adaptive live technical evaluation driven by ReAct tool-calling agents.")

    if not st.session_state.session_id:
        st.info("No active interview session found. Navigate to **Interview Blueprint** to generate your plan and start.")
    else:
        # Progress & Status Bar
        p1, p2, p3 = st.columns(3)
        with p1:
            st.metric("Session ID", f"{st.session_state.session_id[:8]}...")
        with p2:
            st.metric("Question Turn", f"{st.session_state.turn_count}")
        with p3:
            st.metric("Difficulty Level", st.session_state.current_difficulty)

        # AGENT ACTIVITY EXPANDABLE DRAWER
        with st.expander("Agent Activity & Tool Trace", expanded=False):
            if st.session_state.tool_calls:
                for tc in st.session_state.tool_calls:
                    st.markdown(f"**`{tc.get('tool')}`** (`{tc.get('timestamp')}`)\n- **Arguments:** `{json.dumps(tc.get('arguments', {}))}`\n- **Result Summary:** {tc.get('result_summary')}")
            else:
                st.write("No tool calls executed on this turn.")

        st.divider()

        # Transcript History
        for msg in st.session_state.chat_history:
            if msg["role"] == "interviewer":
                st.chat_message("assistant").write(msg["content"])
            else:
                st.chat_message("user").write(msg["content"])

        # Answer Input
        if not st.session_state.is_completed:
            candidate_answer = st.chat_input("Type your technical response here...")
            if candidate_answer:
                st.session_state.chat_history.append({"role": "candidate", "content": candidate_answer})
                with st.spinner("Evaluating response and determining next question..."):
                    try:
                        payload = {
                            "session_id": st.session_state.session_id,
                            "candidate_response": candidate_answer
                        }
                        resp = requests.post(f"{API_BASE_URL}/api/interview/respond", json=payload, timeout=HTTP_TIMEOUT)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.turn_count = data["turn_count"]
                            st.session_state.current_difficulty = data["current_difficulty"]
                            st.session_state.is_completed = data["is_completed"]
                            st.session_state.tool_calls = data.get("tool_calls", [])

                            if data.get("next_question"):
                                st.session_state.current_question = data["next_question"]
                                st.session_state.chat_history.append({"role": "interviewer", "content": data["next_question"]})
                            
                            if data.get("is_completed"):
                                st.session_state.final_report = data.get("final_report")
                                st.success("Interview session completed.")

                            st.rerun()
                        else:
                            st.error(f"Failed to submit response: {resp.text}")
                    except Exception as err:
                        st.error(f"Error submitting answer: {err}")

        # Final Report Display
        if st.session_state.final_report:
            st.divider()
            st.subheader("Final Interview Evaluation Report")
            report = st.session_state.final_report
            st.metric("Overall Evaluation Score", f"{report.get('overall_score', 7.5)} / 10")
            st.markdown(report.get("markdown_report", "Evaluation completed."))


# PAGE 6: HISTORY
elif nav_selection == "History":
    st.title("Interview History")
    st.caption("Past completed interview sessions and evaluation records.")

    try:
        resp = requests.get(f"{API_BASE_URL}/api/history", timeout=10)
        if resp.status_code == 200:
            sessions = resp.json().get("sessions", [])
            if not sessions:
                st.info("No past interview sessions found.")
            else:
                for sess in sessions:
                    with st.expander(f"{sess.get('created_at')} — {sess.get('target_role')} (Score: {sess.get('overall_score')}/10)"):
                        st.write(f"**Session ID:** `{sess.get('session_id')}`")
                        st.write(f"**Turns:** {sess.get('turn_count')}")
                        st.write(f"**Score:** {sess.get('overall_score')}/10")
                        if sess.get("final_report"):
                            st.markdown(sess["final_report"].get("markdown_report", ""))
        else:
            st.error("Unable to load interview history.")
    except Exception as err:
        st.error(f"Error connecting to backend history API: {err}")


# PAGE 7: PROGRESS
elif nav_selection == "Progress":
    st.title("Skill Mastery & Progress")
    st.caption("Category scores and aggregate performance analytics across past attempts.")

    try:
        resp = requests.get(f"{API_BASE_URL}/api/progress", timeout=10)
        if resp.status_code == 200:
            analytics = resp.json().get("analytics", {})
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Interviews", analytics.get("total_interviews", 0))
            with c2:
                st.metric("Average Score", f"{analytics.get('average_score', 0)} / 10")
            with c3:
                cat_scores = analytics.get("category_scores", {})
                st.metric("Top Subject Category", max(cat_scores, key=cat_scores.get) if cat_scores else "N/A")

            st.divider()
            st.subheader("Category Performance Scores")
            for cat, val in analytics.get("category_scores", {}).items():
                st.progress(min(1.0, float(val) / 100.0), text=f"{cat}: {val}%")
        else:
            st.error("Unable to load progress analytics.")
    except Exception as err:
        st.error(f"Error connecting to progress API: {err}")


# PAGE 8: SETTINGS
elif nav_selection == "Settings":
    st.title("System Settings")
    st.caption("Configuration details for LLM engine, API integration, and telemetry.")

    st.markdown('<div class="saas-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-heading">API & Backend Connectivity</div>', unsafe_allow_html=True)
    st.write(f"**API Base URL:** `{API_BASE_URL}`")
    st.write(f"**HTTP Timeout:** `{HTTP_TIMEOUT} seconds`")
    
    if st.button("Check Backend API Health"):
        try:
            h_resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if h_resp.status_code == 200:
                st.success(f"Backend API Healthy: {h_resp.json()}")
            else:
                st.error(f"Health check failed: {h_resp.text}")
        except Exception as err:
            st.error(f"Error reaching backend health endpoint: {err}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="saas-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-heading">Architecture & Telemetry</div>', unsafe_allow_html=True)
    st.write("**LLM Provider:** ChatGroq / ChatOpenAI (Auto-detected from `.env`)")
    st.write("**Orchestration Engine:** LangGraph (StateGraph)")
    st.write("**Vector Storage:** ChromaDB Persistent Client")
    st.write("**Observability:** LangSmith Tracing (`LANGCHAIN_TRACING_V2`)")
    st.markdown('</div>', unsafe_allow_html=True)
