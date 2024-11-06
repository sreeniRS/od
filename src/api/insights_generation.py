import datetime
from typing import List, Tuple, Any, Dict, Optional
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import json


from src.llm.llm import get_llm
import pandas as pd


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
        # df_key = conversation_manager.store_dataframe(df)
        #formatted_data = conversation_manager.format_dataframe_info(df)
        #user_message = f"{prompt}\nDataFrame '{df_key}':\n{formatted_data}"
        conversation_manager.add_message("user", prompt)

        agent = create_pandas_dataframe_agent(
            llm=get_llm(),
            df = df,
            verbose=True, 
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True,
            number_of_head_rows= 20
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



# New Version - Definition of Langgraph Agent

