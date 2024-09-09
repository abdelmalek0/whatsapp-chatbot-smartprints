from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from utility import load_template

class LLMService:
    def __init__(self, model_name, chroma_service):
        self.llm = ChatOllama(model=model_name, temperature=0.0)
        self.chroma_service = chroma_service
        self.rag_chain = self.llm | StrOutputParser()

    def generate_response(self, chat_history, query):
        context = self.chroma_service.retrieve(query)
        new_message = HumanMessagePromptTemplate.from_template(load_template('chat'))
        new_message_formatted = new_message.format(context=context, question=query)
        chat_history.append(new_message_formatted)
        
        llm_response = self.rag_chain.invoke(chat_history)
        
        chat_history.append(AIMessage(content=llm_response))
        return llm_response, chat_history