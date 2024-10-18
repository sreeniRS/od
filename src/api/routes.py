from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.utils.appconfig import AppConfig
from src.utils.azureai import AzureAI
from src.tools.nl_to_odata_tool import nl_to_odata
from src.aiagents.nl2odata_agent import create_graph
from src.llm.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
import requests
from requests.auth import HTTPBasicAuth



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
            After getting the result from the tool, present it to the user in a clear format. 
            The Odata Service which we are using has the following fields. Select the most appropriate fields for the query that you are passing
            in accordance with the user requirement.
            The Fields are:
                1) ORDER_NO - This is the order no which documents the purchase.
                2) ORDER_NO_ITEM - This is the line item which is part of the order
                3) TSF_ENTITY_ID - This is a unique id for the purchasing organization
                4) PURCH_GRP - This is the purchase group or category for the service
                5) SUPPLIER - This is the supplier for the item
                6) CREAT_DATE - This is the date of creation for that particular item
                7) MATERIAL - This is the material used for the Line item
                8) STORE_NAME - This is the plant where the material is manufactured
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
        for message in event['messages']:
            formatted_message = format_ai_message(message)
            result.append(formatted_message)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to convert query")
    lines = result[-1].split('\n')
    # Extract the part between the two newline characters
    if len(lines) > 1:
        extracted_part = lines[3]  # This assumes the part you need is on the second line
        print(extracted_part)
    else:
        print("No valid content found between newlines")
    api_url = endpoint +'/'+ lines[3]
    call_odata_query(api_url)

    return {"odata_query": lines[3]}

def call_odata_query(endpoint: str):

    # Basic authentication credentials
    username = 'DEV_100'
    password = 'Nestle1330$'
    # Make the request
    response = requests.get(endpoint, auth=HTTPBasicAuth(username, password))
    print(response.status_code)
    print(response.json())