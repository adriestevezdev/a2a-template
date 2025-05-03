import requests
import uuid
import time
import re
import os
import sys
from dotenv import load_dotenv

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

# Desktop Commander MCP server for file operations
desktop_commander = MCPServerStdio(
    'npx', ['-y', '@wonderwhy-er/desktop-commander'],
    env={}
)

# Create a client agent that can read files and assign tasks
client_agent = Agent(
    model="openai:gpt-4o-mini",
    system_prompt="""You are a task management agent. Your job is to:
    1. Read the tasks.md file
    2. Identify which tasks are not yet completed (those marked with "[ ]")
    3. Send instructions to another agent to complete those tasks
    4. After the other agent completes tasks, check if they were properly marked as completed
    5. Assign the next set of tasks until all are complete
    
    Work in a step-by-step manner, focusing on one section of tasks at a time.
    """,
    mcp_servers=[desktop_commander]
)

def check_tasks_status():
    """Read tasks.md and check which tasks are completed and which sections have all tasks completed."""
    # In a real implementation, this would use the MCP server to read the file
    with open('tasks.md', 'r') as f:
        content = f.read()
    
    sections = {}
    current_section = None
    
    for line in content.split('\n'):
        if line.startswith('## '):
            current_section = line[3:].strip()
            sections[current_section] = {'completed': 0, 'total': 0}
        elif line.strip().startswith('- ['):
            if current_section:
                sections[current_section]['total'] += 1
                if line.strip().startswith('- [x]'):
                    sections[current_section]['completed'] += 1
    
    return sections

def get_next_section():
    """Get the next section that has incomplete tasks."""
    sections = check_tasks_status()
    for section, status in sections.items():
        if status['completed'] < status['total']:
            return section
    return None

async def main():
    AGENT_BASE_URL = "http://localhost:5000"
    
    print("Task Management Agent starting...")
    print("Connecting to Task Execution Agent...")
    
    # 1. Discover the agent by fetching its Agent Card
    try:
        agent_card_url = f"{AGENT_BASE_URL}/.well-known/agent.json"
        res = requests.get(agent_card_url)
        if res.status_code != 200:
            print(f"Failed to get agent card: {res.status_code}")
            print("Make sure the server is running on http://localhost:5000")
            return
        
        agent_card = res.json()
        print(f"Discovered Agent: {agent_card['name']} – {agent_card.get('description', '')}")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the Task Execution Agent.")
        print("Make sure you've started the server with 'python server.py' in another terminal.")
        return
    
    # Loop until all tasks are completed
    while True:
        async with client_agent.run_mcp_servers():
            # Use the client agent to analyze the tasks file and formulate the next task
            prompt = "Read the tasks.md file and determine which section should be worked on next. " + \
                    "Identify tasks in that section that are not completed."
            result = await client_agent.run(prompt)
            
            next_task_analysis = result.data
            
            # Check if all tasks are complete
            next_section = get_next_section()
            if not next_section:
                print("All tasks are completed! 🎉")
                break
            
            # Generate the task instruction for the server agent
            task_prompt = f"Please complete the tasks in the '{next_section}' section of tasks.md. " + \
                        f"When you finish each task, mark it as completed by changing '[ ]' to '[x]' in the tasks.md file. " + \
                        f"Let me know when you've finished all tasks in this section."
            
            # Create a unique task ID
            task_id = str(uuid.uuid4())
            
            # Prepare the task payload
            task_payload = {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [
                        {"text": task_prompt}
                    ]
                }
            }
            
            print(f"\n📋 Sending task to execute tasks in section: {next_section}")
            print(f"Task message: '{task_prompt}'\n")
            
            # Send the task to the server agent
            tasks_send_url = f"{AGENT_BASE_URL}/tasks/send"
            try:
                response = requests.post(tasks_send_url, json=task_payload)
                
                if response.status_code != 200:
                    print(f"Task request failed: {response.status_code}, {response.text}")
                    continue
                
                task_response = response.json()
                
                # Process and display the server agent's response
                if task_response.get("status", {}).get("state") == "completed":
                    messages = task_response.get("messages", [])
                    if messages:
                        agent_message = messages[-1]  # last message (from agent)
                        agent_reply_text = "".join(part.get("text", "") for part in agent_message.get("parts", []))
                        print("🤖 Agent's reply:", agent_reply_text)
                    else:
                        print("No messages in response!")
                else:
                    print("Task did not complete. Status:", task_response.get("status"))
                
                # Give some time before checking for the next set of tasks
                print("\nWaiting for a moment before checking for the next tasks...\n")
                time.sleep(3)  # Wait for 3 seconds
            except requests.exceptions.ConnectionError:
                print("Error: Lost connection to the Task Execution Agent.")
                print("Make sure the server is still running.")
                return

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
