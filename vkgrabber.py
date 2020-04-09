import re

import vk_api


class VKGrabber:

    def __init__(self, login, password, key_words):
        self.__key_words = key_words
        self.__vk_session = vk_api.VkApi(login=login, password=password)
        self.__vk_session.auth()
        self.__vk = self.__vk_session.get_api()

    def __is_text_interesting(self, text):
        for key_word in self.__key_words:
            if re.search(key_word, text, flags=re.IGNORECASE):
                return True
        return False

    def is_group_exists(self, group):
        response = self.__vk.utils.resolveScreenName(screen_name=group)
        if len(response) == 0:
            return False
        else:
            return True if response['type'] == 'group' else False

    def get_interesting_posts(self, groups, cur):
        notify_message = str()
        for group in groups:
            response = self.__vk.wall.get(domain=group, count=100, filter='all')
            current_max_id = cur.execute('''SELECT MAX(post_ID) FROM POSTS WHERE group_domain = ?;''', (group, )).fetchone()[0]
            if not current_max_id:
                current_max_id = -1
            for post in response['items']:
                if post['id'] > current_max_id:
                    if self.__is_text_interesting(post['text']):
                        cur.execute('''INSERT INTO POSTS (group_domain, post_id, post_text, is_interesting)
                                       VALUES(?, ?, ?, true); ''', (group, post['id'], post['text']))
                        notify_message += 'https://vk.com/{0}?w=wall{1}_{2}\n'.format(group, post['owner_id'], post['id'])
                    else:
                        cur.execute('''INSERT INTO POSTS (group_domain, post_id, post_text, is_interesting)
                                       VALUES(?, ?, ?, false); ''', (group, post['id'], post['text']))
                else:
                    break
        return notify_message
