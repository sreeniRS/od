import xmltodict, json, requests
from requests.auth import HTTPBasicAuth
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from src.utils.appconfig import AppConfig
from src.utils.azureai import AzureAI
from src.tools.nl_to_odata_tool import nl_to_odata
from src.aiagents.nl2odata_agent import create_graph
from src.llm.llm import get_llm



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
            """You are an OData query assistant that converts natural language to OData queries with grouping, filtering, 
            and aggregation capabilities.
            
            The Fields are:
                1) ORDER_NO - This is the order no or order number which documents the purchase.
                2) ORDER_NO_ITEM - This is the line item which is part of the order
                3) TSF_ENTITY_ID - This is a unique id for the purchasing organization
                4) PURCH_GRP - This is the purchase group or category for the service
                5) SUPPLIER - This is the supplier for the item
                6) CREAT_DATE - This is the date of creation for that particular item
                7) MATERIAL - This is the material used for the Line item
                8) STORE_NAME - This is the plant where the material is manufactured
                
                Process:
                    1. Thought: Analyze query requirements (filtering, grouping, aggregation)
                    2. Action: Use nl_to_odata tool 
                    3. Observation: Verify syntax and completeness
                    4. Response: Return OData query.

                Rules:
                    - Use $apply for aggregations/grouping
                    - Handle date ranges in YYYY-MM-DD format
                    - Enclose values in single quotes
                    - Include sap-statistics=true parameter

                Examples:
                    User: Show total orders by supplier
                    Thought: Need grouping by supplier with order count
                    Action: nl_to_odata("group by supplier and count orders")
                    Response: $apply=groupby((SUPPLIER),aggregate(ORDER_NO with count as Total))?sap-statistics=true

                    User: Find orders from supplier ABC created in 2023
                    Thought: Need filter for supplier and date range
                    Action: nl_to_odata("filter supplier equals ABC and creation date between 2023")
                    Response: $apply=filter(SUPPLIER eq 'ABC' and CREAT_DATE gt '2023-01-01' and CREAT_DATE lt '2023-12-31')?sap-statistics=true
                    """,
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
    
    endpoint = 'http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET?'
    api_url = endpoint + lines[3]
    
    print(api_url)
    
    response = call_odata_query(api_url)
    
    print(response)
    return response

def call_odata_query(endpoint: str):

    # Basic authentication credentials
    username = 'DEV_100'
    password = 'Nestle1330$'
    # Make the request
    response = requests.get(endpoint, auth=HTTPBasicAuth(username, password))
    print(response.status_code)


    if response.status_code == 200:
        # Convert XML to Python dictionary
        try:
            xml_data = xmltodict.parse(response.text)
            
            # Convert the dictionary to a JSON string
            json_data = json.dumps(xml_data, indent=4)
            
            # Print or work with the JSON data
            return json_data
        except Exception as e:
            print("Error parsing XML:", str(e))
    else:
        print(f"Error: Received response with status code {response.status_code}")

