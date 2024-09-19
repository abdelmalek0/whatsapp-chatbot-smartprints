from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser, NumberedListOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from utility import load_template
from icecream import ic

class LLMService:
    def __init__(self, model_name, chroma_service):
        self.llm = ChatGroq(model=model_name, temperature=0.1)
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
        self.query_translator = (
            ChatPromptTemplate.from_template(load_template('query_translation'))
            | self.llm
            | StrOutputParser()
        )

    def generate_response(self, chat_history, query):
        
        new_message = HumanMessagePromptTemplate.from_template(load_template('chat'))
        ic(query)
        translated_query = self.query_translator.invoke({
            'history': self._format_history(chat_history[-2:]),
            'message': query
            }
        )
        ic(translated_query)
        # query_topic = self.topic_extractor.invoke(translated_query) 
        # query_topic = query_topic[0] if len(query_topic) else ""
        # ic(query_topic)
        context = self.chroma_service.retrieve(translated_query, score_threshold=.75, k=5)
        
        new_message_formatted = new_message.format(
            history=self._format_history(chat_history[1:]), 
            context=self._format_context(context), 
            message=query
            )
        
        
        ic(new_message_formatted)
        # llm_response = self.rag_chain.invoke(chat_history[:] + [new_message_formatted])
        if len(chat_history) > 3:
            llm_response = self.rag_chain.invoke(chat_history[:1] + chat_history[-2:] + [new_message_formatted])
        else:
            llm_response = self.rag_chain.invoke(chat_history[:1] + [new_message_formatted])
        
        # ic(new_message_formatted.content)
        ic(llm_response)

        chat_history.append(HumanMessage(content=translated_query))
        chat_history.append(AIMessage(content=llm_response))

        return llm_response, chat_history
    
    def _format_history(self, history):
        formatted_history = ""
        for message in history:
            if type(message) == HumanMessage:
                 formatted_history += f'\nCustomer: {message.content}'
            elif type(message) == AIMessage:
                formatted_history += f'\nSupport Agent: {message.content}'
        return formatted_history if formatted_history else 'EMPTY'
    
    def _format_context(self, context):
        formatted_context = ''
        for index, doc in enumerate(context):
            formatted_context += f'\nDocument {index + 1}: \"{doc.page_content.strip()}\"'
        return formatted_context if formatted_context else 'EMPTY'