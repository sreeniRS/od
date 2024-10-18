from src.utils.appconfig import AppConfig
from src.utils.azureai import AzureAI
from src.tools.nl_to_odata_tool import nl_to_odata
from src.agents.nl2odata_agent import create_graph
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

def format_ai_message(message):
    if isinstance(message, AIMessage):
        content = message.content.strip()
        if content:
            return f"AI: {content}"
        elif message.additional_kwargs.get('tool_calls'):
            tool_call = message.additional_kwargs['tool_calls'][0]
            return f"AI used tool: {tool_call['function']['name']}"
    return None


def main():
    config = AppConfig()
    azure_ai = AzureAI(config)

    llm = azure_ai.get_client()
    
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

    # Example usage
    tutorial_questions = [
        "Find customers where age greater than 30"
    ]

    for question in tutorial_questions:
        print(f"\nHuman: {question}")
        events = graph.stream(
            {"messages": ("user", question)}, stream_mode="values"
        )
        for event in events:
            if 'messages' in event:
                for message in event['messages']:
                    formatted_message = format_ai_message(message)
                    if formatted_message:
                        print(formatted_message)

if __name__ == "__main__":
    main()