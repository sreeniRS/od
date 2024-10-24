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

                Examples:
                    User: Show total orders by supplier
                    Thought: Need grouping by supplier with order count
                    Action: nl_to_odata("group by supplier and count orders")
                    Response: $apply=groupby((SUPPLIER),aggregate(ORDER_NO with count as Total))

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
    return Response(content=response, media_type="application/xml")  # Return raw XML with proper content type

def call_odata_query(endpoint: str):
    # Basic authentication credentials
    username = 'DEV_100'
    password = 'Nestle1330$'
    # Make the request
    response = requests.get(endpoint, auth=HTTPBasicAuth(username, password))
    print(response.status_code)

    if response.status_code == 200:
        return response.text  # Return the raw XML response text
    else:
        print(f"Error: Received response with status code {response.status_code}")
        raise HTTPException(status_code=response.status_code, detail="Error fetching OData")

class ConversationManager:
    def __init__(self, max_history: int = 3):
        self.conversation_history: List[Tuple[str, str]] = []
        self.max_history = max_history
        self.dataframe_storage: Dict[str, pd.DataFrame] = {}
        
    def store_dataframe(self, df: pd.DataFrame, name: Optional[str] = None) -> str:
        """
        Store a DataFrame with a unique identifier or custom name.
        Returns the storage key.
        """
        if name is None:
            name = f"df_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.dataframe_storage[name] = df
        return name
    
    def get_dataframe(self, name: str) -> Optional[pd.DataFrame]:
        """Retrieve a stored DataFrame by its name."""
        return self.dataframe_storage.get(name)
    
    def list_stored_dataframes(self) -> List[str]:
        """List all stored DataFrame identifiers."""
        return list(self.dataframe_storage.keys())
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history and maintain max history length."""
        self.conversation_history.append((role, content))
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def convert_to_messages(self) -> List[Any]:
        """Convert conversation history to LangChain message objects."""
        message_objects = []
        for role, content in self.conversation_history:
            if role == "user":
                message_objects.append(HumanMessage(content=content))
            elif role == "assistant":
                message_objects.append(AIMessage(content=content))
        return message_objects
    
    def format_dataframe_info(self, df: pd.DataFrame) -> str:
        """Format DataFrame with a row limit to avoid overloading the LLM context."""
        info = []
        info.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        info.append(f"Columns: {', '.join(df.columns.tolist())}")
        
        # Set a row limit for safety (e.g., only include the first 100 rows)
        row_limit = 100
        if df.shape[0] > row_limit:
            info.append(f"\nDisplaying the first {row_limit} rows (of {df.shape[0]}):")
            info.append(df.head(row_limit).to_string())
        else:
            info.append("\nComplete Data:")
            info.append(df.to_string())
        
        return "\n".join(info)


def insights_generation(prompt: str, df: pd.DataFrame, conversation_manager: Optional[ConversationManager] = None) -> dict:
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    
    try:
        df_key = conversation_manager.store_dataframe(df)
        formatted_data = conversation_manager.format_dataframe_info(df)
        user_message = f"{prompt}\nDataFrame '{df_key}':\n{formatted_data}"
        conversation_manager.add_message("user", user_message)

        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are a helpful assistant who answers user queries based on the provided data. "
                "Provide insights if asked. You have access to the full DataFrame in storage. "
                "Please return your response as a JSON string with 'reasoning', 'code', and 'output' keys. "
                "All three keys 'reasoning', 'code' and 'output' are to be populated with string values unless specified."
                "Print the output in a human readable manner, not the direct code output."
                "Most importantly, only return the json string. Nothing else."
            )),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{prompt}\n{data}")
        ])

        formatted_prompt = prompt_template.format_messages(
            history=conversation_manager.convert_to_messages(),
            prompt=prompt,
            data=formatted_data
        )

        llm = get_llm()  # Assuming this function exists
        ai_msg = llm(formatted_prompt)

        # Debugging: print the full AI message
        print(f"AI Message: {ai_msg}")

        # Access and clean message content
        message_content = ai_msg.content.strip()
        print(f"Raw AI Message Content: '{message_content}'")  # Debug print

        if not message_content:
            raise ValueError("Received empty response from the AI model.")

        # Clean the output to remove markdown formatting
        message_content = message_content.replace("```json", "").replace("```", "").strip()

        # Parse the JSON string
        try:
            parsed_output = json.loads(message_content)
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e} | Content: {message_content}")
            return {"reasoning": "Invalid JSON response", "code": "400", "output": None}

        conversation_manager.add_message("assistant", message_content)

        return parsed_output
    except Exception as e:
        print(f"An exception occurred: {e}")
        return {"reasoning": str(e), "code": "500", "output": None}





