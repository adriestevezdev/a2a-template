import sys
import os
import asyncio
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common.utils import get_agent_card, send_task_to_agent, extract_agent_reply, log_message

from dotenv import load_dotenv
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please make sure you have a valid API key in your .env file.")
    sys.exit(1)

# URLs for our agent servers
PLANNER_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5002"
BACKEND_URL = "http://localhost:5003"

async def main():
    # Accept user input for project description
    print("\n🔍 Project Planner Agent")
    print("=" * 50)
    print("Describe your web application project. Be as detailed as possible.")
    print("Include features, target users, and any specific requirements.")
    print("Type your description and press Enter when done.\n")

    user_input = input("> ")

    # Ask for project path
    print("\nEnter the path where you want to create the project:")
    print("(Leave empty to use the current directory)")
    project_path = input("> ").strip()

    # Use current directory if no path is provided
    if not project_path:
        project_path = os.getcwd()

    # Ensure the path exists
    if not os.path.exists(project_path):
        try:
            os.makedirs(project_path)
            log_message(f"Created directory: {project_path}", "Client")
        except Exception as e:
            log_message(f"Error creating directory {project_path}: {str(e)}", "Client")
            return

    # 1. Discover the planner agent
    log_message("Connecting to Planner Agent...", "Client")
    planner_card = get_agent_card(PLANNER_URL)
    if not planner_card:
        log_message("Failed to connect to Planner Agent. Make sure it's running.", "Client")
        return

    log_message(f"Connected to {planner_card['name']} - {planner_card.get('description', '')}", "Client")

    # 2. Send the user's project description and path to the planner agent
    log_message(f"Sending project description to Planner Agent (Path: {project_path})...", "Client")
    # Format the message to include the project path
    full_message = f"PROJECT_PATH: {project_path}\n\nPROJECT_DESCRIPTION: {user_input}"
    planner_response = send_task_to_agent(PLANNER_URL, full_message)
    planner_reply = extract_agent_reply(planner_response)

    if not planner_reply:
        log_message("Failed to get response from Planner Agent.", "Client")
        return

    log_message("Planner Agent has created the project plan and tasks!", "Client")
    print("\n" + planner_reply + "\n")

    # 3. Now check if we can discover the frontend and backend agents
    log_message("Checking for Frontend and Backend Agents...", "Client")

    frontend_card = get_agent_card(FRONTEND_URL)
    backend_card = get_agent_card(BACKEND_URL)

    if frontend_card and backend_card:
        log_message("Frontend and Backend Agents found! You can now execute:", "Client")
        print(f"\n1. To start Frontend Agent: python agents/frontend/client.py {project_path}")
        print(f"2. To start Backend Agent: python agents/backend/client.py {project_path}")
        print(f"\nThese agents will implement the tasks defined in {os.path.join(project_path, 'tasks.md')}")
    else:
        if not frontend_card:
            log_message("Frontend Agent not found. Make sure it's running on port 5002.", "Client")
        if not backend_card:
            log_message("Backend Agent not found. Make sure it's running on port 5003.", "Client")

if __name__ == "__main__":
    asyncio.run(main())
