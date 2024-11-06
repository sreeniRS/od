from src.utils.appconfig import get_config_instance
from src.utils.azureai import AzureAI
from langchain_core.prompts import ChatPromptTemplate


config = get_config_instance()
azure_ai = AzureAI(config)

llm = None
embedding = None
def get_llm():
    global llm
    if llm is None:
        llm = azure_ai.get_client()
    return llm

def get_embedding():
    global embedding
    if embedding is None:
        embedding = azure_ai.get_embedding_client()
    return embedding