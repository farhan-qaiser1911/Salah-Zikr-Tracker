import os
import datetime
import streamlit as st

# Attempt to import the official google-genai SDK safely
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM CSS (Islamic-inspired Emerald/Cream Palette)
# ==============================================================================
st.set_page_config(
    page_title="Salah & Zikr Tracker",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Main Theme Variables */
    :root {
        --emerald-primary: #0D5C3A;
        --emerald-secondary: #137547;
        --cream-bg: #FDFBF7;
        --gold-accent: #D4AF37;
        --card-bg: #FFFFFF;
        --text-dark: #2C3E50;
    }

    /* Streamlit Background Customization */
    .stApp {
        background-color: var(--cream-bg);
        color: var(--text-dark);
    }

    /* Metric Card Styling */
    .metric-card {
        background-color: var(--card-bg);
        border: 1px solid #EAE6DF;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.03);
        text-align: center;
        margin-bottom: 12px;
    }
    .metric-card h4 {
        color: var(--emerald-primary);
        font-size: 1.1rem;
        margin-bottom: 8px;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--emerald-secondary);
    }
    .metric-card .subtext {
        font-size: 0.85rem;
        color: #6C757D;
        margin-top: 4px;
    }

    /* Custom Header */
    .header-banner {
        background: linear-gradient(135deg, #0D5C3A 0%, #137547 100%);
        color: white;
        padding: 24px;
        border-radius: 12px;
        border-bottom: 4px solid var(--gold-accent);
        margin-bottom: 25px;
    }
    .header-banner h1 {
        color: #FFFFFF !important;
        margin: 0;
        font-size: 2.2rem;
    }
    .header-banner p {
        color: #E2E8F0;
        margin: 5px 0 0 0;
    }

    /* Alert Banner for Temporary Data */
    .session-warning {
        background-color: #FFF9E6;
        border-left: 4px solid var(--gold-accent);
        color: #8A6D3B;
        padding: 10px 15px;
        border-radius: 6px;
        font-size: 0.88rem;
        margin-bottom: 20px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 2. DATA STRUCTURES & SESSION STATE MANAGEMENT
# ==============================================================================
PRAYER_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
DEFAULT_ZIKR_LIST = [
    "SubhanAllah",
    "Alhamdulillah",
    "Allahu Akbar",
    "Astaghfirullah",
    "Durood Sharif"
]


def init_session_state():
    """Initializes in-memory storage using st.session_state."""
    today_str = datetime.date.today().isoformat()

    # Track active selected date
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = today_str

    # Salah Records: { "YYYY-MM-DD": { "Fajr": "Completed" | "Missed" | "Unrecorded", ... } }
    if "salah_records" not in st.session_state:
        st.session_state.salah_records = {}

    # Ensure selected date exists in Salah records
    if st.session_state.selected_date not in st.session_state.salah_records:
        st.session_state.salah_records[st.session_state.selected_date] = {
            p: "Unrecorded" for p in PRAYER_NAMES
        }

    # Zikr Daily Counts: { "YYYY-MM-DD": { "SubhanAllah": 0, ... } }
    if "zikr_counts" not in st.session_state:
        st.session_state.zikr_counts = {}

    # Custom Zikr Entries list
    if "custom_zikr_list" not in st.session_state:
        st.session_state.custom_zikr_list = list(DEFAULT_ZIKR_LIST)

    # Zikr Daily Target
    if "zikr_target" not in st.session_state:
        st.session_state.zikr_target = 100

    # Ensure selected date exists in Zikr counts
    if st.session_state.selected_date not in st.session_state.zikr_counts:
        st.session_state.zikr_counts[st.session_state.selected_date] = {
            z: 0 for z in st.session_state.custom_zikr_list
        }


init_session_state()

# ==============================================================================
# 3. HELPER COMPUTATIONS & DATA LOGIC
# ==============================================================================
def get_salah_stats(date_str):
    """Computes daily Salah stats for a specific date."""
    records = st.session_state.salah_records.get(
        date_str, {p: "Unrecorded" for p in PRAYER_NAMES}
    )
    completed = sum(1 for status in records.values() if status == "Completed")
    missed = sum(1 for status in records.values() if status == "Missed")
    unrecorded = sum(1 for status in records.values() if status == "Unrecorded")
    pct = (completed / 5) * 100
    return {
        "completed": completed,
        "missed": missed,
        "unrecorded": unrecorded,
        "percentage": round(pct, 1)
    }


def get_daily_total_zikr(date_str):
    """Calculates total Zikr count across all types for a given date."""
    counts = st.session_state.zikr_counts.get(date_str, {})
    return sum(counts.values())


def calculate_streak():
    """Calculates consecutive days ending today where at least 1 prayer was completed."""
    today = datetime.date.today()
    streak = 0
    curr_date = today

    while True:
        d_str = curr_date.isoformat()
        if d_str in st.session_state.salah_records:
            stats = get_salah_stats(d_str)
            if stats["completed"] > 0:
                streak += 1
                curr_date -= datetime.timedelta(days=1)
            else:
                break
        else:
            break
    return streak


# ==============================================================================
# 4. GEMINI API INTEGRATION
# ==============================================================================
def get_gemini_client():
    """Retrieves GEMINI_API_KEY from env or Streamlit secrets and initializes Client."""
    if not GENAI_AVAILABLE:
        return None, "google-genai SDK is not installed."

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]

    if not api_key:
        return None, "API key not found. Please set GEMINI_API_KEY in environment or secrets."

    try:
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"Failed to initialize Gemini client: {str(e)}"


def call_gemini_assistant(prompt):
    """Sends prompt to gemini-3.8-flash model with graceful error handling."""
    client, err = get_gemini_client()
    if err:
        return f"⚠️ **AI Assistant Unavailable:** {err}"

    # Explicitly using model ID gemini-3.8-flash as required
    MODEL_ID = "gemini-3.8-flash"

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=(
                    "You are a supportive, respectful, nonjudgmental Islamic Spiritual Habit Assistant. "
                    "Your goal is to offer encouraging, practical habit-building advice based on actual user tracking data. "
                    "Never invent or quote Quranic verses, Hadith references, or religious rulings. "
                    "Do not claim authoritative religious guidance. Focus on habit-building strategies."
                )
            )
        )
        if response and response.text:
            return response.text
        else:
            return "⚠️ Received an empty response from the AI Assistant. Please try again."
    except Exception as e:
        return f"⚠️ **AI Generation Error:** Could not contact model `{MODEL_ID}`. Details: {str(e)}"


