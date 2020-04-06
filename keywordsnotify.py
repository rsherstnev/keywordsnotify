import argparse
import sqlite3
import os
import vk_api
from getpass import getpass
from telebot import TeleBot, apihelper

from vkgrabber import VKGrabber


connection = None
cursor = None

parser = argparse.ArgumentParser()
parser.add_argument('--login', '-l', help='Логин учётной записи VK, из под которой будут производиться запросы к API VK')
parser.add_argument('--password', '-p', help='Пароль учётной записи VK, из под которой будут производиться'
                                             'запросы к API VK')
parser.add_argument('--keywords-file', '-k', help='Файл, в котором содержатся ключевые слова для фильтрации')
parser.add_argument('--groups-file', '-g', help='Файл, в котором содержатся группы Вконтакте, в которых будет'
                                                'осуществлен поиск')
parser.add_argument('--profile-id', '-i', help='ID учетной записи Telegram, которой будет отсылаться сообщение'
                                               'с найденными постами')
parser.add_argument('--bot-token', '-t', help='Токен Telegram бота')
parser.add_argument('--proxy', help='Адрес прокси сервера в формате: socks5://127.0.0.1:9050')

try:

    args = parser.parse_args()
    connection = sqlite3.connect('Posts.db')

    if args.proxy is not None:
        apihelper.proxy = {'https': args.proxy}

    if args.keywords_file is None:
        raise Exception('Не указан файл с ключевыми словами для поиска!')

    if args.groups_file is None:
        raise Exception('Не указан файл с группами, в которых производить поиск!')

    if not os.path.isfile(args.keywords_file):
        raise Exception('Файл ' + args.keywords_file + ' не был найден')

    if not os.path.isfile(args.groups_file):
        raise Exception('Файл ' + args.groups_file + ' не был найден')

    if args.login is None:
        args.login = input('Введите логин учетной записи Вконтакте, '
                           'из под которой будут осуществляться запросы к API VK: ')

    if args.login is not None and args.password is None:
        args.password = getpass(prompt='Введите пароль от учетной записи Вконтакте с логином ' + args.login + ': ')

    if args.profile_id is None:
        args.profile_id = input('Введите ID учетной записи Telegram, которой будет отсылаться сообщение'
                                'с найденными группами: ')

    if args.bot_token is None:
        args.bot_token = getpass(prompt='Введите токен Telegram бота: ')

    keywords = []
    with open(args.keywords_file, 'r', encoding='utf-8') as file:
        for line in file:
            keywords.append(line.strip())

    grabber = VKGrabber(args.login, args.password, keywords)

    groups = []
    with open(args.groups_file, 'r', encoding='utf-8') as file:
        for line in file:
            group = line.strip()
            if grabber.is_group_exists(group):
                groups.append(group)
            else:
                print(group + ' либо не является группой, либо вообще не существует и будет выпущена из сканирования')

    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS POSTS (
                            group_domain TEXT NOT NULL,
                            post_id INTEGER NOT NULL,
                            post_text TEXT,
                            is_interesting BOOLEAN NOT NULL,
                            CONSTRAINT GROUP_POST_ID_PK PRIMARY KEY(group_domain, post_id));''')

    interesting_posts = grabber.get_interesting_posts(groups, cursor)
    connection.commit()

    if len(interesting_posts) != 0:
        TeleBot(args.bot_token).send_message(args.profile_id, interesting_posts)

except vk_api.exceptions.BadPassword:
    print('Введены невалидные учетные данные, повторите попытку')
    raise SystemExit

finally:
    if cursor is not None:
        cursor.close()
    if connection is not None:
        connection.close()
    if os.path.isfile('./vk_config.v2.json'):
        os.remove('./vk_config.v2.json')
