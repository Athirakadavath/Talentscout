import streamlit as st
import os
from dotenv import load_dotenv
from chatbot import TalentScoutBot

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TalentScout Hiring Assistant",
    page_icon="👨‍💼",
    layout="centered",
)

def main():
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "candidate_info" not in st.session_state:
        st.session_state.candidate_info = {
            "name": None,
            "email": None,
            "phone": None,
            "experience": None,
            "position": None,
            "location": None,
            "tech_stack": []
        }

    if "conversation_stage" not in st.session_state:
        st.session_state.conversation_stage = "greeting"

    # Initialize chatbot
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = TalentScoutBot()

    # Display header
    st.title("TalentScout Hiring Assistant")
    st.markdown("Welcome to the initial screening process for TalentScout recruitment agency. Let's get to know you better!")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # If this is the first run, initialize with a greeting
    if len(st.session_state.messages) == 0:
        initial_greeting = st.session_state.chatbot.get_greeting()
        st.session_state.messages.append({"role": "assistant", "content": initial_greeting})
        with st.chat_message("assistant"):
            st.markdown(initial_greeting)

    # Get user input
    if user_input := st.chat_input("Type your response here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get bot response
        bot_response = st.session_state.chatbot.process_message(
            user_input,
            st.session_state.messages,
            st.session_state.candidate_info,
            st.session_state.conversation_stage
        )

        # Update conversation stage if needed
        if st.session_state.chatbot.current_stage != st.session_state.conversation_stage:
            st.session_state.conversation_stage = st.session_state.chatbot.current_stage

        # Update candidate info
        st.session_state.candidate_info = st.session_state.chatbot.candidate_info

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(bot_response)

if __name__ == "__main__":
    main()