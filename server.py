from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import time
import sys

# Load environment variables from .env file
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please make sure you have a valid API key in your .env file.")
    print("The variable should be named 'OPENAI_API_KEY' (not 'OPENAI_API_EKY' or similar).")
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
    system_prompt="""You are a task execution agent that can create, read, and modify files.
    You have access to the Desktop Commander MCP which allows you to interact with the filesystem.
    When you complete tasks, you should mark them as done in the tasks.md file by changing "[ ]" to "[x]".
    Be thorough and detailed in your work. After completing each task, summarize what you've done.
    """,
    mcp_servers=[desktop_commander]
)

# Agent Card metadata
AGENT_CARD = {
    "name": "TaskExecutionAgent",
    "description": "An agent that can execute file-related tasks and mark them as completed.",
    "url": "http://localhost:5000",  # base URL where this agent is hosted
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

    print(f"Received task: {user_text}")
    
    async with agent.run_mcp_servers():
        result = await agent.run(user_text)
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
    print("Starting Task Execution Agent server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000)