# ==============================================================================
# 5. NAVIGATION & SIDEBAR
# ==============================================================================
st.sidebar.image("https://img.icons8.com/color/96/000000/mosque.png", width=64)
st.sidebar.title("Navigation")

navigation_option = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Salah Tracker", "Zikr Counter", "History", "AI Assistant"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Active Date")
selected_date_obj = st.sidebar.date_input(
    "Select Date to Track/View",
    value=datetime.date.fromisoformat(st.session_state.selected_date),
    max_value=datetime.date.today()
)
st.session_state.selected_date = selected_date_obj.isoformat()

# Ensure record structure exists for chosen date
if st.session_state.selected_date not in st.session_state.salah_records:
    st.session_state.salah_records[st.session_state.selected_date] = {
        p: "Unrecorded" for p in PRAYER_NAMES
    }
if st.session_state.selected_date not in st.session_state.zikr_counts:
    st.session_state.zikr_counts[st.session_state.selected_date] = {
        z: 0 for z in st.session_state.custom_zikr_list
    }

st.sidebar.markdown("---")
st.sidebar.info("ℹ️ **Data Note:** All records are held temporary in active session memory.")

# Banner Header
st.markdown(
    f"""
    <div class="header-banner">
        <h1>🕌 AI-Powered Salah & Zikr Tracker</h1>
        <p>Active Session Date: <b>{st.session_state.selected_date}</b></p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="session-warning">
        <b>Session Storage Notice:</b> Data is retained strictly during your active browser session in memory. 
        Data will reset if the server restarts or the session expires. No persistent database is used.
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 6. VIEW 1: DASHBOARD
# ==============================================================================
if navigation_option == "Dashboard":
    st.header("📊 Daily Overview")

    curr_date = st.session_state.selected_date
    salah_stats = get_salah_stats(curr_date)
    total_zikr = get_daily_total_zikr(curr_date)
    target_zikr = st.session_state.zikr_target
    zikr_pct = min(100.0, round((total_zikr / target_zikr) * 100, 1)) if target_zikr > 0 else 0
    streak = calculate_streak()

    # Cards layout
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h4>Salah Progress</h4>
                <div class="value">{salah_stats['completed']} / 5</div>
                <div class="subtext">{salah_stats['percentage']}% Completed</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h4>Zikr Count</h4>
                <div class="value">{total_zikr}</div>
                <div class="subtext">Target: {target_zikr} ({zikr_pct}%)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <h4>Consistency Streak</h4>
                <div class="value">🔥 {streak} Days</div>
                <div class="subtext">Consecutive Days Active</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        unrec = salah_stats['unrecorded']
        missed = salah_stats['missed']
        st.markdown(
            f"""
            <div class="metric-card">
                <h4>Pending / Missed</h4>
                <div class="value">{unrec} Unrec | {missed} Missed</div>
                <div class="subtext">Obligatory Prayers</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("### 📈 Daily Progress Metrics")

    st.write("**Salah Completion Progress**")
    st.progress(salah_stats['percentage'] / 100.0)

    st.write("**Zikr Target Progress**")
    st.progress(min(1.0, total_zikr / target_zikr) if target_zikr > 0 else 0.0)

    st.markdown("---")
    st.markdown("### 📅 Weekly Activity Summary")

    # Generate recent 7 days chart data without using Pandas
    today_obj = datetime.date.fromisoformat(curr_date)
    last_7_days = [(today_obj - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    weekly_salah = [get_salah_stats(d)["completed"] for d in last_7_days]
    short_dates = [d[5:] for d in last_7_days]  # MM-DD format

    chart_data = {
        "Date": short_dates,
        "Completed Salah": weekly_salah
    }
    st.bar_chart(chart_data, x="Date", y="Completed Salah")

    st.markdown("---")
    st.markdown("### 💬 Daily Encouragement")

    # Dynamic encouragement based on actual progress
    if salah_stats['completed'] == 5:
        msg = "MashaAllah! You have completed all five prayers today. May your devotion bring peace and blessings."
    elif salah_stats['completed'] >= 3:
        msg = "Alhamdulillah for the prayers you have offered today. Keep striving to complete the remaining prayers!"
    elif salah_stats['completed'] > 0:
        msg = "You have taken positive steps today by fulfilling your prayers. Stay steady and turn to the next prayer with hope."
    else:
        msg = "Every moment offers a fresh beginning. Take a quiet breath and take the step to establish your prayer today."

    st.info(msg)


# ==============================================================================
# 7. VIEW 2: SALAH TRACKER
# ==============================================================================
elif navigation_option == "Salah Tracker":
    st.header("🕌 Daily Salah Tracker")
    st.write(f"Record or adjust your daily obligatory prayers for **{st.session_state.selected_date}**.")

    salah_today = st.session_state.salah_records[st.session_state.selected_date]

    col_main, col_summary = st.columns([2, 1])

    with col_main:
        for prayer in PRAYER_NAMES:
            current_status = salah_today.get(prayer, "Unrecorded")

            with st.container():
                c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
                c1.subheader(prayer)

                # Visual status indicator
                if current_status == "Completed":
                    c2.markdown("✅ **Completed**")
                elif current_status == "Missed":
                    c2.markdown("❌ **Missed**")
                else:
                    c2.markdown("⚪ **Unrecorded**")

                if c3.button(f"Mark Completed", key=f"btn_comp_{prayer}"):
                    st.session_state.salah_records[st.session_state.selected_date][prayer] = "Completed"
                    st.rerun()

                if c4.button(f"Mark Missed", key=f"btn_miss_{prayer}"):
                    st.session_state.salah_records[st.session_state.selected_date][prayer] = "Missed"
                    st.rerun()

            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    with col_summary:
        st.subheader("Daily Stats")
        stats = get_salah_stats(st.session_state.selected_date)

        st.metric("Completed Prayers", f"{stats['completed']} / 5")
        st.metric("Missed Prayers", f"{stats['missed']}")
        st.metric("Unrecorded Prayers", f"{stats['unrecorded']}")
        st.metric("Completion Rate", f"{stats['percentage']}%")

        if st.button("Reset Day's Salah Record"):
            st.session_state.salah_records[st.session_state.selected_date] = {
                p: "Unrecorded" for p in PRAYER_NAMES
            }
            st.success("Salah records reset for this date.")
            st.rerun()


# ==============================================================================
# 8. VIEW 3: ZIKR COUNTER
# ==============================================================================
elif navigation_option == "Zikr Counter":
    st.header("📿 Zikr Counter")
    st.write(f"Track daily remembrance for **{st.session_state.selected_date}**.")

    # Target settings
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        new_target = st.number_input(
            "Set Daily Zikr Target across all phrases:",
            min_value=1,
            value=st.session_state.zikr_target,
            step=10
        )
        st.session_state.zikr_target = new_target

    with col_t2:
        st.write("")
        st.write("")
        if st.button("Add Custom Zikr Phrase"):
            st.session_state.show_custom_modal = True

    # Form for custom Zikr addition
    if st.session_state.get("show_custom_modal", False):
        with st.form("add_custom_zikr_form"):
            custom_name = st.text_input("Enter Zikr Name (e.g. 'La ilaha illallah')")
            submit = st.form_submit_button("Add to List")
            if submit and custom_name.strip():
                clean_name = custom_name.strip()
                if clean_name not in st.session_state.custom_zikr_list:
                    st.session_state.custom_zikr_list.append(clean_name)
                    # Initialize count for active date
                    st.session_state.zikr_counts[st.session_state.selected_date][clean_name] = 0
                    st.success(f"Added '{clean_name}'!")
                st.session_state.show_custom_modal = False
                st.rerun()

    st.markdown("---")

    date_counts = st.session_state.zikr_counts[st.session_state.selected_date]

    # Render counter for each phrase
    for zikr in st.session_state.custom_zikr_list:
        curr_val = date_counts.get(zikr, 0)

        col_z1, col_z2, col_z3, col_z4 = st.columns([3, 1.5, 1.5, 1])

        col_z1.markdown(f"#### {zikr}")

        # Big counter button (+1)
        if col_z2.button(f"➕ Count ({curr_val})", key=f"inc_{zikr}", use_container_width=True):
            st.session_state.zikr_counts[st.session_state.selected_date][zikr] = curr_val + 1
            st.rerun()

        # Decrement button (-1)
        if col_z3.button("➖ Decrease", key=f"dec_{zikr}", use_container_width=True):
            if curr_val > 0:
                st.session_state.zikr_counts[st.session_state.selected_date][zikr] = curr_val - 1
                st.rerun()

        # Reset button for specific item
        if col_z4.button("🔄", key=f"rst_{zikr}", help=f"Reset {zikr} count"):
            st.session_state.zikr_counts[st.session_state.selected_date][zikr] = 0
            st.rerun()

        st.markdown("<hr style='margin: 4px 0;'>", unsafe_allow_html=True)

    # Overview Total
    total_zikr = get_daily_total_zikr(st.session_state.selected_date)
    rem = max(0, st.session_state.zikr_target - total_zikr)
    st.markdown(f"### Total Zikr Today: **{total_zikr}** / {st.session_state.zikr_target} (Remaining: {rem})")


# ==============================================================================
# 9. VIEW 4: HISTORY
# ==============================================================================
elif navigation_option == "History":
    st.header("📜 Session History Overview")
    st.write("Review recorded logs across active dates in your current browser session.")

    all_dates = sorted(list(set(
        list(st.session_state.salah_records.keys()) +
        list(st.session_state.zikr_counts.keys())
    )), reverse=True)

    if not all_dates:
        st.info("No recorded activity yet in this session.")
    else:
        history_table = []
        for d in all_dates:
            s_stats = get_salah_stats(d)
            z_total = get_daily_total_zikr(d)
            history_table.append({
                "Date": d,
                "Completed Prayers": f"{s_stats['completed']} / 5",
                "Missed Prayers": s_stats['missed'],
                "Unrecorded": s_stats['unrecorded'],
                "Total Zikr": z_total
            })

        st.table(history_table)


# ==============================================================================
# 10. VIEW 5: AI ASSISTANT
# ==============================================================================
elif navigation_option == "AI Assistant":
    st.header("🤖 AI Spiritual Habit Assistant")
    st.write("Get personalized, non-judgmental habit analysis and practical routine suggestions based on your logged records.")

    # Prepare actual session summary for AI analysis
    curr_date = st.session_state.selected_date
    s_stats = get_salah_stats(curr_date)
    z_total = get_daily_total_zikr(curr_date)
    streak = calculate_streak()

    summary_context = f"""
    Current Date: {curr_date}
    Salah Progress Today: {s_stats['completed']}/5 completed, {s_stats['missed']} missed, {s_stats['unrecorded']} unrecorded.
    Daily Total Zikr: {z_total} counts (Target: {st.session_state.zikr_target}).
    Current Streak: {streak} consecutive days.
    """

    st.markdown("### 🔍 Quick Actions")
    col_a1, col_a2 = st.columns(2)

    if col_a1.button("Analyze My Progress & Habits", use_container_width=True):
        prompt = f"""
        Analyze my actual tracking data for today and give me supportive advice:
        {summary_context}
        Please provide:
        1. Concise positive encouragement based on what I recorded.
        2. One manageable suggestion for building consistency in prayer or Zikr.
        """
        with st.spinner("Analyzing progress with Gemini AI..."):
            response = call_gemini_assistant(prompt)
            st.markdown("### 💡 AI Feedback")
            st.write(response)

    if col_a2.button("Suggest Realistic Zikr Routine", use_container_width=True):
        prompt = f"""
        Based on my recorded Zikr total of {z_total} today and target of {st.session_state.zikr_target},
        suggest a manageable, realistic daily Zikr routine broken down across the day.
        Keep advice practical and encouraging without asserting religious rulings or fake Hadith.
        """
        with st.spinner("Generating routine suggestion..."):
            response = call_gemini_assistant(prompt)
            st.markdown("### 📿 Suggested Routine")
            st.write(response)

    st.markdown("---")
    st.markdown("### 💬 Ask a Habit Building Question")
    user_query = st.text_input("Ask a question about establishing consistent worship habits:")

    if st.button("Ask Assistant") and user_query.strip():
        prompt = f"""
        User tracking context:
        {summary_context}

        User Question: {user_query}
        Provide a helpful, nonjudgmental, respectful answer focusing on habit formation techniques.
        """
        with st.spinner("Consulting AI Assistant..."):
            response = call_gemini_assistant(prompt)
            st.markdown("### 📝 Response")
            st.write(response)

# ==============================================================================
# FOOTER
# ==============================================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #7F8C8D; font-size: 0.85rem;'>"
    "AI-Powered Salah & Zikr Tracker • Built with Streamlit & Google Gemini API"
    "</div>",
    unsafe_allow_html=True
)
