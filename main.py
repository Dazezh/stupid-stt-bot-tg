import requests
import random
import time
import telebot

from threading import Thread
from STT import stt

# ПРИВЕТ! Я не знаю зачем ты скачал этого бота, но удачи тебе

token = '' # Сюда вставь токен своего бота
admin = 0 # Сюда вставляем ID пользователя, ему будут сообщения с ошибками приходить

# Токен получаем у https://t.me/BotFather
# Свой ID можно получить у https://t.me/getmyid_bot

bot = telebot.TeleBot(token, parse_mode = 'Markdown')

me = bot.get_me()

class internal_function():
    session_stat = {
        'vk': [1, 1],
        'vosk': [1, 1]
    }

    query = {
        'now_recognition': 0,
        'query': []
    }
    
    def rewrite_and_compress(self, message: telebot.types.Message, action: str):
        bot.send_chat_action(message.from_user.id, 'typing', 1)
        bot.reply_to(message, '*Хорошо!✅* Ваш текст поставлен в обработку!')
        bot.send_chat_action(message.from_user.id, 'typing', 20)

        headers = {
            'accept': 'application/json',
        }

        json_data = {
            'instances': [
                {
                    'text': message.text,
                },
            ],
        }

        if action == 'rewrite': # если переписать текст, то добавляем способ выбора лучшего текста
            json_data['instances'][0]['range_mode'] = 'bertscore'
            json_data['instances'][0]['num_return_sequences'] = 4

            response = requests.post('https://api.aicloud.sbercloud.ru/public/v2/rewriter/predict', headers=headers, json=json_data)
        
        else:
            response = requests.post('https://api.aicloud.sbercloud.ru/public/v2/summarizator/predict', headers=headers, json=json_data)

        response = response.json()

        if not response.get('comment') or response.get('comment') == 'Ok':
            if action == 'rewrite':
                if response['prediction_best']['bertscore'] in response['predictions_all']: # если лучший вариант находится в списке всех, то удаляем
                    response['predictions_all'].pop(response['predictions_all'].index(response['prediction_best']['bertscore']))

                bot.send_message(message.from_user.id, f'*Лучший:*\n `{response["prediction_best"]["bertscore"]}`')

                for index in range(len(response['predictions_all']) - 1):
                    bot.send_message(message.from_user.id, f'*Вариант №{index + 1}*\n `{response["predictions_all"][index]}`')

                return
            
            else:
                bot.send_message(message.from_user.id, f'*Сжатый текст:*\n `{response["predictions"]}`')

        elif response.get('comment'):
            return bot.send_message(message.from_user.id, f'*Произошла ошибка!❌* Коментарий ИИ: `{response.get("comment")}`')
        
        else:
            return bot.send_message(message.from_user.id, '*Что-то пошло не так!❌* Не удалось обработать текст')

    def add_stat(self, message: telebot.types.Message, **other):        
        if message.voice:
            self.session_stat[other['service']][0] += message.voice.duration # длина расшифрованных сообщений определённым сервисом
            self.session_stat[other['service']][1] += other['recognition_time'] # потрачено на распознание персонально
        
        elif message.video_note: # точно также, но если кружочек
            self.session_stat[other['service']][0] += message.video_note.duration # длина расшифрованных сообщений определённым сервисом
            self.session_stat[other['service']][1] += other['recognition_time'] # потрачено на распознание персонально
        
        return
    
    def recognition(self, message, app):
        bot.edit_message_text(
            '*WOW!* Неужели твоя очередь!',
            message.chat.id,
            message.id
        )

        session_stat = self.session_stat

        temp = time.time()

        seconds_recognized = session_stat[app[0]][1] / session_stat[app[0]][0]
        
        if message.reply_to_message.content_type == 'voice': # это проверка на войс или кружочек
            file_id = message.reply_to_message.voice.file_id # id файла
            duration = message.reply_to_message.voice.duration # длина голосового
        
        else: # так же для кружочка
            file_id = message.reply_to_message.video_note.file_id
            duration = message.reply_to_message.video_note.duration

        bot.edit_message_text(
            '*WOW!* Неужели твоя очередь!\nЭто займёт: _~{0}s_'.format(round(seconds_recognized * duration)),
            message.chat.id,
            message.id,
        )

        with open(file_id, 'wb') as file: # скачиваем файл
            file_info = bot.get_file(file_id)

            file.write(bot.download_file(file_info.file_path))
        
        message.reply_to_message.text = stt.with_app(file_id, app[0])
        temp = round(time.time() - temp, 2)

        if not message.reply_to_message.text:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text = f'расшифровать🗣', callback_data = '-{0}{1}'.format(app[0], app[1])))

            bot.edit_message_text(
                '<b>{0} не удалось расшифровать</b>\n{1}'.format(app[0], message.html_text),
                message.chat.id,
                message.id,
                reply_markup = markup,
                parse_mode = 'html'
            )
        
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text = f'расшифровать🗣', callback_data = 'n{0}'.format(app[1])))
            
            bot.edit_message_text(
                ' _{1}_\n*{2}/{0}s*'.format(temp, message.reply_to_message.text, app[0]),
                message.chat.id,
                message.id,
                reply_markup = markup
            )
        
        self.query['now_recognition'] -= 1

        return self.add_stat(message.reply_to_message, recognition_time = temp, service = app[0]) # отправка статистики на учёт

    def task(self):
        while True:
            if self.query['query'] and self.query['now_recognition']:
                for message in self.query['query']:
                    try:
                        bot.edit_message_text(
                            '''*Opps!* У нас очередь из сообщений на обработку🙊
        Ваша позиция: {0}
        Осталось ждать: _~я не умею считать_
                            '''.format(self.query['query'].index(message) + 1),
                        message[0].chat.id,
                        message[0].id
                        )
                    
                    except:
                        pass

            if self.query['query'] and self.query['now_recognition'] < 2:
                self.query['now_recognition'] += 1

                message = self.query['query'].pop(0) # message[0] - Телеграмм сообщение, message[1] - приложение для расшифровки

                th = Thread(target = self.recognition, args = (message[0], message[1]))
                th.start()

            time.sleep(0.2)

