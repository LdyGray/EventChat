import streamlit as st
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain_core.runnables import RunnableBranch
from langchain_core.output_parsers import StrOutputParser
import os

llm = OpenAI(openai_api_key=st.secrets["MyOpenAIKey2"])


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
    (lambda x: "Add" in x["issue_type"], positive_chain),
    (lambda x: "Remove" in x["issue_type"], nofault_chain),
    lambda x: fault_chain,
)
full_chain = {"issue_type": issue_type_chain, "content": lambda x: x["content"]} | branch

# streamlit app layout
st.title("Airline Experience Feedback")
prompt = st.text_input("Use me to update your calendar", "Add an event, remove an event, ask for today's schedule")

# Run the chain
response = full_chain.invoke({"content": prompt})

