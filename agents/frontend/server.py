from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import sys
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common.utils import log_message, ensure_file_exists

# Load environment variables from .env file
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please make sure you have a valid API key in your .env file.")
    sys.exit(1)

from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai import Agent

app = Flask(__name__)

# Desktop Commander MCP server for file/terminal operations
desktop_commander = MCPServerStdio(
    'npx', ['-y', '@wonderwhy-er/desktop-commander'],
    env={}
)

agent = Agent(
    model="openai:gpt-4o-mini",
    system_prompt="""You are a specialized frontend development agent with expertise in:

    - HTML, CSS, and JavaScript
    - Modern frontend frameworks (React, Vue, Angular)
    - Responsive design
    - UI/UX implementation
    - Frontend testing and optimization

    Your responsibilities:
    1. Implement frontend tasks from the tasks.md file
    2. Create and modify frontend code files
    3. Mark completed tasks in tasks.md by changing "[ ]" to "[x]"
    4. Provide detailed explanations of your implementation decisions

    You should focus ONLY on frontend-related tasks. You have access to the filesystem
    through Desktop Commander MCP to create directories, files, and modify code.

    When implementing tasks:
    - Follow best practices for modern frontend development
    - Create clean, maintainable, and well-documented code
    - Consider responsive design and accessibility
    - Structure your code in a logical and organized manner
    - Create any necessary directories and files
    """,
    mcp_servers=[desktop_commander]
)

# Agent Card metadata
AGENT_CARD = {
    "name": "FrontendAgent",
    "description": "A specialized frontend development agent that implements web application UI/UX.",
    "url": "http://localhost:5002",  # base URL where this agent is hosted
    "version": "1.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False
    }
}

# Endpoint to serve the Agent Card
@app.get("/.well-known/agent.json")
def get_agent_card():
    return jsonify(AGENT_CARD)

# Endpoint to handle task requests
@app.post("/tasks/send")
async def handle_task():
    task_request = request.get_json()
    if not task_request:
        return jsonify({"error": "Invalid request"}), 400

    task_id = task_request.get("id")
    # Extract user's message text from the request
    try:
        user_text = task_request["message"]["parts"][0]["text"]
    except Exception as e:
        return jsonify({"error": "Bad message format"}), 400

    log_message(f"Received frontend task", "FrontendAgent")

    # Extract project path from the message if available
    project_path = "/home/adria/a2a-agent"  # Default path

    if "PROJECT_PATH:" in user_text:
        try:
            path_line = [line for line in user_text.split('\n') if "PROJECT_PATH:" in line][0]
            project_path = path_line.split("PROJECT_PATH:", 1)[1].strip()
            log_message(f"Using project path: {project_path}", "FrontendAgent")
        except Exception as e:
            log_message(f"Error parsing project path: {str(e)}. Using default path.", "FrontendAgent")

    async with agent.run_mcp_servers():
        result = await agent.run(f"""
I'll help you with the frontend development tasks as specified. First, I'll analyze the project:

1. Read the plan.md file in {project_path} to understand the project architecture and technology choices
2. Read the tasks.md file in {project_path} to identify the frontend tasks that need to be implemented
3. {user_text}

IMPORTANT: For any npm or Node.js related commands (npm init, npm install, etc.), make sure to:
- ALWAYS change to the project directory first: cd {project_path}
- Run all npm commands within the project directory
- Initialize any new Node.js projects with: cd {project_path} && npm init
- Install dependencies with: cd {project_path} && npm install [package]
- NEVER run npm commands in the current directory without changing to {project_path} first

For each task I complete, I'll:
- Create the necessary files and directories in {project_path}
- Implement the code following best practices
- Mark the task as completed in the tasks.md file by replacing "[ ]" with "[x]"
- Provide a summary of what I've done

Let me get started right away.
""")
    response_text = result.data

    # Formulate A2A response Task
    response_task = {
        "id": task_id,
        "status": {"state": "completed"},
        "messages": [
            task_request.get("message", {}),  # include original user message
            {
                "role": "agent",
                "parts": [{"text": response_text}]
            }
        ]
    }
    return jsonify(response_task)

if __name__ == "__main__":
    log_message("Starting Frontend Agent server on http://localhost:5002", "FrontendAgent")
    app.run(host="0.0.0.0", port=5002)
