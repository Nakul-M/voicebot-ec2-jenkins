from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# Create LLM instance
llm = ChatOllama(
    model="gemma3:1b",
    base_url="http://localhost:11434",  
    temperature=0.7,
)

# Send a prompt
response = llm.invoke([
    HumanMessage(content="hello")
])

print(response.content)