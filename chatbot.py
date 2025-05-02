"""
TalentScout Hiring Assistant Chatbot

This module provides the core functionality for the TalentScout Hiring Assistant,
a chatbot that helps in the initial screening of tech candidates.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine OpenAI SDK version and import appropriately
try:
    from openai import OpenAI
    USING_NEW_SDK = True
    logger.info("Using new OpenAI SDK")
except ImportError:
    import openai
    USING_NEW_SDK = False
    logger.info("Using legacy OpenAI SDK")


class TalentScoutBot:
    """
    Hiring Assistant chatbot for TalentScout recruitment agency.

    This class handles the conversation flow, information gathering,
    and technical question generation for candidate screening.
    """

    def __init__(self):
        """Initialize the TalentScout bot with default settings."""
        # Set up OpenAI client
        if USING_NEW_SDK:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            openai.api_key = os.getenv("OPENAI_API_KEY")

        # Initialize conversation state
        self.current_stage = "greeting"
        self.candidate_info = {
            "name": None,
            "email": None,
            "phone": None,
            "experience": None,
            "position": None,
            "location": None,
            "tech_stack": []
        }

        # Define conversation stages
        self.stages = [
            "greeting",
            "name",
            "contact_info",
            "experience",
            "position",
            "location",
            "tech_stack",
            "technical_questions",
            "closing"
        ]

        logger.info("TalentScoutBot initialized")

    def get_greeting(self) -> str:
        """Generate initial greeting message."""
        return """
        Hello! I'm the TalentScout Hiring Assistant. 👋

        I'm here to help with your initial screening process for tech positions.
        I'll ask you a few questions about your background and technical skills.

        Let's start with your name. What is your full name?
        """

    def process_message(self, user_message: str, message_history: List[Dict[str, str]],
                      candidate_info: Dict[str, Any], conversation_stage: str) -> str:
        """
        Process incoming user message and generate a response.

        Args:
            user_message: The message from the user
            message_history: Previous messages in the conversation
            candidate_info: Dictionary containing candidate information
            conversation_stage: Current stage of the conversation

        Returns:
            str: Response from the bot
        """
        # Update internal state
        self.candidate_info = candidate_info
        self.current_stage = conversation_stage

        logger.info(f"Processing message in stage: {self.current_stage}")

        # Check for exit keywords
        if self._is_exit_request(user_message):
            self.current_stage = "closing"
            return self._generate_closing_message()

        # Process message based on current stage
        if self.current_stage == "greeting" or self.current_stage == "name":
            self._extract_name(user_message)
            if self.candidate_info["name"]:
                self.current_stage = "contact_info"
                return self._generate_contact_request_message()
            else:
                return "I didn't quite catch your name. Could you please provide your full name?"

        elif self.current_stage == "contact_info":
            self._extract_contact_info(user_message)
            if self.candidate_info["email"] and self.candidate_info["phone"]:
                self.current_stage = "experience"
                return self._generate_experience_request_message()
            else:
                missing = []
                if not self.candidate_info["email"]:
                    missing.append("email address")
                if not self.candidate_info["phone"]:
                    missing.append("phone number")
                return f"I still need your {' and '.join(missing)}. Could you provide that information?"

        elif self.current_stage == "experience":
            self._extract_experience(user_message)
            self.current_stage = "position"
            return self._generate_position_request_message()

        elif self.current_stage == "position":
            self._extract_position(user_message)
            self.current_stage = "location"
            return self._generate_location_request_message()

        elif self.current_stage == "location":
            self._extract_location(user_message)
            self.current_stage = "tech_stack"
            return self._generate_tech_stack_request_message()

        elif self.current_stage == "tech_stack":
            self._extract_tech_stack(user_message)
            self.current_stage = "technical_questions"
            return self._generate_technical_questions()

        elif self.current_stage == "technical_questions":
            # After receiving answers to technical questions, we move to closing
            self.current_stage = "closing"
            return self._generate_closing_message()

        # Default response using LLM
        return self._generate_llm_response(user_message, message_history)

    def _is_exit_request(self, message: str) -> bool:
        """Check if user wants to end the conversation."""
        exit_keywords = ["exit", "quit", "goodbye", "bye", "end", "stop"]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in exit_keywords)

    def _extract_name(self, message: str) -> None:
        """Extract name from user message."""
        # Simple implementation - in a real app, use LLM or better NLP
        # Filter out common bot-addressing terms
        filtered_message = re.sub(r'\b(hi|hello|hey|my name is|i am|i\'m)\b', '', message, flags=re.IGNORECASE)
        name = filtered_message.strip()

        # Only update if we got something meaningful
        if name and len(name) > 1:
            self.candidate_info["name"] = name
            logger.info(f"Extracted name: {name}")

    def _extract_contact_info(self, message: str) -> None:
        """Extract email and phone from user message."""
        # Email extraction with regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, message)
        if email_match:
            self.candidate_info["email"] = email_match.group()
            logger.info(f"Extracted email: {email_match.group()}")

        # Phone extraction with regex
        # This handles various formats like: (123) 456-7890, 123-456-7890, 123.456.7890, etc.
        phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phone_match = re.search(phone_pattern, message)
        if phone_match:
            self.candidate_info["phone"] = phone_match.group()
            logger.info(f"Extracted phone: {phone_match.group()}")

    def _extract_experience(self, message: str) -> None:
        """Extract years of experience from user message."""
        # Try to find a number followed by years/yrs
        experience_pattern = r'\b(\d+)\s*(years?|yrs?)\b'
        experience_match = re.search(experience_pattern, message, re.IGNORECASE)

        if experience_match:
            self.candidate_info["experience"] = experience_match.group(1)
            logger.info(f"Extracted experience: {experience_match.group(1)} years")
        else:
            # If no clear number pattern, just save the whole response
            self.candidate_info["experience"] = message.strip()
            logger.info(f"Saved experience response: {message.strip()}")

    def _extract_position(self, message: str) -> None:
        """Extract desired position from user message."""
        self.candidate_info["position"] = message.strip()
        logger.info(f"Saved position: {message.strip()}")

    def _extract_location(self, message: str) -> None:
        """Extract location from user message."""
        self.candidate_info["location"] = message.strip()
        logger.info(f"Saved location: {message.strip()}")

    def _extract_tech_stack(self, message: str) -> None:
        """Extract tech stack from user message."""
        # Common technologies to look for
        tech_keywords = [
            # Languages
            "python", "java", "javascript", "typescript", "c#", "c++", "ruby", "go", "rust", "php", "swift", "kotlin",
            # Frontend
            "react", "angular", "vue", "svelte", "html", "css", "sass", "bootstrap", "tailwind", "jquery",
            # Backend
            "node", "express", "django", "flask", "spring", "asp.net", "laravel", "ruby on rails", "fastapi",
            # Databases
            "sql", "mysql", "postgresql", "mongodb", "firebase", "oracle", "sqlite", "redis", "elasticsearch",
            # Cloud
            "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "serverless", "lambda",
            # Other
            "machine learning", "ai", "devops", "git", "github", "gitlab", "ci/cd", "agile", "scrum"
        ]

        # First try to split by commas if the format seems to be a comma-separated list
        if "," in message:
            tech_list = [item.strip().lower() for item in message.split(',')]
            # Add other common separators
            tech_list = [item for sublist in [item.split('/') for item in tech_list] for item in sublist]
            tech_list = [item for sublist in [item.split('and') for item in tech_list] for item in sublist]
            tech_list = [item.strip() for item in tech_list if item.strip()]
            self.candidate_info["tech_stack"] = tech_list
            logger.info(f"Extracted tech stack (split method): {tech_list}")
        else:
            # If no commas, try to identify tech keywords
            message_lower = message.lower()
            found_tech = []

            for tech in tech_keywords:
                if tech in message_lower:
                    found_tech.append(tech)

            # If automated extraction found technologies, use them
            if found_tech:
                self.candidate_info["tech_stack"] = found_tech
                logger.info(f"Extracted tech stack (keyword method): {found_tech}")
            else:
                # Otherwise, use the LLM to extract tech stack
                self.candidate_info["tech_stack"] = self._extract_tech_stack_with_llm(message)
                logger.info(f"Extracted tech stack (LLM method): {self.candidate_info['tech_stack']}")

    def _extract_tech_stack_with_llm(self, message: str) -> List[str]:
        """Use LLM to extract tech stack items from a message."""
        prompt = [
            {
                "role": "system",
                "content": """
                You are a helpful assistant that extracts technology keywords from text.
                Output ONLY a Python list of technology names, with no other text or explanation.
                For example: ['Python', 'React', 'AWS', 'PostgreSQL']
                """
            },
            {
                "role": "user",
                "content": f"Extract technology keywords from this text: {message}"
            }
        ]

        try:
            if USING_NEW_SDK:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens=100,
                    temperature=0.3
                )
                tech_text = response.choices[0].message.content.strip()
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens=100,
                    temperature=0.3
                )
                tech_text = response.choices[0].message.content.strip()

            # Try to parse the response as a Python list
            try:
                # Clean up the response - remove quotes, brackets
                tech_text = tech_text.replace("'", '"')
                tech_list = json.loads(tech_text)
                if isinstance(tech_list, list):
                    return tech_list
                else:
                    return [message.strip()]
            except:
                # If parsing fails, fall back to basic comma splitting
                return [item.strip() for item in message.split(',') if item.strip()]

        except Exception as e:
            logger.error(f"Error extracting tech stack with LLM: {e}")
            return [message.strip()]

    def _generate_contact_request_message(self) -> str:
        """Generate message asking for contact information."""
        return f"Thanks, {self.candidate_info['name']}! Could you please provide your email address and phone number so we can contact you?"

    def _generate_experience_request_message(self) -> str:
        """Generate message asking about work experience."""
        return "Great! Now, how many years of experience do you have in the tech industry?"

    def _generate_position_request_message(self) -> str:
        """Generate message asking about desired position."""
        return f"Thank you! What position(s) are you interested in applying for at our company?"

    def _generate_location_request_message(self) -> str:
        """Generate message asking about current location."""
        return f"Great! Could you please tell me your current location?"

    def _generate_tech_stack_request_message(self) -> str:
        """Generate message asking about tech stack."""
        return f"""Thank you for that information! Now, I'd like to know about your technical skills.

