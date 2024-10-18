from src.utils.appconfig import AppConfig
from src.utils.azureai import AzureAI
from langchain_core.prompts import ChatPromptTemplate


config = AppConfig()
azure_ai = AzureAI(config)

llm = None

def get_llm():
    global llm
    if llm is None:
        llm = azure_ai.get_client()
    return llm 