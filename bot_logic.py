import telebot
import os
import requests
from telegram import Update
from telegram.ext import CallbackContext
from telebot import TeleBot, types
from telebot.types import Message
from screenshots2songs import sign_in_vk_1, sign_in_vk_2, recognize_text, get_link, crop_img, define_img_type
from private_data import bot_token, imgs_path, permitted_logins

states = {}

bot = telebot.TeleBot(bot_token)


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Бот создан для личного пользования')
    handle_state_one(message)


@bot.message_handler(func=lambda message: True, state=1)
def handle_state_one(message: Message):
    bot.send_message(message.chat.id, 'Введите свой логин')
    bot.register_next_step_handler(message, lambda m: handle_state_two(m))


@bot.message_handler(func=lambda message: True, state=2)
def handle_state_two(message: Message):
    login = message.text
    if login in permitted_logins:
        bot.send_message(message.chat.id, f'Добро пожаловать {login}!\n ')
        handle_state_three(message)
    else:
        bot.send_message(message.chat.id, 'К сожалению, у вас нет доступа')
        bot.register_next_step_handler(message, lambda m: handle_state_two(m))


@bot.message_handler(func=lambda message: True, state=3)
def handle_state_three(message: Message):
    bot.send_message(message.chat.id, 'Захожу в ВК..')
    driver = sign_in_vk_1()
    user_id = message.from_user.id
    states[user_id] = {'driver': driver}
    bot.send_message(message.chat.id, 'Для продолжения введи код от ВК')
    bot.register_next_step_handler(message, lambda m: handle_state_four(m, driver))


@bot.message_handler(func=lambda message: True, state=4)
def handle_state_four(message, driver):
    code = message.text
    driver = sign_in_vk_2(driver, code)
    bot.send_message(message.chat.id, 'Отлично! Аутентификация завершена')
    bot.send_message(message.chat.id, 'Пришли скриншот')
    bot.register_next_step_handler(message, lambda m: handle_state_five(m, driver))


@bot.message_handler(content_types=['photo'], state = 5)
def handle_state_five(message, driver):
    bot.send_message(message.chat.id, 'Скриншот принят')
    image_id = message.photo[-1].file_id
    image_info = bot.get_file(image_id)
    image_path = image_info.file_path
    image_filename = os.path.basename(image_path)
    image_bytes = requests.get(f'https://api.telegram.org/file/bot{bot_token}/{image_path}').content
    save_path = os.path.join(imgs_path, image_filename)
    with open(save_path, 'wb') as f:
        f.write(image_bytes)
    abs_path = os.path.abspath(save_path)
    img_type = define_img_type(abs_path)
    if img_type == 4:
        song_info = recognize_text(abs_path, img_type)
        bot.send_message(message.chat.id, f'"{song_info}"')
        result = get_link(driver, song_info, '')
    else:
        title_img_path, author_img_path = crop_img(abs_path, img_type)
        title = recognize_text(title_img_path, img_type)
        author = recognize_text(author_img_path, img_type)
        song_info = title + ' ' + author
        bot.send_message(message.chat.id, f'"{song_info}"')
        result = get_link(driver, title, author)
    bot.send_message(message.chat.id, result)
    bot.send_message(message.chat.id, 'Если есть еще скриншоты - присылай. Если нет - пиши "Конец"')
    bot.register_next_step_handler(message, lambda m: handle_state_six(m, driver))

@bot.message_handler(content_types=['photo'], state = 6)
def handle_state_six(message, driver):
    answer = message.text
    if message.content_type == 'text':
        if answer == 'Конец':
            driver.quit()
            bot.send_message(message.chat.id, 'Когда захочешь поболтать, пиши /start')
        else:
            bot.send_message(message.chat.id, 'Пришли скриншот')
            bot.register_next_step_handler(message, lambda m: handle_state_five(m, driver))
    else:
        handle_state_five(message, driver)


if __name__ == '__main__':
    bot.polling(none_stop=True)
