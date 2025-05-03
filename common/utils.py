import requests
import uuid
import time
import os
import sys
from datetime import datetime

def get_agent_card(base_url):
    """Fetch the agent card from the specified server."""
    try:
        agent_card_url = f"{base_url}/.well-known/agent.json"
        res = requests.get(agent_card_url)
        if res.status_code != 200:
            print(f"Failed to get agent card: {res.status_code}")
            return None
        return res.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the agent at {base_url}.")
        return None

def send_task_to_agent(base_url, task_prompt, task_id=None):
    """Send a task to an agent and return the response."""
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    task_payload = {
        "id": task_id,
        "message": {
            "role": "user",
            "parts": [
                {"text": task_prompt}
            ]
        }
    }
    
    try:
        tasks_send_url = f"{base_url}/tasks/send"
        response = requests.post(tasks_send_url, json=task_payload, timeout=300)  # 5-minute timeout
        
        if response.status_code != 200:
            print(f"Task request failed: {response.status_code}, {response.text}")
            return None
        
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Lost connection to the agent at {base_url}.")
        return None
    except requests.exceptions.Timeout:
        print(f"Error: Request to the agent at {base_url} timed out.")
        return None

def extract_agent_reply(task_response):
    """Extract the text reply from an agent's task response."""
    if not task_response:
        return None
        
    if task_response.get("status", {}).get("state") == "completed":
        messages = task_response.get("messages", [])
        if messages:
            agent_message = messages[-1]  # last message (from agent)
            # Extract text from the agent's message parts
            agent_reply_text = "".join(part.get("text", "") for part in agent_message.get("parts", []))
            return agent_reply_text
    
    return None

def log_message(message, agent_name=None):
    """Log a message with timestamp and agent name."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{timestamp}]"
    if agent_name:
        prefix += f" [{agent_name}]"
    print(f"{prefix} {message}")

def ensure_file_exists(filepath, default_content=""):
    """Ensure a file exists, creating it with default content if it doesn't."""
    if not os.path.exists(filepath):
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(filepath, 'w') as f:
            f.write(default_content)
