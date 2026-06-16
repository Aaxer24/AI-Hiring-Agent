from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from config.settings import settings

llm = ChatOpenAI(model=settings.openai_chat_model, temperature=0)

prompt = PromptTemplate(
    input_variables=["jd"],
    template="""
Convert the job description into structured JSON with:
role, skills, experience, priority_weights.

JD:
{jd}
"""
)

def process_jd(jd_text: str) -> str:
    return llm.invoke(prompt.format(jd=jd_text)).content
