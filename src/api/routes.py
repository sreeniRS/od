import json, datetime, asyncio, time
from aiohttp import ClientSession, BasicAuth
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from typing import List, Tuple, Dict, Optional
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent


from src.tools.nl_to_odata_tool import nl_to_odata
from src.aiagents.nl2odata_agent import create_graph
from src.llm.llm import get_llm
from src.utils.call import call_odata


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
                - Enclose values in single quotes.
                
            Examples:
                User: Show total orders by supplier
                Thought: Need grouping by supplier with order count
                Action: nl_to_odata("group by supplier and count orders")
                Response: $apply=groupby((SUPPLIER, CURRENCY),aggregate(ORDER_NO with count as Total))

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
    
    # Extract messages from events and format them
    for event in events:
        for message in event['messages']:
            formatted_message = format_ai_message(message)
            result.append(formatted_message)
    
    if not result:
        raise HTTPException(status_code=400, detail="Failed to convert query")
    

    # Construct the API URL using the last formatted message
    filter = result[-1] + "&$count=True"
    
    print(filter)

    return call_odata(filter)    
    

############################## INSIGHTS_AGENT ##########################################################################
        #formatted_prompt = prompt_template.format_messages(
        #    history=conversation_manager.convert_to_messages(),
        #    prompt=prompt,
        #    data=formatted_data
        #)

        #llm = get_llm()  # Assuming this function exists
        #ai_msg = llm(formatted_prompt)

        # Debugging: print the full AI message
        #print(f"AI Message: {ai_msg}")

        # Access and clean message content
        #message_content = ai_msg.content.strip()
        #print(f"Raw AI Message Content: '{message_content}'")  # Debug print

        #if not message_content:
        #    raise ValueError("Received empty response from the AI model.")

        # Clean the output to remove markdown formatting
        #message_content = message_content.replace("```json", "").replace("```", "").strip()

        # Parse the JSON string
        #try:
        #    parsed_output = json.loads(message_content)
        #except json.JSONDecodeError as e:
        #    print(f"JSON decoding error: {e} | Content: {message_content}")
        #    return {"reasoning": "Invalid JSON response", "code": "400", "output": None}

        #conversation_manager.add_message("assistant", message_content)

        #return parsed_output
    #except Exception as e:
    #    print(f"An exception occurred: {e}")
    #    return {"reasoning": str(e), "code": "500", "output": None}





