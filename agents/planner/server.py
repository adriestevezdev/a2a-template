from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import sys
import json

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
    system_prompt="""You are a project planning agent with expertise in software architecture.

    Your responsibilities include:
    1. Interpreting user requirements for web applications
    2. Creating detailed project plans and task lists
    3. Breaking down projects into frontend and backend tasks
    4. Coordinating work between frontend and backend development teams

    When you receive a project request:
    - Create a detailed plan.md that outlines the architecture, technologies, and approach
    - Create a tasks.md file with separate sections for frontend and backend tasks
    - Each task should have a checkbox ([ ]) that can be marked as completed
    - Ensure tasks are specific, actionable, and well-organized

    You have access to the filesystem through Desktop Commander MCP to create and modify files.
    """,
    mcp_servers=[desktop_commander]
)

# Agent Card metadata
AGENT_CARD = {
    "name": "PlannerAgent",
    "description": "A project planning agent that creates detailed plans and tasks for web applications.",
    "url": "http://localhost:5001",  # base URL where this agent is hosted
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

    log_message(f"Received planning request", "PlannerAgent")

    # Extract project path and description from the message
    # Format expected: "PROJECT_PATH: /path/to/project\n\nPROJECT_DESCRIPTION: Project description"
    project_path = "/home/adria/a2a-agent"  # Default path
    project_description = user_text

    if "PROJECT_PATH:" in user_text and "PROJECT_DESCRIPTION:" in user_text:
        try:
            parts = user_text.split("PROJECT_DESCRIPTION:", 1)
            project_description = parts[1].strip()
            path_part = parts[0].split("PROJECT_PATH:", 1)[1].strip()
            project_path = path_part.split("\n\n")[0].strip()
            log_message(f"Using project path: {project_path}", "PlannerAgent")
        except Exception as e:
            log_message(f"Error parsing project path: {str(e)}. Using default path.", "PlannerAgent")

    # Ensure necessary directories exist
    plan_file = os.path.join(project_path, "plan.md")
    tasks_file = os.path.join(project_path, "tasks.md")

    ensure_file_exists(plan_file, "# Project Plan\n\n")
    ensure_file_exists(tasks_file, "# Project Tasks\n\n")

    async with agent.run_mcp_servers():
        result = await agent.run(f"""
Based on the following project request, create a detailed project plan and task list:

USER REQUEST:
{project_description}

First, analyze the requirements thoroughly. Then:

1. Create or update {plan_file} with a comprehensive project plan including:
   - Project overview
   - Architecture design
   - Technology stack
   - Implementation approach
   - Timeline/milestones

2. Create or update {tasks_file} with specific tasks organized into sections:
   - Frontend tasks (clearly labeled)
   - Backend tasks (clearly labeled)
   - Any infrastructure or setup tasks

Each task should have a checkbox (e.g., "- [ ] Task description") that can be marked as completed later.

IMPORTANT: When writing the tasks, make it clear that for any npm or Node.js related commands (npm init, npm install, etc.), the agents should:
- ALWAYS change to the project directory first: cd {project_path}
- Run all npm commands within the project directory
- Initialize any new Node.js projects with: cd {project_path} && npm init
- Install dependencies with: cd {project_path} && npm install [package]
- NEVER run npm commands in the current directory without changing to {project_path} first

Be thorough and detailed in your planning. Think about what would be needed for a complete implementation.
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
    log_message("Starting Planner Agent server on http://localhost:5001", "PlannerAgent")
    app.run(host="0.0.0.0", port=5001)
