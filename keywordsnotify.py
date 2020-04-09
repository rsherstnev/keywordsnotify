import argparse
from getpass import getpass
import os
import sqlite3

from telebot import TeleBot, apihelper
import vk_api

from vkgrabber import VKGrabber


class MyException(Exception):
    pass


HELP = '''Usage: keywordsnotify.py [--login LOGIN] [--password PASSWORD] [--keywords-file KEYWORDS_FILE]
                         [--groups-file GROUPS_FILE] [--profile-id PROFILE_ID] [--bot-token BOT_TOKEN]
                         [--proxy PROXY_TYPE://USER:PASSWORD@IP:PORT]

Options:
-h, --help              Вывести данную помощь.
-l, --login             Логин учётной записи Вконтакте, из под которой будут производиться запросы к API VK.
-p, --password          Пароль учётной записи Вконтакте, из под которой будут производиться запросы к API VK.
-k, --keywords-file     Файл, в котором содержатся ключевые слова для фильтрации.
-g, --groups-file       Файл, в котором содержатся группы Вконтакте, в которых будет осуществлен поиск.
-i, --profile-id        ID учетной записи Telegram, которой будет отсылаться сообщение с найденными постами.
-t, --bot-token         Токен Telegram бота.

Extra options:
    --proxy             Адрес прокси сервера, например, socks5://127.0.0.1:9050.
'''

connection = None
cursor = None

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='store_true')
parser.add_argument('-l', '--login')
parser.add_argument('-p', '--password')
parser.add_argument('-k', '--keywords-file')
parser.add_argument('-g', '--groups-file')
parser.add_argument('-i', '--profile-id')
parser.add_argument('-t', '--bot-token', )
parser.add_argument('--proxy')

try:

    args = parser.parse_args()

    if args.help:
        print(HELP)
        raise SystemExit

    connection = sqlite3.connect('Posts.db')

    if args.proxy:
        apihelper.proxy = {'https': args.proxy}

    if not args.keywords_file:
        raise MyException('Не указан файл с ключевыми словами для поиска!')

    if not args.groups_file:
        raise MyException('Не указан файл с группами, в которых производить поиск!')

    if not os.path.isfile(args.keywords_file):
        raise MyException('Файл ' + args.keywords_file + ' не был найден')

    if not os.path.isfile(args.groups_file):
        raise MyException('Файл ' + args.groups_file + ' не был найден')

    if not args.login:
        args.login = input('Введите логин учетной записи Вконтакте, '
                           'из под которой будут осуществляться запросы к API VK: ')

    if args.login and not args.password:
        args.password = getpass(prompt='Введите пароль от учетной записи Вконтакте с логином ' + args.login + ': ')

    if not args.profile_id:
        args.profile_id = input('Введите ID учетной записи Telegram, которой будет отсылаться сообщение'
                                'с найденными группами: ')

    if not args.bot_token:
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

except KeyboardInterrupt:
    pass

except vk_api.exceptions.BadPassword:
    print('Введены невалидные учетные данные, повторите попытку')

except MyException as error:
    print(error)

finally:
    if cursor:
        cursor.close()
    if connection:
        connection.close()
    if os.path.isfile('./vk_config.v2.json'):
        os.remove('./vk_config.v2.json')
