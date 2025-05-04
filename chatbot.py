"""
TalentScout Hiring Assistant Chatbot

This module provides the core functionality for the TalentScout Hiring Assistant,
a chatbot that helps in the initial screening of tech candidates.
Enhanced with database storage capabilities.
"""

import os
import re
import json
import logging
import requests
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CandidateDatabase:
    """Database handler for storing candidate information"""
    def __init__(self, db_path="candidates.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create candidates table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            experience TEXT,
            position TEXT,
            location TEXT,
            tech_stack TEXT,
            application_time TIMESTAMP,
            status TEXT DEFAULT 'new',
            conversation_history TEXT,
            notes TEXT
        )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def save_candidate(self, candidate_info, conversation_history=None):
        """Save candidate information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Convert tech_stack list to JSON string
        if isinstance(candidate_info.get('tech_stack', []), list):
            tech_stack_json = json.dumps(candidate_info.get('tech_stack', []))
        else:
            tech_stack_json = json.dumps([])

        # Convert conversation history to JSON string
        if conversation_history:
            conv_history_json = json.dumps(conversation_history)
        else:
            conv_history_json = json.dumps([])

        try:
            cursor.execute('''
            INSERT INTO candidates
            (name, email, phone, experience, position, location, tech_stack,
            application_time, conversation_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                candidate_info.get('name', ''),
                candidate_info.get('email', ''),
                candidate_info.get('phone', ''),
                candidate_info.get('experience', ''),
                candidate_info.get('position', ''),
                candidate_info.get('location', ''),
                tech_stack_json,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                conv_history_json
            ))

            conn.commit()
            candidate_id = cursor.lastrowid
            logger.info(f"Saved candidate with ID {candidate_id}")
            result = {"success": True, "candidate_id": candidate_id}
        except sqlite3.IntegrityError as e:
            # Handle duplicate email
            logger.error(f"Database error saving candidate: {e}")
            result = {"success": False, "error": "Candidate with this email already exists"}
        finally:
            conn.close()

        return result

    def get_candidate_by_email(self, email):
        """Retrieve candidate by email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM candidates WHERE email = ?", (email,))
        result = cursor.fetchone()

        conn.close()

        if result:
            # Parse JSON fields
            candidate = dict(result)
            candidate['tech_stack'] = json.loads(candidate['tech_stack'])
            candidate['conversation_history'] = json.loads(candidate['conversation_history'])
            return candidate
        return None

    def get_candidate_by_id(self, candidate_id):
        """Retrieve candidate by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
        result = cursor.fetchone()

        conn.close()

        if result:
            # Parse JSON fields
            candidate = dict(result)
            candidate['tech_stack'] = json.loads(candidate['tech_stack'])
            candidate['conversation_history'] = json.loads(candidate['conversation_history'])
            return candidate
        return None

    def update_candidate_status(self, candidate_id, status, notes=None):
        """Update candidate status and notes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if notes:
            cursor.execute(
                "UPDATE candidates SET status = ?, notes = ? WHERE id = ?",
                (status, notes, candidate_id)
            )
        else:
            cursor.execute(
                "UPDATE candidates SET status = ? WHERE id = ?",
                (status, candidate_id)
            )

        conn.commit()
        conn.close()
        logger.info(f"Updated candidate {candidate_id} status to {status}")
        return True

    def list_recent_candidates(self, limit=50):
        """List recent candidates"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, name, email, position, application_time, status
        FROM candidates ORDER BY application_time DESC LIMIT ?
        ''', (limit,))

        candidates = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return candidates


class TalentScoutBot:
    """
    Hiring Assistant chatbot for TalentScout recruitment agency.

    This class handles the conversation flow, information gathering,
    and technical question generation for candidate screening.
    """

    def __init__(self):
        """Initialize the TalentScout bot with default settings."""
        # Set up Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("No Gemini API key found in environment variables")
            self.api_working = False
        else:
            self.api_working = True
            logger.info("Gemini API initialized")

        # Initialize database
        self.db = CandidateDatabase()

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

        # Tech stack categories for better question generation
        self.tech_categories = {
            "languages": [
                "python", "java", "javascript", "typescript", "c#", "c++", "ruby",
                "go", "rust", "php", "swift", "kotlin", "scala", "perl", "haskell"
            ],
            "frontend": [
                "react", "angular", "vue", "svelte", "html", "css", "sass", "less",
                "bootstrap", "tailwind", "jquery", "webpack", "next.js", "gatsby"
            ],
            "backend": [
                "node", "express", "django", "flask", "spring", "asp.net", "laravel",
                "ruby on rails", "fastapi", "nestjs", "graphql", "rest", "soap"
            ],
            "databases": [
                "sql", "mysql", "postgresql", "mongodb", "firebase", "oracle", "sqlite",
                "redis", "elasticsearch", "dynamodb", "cassandra", "neo4j", "couchdb"
            ],
            "cloud": [
                "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "serverless",
                "lambda", "ec2", "s3", "heroku", "netlify", "vercel"
            ],
            "mobile": [
                "android", "ios", "react native", "flutter", "xamarin", "swift", "kotlin",
                "objective-c", "mobile development"
            ],
            "devops": [
                "jenkins", "github actions", "gitlab ci", "travis", "docker", "kubernetes",
                "terraform", "ansible", "puppet", "chef", "ci/cd", "devops"
            ],
            "ai_ml": [
                "machine learning", "deep learning", "ai", "tensorflow", "pytorch", "keras",
                "scikit-learn", "nlp", "computer vision", "data science"
            ],
            "testing": [
                "junit", "pytest", "jest", "mocha", "cypress", "selenium", "testing",
                "tdd", "bdd", "qa"
            ]
        }

        logger.info("TalentScoutBot initialized")

    def get_greeting(self) -> str:
        """Generate initial greeting message."""
        return "Hello! I'm the TalentScout Hiring Assistant. 👋\n\nI'm here to help with your initial screening process for tech positions.\nI'll ask you a few questions about your background and technical skills.\n\nLet's start with your name. What is your full name?"

    def process_message(self, user_message: str, message_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process incoming user message and generate a response.

        Args:
            user_message: The message from the user
            message_history: Previous messages in the conversation

        Returns:
            Dict containing response text and updated state
        """
        # Initialize message history if None
        if message_history is None:
            message_history = []

        # Extract conversation state if available in message history
        if message_history and len(message_history) > 0:
            # Try to find the latest state in message history
            for message in reversed(message_history):
                if message.get("metadata") and message["metadata"].get("conversation_stage"):
                    self.current_stage = message["metadata"]["conversation_stage"]
                    if message["metadata"].get("candidate_info"):
                        self.candidate_info = message["metadata"]["candidate_info"]
                    break

        logger.info(f"Processing message in stage: {self.current_stage}")

        # Check for exit keywords
        if self._is_exit_request(user_message):
            self.current_stage = "closing"
            response = self._generate_closing_message(message_history)
            result = {
                "response": response,
                "stage": "closing",
                "candidate_info": self.candidate_info,
                "completed": True
            }

            # Save candidate data if we have required info
            if (self.current_stage == "closing" and
                self.candidate_info.get("name") and
                self.candidate_info.get("email")):
                self.save_candidate(message_history)

            return result

        # Process message based on current stage
        if self.current_stage == "greeting" or self.current_stage == "name":
            self._extract_name(user_message)
            if self.candidate_info["name"]:
                self.current_stage = "contact_info"
                response = self._generate_contact_request_message()
            else:
                response = "I didn't quite catch your name. Could you please provide your full name?"

        elif self.current_stage == "contact_info":
            self._extract_contact_info(user_message)
            if self.candidate_info["email"] and self.candidate_info["phone"]:
                self.current_stage = "experience"
                response = self._generate_experience_request_message()
            else:
                missing = []
                if not self.candidate_info["email"]:
                    missing.append("email address")
                if not self.candidate_info["phone"]:
                    missing.append("phone number")
                response = f"I still need your {' and '.join(missing)}. Could you provide that information?"

        elif self.current_stage == "experience":
            self._extract_experience(user_message)
            self.current_stage = "position"
            response = self._generate_position_request_message()

        elif self.current_stage == "position":
            self._extract_position(user_message)
            self.current_stage = "location"
            response = self._generate_location_request_message()

        elif self.current_stage == "location":
            self._extract_location(user_message)
            self.current_stage = "tech_stack"
            response = self._generate_tech_stack_request_message()

        elif self.current_stage == "tech_stack":
            self._extract_tech_stack(user_message)
            self.current_stage = "technical_questions"
            response = self._generate_technical_questions()

        elif self.current_stage == "technical_questions":
            # After receiving answers to technical questions, we move to closing
            self.current_stage = "closing"
            response = self._generate_closing_message(message_history)

            # Save candidate data
            if self.candidate_info.get("name") and self.candidate_info.get("email"):
                self.save_candidate(message_history)
        else:
            # Default response using LLM
            response = self._generate_llm_response(user_message, message_history)

        # Return response and updated state
        result = {
            "response": response,
            "stage": self.current_stage,
            "candidate_info": self.candidate_info,
            "completed": (self.current_stage == "closing")
        }

        return result

    def save_candidate(self, message_history):
        """Save candidate information to database"""
        # Save candidate to database
        save_result = self.db.save_candidate(self.candidate_info, message_history)

        if save_result["success"]:
            logger.info(f"Candidate saved with ID {save_result['candidate_id']}")
            return True
        else:
            logger.error(f"Failed to save candidate: {save_result.get('error')}")
            return False

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
        # Common technologies to look for - combined from tech_categories
        tech_keywords = []
        for category in self.tech_categories.values():
            tech_keywords.extend(category)

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
                # Otherwise, use the LLM to extract tech stack if API is working
                if self.api_working:
                    try:
                        self.candidate_info["tech_stack"] = self._extract_tech_stack_with_llm(message)
                        logger.info(f"Extracted tech stack (LLM method): {self.candidate_info['tech_stack']}")
                    except Exception as e:
                        logger.error(f"Error extracting tech stack with LLM: {e}")
                        # Fallback to simple word extraction
                        self.candidate_info["tech_stack"] = [message.strip()]
                else:
                    # Simple fallback if API is not working
                    self.candidate_info["tech_stack"] = [message.strip()]
                    logger.info(f"Saved tech stack as single item: {message.strip()}")

    def _extract_tech_stack_with_llm(self, message: str) -> List[str]:
        """Use Gemini API to extract tech stack items from a message."""
        prompt = "Extract technology keywords from this text: " + message + "\n\nOutput ONLY a JSON array of technology names, with no other text or explanation.\nFor example: [\"Python\", \"React\", \"AWS\", \"PostgreSQL\"]\n\nDo not include explanations, notes, or anything except the JSON array."

        try:
            # Call Gemini API
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=30
            )

            # Check for successful response
            if response.status_code == 200:
                response_data = response.json()

                # Extract text from Gemini response
                tech_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "[]")

                # Try to parse the response as a JSON array
                try:
                    tech_list = json.loads(tech_text)
                    if isinstance(tech_list, list):
                        return tech_list
                    else:
                        return [message.strip()]
                except:
                    # If parsing fails, fall back to basic comma splitting
                    return [item.strip() for item in message.split(',') if item.strip()]
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return [message.strip()]

        except Exception as e:
            logger.error(f"Error extracting tech stack with Gemini: {e}")
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
        return f"Thank you for that information! Now, I'd like to know about your technical skills.\n\nPlease list the programming languages, frameworks, databases, and tools that you are proficient in.\nFor example: Python, React, AWS, SQL, etc."

    def _categorize_tech_stack(self, tech_stack: List[str]) -> Dict[str, List[str]]:
        """Categorize technologies in the tech stack by type."""
        categorized = {category: [] for category in self.tech_categories.keys()}

        for tech in tech_stack:
            tech_lower = tech.lower()
            for category, items in self.tech_categories.items():
                if any(item == tech_lower or item in tech_lower for item in items):
                    categorized[category].append(tech)
                    break

        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}

    def _generate_technical_questions(self) -> str:
        """Generate technical questions based on the candidate's tech stack using Gemini API."""
        tech_stack = self.candidate_info["tech_stack"]

        if not tech_stack or len(tech_stack) == 0:
            return "I don't have information about your technical skills. Could you please share your tech stack with me?"

        tech_stack_str = ", ".join(tech_stack)

        # Check if API is working before attempting to generate questions
        if not self.api_working or not self.api_key:
            # If API is not working, use fallback questions
            categorized_tech = self._categorize_tech_stack(tech_stack)
            return self._generate_fallback_technical_questions(categorized_tech, tech_stack_str)

        # Direct, simple prompt for generating tech-specific questions
        prompt = "Generate 4-5 technical interview questions for a candidate with experience in: " + tech_stack_str + "\n\nRequirements for questions:\n1. Each question must specifically mention one of the technologies in their tech stack\n2. Questions should range from medium to hard difficulty\n3. Include at least one scenario-based question where they explain how they'd solve a problem\n4. Questions should test deep knowledge, not just basics\n5. Questions should not be answerable with just yes/no\n\nFormat your response as a clean numbered list with no indentation. Do not include any introductory text or explanations."

        try:
            # Call Gemini API
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=30
            )

            # Check for successful response
            if response.status_code == 200:
                response_data = response.json()

                # Extract text from Gemini response
                questions = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                # Remove any indentation from the response to prevent alignment issues
                questions = "\n\n".join(line.strip() for line in questions.split("\n"))

                return f"Based on your tech stack ({tech_stack_str}), I'd like to ask you a few technical questions:\n\n{questions}\n\nPlease answer these questions to help us assess your technical proficiency."
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                self.api_working = False  # Mark API as not working for future calls
                # Provide more specific fallback questions based on tech categories
                categorized_tech = self._categorize_tech_stack(tech_stack)
                return self._generate_fallback_technical_questions(categorized_tech, tech_stack_str)

        except Exception as e:
            logger.error(f"Error generating technical questions: {e}")
            self.api_working = False  # Mark API as not working for future calls
            # Provide more specific fallback questions based on tech categories
            categorized_tech = self._categorize_tech_stack(tech_stack)
            return self._generate_fallback_technical_questions(categorized_tech, tech_stack_str)

    def _generate_fallback_technical_questions(self, categorized_tech: Dict[str, List[str]], tech_stack_str: str) -> str:
        """Generate fallback technical questions if the LLM call fails."""
        fallback_questions = []

        # Generate language-specific questions
        if "languages" in categorized_tech and categorized_tech["languages"]:
            primary_language = categorized_tech["languages"][0]
            fallback_questions.append(f"1. What features or aspects of {primary_language} do you find most useful in your development work? Please provide specific examples.")

        # Generate frontend-specific questions
        if "frontend" in categorized_tech and categorized_tech["frontend"]:
            frontend_tech = categorized_tech["frontend"][0]
            fallback_questions.append(f"2. Describe a challenging UI/UX problem you solved using {frontend_tech}. What was your approach and what was the outcome?")

        # Generate backend-specific questions
        if "backend" in categorized_tech and categorized_tech["backend"]:
            backend_tech = categorized_tech["backend"][0]
            fallback_questions.append(f"3. How do you handle API security and performance optimization in {backend_tech}? Share some best practices you follow.")

        # Generate database-specific questions
        if "databases" in categorized_tech and categorized_tech["databases"]:
            db_tech = categorized_tech["databases"][0]
            fallback_questions.append(f"4. What strategies do you use for database optimization in {db_tech}? How do you handle large datasets?")

        # Add cloud/deployment question if applicable
        if "cloud" in categorized_tech and categorized_tech["cloud"]:
            cloud_tech = categorized_tech["cloud"][0]
            fallback_questions.append(f"5. How have you used {cloud_tech} in your projects? What services or features do you have the most experience with?")

        # Ensure we have at least 3 questions
        if len(fallback_questions) < 3:
            fallback_questions.append("6. Describe a challenging technical project you've worked on recently. What technologies did you use, what problems did you encounter, and how did you solve them?")
            fallback_questions.append("7. How do you stay updated with the latest developments in your technical field? Which resources do you find most valuable?")
            fallback_questions.append("8. What is your approach to debugging complex technical issues? Please walk me through your process with a specific example.")

        # Format and return the questions
        questions_text = "\n\n".join(fallback_questions[:5])  # Limit to 5 questions

        return f"Based on your tech stack ({tech_stack_str}), I'd like to ask you a few technical questions:\n\n{questions_text}\n\nPlease answer these questions to help us assess your technical proficiency."

    def _generate_closing_message(self, message_history=None) -> str:
        """Generate closing message and save candidate data."""
        # Save candidate data if we have required info and message_history is provided
        if message_history and self.candidate_info.get("name") and self.candidate_info.get("email"):
            self.save_candidate(message_history)

        name = self.candidate_info.get("name", "candidate")
        email = self.candidate_info.get("email", "your email")

        # Generate timestamp for application
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"Thank you for taking the time to chat with me, {name}!\n\nI've collected your information for the initial screening process. Here's what I have:\n- Name: {self.candidate_info.get('name', 'Not provided')}\n- Contact: {self.candidate_info.get('email', 'Not provided')}\n- Experience: {self.candidate_info.get('experience', 'Not provided')}\n- Position interest: {self.candidate_info.get('position', 'Not provided')}\n- Location: {self.candidate_info.get('location', 'Not provided')}\n- Tech stack: {', '.join(self.candidate_info.get('tech_stack', ['Not provided']))}\n\nYour application has been recorded at {timestamp}.\n\nA TalentScout recruiter will review your details and get back to you soon via {email}.\n\nIf you have any questions in the meantime, feel free to reach out to our recruitment team at recruitment@talentscout.example.com\n\nHave a great day!"

    def _generate_llm_response(self, user_message: str, message_history: List[Dict[str, str]]) -> str:
        """Generate response using Gemini API when a more contextual response is needed."""
        if not self.api_working or not self.api_key:
            return "I'm not sure how to respond to that. Let's continue with the screening process."

        # Create a conversation prompt based on history and stage
        prompt = self._create_prompt_for_gemini(user_message, message_history)

        try:
            # Call Gemini API
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=30
            )

            # Check for successful response
            if response.status_code == 200:
                response_data = response.json()

                # Extract text from Gemini response
                response_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                return response_text
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                self.api_working = False
                return "I'm not sure how to respond to that. Let's continue with the screening process."

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            self.api_working = False
            return "I'm not sure how to respond to that. Let's continue with the screening process."

    def _create_prompt_for_gemini(self, user_message: str, message_history: List[Dict[str, str]]) -> str:
        """Create a prompt for Gemini based on current conversation stage."""
        # Create system context
        system_context = f"You are a hiring assistant for TalentScout, a recruitment agency specializing in technology placements.\nYour task is to conduct an initial screening of candidates by gathering information and asking relevant technical questions.\n\nCurrent conversation stage: {self.current_stage}\nCurrent candidate information: {json.dumps(self.candidate_info, indent=2)}\n\nFocus on gathering the information needed for the current stage and then move to the next stage.\nBe professional, friendly, and concise in your responses.\nMaintain the conversation in the context of a job application process."

        # Add conversation history
        conversation_history = "\n\n--- Previous Messages ---\n"
        for message in message_history[-5:]:  # Use last 5 messages to avoid token limits
            role = "User" if message.get("role", "") == "user" else "Assistant"
            conversation_history += f"{role}: {message.get('content', '')}\n"

        # Combine everything into a final prompt
        final_prompt = f"{system_context}\n\n{conversation_history}\n\nUser: {user_message}\n\nYour response:"

        return final_prompt


def test_gemini_api():
    """Test the Gemini API connection."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ No Gemini API key found in environment variables.")
        return False

    try:
        # Simple test request
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={api_key}",
            json={
                "contents": [{
                    "parts": [{
                        "text": "Hello, please respond with the text 'API working properly'"
                    }]
                }]
            },
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Gemini API connection successful!")
            return True
        else:
            print(f"❌ Gemini API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        return False


if __name__ == "__main__":
    # Initialize database
    db = CandidateDatabase()

    # Test the API connection
    api_working = test_gemini_api()

    # Print current version info
    print(f"TalentScout Hiring Assistant v2.0.0")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Simple test for the chatbot
    bot = TalentScoutBot()
    greeting = bot.get_greeting()
    print("\n" + greeting)

    # Test conversation flow
    if api_working:
        print("\nAPI is working properly. The chatbot will use the Gemini API to generate responses.")
    else:
        print("\nAPI is not working. The chatbot will use fallback responses.")

    print("Database storage: Enabled")
    print("\nSystem ready to process candidate conversations.")