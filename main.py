from src.utils.appconfig import AppConfig
from src.utils.azureai import AzureAI
from src.tools.nl_to_odata_tool import nl_to_odata
from src.agents.nl2odata_agent import create_graph
from langchain_core.prompts import ChatPromptTemplate

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
        events = graph.stream(
            {"messages": ("user", question)}, stream_mode="values"
        )
        for event in events:
            print(event)
            print("--------------------------------------")
            human_message = event['messages'][0].content
            print("Human_message:", human_message)
            print("-------------------------------------")

if __name__ == "__main__":
    main()