from utils import encode_word_vec, pad_sequence
import numpy as np
from keras.models import load_model
import pickle
from controllers.chat_controller import ChatController
from controllers.planning_controller import PlanningController
from controllers.general_controller import GeneralController
from controllers.iot_controller import IOTController
from response_model import *

class VirtualAssistant(object):
    def __init__(self, name, address, mqtt_broker, location, intent_model, vocab_file, debug=False):
        self.NAME = name
        self.ADDRESS = address
        self.DEBUG = debug

        self.intent_model = load_model(intent_model)
        self.word_to_int, self.int_to_label, self.seq_length = pickle.load(open(vocab_file, 'rb'))
        self.CONF_THRESH = 85

        self.chatControl = ChatController(debug=debug)
        self.planningControl = PlanningController(self.ADDRESS, debug=debug)
        self.generalControl = GeneralController(self.ADDRESS, location, debug=debug)       
        self.iotControl = IOTController(self.ADDRESS, mqtt_broker, debug=debug) 

        intent, conf = self.predict_intent('bigblankbig')

    def log(self, text, end='\n'):
        if self.DEBUG:
            print(text, end=end)

    def understand(self, command):
        
        response = None
        intent = ''
        conf = 0.0
        if f'hey {self.NAME}' == command or f'yo {self.NAME}' == command or self.NAME == command:
            response = Response(f'Yes {self.ADDRESS}?')
            intent = 'wakeup'
            conf = 100.0
        elif 'shut down' in command:
            response = Response(f'Ok {self.ADDRESS}, see you soon')
            intent = 'shutdown'
            conf = 100.0
        elif 'thanks' == command or f'thanks {self.NAME}' == command:
            response = Response(f'No problem {self.ADDRESS}')
            intent = 'thanks'
            conf = 100.0
        else:
            if not response:
                response = Response('')
                words = command.split()
                if self.NAME in words[0]:
                    words[0] = ''
                command = ' '.join(words)
            
                if command:
                    
                    intent, conf = self.predict_intent(command.replace(self.NAME, 'bignamebig'))
                    
                    self.log(f'intent: {intent} | conf: {conf}')

                    if conf > self.CONF_THRESH:
                        if intent == 'greeting':
                            response =  self.greeting(command)

                        if intent == 'goodbye':
                            response = self.goodbye()

                        if intent == 'schedule':
                            response = self.planningControl.check_calendar(command)

                        if intent == 'play':
                            #need to work on extracting subject
                            response = self.generalControl.play(command)

                        if intent == 'time':
                            response = self.generalControl.get_time(command)
                        
                        if intent == 'weather':
                            response = self.generalControl.get_weather(command)

                        if intent == 'lookup':
                            response = self.generalControl.search(command)
                        
                        if intent == 'volume':
                            response = self.generalControl.volume(command)

                        if intent == 'reminder':
                            #todo
                            response = self.planningControl.set_reminder(command)

                        if intent == 'math':
                            #todo
                            response = self.generalControl.answer_math(command)

                        if intent == 'lights':
                            response = self.iotControl.light_control(command)
                    '''
                    if not response:
                        response = self.chatControl.chat(command)
                    '''
                    
        return (response, intent, conf)

    def greeting(self, command):
        if 'morning' in command:
            return f'Good morning {self.ADDRESS}'
        elif 'afternoon' in command:
            return f'Good afternoon {self.ADDRESS}'
        elif 'night' in command:
            return f'Good night {self.ADDRESS}'
        return f'Hello {self.ADDRESS}'

    def goodbye(self):
        return f'Goodbye {self.ADDRESS}, I\'ll talk to you later'     

    def predict_intent(self, text):
        encoded = encode_word_vec(text, self.word_to_int)
        padded = pad_sequence(encoded, self.seq_length)
        prediction = self.intent_model.predict(np.array([padded]))[0]
        argmax = np.argmax(prediction)
        return self.int_to_label[argmax], round(float(prediction[argmax])*100, 3)

    @property
    def name(self):
        return self.NAME

    @property
    def address(self):
        return self.ADDRESS

    def reset_chat(self):
        self.log('Chat reset')
        self.chatControl.reset_chat()
            
