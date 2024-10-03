import streamlit as st
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain_core.runnables import RunnableBranch
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from gcsa.recurrence import Recurrence, DAILY, SU, SA

from beautiful_date import Jan, Apr
import os

llm = OpenAI(openai_api_key=st.secrets["MyOpenAIKey2"]


calendar = GoogleCalendar('grayh@bu.edu')
event = Event(
    'Breakfast',
    start=(1 / Jan / 2019)[9:00],
    recurrence=[
        Recurrence.rule(freq=DAILY),
        Recurrence.exclude_rule(by_week_day=[SU, SA]),
        Recurrence.exclude_times([
            (19 / Apr / 2019)[9:00],
            (22 / Apr / 2019)[9:00]
        ])
    ],
    minutes_before_email_reminder=50
)

calendar.add_event(event)

for event in calendar:
    print(event)

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

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: msgs,  # Always return the instance created earlier
    input_messages_key="question",
    history_messages_key="history",
)


for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

if prompt := st.chat_input():
    st.chat_message("human").write(prompt)

    # As usual, new messages are added to StreamlitChatMessageHistory when the Chain is called.
    config = {"configurable": {"session_id": "any"}}
    response = chain_with_history.invoke({"question": prompt}, config)
    st.chat_message("ai").write(response.content)



# Function to authenticate with Google Calendar API
def authenticate_google_calendar():
    # Load the credentials from Streamlit secrets
    credentials_info = st.secrets["gcp_service_account"]
    
    creds = service_account.Credentials.from_service_account_info(
        credentials_info
    )
    
    # Create the Google Calendar service
    calendar_service = build('calendar', 'v3', credentials=creds)
    return calendar_service

### Create the decision-making chain
issue_template = """You are a personal assistant.
From the following content, determine whether the user is doing one of the following three things:
* Add: The user would like to add an event to their calendar.
* Remove: The user would like to remove an event from their calendar.
* SeeSchedule: The user would like to see a list of the events on their calendar for today.

Only respond with Add, Remove, or SeeSchedule.

Content:
{content}

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




Content:
{Content}

"""
) | llm


#### Case 2: Remove
nofault_chain = PromptTemplate.from_template(
    """You are a personal assistant. 

Remove the event described from the user's calendar.




Content:
{Content}

"""
) | llm


#### Case 3: SeeSchedule
fault_chain = PromptTemplate.from_template(
    """You are a personal assistant. 

Provide a list of the events on the user's calendar for the day, including the event title and start and end time.




Content:
{Content}

"""
) | llm



### Put all the chains together
branch = RunnableBranch(
    (lambda x: "Add" in x["issue_type"], add_chain),
    (lambda x: "Remove" in x["issue_type"], remove_chain),
    lambda x: fault_chain,
)
full_chain = {"issue_type": issue_type_chain, "content": lambda x: x["content"]} | branch

# streamlit app layout
st.title("Calendar Update Bot")
prompt = st.text_input("Use me to update your calendar", "Add an event, remove an event, ask for today's schedule")

# Run the chain
response = full_chain.invoke({"content": prompt})

