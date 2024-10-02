from icecream import ic
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import NumberedListOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_groq import ChatGroq
from langfuse.callback import CallbackHandler

from utility import check_text_language
from utility import load_template

class LLMService:
    def __init__(self, model_name, chroma_service):
        self.llm = ChatGroq(model=model_name, temperature=0.0)
        self.chroma_service = chroma_service
        self.langfuse_handler = CallbackHandler()
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

    def generate_response(self, current_session, query, user_phonenumber):
        query = query.encode('utf-8').decode()
        chat_history = current_session.messages
        new_message = HumanMessagePromptTemplate.from_template(load_template('chat'))
        
        translated_query = self.query_translator.invoke({
            'history': self._format_history(chat_history[-2:]),
            'message': query
            }
        )
        
        message_language = check_text_language(query)
        context = self.chroma_service.retrieve(translated_query, 
                                               message_language, 
                                               score_threshold=.5, 
                                               k=7)    
        ic(query)
        ic(translated_query)
        ic(message_language)
        new_message_formatted = new_message.format(
            history=self._format_history(chat_history[1:]), 
            context=self._format_context(context), 
            message=query,
            language= message_language
            )
        
        
        ic(new_message_formatted)
        # llm_response = self.rag_chain.invoke(chat_history[:] + [new_message_formatted])
        config = {
            "callbacks": [self.langfuse_handler],
            "run_name": "chat",
            "metadata": {
                "langfuse_session_id": current_session.id,
                "langfuse_user_id": user_phonenumber,
                "input":query
            },
        }
        if len(chat_history) > 3:
            llm_response = self.rag_chain.invoke(input=chat_history[:1] + chat_history[-2:] + [new_message_formatted],
                                                 config=config)
        else:
            llm_response = self.rag_chain.invoke(input=chat_history[:1] + [new_message_formatted],
                                                 config=config)
        
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
