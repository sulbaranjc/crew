from langchain_ollama import ChatOllama

MODEL = "qwen2.5:7b-32k"
BASE_URL = "http://127.0.0.1:11434"

llm = ChatOllama(model=MODEL, base_url=BASE_URL, temperature=0.2)
