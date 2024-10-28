# File meant for the logic and state of the Insight Generation Agent

from langchain.prompts import ChatPromptTemplate
#This is where you define general agent 


def create_agent_node(agent, state, name):
    pass


def create_agent(prompt, ):

    system_prompt = ChatPromptTemplate.from_message({
        [('system', 'You are a helpful AI assistant who answers whatever question that is provided with useful output.')]
    })

    pass


def create_agent_node_template(state, name):
    return lambda x: create_agent_node(x, state, name)