in_func = internal_function()

@bot.callback_query_handler(func=lambda call: True)
def re_stt(call: telebot.types.CallbackQuery):
    message = call.message

    if not message.reply_to_message:
        bot.edit_message_text(
            'Расшифровка сообщения теперь невозможна, изначальное сообщение удалено',
            message.chat.id,
            message.id
        )
        return bot.answer_callback_query(call.id, 'Ня пока')

    if call.data.startswith('~'):
        call.data = call.data.replace('~', '')

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text = 'расшифровать🗣', callback_data = 'n{0}'.format(call.data)))

        bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup = markup)
        return bot.answer_callback_query(call.id, 'ok')
    
    if not call.data or call.data.startswith('n'):
        call.data = call.data.replace('n', '')

        if '-' in call.data:
            data = call.data.rsplit('-')
        
        else:
            data = ()
        
        markup = telebot.types.InlineKeyboardMarkup()

        if 'vk' in data:
            markup.add(telebot.types.InlineKeyboardButton(text = 'VK❌', callback_data = '!'))
        
        else:
            markup.add(telebot.types.InlineKeyboardButton(text = 'VK🚾', callback_data = 'vk%{0}'.format(call.data)))
        
        if 'vosk' in data:
            markup.add(telebot.types.InlineKeyboardButton(text = 'Vosk❌', callback_data = '!'))
        
        else:
            markup.add(telebot.types.InlineKeyboardButton(text = 'Vosk🆓', callback_data = 'vosk%{0}'.format(call.data)))
        
        markup.add(telebot.types.InlineKeyboardButton(text = 'назад◀️', callback_data = '~{0}'.format(call.data)))
        
        bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup = markup)
        return bot.answer_callback_query(call.id, 'Выберайте')
    
    elif '%' in call.data:
        app = call.data.rsplit('%')
        
        if len(app) < 2:
            app.append['']
        
        in_func.query['query'].append((message, app))
        return bot.answer_callback_query(call.id, 'В очереди')
    
    elif call.data == '!':
        return bot.answer_callback_query(call.id, 'Невозможно!')
    
    elif '-' in call.data:
        data = call.data.rsplit('-')
        markup = telebot.types.InlineKeyboardMarkup()

        if 'vk' in data:
            markup.add(telebot.types.InlineKeyboardButton(text = 'VK❌', callback_data = '!'))
        
        else:
            markup.add(telebot.types.InlineKeyboardButton(text = 'VK🚾', callback_data = 'vk%{0}'.format(call.data)))
        
        if 'vosk' in data:
            markup.add(telebot.types.InlineKeyboardButton(text = 'Vosk❌', callback_data = '!'))
        
        else:
            markup.add(telebot.types.InlineKeyboardButton(text = 'Vosk🆓', callback_data = 'vosk%{0}'.format(call.data)))
        
        markup.add(telebot.types.InlineKeyboardButton(text = 'назад◀️', callback_data = '~{0}'.format(call.data)))
        
        bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup = markup)
        return bot.answer_callback_query(call.id, 'Выберайте')
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text = 'расшифровать🗣', callback_data = 'n'))
    bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup = markup)
    return bot.answer_callback_query(call.id, 'Попробуйте ещё раз')

