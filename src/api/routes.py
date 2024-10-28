import requests, datetime
from requests.auth import HTTPBasicAuth
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response  # Import the Response class
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import List, Tuple, Any, Dict, Optional
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
import json


from src.tools.nl_to_odata_tool import nl_to_odata
from src.aiagents.nl2odata_agent import create_graph
from src.llm.llm import get_llm
import pandas as pd


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
                6) CreateDate - This is the date of creation of a particular purchase order or order number
                7) MATERIAL - This is the material used for the Line item
                8) STORE_NAME - This is the plant where the material is manufactured
                9) UNIT_COST - This is the amount for the order for a particular line item 
                10) MATERIAL_DESC - This is the description of the material used
                11) SUP_NAME - This is the supplier name.
            Time Period Definitions:
                - Q1: April 1 to June 30
                - Q2: July 1 to September 30
                - Q3: October 1 to December 31
                - Q4: January 1 to March 31

                - First Half or H1: April 1 to September 30
                - Second Half or H2: October 1 to March 31
                - Last Quarter: Previous 3 months from current date
                - Last Year: Previous year from current date
                - fiscal year : April 1 to next year's March 31
                - YTD: January 1 to current date of current year
            Process:
                1. Thought: Analyze query requirements (filtering, grouping, aggregation)
                2. Action: Use nl_to_odata tool 
                3. Observation: Verify syntax and completeness
                4. Response: Return OData query.
            Rules:
                - Use $apply for aggregations/grouping
                - Handle date ranges in YYYYMMDD format
                - Enclose values in single quotes
            Examples:
                User: Show total orders by supplier
                Thought: Need grouping by supplier with order count
                Action: nl_to_odata("group by supplier and count orders")
                Response: $apply=groupby((SUPPLIER),aggregate(ORDER_NO with count as Total))

                User: Find orders from supplier ABC created in 2023
                Thought: Need filter for supplier and date range
                Action: nl_to_odata("filter supplier equals ABC and creation date between 2023")
                Response: $filter(SUPPLIER eq 'ABC' and CREAT_DATE gt '20230101' and CREAT_DATE lt '20231231')

                User: Show orders from Q1 2023
                Thought: Need filter for Q1 date range
                Action: nl_to_odata("filter creation date in Q1 2023")
                Response: $filter=CreateDate ge '20230401' and CreateDate le '20230630'

                User: Show orders from H1 2023
                Thought: Need filter for first half year range
                Action: nl_to_odata("filter creation date in first half 2023")
                Response: $filter=CreateDate ge '20230401' and CreateDate le '20230930'
                
                *** FOLLOW THE DEFINITNIONS FOR THE INDIAN FINANCIAL YEAR FOR DATE RELATED QUERIES ***
                *** OUTPUT ONLY THE ODATA QUERY ****
                
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
    else:
        print("No valid content found between newlines")
    
    endpoint = 'http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata4/sap/zsb_po_grn_sb4/srvd_a2x/sap/zsd_po_grn_det/0001/ZC_GRN_PO_DET?'
    api_url = endpoint + result[-1] + "&$count=True"
    
    print(api_url)
    
    response_content = call_odata_query(api_url)
    print(type(response_content))  
    return response_content

def call_odata_query(endpoint: str):
    # Basic authentication credentials
    username = 'RT_F_002'
    password = 'Teched@2024'
    # Make the request
    response = requests.get(endpoint, auth=HTTPBasicAuth(username, password))
    print(response.status_code)

    if response.status_code == 200:
        try:
            # Attempt to parse JSON content
            json_response = response.json()
            return json_response
        except ValueError:  # If JSON decoding fails
            print("Error: Response is not in JSON format.")
            raise HTTPException(status_code=500, detail="Response is not in JSON format")
    else:
        print(f"Error: Received response with status code {response.status_code}")
        print(response.text)
        raise HTTPException(status_code=response.status_code, detail="Error fetching OData")

