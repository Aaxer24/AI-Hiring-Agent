from config.llm_factory import get_llm
from langchain_core.prompts import PromptTemplate

llm = get_llm()

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
