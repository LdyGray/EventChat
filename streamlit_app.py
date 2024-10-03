import streamlit as st
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain_core.runnables import RunnableBranch
from langchain_core.output_parsers import StrOutputParser
import os

llm = OpenAI(openai_api_key=st.secrets["MyOpenAIKey2"])
key = st.secrets["MyOpenAIKey2"]

# Just following this: https://python.langchain.com/docs/integrations/memory/streamlit_chat_message_history/
import streamlit as st
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI


# # Optionally, specify your own session_state key for storing messages
msgs = StreamlitChatMessageHistory(key="special_app_key")

if len(msgs.messages) == 0:
    msgs.add_ai_message("How can I help you?")


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an AI personal assistant helping a human manage their calendar."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)

llm = ChatOpenAI(api_key=st.secrets["MyOpenAIKey2"])
chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: msgs,  # Always return the instance created earlier
    input_messages_key="question",
    history_messages_key="history",
)


import streamlit as st

for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

if prompt := st.chat_input():
    st.chat_message("human").write(prompt)

    # As usual, new messages are added to StreamlitChatMessageHistory when the Chain is called.
    config = {"configurable": {"session_id": "any"}}
    response = chain_with_history.invoke({"question": prompt}, config)
    st.chat_message("ai").write(response.content)


### Create the decision-making chain
issue_template = """You are a personal assistant.
From the following content, determine whether the user is doing one of the following three things:
* Add: The user would like to add an event to their calendar.
* Remove: The user would like to remove an event from their calendar.
* SeeSchedule: The user would like to see a list of the events on their calendar for today.

Only respond with Add, Remove, or SeeSchedule.

review:
{review}

"""
issue_type_chain = (
    PromptTemplate.from_template(issue_template)
    | llm
    | StrOutputParser()
)


#### Case 1: Add
positive_chain = PromptTemplate.from_template(
       """You are a personal assistant. 

Add the event described to the user's calendar.




review:
{review}

"""
) | llm


#### Case 2: Remove
nofault_chain = PromptTemplate.from_template(
    """You are a personal assistant. 

Remove the event described from the user's calendar.




review:
{review}

"""
) | llm


#### Case 3: SeeSchedule
fault_chain = PromptTemplate.from_template(
    """You are a personal assistant. 

Provide a list of the events on the user's calendar for the day, including the event title and start and end time.




review:
{review}

"""
) | llm



### Put all the chains together
branch = RunnableBranch(
    (lambda x: "Add" in x["issue_type"], add_chain),
    (lambda x: "Remove" in x["issue_type"], remove_chain),
    lambda x: SeeSchedule_chain,
)
full_chain = {"issue_type": issue_type_chain, "review": lambda x: x["review"]} | branch

# streamlit app layout
st.title("Airline Experience Feedback")
prompt = st.text_input("Share with us your experience of the latest trip", "My trip was awesome")

# Run the chain
response = full_chain.invoke({"review": prompt})

