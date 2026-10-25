import streamlit as st
from agent import analyze, follow_up, to_markdown

st.set_page_config(page_title="Visual Investigation Agent", layout="wide")
st.title("Visual Investigation Agent")

up = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "webp"])
search = st.checkbox("Use web search for verification", value=False)

if up:
    st.image(up, width=400)
    if st.button("Analyze"):
        with st.spinner("Investigating..."):
            report, hist = analyze(up.getvalue(), up.type, search)
        st.session_state.report, st.session_state.hist = report, hist
        st.session_state.chat = []

if "report" in st.session_state:
    st.markdown(to_markdown(st.session_state.report))
    st.divider()
    st.subheader("Ask follow-up questions")
    for role, msg in st.session_state.chat:
        st.chat_message(role).write(msg)
    q = st.chat_input("e.g. Why do you think this is from that period?")
    if q:
        st.chat_message("user").write(q)
        ans = follow_up(st.session_state.hist, q)
        st.chat_message("assistant").write(ans)
        st.session_state.chat += [("user", q), ("assistant", ans)]