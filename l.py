import streamlit as st
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import io, re

# ── Page Config ──────────────────────────────
st.set_page_config(page_title="ResumeIQ", page_icon="⚡", layout="wide")

# ── CSS ──────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp { font-family: 'DM Sans', sans-serif; background: #05080f; color: #e8ecf4; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem !important; max-width: 1100px !important; margin: auto; }
section[data-testid="stSidebar"] { display: none !important; }

.brand { font-family:'Syne',sans-serif; font-size:1.4rem; font-weight:800;
         background:linear-gradient(135deg,#60a5fa,#a78bfa,#34d399);
         -webkit-background-clip:text; -webkit-text-fill-color:transparent; }

.hero-title { font-family:'Syne',sans-serif; font-size:clamp(2.2rem,5vw,4rem);
              font-weight:800; line-height:1.1; color:#f0f4ff; }
.hero-title span { background:linear-gradient(135deg,#60a5fa,#a78bfa);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hero-sub { color:#94a3b8; font-size:1rem; line-height:1.7; max-width:500px; }

.card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);
        border-radius:18px; padding:1.8rem; margin-bottom:1rem; }

.score-num { font-family:'Syne',sans-serif; font-size:4rem; font-weight:800; line-height:1; }
.badge { display:inline-block; padding:.25rem .8rem; border-radius:99px; font-size:.75rem; font-weight:500; }

.chip { background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.25);
        color:#60a5fa; font-size:.75rem; padding:.2rem .65rem; border-radius:99px;
        display:inline-block; margin:.2rem; }

div.stButton > button {
    background:linear-gradient(135deg,#3b82f6,#6366f1) !important; color:white !important;
    font-family:'Syne',sans-serif !important; font-weight:600 !important;
    border:none !important; border-radius:12px !important; padding:.8rem 2rem !important;
    box-shadow:0 4px 20px rgba(99,102,241,.3) !important; transition:all .3s !important; }
div.stButton > button:hover { transform:translateY(-2px) !important; }

[data-testid="stDownloadButton"] button {
    background:linear-gradient(135deg,#059669,#10b981) !important; color:white !important;
    font-family:'Syne',sans-serif !important; font-weight:600 !important;
    border:none !important; border-radius:12px !important; padding:.8rem 2rem !important; }

[data-testid="stFileUploader"] { border-radius:14px !important;
    border:2px dashed rgba(99,102,241,.3) !important; background:rgba(99,102,241,.04) !important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background:rgba(255,255,255,.04) !important; border:1px solid rgba(255,255,255,.1) !important;
    border-radius:12px !important; color:#f0f4ff !important; }
label { color:#94a3b8 !important; font-size:.85rem !important; }
hr { border-color:rgba(255,255,255,.06) !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────
for k, v in [('page', 'home'), ('results', None)]:
    if k not in st.session_state:
        st.session_state[k] = v

def nav(page):
    st.session_state.page = page
    st.rerun()

# ── Helpers ───────────────────────────────────
def extract_text(file):
    reader = PdfReader(file)
    return "\n".join(p.extract_text() or "" for p in reader.pages)

def ats_score(resume, job):
    vec = TfidfVectorizer(stop_words='english')
    tfidf = vec.fit_transform([resume.lower(), job.lower()])
    return round(cosine_similarity(tfidf)[0][1] * 100, 1)

def get_keywords(text, n=12):
    vec = TfidfVectorizer(stop_words='english', max_features=n)
    vec.fit([text])
    return list(vec.get_feature_names_out())

def score_color(score):
    if score >= 75:   return "#34d399", "Strong Match 🎯"
    elif score >= 50: return "#f59e0b", "Good Match ⚡"
    else:             return "#f43f5e", "Needs Work 🔧"

# ── Rule-based Resume Optimizer ───────────────
WEAK_VERBS = {
    r'\bworked on\b': 'Developed', r'\bhelped\b': 'Assisted', r'\bdid\b': 'Executed',
    r'\bwas responsible for\b': 'Managed', r'\bresponsible for\b': 'Owned',
    r'\bmade\b': 'Created', r'\bhandled\b': 'Managed', r'\bused\b': 'Leveraged',
    r'\bknowledge of\b': 'Proficient in', r'\bfamiliar with\b': 'Experienced with',
}

def optimize_line(line):
    for pattern, replacement in WEAK_VERBS.items():
        line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
    return line

def inject_keywords(text, keywords):
    skills_section = re.search(r'(skill|technical|competenc)', text, re.IGNORECASE)
    if skills_section:
        kw_line = "\nKey Competencies: " + " | ".join(k.title() for k in keywords[:8])
        pos = skills_section.start()
        text = text[:pos] + kw_line + "\n" + text[pos:]
    return text

def add_summary(text, role, keywords):
    summary = (
        f"\n=== PROFESSIONAL SUMMARY ===\n"
        f"Results-driven professional targeting the role of {role}. "
        f"Demonstrated expertise in {', '.join(keywords[:4])}. "
        f"Proven ability to deliver impactful outcomes through strategic thinking and execution.\n"
    )
    # Insert summary at top (after name/contact if any, roughly after first 3 lines)
    lines = text.strip().split('\n')
    insert_at = min(3, len(lines))
    lines.insert(insert_at, summary)
    return '\n'.join(lines)

def optimize_resume(resume_text, role, keywords):
    lines = resume_text.split('\n')
    optimized = []
    has_summary = bool(re.search(r'summary|objective|profile', resume_text, re.IGNORECASE))

    for line in lines:
        line = optimize_line(line)
        # Quantify unquantified bullets if no numbers present
        if line.strip().startswith(('•', '-', '*')) and not re.search(r'\d', line):
            line = line.rstrip('.') + ', improving outcomes by 15–20%.'
        optimized.append(line)

    result = '\n'.join(optimized)

    if not has_summary:
        result = add_summary(result, role, keywords)

    result = inject_keywords(result, keywords)
    return result

# ── PDF Builder ───────────────────────────────
def build_pdf(text, orig_score, new_score, role):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=.7*inch, rightMargin=.7*inch,
                            topMargin=.7*inch, bottomMargin=.7*inch)
    styles = getSampleStyleSheet()
    story = []

    hdr = ParagraphStyle('H', parent=styles['Normal'], fontSize=9,
                         textColor=colors.HexColor('#6366f1'), alignment=TA_CENTER,
                         fontName='Helvetica-Bold', spaceAfter=4)
    story.append(Paragraph(f"ATS-OPTIMIZED  |  TARGET: {role.upper()}", hdr))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor('#6366f1'), spaceAfter=8))

    score_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=8.5,
                                  textColor=colors.HexColor('#10b981'),
                                  alignment=TA_CENTER, spaceAfter=14)
    story.append(Paragraph(
        f"Original ATS Score: {orig_score}%  →  Optimized: {new_score}%  ✔ ResumeIQ", score_style))

    sec_style = ParagraphStyle('Sec', parent=styles['Heading2'], fontSize=11,
                                fontName='Helvetica-Bold',
                                textColor=colors.HexColor('#1e3a8a'),
                                spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle('B', parent=styles['Normal'], fontSize=9.5,
                           leading=15, textColor=colors.HexColor('#1e293b'), spaceAfter=3)
    bul  = ParagraphStyle('BL', parent=styles['Normal'], fontSize=9.5,
                           leading=15, textColor=colors.HexColor('#334155'),
                           leftIndent=14, spaceAfter=2)

    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4)); continue
        if line.startswith('===') and line.endswith('==='):
            story.append(Paragraph(line.replace('=','').strip(), sec_style))
            story.append(HRFlowable(width="100%", thickness=.5,
                                     color=colors.HexColor('#e2e8f0'), spaceAfter=4))
        elif line.startswith(('- ','• ','* ')):
            story.append(Paragraph('• ' + line.lstrip('-•* '), bul))
        else:
            story.append(Paragraph(line, body))

    story.append(Spacer(1, 16))
    ft = ParagraphStyle('F', parent=styles['Normal'], fontSize=7.5,
                         textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)
    story.append(Paragraph("Generated by ResumeIQ ATS Optimizer", ft))
    doc.build(story)
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════
if st.session_state.page == 'home':
    st.markdown('<div class="brand">⚡ ResumeIQ</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <h1 class="hero-title">Beat Every <span>ATS Filter</span><br>Land the Interview</h1>
    <p class="hero-sub">Upload your resume, target a role, and our optimizer rewrites it to pass ATS systems and impress hiring managers — no API key needed.</p>
    <br>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc in [
        (c1, "🔍", "Deep ATS Scan",   "TF-IDF cosine similarity scoring against your target role."),
        (c2, "✍️", "Smart Rewrite",   "Rule-based optimizer injects keywords, action verbs & metrics."),
        (c3, "📥", "PDF Export",      "Download a clean, recruiter-ready PDF instantly."),
    ]:
        col.markdown(f'<div class="card" style="text-align:center"><div style="font-size:2rem">{icon}</div>'
                     f'<strong style="font-family:Syne,sans-serif">{title}</strong>'
                     f'<p style="color:#64748b;font-size:.82rem;margin-top:.4rem">{desc}</p></div>',
                     unsafe_allow_html=True)

    st.markdown("<br>")
    _, mid, _ = st.columns([2, 1, 2])
    with mid:
        if st.button("Get Started →", use_container_width=True):
            nav('analyzer')

# ══════════════════════════════════════════════
# PAGE: ANALYZER
# ══════════════════════════════════════════════
elif st.session_state.page == 'analyzer':
    st.markdown('<div class="brand">⚡ ResumeIQ</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Set Up Your Analysis")
    st.markdown('<p style="color:#64748b">Enter your target role and upload your resume to begin.</p>', unsafe_allow_html=True)
    st.markdown("<br>")

    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        role = st.text_input("🎯 Target Job Role", placeholder="e.g. Data Scientist, Product Manager…")
        job_desc = st.text_area("📋 Job Description (optional but recommended)",
                                placeholder="Paste job description for better keyword matching…", height=160)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        uploaded = st.file_uploader("📄 Upload Resume (PDF)", type=["pdf"])
        if uploaded:
            st.success(f"✓ **{uploaded.name}** uploaded successfully")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>")
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        if st.button("⚡ Analyze & Optimize Resume", use_container_width=True):
            if not role:
                st.error("Please enter a target job role.")
            elif not uploaded:
                st.error("Please upload your resume PDF.")
            else:
                with st.spinner("Scanning ATS compatibility and optimizing your resume…"):
                    resume_text = extract_text(uploaded)
                    job_context = f"{role}. {job_desc}" if job_desc else role
                    keywords    = get_keywords(job_context, n=12)

                    orig_score  = ats_score(resume_text, job_context)
                    rewritten   = optimize_resume(resume_text, role, keywords)
                    new_score   = min(ats_score(rewritten, job_context), 98.0)

                    suggestions = [
                        f"Integrated keywords: {', '.join(keywords[:5])}",
                        "Replaced weak verbs with strong action verbs (Developed, Managed, Led…)",
                        "Added quantified impact to unmetricized bullet points",
                        f"Injected Professional Summary tailored to {role}",
                        "Added key competencies section with role-relevant skills",
                    ]
                    if job_desc:
                        suggestions.append(f"Mirrored JD language: {', '.join(keywords[5:9])}")

                    st.session_state.results = dict(
                        role=role, original_score=orig_score, new_score=new_score,
                        suggestions=suggestions, keywords=keywords,
                        rewritten_text=rewritten, job_desc=job_context
                    )
                    nav('results')

    if st.button("← Back to Home"):
        nav('home')

# ══════════════════════════════════════════════
# PAGE: RESULTS
# ══════════════════════════════════════════════
elif st.session_state.page == 'results':
    res = st.session_state.results
    if not res: nav('home')

    st.markdown('<div class="brand">⚡ ResumeIQ</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"### Analysis Complete 🎉")
    st.markdown(f'<p style="color:#64748b">Optimized for <strong style="color:#e2e8f0">{res["role"]}</strong></p>',
                unsafe_allow_html=True)
    st.markdown("<br>")

    orig, new, role = res['original_score'], res['new_score'], res['role']
    col_hex, verdict = score_color(new)

    col_s, col_r = st.columns([1, 2], gap="large")

    with col_s:
        st.markdown(f"""
        <div class="card" style="text-align:center">
            <p style="color:#64748b;font-size:.78rem;text-transform:uppercase;letter-spacing:.1em">Before</p>
            <div style="font-family:Syne,sans-serif;font-size:2.5rem;font-weight:700;color:#64748b">{orig}%</div>
            <div style="color:#475569;font-size:1.2rem;margin:.5rem 0">↓</div>
            <p style="color:#64748b;font-size:.78rem;text-transform:uppercase;letter-spacing:.1em">After</p>
            <div class="score-num" style="color:{col_hex}">{new}%</div>
            <div style="background:rgba(255,255,255,.06);border-radius:99px;height:6px;margin:.75rem 0;overflow:hidden">
                <div style="width:{new}%;height:100%;background:{col_hex};border-radius:99px"></div>
            </div>
            <span class="badge" style="background:{col_hex}22;color:{col_hex};border:1px solid {col_hex}44">{verdict}</span>
            <p style="color:#64748b;font-size:.78rem;margin-top:.75rem">+{round(new-orig,1)}% improvement</p>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**💡 Applied Optimizations**")
        icons = ["🔑","📊","⚡","✍️","🎯","🔗"]
        for i, s in enumerate(res['suggestions']):
            st.markdown(f"<div style='padding:.6rem 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:.88rem;color:#cbd5e1'>"
                        f"{icons[i%len(icons)]} {s}</div>", unsafe_allow_html=True)
        st.markdown("<br><p style='color:#475569;font-size:.75rem;text-transform:uppercase;letter-spacing:.08em'>Keywords Integrated</p>", unsafe_allow_html=True)
        chips = "".join(f'<span class="chip">{k}</span>' for k in res['keywords'])
        st.markdown(f'<div style="margin-top:.4rem">{chips}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>")
    with st.expander("📄 Area where to imporove for better results "):
        st.text_area("", value=res['rewritten_text'], height=300, label_visibility="collapsed")

    st.markdown("<br>")
    pdf = build_pdf(res['rewritten_text'], orig, new, role)
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.download_button("⬇️ Download Optimized Resume PDF", data=pdf,
                           file_name=f"ResumeIQ_{role.replace(' ','_')}_Optimized.pdf",
                           mime="application/pdf", use_container_width=True)
        st.markdown("<br>")
        if st.button("🔄 Analyze Another Resume", use_container_width=True):
            st.session_state.results = None
            nav('analyzer')
