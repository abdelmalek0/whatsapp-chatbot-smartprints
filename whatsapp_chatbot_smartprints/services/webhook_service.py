import os
from threading import Thread

import httpx
import neuralspace as ns
from groq import Groq
from icecream import ic
from langchain_core.messages import SystemMessage
from pydub import AudioSegment

from structs.session import Session
from utility import load_template

RESET_KEYWORD = '/reset'

class WebhookService:
    def __init__(self, graph_api_token, verify_token, llm_service, audio_storage):
        self.graph_api_token = graph_api_token
        self.verify_token = verify_token
        self.llm_service = llm_service
        self.audio_storage = audio_storage

        # self.recognizer = whisper.load_model("medium.en")
        self.groq_client = Groq()
        self.vai = ns.VoiceAI()
        self.vai_config = {
            "file_transcription": {
                "mode": "advanced",
            },
            "sentiment_detect": False
        }
        self.sessions = {}

    def handle_webhook(self, data):
        message = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [{}])[0]
        business_phone_number_id = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('metadata', {}).get('phone_number_id')
        
        if message.get('type') == 'text':
            self.mark_as_read(business_phone_number_id, message['id'])  
            print(f"You received a message from {message['from']} saying:\n{message['text']['body']}")
            
            if message['text']['body'].strip() == RESET_KEYWORD:
                if message['from'] in self.sessions:
                    del self.sessions[message['from']]
            else:
                Thread(target=self.reply_using_llm, 
                    args=[business_phone_number_id, 
                            message['from'], 
                            message['text']['body'], 
                            message['id']]
                ).start()
        if message.get('type') == 'audio':
            self.mark_as_read(business_phone_number_id, message['id'])  
            # Replace with your WhatsApp API credentials and message details
            base_url = 'https://graph.facebook.com/v20.0/'  # Adjust this URL based on the WhatsApp API you are using
            media_id = message.get('audio').get('id')

            # Construct the URL for downloading the media
            media_url = f"{base_url}{media_id}"
            headers = {
                "Authorization": f"Bearer {self.graph_api_token}",
                "Content-Type": "application/json"
            }
            # Send a GET request to download the media
            response = httpx.get(media_url, headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                Thread(target=self.handle_audio,
                       args=[
                           response.json()['url'],
                           message,
                           business_phone_number_id, 
                        ]
                ).start()
            else:
                print(f"Failed to download audio. Status code: {response.status_code}")
            
        return '', 200

    def mark_as_read(self, business_phone_number_id, message_id):
        response = httpx.post(
            f"https://graph.facebook.com/v20.0/{business_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {self.graph_api_token}"},
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }
        )
        ic(response.json())

    def reply_using_llm(self, business_phone_number_id, to, body, replied_to=None):
        current_session = self.sessions.get(to, Session([SystemMessage(content=load_template('system'))]))
        llm_response, updated_chat_history = self.llm_service.generate_response(current_session, body, to)
        
        current_session.update_messages(updated_chat_history)
        self.sessions[to] = current_session
        
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
    
    def ogg_to_wav(self, ogg_path: str, wav_path: str):
        # Convert OGG file to WAV format
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")

    def transcribe_offline(self, audio_filename):
        result = self.recognizer.transcribe(audio_filename)
        return result['text'].strip()
    
    def transcribe_using_groq(self, audio_filename: str) -> str :
        with open(audio_filename, "rb") as file:
            transcription = self.groq_client.audio.transcriptions.create(
            file=(audio_filename, file.read()), # Required audio file
            model="whisper-large-v3", # Required model to use for transcription
            response_format="json",
            prompt="Transcribe only avoid translation.",
            temperature=0.0,
            )
        return transcription.text.strip()

    def transcribe_using_neuralspace(self, audio_filename: str)-> str:
        job_id = self.vai.transcribe(file=audio_filename, config=self.vai_config)
        result = self.vai.poll_until_complete(job_id)
        content = result["data"]["result"]["transcription"]["channels"]["0"]["transcript"]
        return content.strip()
        
    def handle_audio(self, audio_url, message, business_phone_number_id):
        headers = {
            "Authorization": f"Bearer {self.graph_api_token}",
            "Content-Type": "application/json"
        }
        ogg_audio_filepath = os.path.join(self.audio_storage, f"temp_{message['from']}.ogg")
        wav_audio_filepath = os.path.join(self.audio_storage, f"temp_{message['from']}.wav")
        # get audio data
        with open(ogg_audio_filepath, 'wb') as file:
            file.write(httpx.get(audio_url, headers=headers).content)
        # convert to correct format
        self.ogg_to_wav(ogg_audio_filepath, 
                        wav_audio_filepath)
        
        # language detection and trascription
        # message_body = self.transcribe_using_groq(wav_audio_filepath)
        message_body = self.transcribe_using_neuralspace(wav_audio_filepath)

        print(f"You received an audio message from {message['from']} saying:\n{message_body}")
        # reply using llm
        Thread(target=self.reply_using_llm, 
               args=[business_phone_number_id, 
                    message['from'], 
                    message_body, 
                    message['id']]
            ).start()
