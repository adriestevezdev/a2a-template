import sys
import os
import asyncio
import time
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common.utils import get_agent_card, send_task_to_agent, extract_agent_reply, log_message

from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please make sure you have a valid API key in your .env file.")
    sys.exit(1)

# URLs for our agent servers
FRONTEND_URL = "http://localhost:5002"

# Desktop Commander MCP server for file operations
desktop_commander = MCPServerStdio(
    'npx', ['-y', '@wonderwhy-er/desktop-commander'],
    env={}
)

# Local agent for analyzing tasks
client_agent = Agent(
    model="openai:gpt-4o-mini",
    system_prompt="""You analyze tasks.md files to identify frontend tasks that need to be completed.
    You help coordinate the work of a frontend development agent by identifying which tasks to work on next.
    """,
    mcp_servers=[desktop_commander]
)

def get_frontend_tasks(project_path):
    """Read tasks.md and identify uncompleted frontend tasks."""
    try:
        tasks_file = os.path.join(project_path, 'tasks.md')
        with open(tasks_file, 'r') as f:
            content = f.read()

        # Look for sections that might contain frontend tasks
        frontend_section_pattern = r'#{1,3}\s+(?:Frontend|Front[- ]?end|UI|User Interface).*?\n(.*?)(?=#{1,3}|\Z)'
        frontend_sections = re.findall(frontend_section_pattern, content, re.DOTALL | re.IGNORECASE)

        if not frontend_sections:
            return "No frontend section found in tasks.md"

        # Find incomplete tasks in those sections
        incomplete_tasks = []
        for section in frontend_sections:
            task_pattern = r'- \[ \](.*?)(?=\n- |\n\n|\Z)'
            tasks = re.findall(task_pattern, section, re.DOTALL)
            incomplete_tasks.extend(tasks)

        if not incomplete_tasks:
            return "All frontend tasks are completed!"

        # Format the tasks
        task_list = "\n".join(f"- {task.strip()}" for task in incomplete_tasks)
        return f"Uncompleted frontend tasks:\n\n{task_list}"
    except Exception as e:
        return f"Error reading tasks.md: {e}"

async def main():
    # Get project path from command line arguments or use current directory
    project_path = os.getcwd()
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        if not os.path.exists(project_path):
            log_message(f"Error: Project path {project_path} does not exist.", "Frontend Client")
            return

    log_message(f"Using project path: {project_path}", "Frontend Client")

    # 1. Discover the frontend agent
    log_message("Connecting to Frontend Agent...", "Frontend Client")
    frontend_card = get_agent_card(FRONTEND_URL)
    if not frontend_card:
        log_message("Failed to connect to Frontend Agent. Make sure it's running.", "Frontend Client")
        return

    log_message(f"Connected to {frontend_card['name']} - {frontend_card.get('description', '')}", "Frontend Client")

    # Check if plan.md and tasks.md exist
    plan_file = os.path.join(project_path, 'plan.md')
    tasks_file = os.path.join(project_path, 'tasks.md')

    if not os.path.exists(plan_file) or not os.path.exists(tasks_file):
        log_message(f"Error: plan.md or tasks.md not found in {project_path}. Run the Planner Agent first.", "Frontend Client")
        return

    # Continuous loop to process frontend tasks
    while True:
        # Use the client agent to analyze the tasks file
        async with client_agent.run_mcp_servers():
            result = await client_agent.run(f"Read the {tasks_file} file and identify uncompleted frontend tasks.")
            next_task_analysis = result.data

        # Check if there are any frontend tasks to complete
        frontend_tasks = get_frontend_tasks(project_path)
        if "All frontend tasks are completed" in frontend_tasks:
            log_message("All frontend tasks are completed! 🎉", "Frontend Client")
            break

        # Generate instructions for frontend agent
        task_prompt = f"""Please implement the next set of frontend tasks from {tasks_file}.

PROJECT_PATH: {project_path}

Here are the pending frontend tasks:
{frontend_tasks}

IMPORTANT: For any npm or Node.js related commands (npm init, npm install, etc.), make sure to:
- ALWAYS change to the project directory first: cd {project_path}
- Run all npm commands within the project directory
- Initialize any new Node.js projects with: cd {project_path} && npm init
- Install dependencies with: cd {project_path} && npm install [package]
- NEVER run npm commands in the current directory without changing to {project_path} first

Please work on these tasks one by one. For each task:
1. Create or modify the necessary files in the project path: {project_path}
2. Implement the functionality described
3. Mark the task as completed in {tasks_file} (change "[ ]" to "[x]")

After completing each task, provide a summary of what you've done.
"""

        log_message("Sending frontend tasks to agent...", "Frontend Client")
        frontend_response = send_task_to_agent(FRONTEND_URL, task_prompt)
        frontend_reply = extract_agent_reply(frontend_response)

        if not frontend_reply:
            log_message("Failed to get response from Frontend Agent.", "Frontend Client")
            break

        log_message("Frontend Agent has completed some tasks!", "Frontend Client")
        print("\n" + frontend_reply + "\n")

        log_message("Waiting before checking for more tasks...", "Frontend Client")
        time.sleep(3)  # Short pause before next iteration

if __name__ == "__main__":
    asyncio.run(main())
