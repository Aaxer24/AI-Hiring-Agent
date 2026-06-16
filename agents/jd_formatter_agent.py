from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def format_for_platforms(jd_text):
    prompt = f"""
Format the following job description for:

1. LinkedIn
2. Indeed
3. Career Page

Provide clearly separated sections.

JD:
{jd_text}
"""
    return llm.invoke(prompt).content
