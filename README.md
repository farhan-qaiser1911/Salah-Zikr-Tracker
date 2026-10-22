# 🕌 AI-Powered Salah & Zikr Tracker

A simple, modern, Islamic-inspired dashboard designed to help users track their five daily obligatory Salah prayers, count daily Zikr, monitor consistency streaks, and obtain personalized, nonjudgmental spiritual habit insights powered by the official **Google Gemini API**.

---

## 🌟 Key Features

1. **Clean Islamic Dashboard:**
   - Visual stats for today's Salah completion and Zikr progress.
   - Active daily streak tracking.
   - Weekly bar charts showing prayer consistency across days.
   - Encouragement messages tailored dynamically to actual logged data.

2. **Salah Tracker:**
   - Dedicated tracking for Fajr, Dhuhr, Asr, Maghrib, and Isha.
   - Explicit distinction between **Completed**, **Missed**, and **Unrecorded** prayers.
   - Future or unrecorded prayers are never automatically marked as missed.
   - Capability to edit or reset daily prayer statuses.

3. **Zikr Counter:**
   - Preset phrases (*SubhanAllah*, *Alhamdulillah*, *Allahu Akbar*, *Astaghfirullah*, *Durood Sharif*).
   - Support for custom Zikr entry creation.
   - Large increment (+1), decrement (-1 without negative values), and individual phrase reset buttons.
   - Custom daily overall Zikr target setting.

4. **AI Spiritual Habit Assistant (Optional):**
   - Integrates Google's `gemini-3.8-flash` model using the official `google-genai` SDK.
   - Provides gentle, habit-focused analysis based on actual session stats.
   - Operates safely without fabricating religious citations, Hadiths, or rulings.
   - Core app functions remain 100% operational even without an API key.

5. **Session Data Privacy:**
   - Uses Python primitives and Streamlit `st.session_state`.
   - Zero database, Pandas, CSV, or external tracking dependencies.

---

## 📋 Requirements & Dependencies

- **Python 3.9+**
- **Streamlit**
- **google-genai** (Official Google GenAI SDK)

---

## 🚀 Quickstart & Launch Instructions

### 1. Clone or Download Project
Place `app.py`, `readme.md`, and `requirements.txt` into a single folder.

### 2. Create Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate# Salah-Zikr-Tracker
