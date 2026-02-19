import streamlit as st
from openai import OpenAI

# 1. AUTH & SETUP
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(
    page_title="Cheer Dad Translator",
    page_icon="📣",
    initial_sidebar_state="collapsed"
)

# --- CLEAN UI FIX ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 2. BRANDING & HEADER
st.title("📣 Cheer Dad Translator 🏈")
st.subheader("Understand your cheerleader - in sports terms you already know.")

# 3. USAGE & ACCESS LOGIC
query_params = st.query_params
is_paid = query_params.get("paid") == "true"

if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0

# 4. MAIN INTERFACE
sport = st.selectbox(
    "Translate Cheer Talk to:",
    ["NFL Football", "NBA Basketball", "MLB Baseball", "PGA Golf", "Soccer"]
)

audio_file = st.audio_input("Record her recap")

# 5. TRANSLATION LOGIC
if audio_file:
    # Allow translation if they have paid OR have free uses left
    if is_paid or st.session_state.usage_count < 3:
        with st.spinner("Breaking down the film..."):
            # Fix for Whisper file detection
            audio_file.name = "record.wav" 

            # A. Transcribe
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            
            # B. AI Translation
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a hardcore, slightly rowdy {sport} fan. Translate cheerleading news into {sport} lingo. Use high-stakes sports terminology. Talk like a buddy at a sports bar."},
                    {"role": "user", "content": transcript.text}
                ]
            )
            
            st.session_state.usage_count += 1
            
            # C. Display Result
            st.success(f"### {sport} Post-Game Analysis:")
            st.write(response.choices[0].message.content)
            
            if is_paid:
                st.caption("✅ MVP All-Access Active")
            
            # Email capture for the first free use (only for non-paid users)
            if not is_paid and st.session_state.usage_count == 1:
                st.info("Want to stay up-to-date with CheerDad App? Enter your email for season updates:")
                st.text_input("Email Address", key="user_email")
    else:
        st.warning("⚠️ Play clock's at zero! You've used your 3 free translations.")
        st.write("### Support a Fellow Coach")
        st.write("""
            This app is funded by a Dad/Cheer coach. If you're enjoying it, 
            grab a **Season Pass** to help cover the AI costs and keep 
            this tool alive for the community!
        """)

# 6. MONETIZATION (Only show if NOT paid)
if not is_paid:
    st.divider()
    st.markdown("### 🏆 Stay in the Game")
    st.write("Love the app? Support the developer and get unlimited translations.")
    
    st.info("⭐ Most dads choose All-Access during competition season")
    
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Monthly Pass ($4.99/mo)", "https://buy.stripe.com/3cIeV59iP6SAfeI9zs7AI03")
        st.caption("30 Days of Unlimited Translations")
    with col2:
        st.link_button("All-Access Championship Pass ($14.99/yr)", "https://buy.stripe.com/bJecMXgLh7WEc2wdPI7AI05")
        st.caption("One Year: Covers every competition & practice")

# 7. FOOTER & LEGAL
st.divider()

# Footer + legal (Centered and original tech-style)
footer_html = """
<div style="text-align: center; font-family: sans-serif;">
    <p style="color: #888888; font-size: 14px; margin-bottom: 2px;">
        Powered by <a href="https://cheerconnect.app" target="_blank" style="text-decoration: none; color: white; font-weight: bold;">CheerConnect</a>
    </p>
    <p style="font-size: 13px; color: #BBBBBB; margin-bottom: 15px;">
        Coaches & Gym Owners: This was built for fun — CheerConnect was built for your business. 
        <br>
        <a href="https://cheerconnect.app" target="_blank" style="color: #55aaff;">Learn More</a>
    </p>
    <p style="font-size: 10px; color: #666666; line-height: 1.4;">
        © 2026 Cheer Dad Translator. All rights reserved.<br>
        <a href="https://docs.google.com/document/d/1z_ffg-GPW2M_pdwdZ3qIl-yLxbw1ajxU7Hvmn7NUaVc/edit?usp=sharing" target="_blank" style="color: #666666;">Privacy Policy</a> | 
        <a href="https://docs.google.com/document/d/1z_ffg-GPW2M_pdwdZ3qIl-yLxbw1ajxU7Hvmn7NUaVc/edit?usp=sharing" target="_blank" style="color: #666666;">Terms of Service</a><br>
        <span style="font-style: italic; opacity: 0.6;">Not affiliated with any cheerleading organization. For entertainment purposes only.</span>
    </p>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)



