import openai
import time
from dotenv import load_dotenv

# Assummes you have a .env file containing OPENAI_API_KEY=<your key> in the same directory
load_dotenv()

# Initialize OpenAI Client
client = openai.Client()

# Step 1: Create an Assistant
assistant = client.beta.assistants.create(
    name="Patry",
    instructions="Te llamas Patry. ",
     tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": ["vs_QRTpJ8wF4sklsFCxK5G8xuOp"]}},
    model="gpt-4o-mini"
)

# Step 2: Create a Thread
thread = client.beta.threads.create()

content = input("Dime que quieres saber:  ")

# Step 3: Add a Message to a Thread
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user", 
    content=content
)

# Step 4: Run the Assistant
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
    instructions="Por favor, dame la respuesta a la pregunta y termina la respuesta con tu nombre(Patry)"
)   

# Waits for the run to be completed. 
while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, 
                                                   run_id=run.id)
    if run_status.status == "completed":
        break
    elif run_status.status == "failed":
        print("Run failed:", run_status.last_error)
        break
    time.sleep(2)  # wait for 2 seconds before checking again


# Step 5: Parse the Assistant's Response and print the Results
messages = client.beta.threads.messages.list(
    thread_id=thread.id
)

# Prints the messages the latest message the bottom
number_of_messages = len(messages.data)
print( f'Number of messages: {number_of_messages}')

for message in reversed(messages.data):
    role = message.role  
    for content in message.content:
        if content.type == 'text':
            response = content.text.value 
            print(f'\n{role}: {response}')