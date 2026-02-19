import streamlit as st
from openai import OpenAI

# 1. AUTH & SETUP
# The key is pulled from Streamlit's secure secrets manager
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(
    page_title="Cheer Dad Translator",
    page_icon="📣",
    initial_sidebar_state="collapsed"
)

# 2. BRANDING & HEADER
st.title("📣 Cheer Dad Translator")
st.subheader("The Sideline Essential")

# 3. USAGE TRACKER
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0

# 4. MAIN INTERFACE
sport = st.selectbox(
    "Translate Cheer Talk to:",
    ["NFL Football", "NBA Basketball", "MLB Baseball", "PGA Golf", "Soccer"]
)

# Recording Widget
audio_file = st.audio_input("Record her recap")

# 5. TRANSLATION LOGIC (Indentation Fixed)
if audio_file:
    if st.session_state.usage_count < 3:
        with st.spinner("Breaking down the film..."):
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
            
            # Email capture for the first free use
            if st.session_state.usage_count == 1:
                st.info("Want the highlights? Enter your email for season updates:")
                st.text_input("Email Address", key="user_email")
    else:
        # This else now aligns perfectly with the usage_count check
        st.warning("⚠️ Play clock's at zero! You've used your 3 free translations.")
        st.write("Upgrade now to stay in the game for the rest of the season!")

# 6. MONETIZATION (Updated Product Names)
st.divider()
st.markdown("### 🏆 Stay in the Game")
st.write("Love the app? Support the developer and get unlimited translations.")

# Recommended Plan Highlight
st.info("⭐ **RECOMMENDED: All-Access Championship Pass** - Best value for the season!")

col1, col2 = st.columns(2)
with col1:
    # Use your Stripe Link for the Monthly Pass
    st.link_button("Monthly Pass ($4.99/mo)", "https://buy.stripe.com/3cIeV59iP6SAfeI9zs7AI03")
    st.caption("30 Days of Unlimited Translations")

with col2:
    # Use your Stripe Link for the Annual Pass
    st.link_button("All-Access Championship Pass ($14.99/yr)", "https://buy.stripe.com/bJecMXgLh7WEc2wdPI7AI05")
    st.caption("One Year: Covers every competition & practice")

# 7. FOOTER & LEGAL
st.divider()
st.markdown(
    """
    <div style="text-align: center;">
        <p style="color: grey; font-size: 14px;">Powered by <a href="https://cheerconnect.app" target="_blank" style="text-decoration: none; color: inherit;"><b>CheerConnect</b></a></p>
        <p style="font-size: 12px;">Coaches: Automate your team updates. <a href="https://cheerconnect.app" target="_blank">Learn More</a></p>
        <br>
        <p style="font-size: 10px; color: lightgrey;">
            © 2026 Cheer Dad Translator. All rights reserved.<br> 
            <a href="https://docs.google.com/document/d/1z_ffg-GPW2M_pdwdZ3qIl-yLxbw1ajxU7Hvmn7NUaVc/edit?usp=sharing" target="_blank">Privacy Policy</a> | 
            <a href="https://docs.google.com/document/d/1z_ffg-GPW2M_pdwdZ3qIl-yLxbw1ajxU7Hvmn7NUaVc/edit?usp=sharing" target="_blank">Terms of Service</a><br>
            <i>Not affiliated with any cheerleading organization. For entertainment purposes only.</i>
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)