@bot.message_handler(content_types = ['video_note', 'voice'])
def video_note_and_audio(message: telebot.types.Message): # расшифровка голосовых и кружочков
    reply_message = bot.reply_to(message, '🔘*Думаю...*')

    if message.content_type == 'voice': # это проверка на войс или кружочек
        duration = message.voice.duration # длина голосового
    
    else: # так же для кружочка
        duration = message.video_note.duration
    
    if duration > 362: # ограничение на анализ 6 минут
        return bot.edit_message_text(  # конвертирование файла возвращает то, за сколько конвертировал и что будет распознавать сообщение
            '❌*Извините*, слишком много контента. Я могу *максимум 6 минут*',
            reply_message.chat.id,
            reply_message.id
            )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text = 'расшифровать🗣', callback_data = 'n'))

    bot.edit_message_text(
        '*ГС*',
        reply_message.chat.id,
        reply_message.id,
        reply_markup = markup
        )

@bot.message_handler(commands = ['rewrite'])
def rewrite_text(message: telebot.types.Message):
    bot.send_chat_action(message.chat.id, 'typing', 1)

    if message.text.startswith('/rewrite'):
        message.text = message.text.replace('/rewrite', '', 1).strip()

    if message.text.startswith('@'):
        message.text = message.text.replace(f'@{me.username}', '', 1).strip()

    if message.text:
        in_func.rewrite_and_compress(message.from_user.id, message.text, 'rewrite')
    
    else:
        bot.reply_to(message, 'Я не смог найти текст\nПишите так /rewrite ваш текст')

@bot.message_handler(commands = ['compress'])
def compress_text(message):
    bot.send_chat_action(message.chat.id, 'typing', 1)

    if message.text.startswith('/compress'):
        message.text = message.text.replace('/compress', '', 1).strip()

    if message.text.startswith('@'):
        message.text = message.text.replace(f'@{me.username}', '', 1).strip()

    if message.text:
        in_func.rewrite_and_compress(message, 'compress')
    
    else:
        bot.reply_to(message, 'Я не смог найти текст\nПишите так /compress ваш текст')

@bot.message_handler(commands = ['start'])
def start(message: telebot.types.Message):
    return bot.send_message(message.chat.id, 'Я - Такмот. Мой создатель в депресии и оставил у меня только две функции:\n1. Расшифровка голосовых сообщений 2. Выбор из вариантов')

@bot.message_handler(content_types = ['text'])
def text_message(message: telebot.types.Message): # анализ текстовых сообщений
    if message.text.lower() in ('бот?', 'жив?', 'живой', 'бот жив', 'бот'):
        return bot.send_message(message.chat.id, random.choice((
            'Я - жив', 'Живой я', 'Ещё вас переживу', 'Тут я',
            'Что случилось?', 'Ну?', 'Ко мне вопрос?', 'Допустим тут'
        )))
    
    elif not message.reply_to_message:
        return
    
    elif not message.reply_to_message.from_user.id == me.id:
        return
    
    if ' или ' in message.text:
        return bot.send_message(message.chat.id, random.choice(message.text.rsplit(' или ')))
    
    else:
        return bot.send_message(message.chat.id, random.choice((
            '*YES!*', '*NO!*', 'Хм... *Нет*?',
            'Хм... *Да*?', 'no 👎🏿', 'yes 👍🏿',
            '✅', '❌', 'Допустим *да*',
            'Допустим *нет*', 'Нет...',
            'Да...',
        )))

def main():
    th = Thread(target = in_func.task)
    th.start()
    
    bot.send_message(admin, f'''*Бот запущен✅*
    Дата: {time.ctime(time.time())}
    ''')

    while True:
        try:
            bot.polling(timeout = 100, long_polling_timeout = 100)
        
        except Exception as ex:
            bot.stop_polling()
            bot.send_message(admin, f'*Произошла ошибка!*\n`{ex}`')

if __name__ == '__main__':
    main()