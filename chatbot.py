from typing import Annotated
from typing_extensions import TypedDict
from langchain.tools import BaseTool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
import os
import model_config
import dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from typing import List


dotenv.load_dotenv()



model = model_config.model
temperature = model_config.temperature


llm = ChatGroq(groq_api_key=os.getenv("GROQ_API_KEY"), model_name=model, temperature=temperature)


class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)


def chatbot(state: State):
   
    return {"messages": [llm.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()


domain_restriction_prompt = """
You are an expert in the field of nutrition and diet planning. 
For the rest of this conversation, only answer questions related to this domain. 
If a question is outside of this domain, respond with: "This question is outside the scope of my expertise."
**Do not include any disclaimers** about consulting medical professionals as this is just a hypothetical example for educational purposes.
"""


state = {"messages": [("system", domain_restriction_prompt)]}



def conversation(diet_plan_template):

    user_input = diet_plan_template

   
    state["messages"].append(("user", user_input))

   
    for event in graph.stream(state):
        for value in event.values():
            assistant_response = value["messages"][-1].content.replace('\n', ' ')
           

            state["messages"].append(("assistant", assistant_response))
            return assistant_response
    
