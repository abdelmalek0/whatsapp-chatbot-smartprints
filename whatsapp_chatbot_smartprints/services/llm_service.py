from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser, NumberedListOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from utility import load_template

class LLMService:
    def __init__(self, model_name, chroma_service):
        self.llm = ChatOllama(model=model_name, temperature=0.0)
        self.chroma_service = chroma_service
        self.rag_chain = self.llm | StrOutputParser()
        self.topic_extractor = (
            ChatPromptTemplate.from_template(template=load_template('topic'))
            | self.llm 
            | NumberedListOutputParser()
        )
        self.summarizer = (
            ChatPromptTemplate.from_template(template=load_template('summary'))
            | self.llm  
            | StrOutputParser()
        )

    def generate_response(self, chat_history, query):
        context = self.chroma_service.retrieve(query)
        new_message = HumanMessagePromptTemplate.from_template(load_template('chat'))
        new_message_formatted = new_message.format(
            history=self.format_history(chat_history[1:]), 
            context=context, 
            question=query
            )
        # print('#'*50)
        # print(self.format_history(chat_history[1:]))
        chat_history.append(HumanMessage(content=query))
        
        llm_response = self.rag_chain.invoke(chat_history[:-1] + [new_message_formatted])
        # print('&'*50)
        # print(new_message_formatted.content)
        # print('&'*50)
        # print(llm_response)
        # print('*'*50)
        chat_history.append(AIMessage(content=llm_response))
        return llm_response, chat_history
    
    def format_history(self, history):
        formatted_history = ""
        for message in history:
            if type(message) == HumanMessage:
                 formatted_history += f'\nHuman: {message.content}'
            elif type(message) == AIMessage:
                formatted_history += f'\nAI: {message.content}'
        return formatted_history