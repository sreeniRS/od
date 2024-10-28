import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import List, Tuple, Any, Dict, Optional
from langchain_core.prompts import MessagesPlaceholder
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
            """You are working with a dataset containing information about orders, line items, suppliers, 
            and purchase details.

            A user will ask you natural language queries to generate insights or analyze this dataset. 
            Based on the user's query, you need to:

            1. **Understand the query**: Identify the key focus of the user's request (e.g., top suppliers, order trends, material usage, supplier performance).
            2. **Generate relevant insights**: Provide a detailed response based on the dataset, highlighting key statistics, patterns, trends, and any notable findings.
            3. **Perform data analysis**: Calculate averages, sums, or rankings if required, and provide relevant insights (e.g., "Top 5 suppliers by order value" or "Order trends over time").
            4. **Format your response**: Present the insights clearly, with concise explanations and numerical or categorical details where applicable. Make sure the analysis aligns with the user's request.
            5. **Include recommendations** (if relevant): Suggest actions based on the insights generated (e.g., focusing on top-performing suppliers or identifying areas for improvement).

            Use the following example queries to guide your analysis:
            - "Who are the top 5 suppliers by total order value?"
            - "What are the trends in order creation over the past six months?"
            - "Which materials are used the most across all orders?"
            - "How does Supplier A perform compared to other suppliers in terms of order value?"
            - "What is the distribution of purchase groups in the dataset?"

            Ensure that your responses are accurate, insightful, and based on the data provided. 
            If any calculations or data summaries are required, perform them as part of your analysis.
            ***Please return your response as a JSON string with 'reasoning', 'code', and 'output' keys. ***
            ***All three keys 'reasoning', 'code' and 'output' are to be populated with string values unless specified.***
            ***Print the output in a human readable manner, not the direct code output.***
            ***Most importantly, only return the json string. Nothing else.***
            """
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



# New Version - Definition of Langgraph Agent

