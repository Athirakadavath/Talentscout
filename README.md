# Talentscout
# TalentScout Hiring Assistant

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen)
![SQLite](https://img.shields.io/badge/database-SQLite-orange)
![Gemini](https://img.shields.io/badge/AI-Gemini%201.5%20Pro-purple)

**Last Updated:** 2025-05-04 05:59:45 (UTC)  
**Current User:** Athirakadavath

## Project Overview

The TalentScout Hiring Assistant is an AI-powered chatbot designed to streamline the initial screening process for technical candidates. It conducts structured interviews to collect candidate information and evaluates technical proficiency through dynamically generated questions based on each candidate's specific tech stack.

### Key Features

- **Structured conversation flow** for information gathering
- **Dynamic technical assessment** tailored to each candidate's tech stack
- **Persistent data storage** in SQLite database
- **Intelligent information extraction** using regex and NLP
- **Fallback mechanisms** for robust operation when the AI API is unavailable

## Installation Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Gemini API key (optional, but recommended for optimal functionality)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/talentscout.git
cd talentscout

### Step 2: Set Up Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Dependencies

The application requires the following packages:
- requests
- python-dotenv
- logging

## Configuration

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

### Step 5: Run the Application

```bash
python chatbot.py
```

### Conversation Stages

The chatbot follows a structured sequence of stages:

1. **Greeting**: Introduction and request for candidate's name
2. **Contact Information**: Collection of email and phone number
3. **Experience**: Inquiry about professional experience
4. **Position**: Identification of desired role
5. **Location**: Collection of candidate's location
6. **Tech Stack**: Assessment of technical skills and proficiencies
7. **Technical Questions**: Generation of tailored technical questions
8. **Closing**: Summary of collected information and next steps

### Viewing Candidate Data

Use any SQLite browser (e.g., DB Browser for SQLite) to open candidates.db and review candidate records.

```sql
-- Example query to view all candidates
SELECT * FROM candidates ORDER BY application_time DESC;
```

## Technical Details

### Architecture

The application follows a modular object-oriented design with two main classes:

- **TalentScoutBot**: Handles conversation flow, information extraction, and technical question generation
- **CandidateDatabase**: Manages database operations for storing candidate information

### Libraries and Dependencies

- **Gemini API**: Powers the intelligent question generation and contextual responses
- **SQLite**: Provides lightweight, serverless database functionality
- **python-dotenv**: Manages environment variables
- **logging**: Implements comprehensive application logging
- **requests**: Handles API calls to the Gemini service
- **re (regex)**: Extracts structured information from unstructured text

### Database Schema

```sql
CREATE TABLE candidates (
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
```

### Tech Stack Categorization

The system categorizes technical skills into domains to generate more relevant questions:

- **Languages**: Python, Java, JavaScript, etc.
- **Frontend**: React, Angular, Vue, etc.
- **Backend**: Node.js, Django, Flask, etc.
- **Databases**: SQL, MongoDB, Redis, etc.
- **Cloud**: AWS, Azure, GCP, etc.
- **Mobile**: Android, iOS, React Native, etc.
- **DevOps**: Jenkins, Docker, Kubernetes, etc.
- **AI/ML**: TensorFlow, PyTorch, NLP, etc.
- **Testing**: JUnit, Pytest, Cypress, etc.

### Prompt Design

The chatbot employs several carefully crafted prompt strategies:

#### Information Extraction Prompts

For extracting tech skills from unstructured text:

```
Extract technology keywords from this text: [candidate response]

Output ONLY a JSON array of technology names, with no other text or explanation.
For example: ["Python", "React", "AWS", "PostgreSQL"]
```

#### Technical Question Generation Prompts

For generating relevant technical questions:

```
Generate 4-5 technical interview questions for a candidate with experience in: [tech stack]

Requirements for questions:
1. Each question must specifically mention one of the technologies in their tech stack
2. Questions should range from medium to hard difficulty
3. Include at least one scenario-based question where they explain how they'd solve a problem
4. Questions should test deep knowledge, not just basics
5. Questions should not be answerable with just yes/no
```

#### Contextual Response Prompts

For generating appropriate conversational responses:

```
You are a hiring assistant for TalentScout, a recruitment agency specializing in technology placements.
Your task is to conduct an initial screening of candidates by gathering information and asking relevant technical questions.

Current conversation stage: [stage]
Current candidate information: [json data]

Focus on gathering the information needed for the current stage and then move to the next stage.
Be professional, friendly, and concise in your responses.
Maintain the conversation in the context of a job application process.
```

## Challenges & Solutions

### Challenge 1: Inconsistent Contact Information Formats

**Problem**: Candidates provide contact information in various formats, making extraction difficult.

**Solution**: Implemented robust regex patterns that can handle multiple phone number formats (international, with/without parentheses, different separators) and validate email addresses properly.

### Challenge 2: Technical Skill Identification

**Problem**: Candidates describe their technical skills in unstructured ways, mixing frameworks, languages, and tools.

**Solution**:
- Implemented multiple extraction strategies (comma splitting, keyword matching)
- Used the Gemini API for intelligent extraction of technologies from free-text responses
- Created a comprehensive tech category system for better question generation

### Challenge 3: Graceful API Failure Handling

**Problem**: API calls to Gemini could fail due to connectivity issues, rate limiting, or service outages.

**Solution**: Implemented a robust fallback system that:
- Detects API failures and switches to offline mode
- Provides pre-defined question templates based on tech categories
- Continues functioning without degrading the core experience

### Challenge 4: Conversation Context Maintenance

**Problem**: Maintaining coherent conversation state across multiple messages.

**Solution**:
- Designed a structured conversation flow with clear stages
- Implemented metadata storage with each message
- Created state recovery mechanisms to handle interrupted conversations

### Challenge 5: Database Design for Flexibility

**Problem**: Designing a database schema that accommodates both structured data (name, email) and unstructured data (conversation history).

**Solution**:
- Used JSON serialization for complex data types (tech stack, conversation history)
- Implemented a schema that balances queryability and flexibility
- Added indexes for common query patterns to improve performance

## Data Storage Implementation

The TalentScout Hiring Assistant uses SQLite as its primary storage mechanism. This choice was made for several reasons:

### Why SQLite?

- **Serverless architecture**: No separate database server needed
- **Zero configuration**: Works out of the box with no setup
- **Cross-platform compatibility**: Runs on all major operating systems
- **Single file storage**: The entire database is contained in candidates.db
- **Reliability**: ACID-compliant transactions ensure data integrity

### Data Access

Data is stored and accessed through the CandidateDatabase class which provides methods for:
- Saving candidate information
- Retrieving candidates by ID or email
- Updating candidate status
- Listing recent candidates

## Security Considerations

Since SQLite relies on file system permissions for security:
- Set appropriate file permissions on the database file
- Ensure the application runs with minimal required privileges
- Consider encrypting the database file for additional security
- Implement access controls at the application level

## Developer Notes

- **Development Environment**: The chatbot was developed and tested on Python 3.8+
- **Testing**: Extensive testing was performed with various candidate responses
- **Logging**: Comprehensive logging is implemented for debugging purposes
- **Maintenance**: Regular updates are recommended to keep tech stack categories current

## Future Enhancements

- **Resume Parsing**: Add capability to extract information directly from uploaded resumes
- **Multi-language Support**: Expand to support interviews in multiple languages
- **Advanced Analytics**: Implement statistical analysis of candidate responses
- **Integration Options**: Add webhooks and API endpoints for integration with ATS systems
- **Video Interview**: Add capability to conduct and analyze video interviews

---
