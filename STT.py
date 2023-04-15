import json
import os
import wave
import time
import requests

from pydub import AudioSegment

from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)

vk_token = '' # Создаём приложение в вк и купируем токен

class find_and_convert_number:
    def replace_const(self, text: list):
        find = False # если найдём хоть одно число станет True

        const_nums = {
            'один': 1, 'два': 2, 'три': 3, 'четыре': 4,
            'пять': 5, 'шесть': 6, 'семь': 7, 'восемь': 8,
            'девять': 9, 'десять': 10, 'двадцать': 20,
            'тридцать': 30, 'сорок': 40, 'пятьдесят': 50, 
            'шестьдесят': 60, 'семьдесят': 70, 'восемьдесят': 80, 
            'девяносто': 90, 'сто': 100, 'двести': 200, 
            'триста': 300, 'четыреста': 400, 'пятьсот': 500,
            'шестьсот': 600, 'семьсот': 700, 'восемьсот': 800, 
            'девятьсот': 900, 'тысяча': 1000, 'полтора': 1.5,
            'одинадцать': 11, 'двенадцать': 12, 'тринадцать': 13, 
            'четырнадцать': 14, 'пятнадцать': 15, 'шестнадцать': 16,
            'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
            'ноль': 0, 'тысяч': 1000
        }

        for word in text:
            if word in const_nums.keys():
                find = True

                index = text.index(word) # берём первое попавшееся слово, совпадающее с числительным

                text.insert(index, const_nums[word]) # вставляем на место этого слова число

                text.pop(index + 1) # удаляем слово
        
        return find

    def bitwise_compare(self, num_1: int, num_2: int):
        if num_1 == 10:
            return False
        
        num_1 = str(num_1)
        num_1 = int(num_1[len(num_1) - len(str(num_2)):]) # удаляем лишние разряды в начале

        if num_1 == 0:
            return True
        
        else:
            return False

    def num_to_num(self, text: list):
        if not self.replace_const(text):
            return

        while True:
            for index in range(len(text) - 1):
                num = text[index] # получаем число из списка

                try: 
                    if type(num) == type(str()) or type(text[index + 1]) == type(str()): # если это не число и следущее слово тоже не число, то пропускаем
                        continue

                    elif num > text[index + 1] and self.bitwise_compare(num, text[index + 1]): # если следущее за числом больше предыдущего, то пропускаем
                        num += text[index + 1]

                        text.insert(index, num)

                        text.pop(index + 1) # удаляем предыдущее число
                        text.pop(index + 1) # и следущее за ним число, так как его мы прибавили

                        break # когда изменили одно значание, то перезапускаем поиск

                    else:
                        continue
                
                except: # если выехали за массив, то выключаем поиск
                    break
            
            else:
                break
        
        return
    
    def convert(self, text: str):
        if not text:
            return text
        
        text = text.rsplit()
        
        self.num_to_num(text)

        return ' '.join((str(word) for word in text))

class voice_to_text(find_and_convert_number):
    model = Model('model')

    vk_data = {
        'access_token': vk_token,
        'upload_token': {
            'url': None,
            'death_time': 0
        }
    }

    def audio_convert(self, path: str): # конвертация гс и кружочков в wav
        voice = AudioSegment.from_file(path)

        voice.export(path, 'wav', parameters = ['-ar', '16000' , '-ac', '1', '-f', 's16le', '-'])

        return

    def offline_stt(self, path): # внутренняя служба расшифровки
        self.audio_convert(path)
        
        stt = KaldiRecognizer(self.model, 48000)

        with wave.open(path, 'rb') as wf:
            data = 1
            while data:
                data = wf.readframes(4000)

                stt.AcceptWaveform(data)
        
        text = json.loads(stt.FinalResult())['text']

        return text
    
    def __get_upload_url(self):
        if self.vk_data['upload_token']['url'] and self.vk_data['upload_token']['death_time'] > time.time():
            return self.vk_data['upload_token']['url']
        
        response = requests.get(
            url = 'https://api.vk.com/method/asr.getUploadUrl',
            params = {
                'access_token': self.vk_data['access_token'],
                'v': 5.131
            }
        ).json()

        self.vk_data['upload_token']['url'] = response['response']['upload_url']

        self.vk_data['upload_token']['death_time'] = time.time() + 85000

        return self.vk_data['upload_token']['url']
    
    def vk(self, path):
        url = self.__get_upload_url()

        with open(path, 'rb') as voice:
            response = requests.post(
                url = url,
                files = {
                    'file': voice.read()
                }
            ).text
        
        if eval(response).get('error_code'):
            raise Exception(response['error_msg'])
        
        response = requests.get(
            url = 'https://api.vk.com/method/asr.process',
            params = {
                'access_token': self.vk_data['access_token'],
                'audio': response,
                'model': 'spontaneous',
                'v': 5.131
            }
        ).json()

        while True:
            temp = requests.get(
                url = 'https://api.vk.com/method/asr.checkStatus',
                params = {
                    'access_token': self.vk_data['access_token'],
                    'task_id': response['response']['task_id'],
                    'v': 5.131
                }
            ).json()

            if temp['response']['status'] == 'finished':
                return temp['response']['text']
            
            elif temp['response']['status'] == 'processing':
                time.sleep(0.2)
            
            else:
                raise Exception('Вк говно')
    
    def with_app(self, path: str, app: str = 'offline'):
        apps = {
            'vosk': 'self.convert(self.offline_stt(path))',
            'vk': 'self.vk(path)'
        }

        try:
            text = eval(apps[app])
        
        except:
            text = ''
        
        os.remove(path)
        return text

stt = voice_to_text()