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


from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

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
                12) CURRENCY_CODE - This is the Currency Code which is used for the particular Cost
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
    print(response_content) 
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
    
    #def convert_to_messages(self) -> List[Any]:
    #   """Convert conversation history to LangChain message objects."""
    #    message_objects = []
    #   for role, content in self.conversation_history:
    #        if role == "user":
    #            message_objects.append(HumanMessage(content=content))
    #        elif role == "assistant":
    #            message_objects.append(AIMessage(content=content))
    #   return message_objects
    
    #def format_dataframe_info(self, df: pd.DataFrame) -> str:
    #    """Format DataFrame with a row limit to avoid overloading the LLM context."""
    #    info = []
    #    info.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    #    info.append(f"Columns: {', '.join(df.columns.tolist())}")
        
        # Set a row limit for safety (e.g., only include the first 100 rows)
    #    row_limit = 100
    #    if df.shape[0] > row_limit:
    #        info.append(f"\nDisplaying the first {row_limit} rows (of {df.shape[0]}):")
    #        info.append(df.head(row_limit).to_string())
    #    else:
    #        info.append("\nComplete Data:")
    #       info.append(df.to_string())
        
    #    return "\n".join(info)

def insights_generation(prompt: str, df: pd.DataFrame, conversation_manager: Optional[ConversationManager] = None) -> dict:
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    
    try:
        df_key = conversation_manager.store_dataframe(df)
        #formatted_data = conversation_manager.format_dataframe_info(df)
        #user_message = f"{prompt}\nDataFrame '{df_key}':\n{formatted_data}"
        conversation_manager.add_message("user", prompt)

        agent = create_pandas_dataframe_agent(
            llm=get_llm(),
            df = df,
            verbose=True, 
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True
        )

        #json compliant string format
        safe_prompt = prompt.replace('\n', '\\n') + "\nPlease respond in Json format with keys 'reasoning', 'code', and 'output'."

        ai_response = agent.invoke(safe_prompt)

        #printing the raw response
        #print(f"Raw AI response: {ai_response}")
        #
        #Extract the output for processing
        response_content = ai_response.get("output")

        if not response_content:
            raise ValueError("No output received from the agent")


        # Remove Markdown formatting if present
        if response_content.startswith("```json"):
            response_content = response_content[7:]  # Remove initial ```json
        if response_content.endswith("```"):
            response_content = response_content[:-3]  # Remove trailing ```

        try:
            #respose_content = ai_response.get("arguments", "")
            parsed_output = json.loads(response_content.strip())
            # Add Ai response to the conversational history
            conversation_manager.add_message("assistant", response_content)
            return parsed_output
        except json.JSONDecodeError:
            print(f"Non -Json Response: {response_content}")
            return {"reasoning": "Received plain text insted of Json",
                    "code": "400",
                    "output": None}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"reasoning": str(e), "code": "500", "output":None}
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





