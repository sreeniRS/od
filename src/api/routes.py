from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.utils.appconfig import AppConfig
from src.utils.azureai import AzureAI
from src.tools.nl_to_odata_tool import nl_to_odata
from src.aiagents.nl2odata_agent import create_graph
from src.llm.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage


router = APIRouter()

class Query(BaseModel):
    text: str 


def format_ai_message(message):
    if isinstance(message, AIMessage):
        content = message.content.strip()
        if content:
            return content
        elif message.additional_kwargs.get('tool_calls'):
            tool_call = message.additional_kwargs['tool_calls'][0]
            return f"Used tool: {tool_call['function']['name']}"
    return None


@router.post("/convert")
def convert_to_odata(query: Query):
    llm = get_llm()
    
    text2Odata_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            '''You are an efficient query assistant specialized in converting natural language into OData queries. 
            Your job is to help users transform their natural language requests into proper OData queries for interacting 
            with their API's. You will take a user's natural language query, parse it, and return the correct OData query format.
            
            Always use the "nl_to_odata" tool to generate the OData query. Do not attempt to create the query yourself.
            After getting the result from the tool, present it to the user in a clear format
            ''',
        ),
        ("placeholder", "{messages}"),
    ])

    text2Odata_tool = [nl_to_odata]
    text2Odata_assistant_runnable = text2Odata_prompt | llm.bind_tools(text2Odata_tool)

    graph = create_graph(text2Odata_assistant_runnable, text2Odata_tool)

    events = graph.stream(
        {"messages": ("user", query.text)}, stream_mode="values"
    )
    
    result = []
    for event in events:
        if 'messages' in event:
            for message in event['messages']:
                formatted_message = format_ai_message(message)
                if formatted_message:
                    result.append(formatted_message)
    
    if not result:
        raise HTTPException(status_code=400, detail="Failed to convert query")
    
    return {"odata_query": result[-1]}