Please list the programming languages, frameworks, databases, and tools that you are proficient in.
For example: Python, React, AWS, SQL, etc."""

    def _generate_technical_questions(self) -> str:
        """Generate technical questions based on the candidate's tech stack."""
        tech_stack = self.candidate_info["tech_stack"]

        if not tech_stack or len(tech_stack) == 0:
            return "I don't have information about your technical skills. Could you please share your tech stack with me?"

        # For each item in tech stack, we'll use the LLM to generate questions
        tech_stack_str = ", ".join(tech_stack)

        # We'll use the LLM to generate technical questions
        prompt = [
            {
                "role": "system",
                "content": f"""
                You are a technical interviewer for a recruitment agency.
                Generate 3-5 relevant technical questions to assess the candidate's proficiency in these technologies: {tech_stack_str}.

                The questions should:
                1. Be specific to the technologies mentioned
                2. Be appropriate for an initial screening
                3. Test both theoretical knowledge and practical experience
                4. Be challenging but not overly complex
                5. Be formatted as a numbered list

                DO NOT ask the candidate to write complete code or complex algorithms.
                """
            }
        ]

        try:
            if USING_NEW_SDK:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens=500,
                    temperature=0.7
                )
                questions = response.choices[0].message.content.strip()
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens=500,
                    temperature=0.7
                )
                questions = response.choices[0].message.content.strip()

            return f"""
            Based on your tech stack ({tech_stack_str}), I'd like to ask you a few technical questions:

            {questions}

            Please answer these questions to help us assess your technical proficiency.
            """
        except Exception as e:
            logger.error(f"Error generating technical questions: {e}")
            return f"""
            Based on your tech stack ({tech_stack_str}), I'd like to ask you some technical questions:

            1. Can you describe a challenging project where you used these technologies?
            2. What is your strongest technical skill, and how have you applied it in your work?
            3. How do you stay updated with the latest developments in these technologies?

            Please provide brief answers to these questions.
            """

    def _generate_closing_message(self) -> str:
        """Generate closing message."""
        name = self.candidate_info.get("name", "candidate")
        email = self.candidate_info.get("email", "your email")

        return f"""
        Thank you for taking the time to chat with me, {name}!

        I've collected your information for the initial screening process. Here's what I have:
        - Name: {self.candidate_info.get("name", "Not provided")}
        - Contact: {self.candidate_info.get("email", "Not provided")}
        - Experience: {self.candidate_info.get("experience", "Not provided")}
        - Position interest: {self.candidate_info.get("position", "Not provided")}
        - Location: {self.candidate_info.get("location", "Not provided")}
        - Tech stack: {", ".join(self.candidate_info.get("tech_stack", ["Not provided"]))}

        A TalentScout recruiter will review your details and get back to you soon via {email}.

        If you have any questions in the meantime, feel free to reach out to our recruitment team at recruitment@talentscout.example.com

        Have a great day!
        """

    def _generate_llm_response(self, user_message: str, message_history: List[Dict[str, str]]) -> str:
        """Generate response using LLM when a more contextual response is needed."""
        # Create prompt based on conversation history and stage
        prompt = self._create_prompt_for_stage(user_message, message_history)

        try:
            # Call LLM API using appropriate SDK version
            if USING_NEW_SDK:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens=300,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens=300,
                    temperature=0.7
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return "I apologize, but I'm having trouble generating a response. Could you please repeat that?"

    def _create_prompt_for_stage(self, user_message: str, message_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Create a prompt for the LLM based on current conversation stage."""
        # System message sets the context for the LLM
        system_message = {
            "role": "system",
            "content": f"""
            You are a hiring assistant for TalentScout, a recruitment agency specializing in technology placements.
            Your task is to conduct an initial screening of candidates by gathering information and asking relevant technical questions.

            Current conversation stage: {self.current_stage}
            Current candidate information: {self.candidate_info}

            Focus on gathering the information needed for the current stage and then move to the next stage.
            Be professional, friendly, and concise in your responses.
            Maintain the conversation in the context of a job application process.
            """
        }

        # Prepare conversation history for the prompt
        prompt_messages = [system_message]

        # Add relevant conversation history
        for message in message_history[-10:]:  # Use last 10 messages to avoid token limits
            prompt_messages.append({
                "role": message["role"],
                "content": message["content"]
            })

        # Add the current user message
        prompt_messages.append({
            "role": "user",
            "content": user_message
        })

        return prompt_messages


if __name__ == "__main__":
    # Simple test code to verify the chatbot works
    bot = TalentScoutBot()
    print(bot.get_greeting())