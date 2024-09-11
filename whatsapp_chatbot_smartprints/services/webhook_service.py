import httpx
from langchain_core.messages import SystemMessage
from threading import Thread
from utility import load_template

RESET_KEYWORD = '/reset'

class WebhookService:
    def __init__(self, graph_api_token, verify_token, llm_service):
        self.graph_api_token = graph_api_token
        self.verify_token = verify_token
        self.llm_service = llm_service
        self.messages = {}

    def handle_webhook(self, data):
        message = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [{}])[0]
        
        if message.get('type') == 'text':
            business_phone_number_id = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('metadata', {}).get('phone_number_id')
            
            self.mark_as_read(business_phone_number_id, message['id'])
            
            print(f"You received a message from {message['from']} saying:\n{message['text']['body']}")
            
            if message['text']['body'].strip() == RESET_KEYWORD:
                self.messages = {}
            else:
                Thread(target=self.reply_using_llm, 
                    args=[business_phone_number_id, 
                            message['from'], 
                            message['text']['body'], 
                            message['id']]
                ).start()
        
        return '', 200

    def mark_as_read(self, business_phone_number_id, message_id):
        httpx.post(
            f"https://graph.facebook.com/v20.0/{business_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {self.graph_api_token}"},
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }
        )

    def reply_using_llm(self, business_phone_number_id, to, body, replied_to=None):
        chat_history = self.messages.get(to, 
                                         [SystemMessage(content=load_template('system'))]
                                         ).copy()
        
        llm_response, updated_chat_history = self.llm_service.generate_response(chat_history, body)
        
        self.messages[to] = updated_chat_history
        
        self.send_message(business_phone_number_id, to, llm_response, replied_to)

    def send_message(self, business_phone_number_id, to, body, replied_to=None):
        url = f"https://graph.facebook.com/v20.0/{business_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.graph_api_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        
        if replied_to:
            data['context'] = {"message_id": replied_to}
        
        httpx.post(url, headers=headers, json=data)