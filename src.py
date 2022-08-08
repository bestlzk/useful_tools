import requests
import logging
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from lxml import etree

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO)


class SRCMonitor(object):
    def __init__(self):
        self.tsrc_unread_message_num = 0
        self.tsrc_session = requests.Session()
        self.tsrc_cookie = 'xxx'

        self.bsrc_unread_message_num = 0
        self.bsrc_session = requests.Session()
        self.bsrc_cookie = 'xxx'

    def get_sign(self, key):
        timestamp = round(time.time() * 1000)
        msg = '{}\n{}'.format(timestamp, key)
        hmac_code = hmac.new(key.encode(), msg.encode(), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus((base64.b64encode(hmac_code)))
        return '&timestamp={}&sign={}'.format(timestamp, sign)

    def send_message(self, content):
        url = 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
        key = 'xxx'
        url += self.get_sign(key)
        content = {
            'msgtype': 'markdown',
            'markdown': {
                'title': content['name'],
                'text': '[{}]({}): 你有{}条未读消息'.format(content['name'], content['homepage'], content['num'])
            }
        }
        requests.post(url, headers={'content-type': 'application/json'}, data=json.dumps(content))

    def tsrc(self):
        name = '腾讯安全应急响应中心'
        homepage = 'https://security.tencent.com/'
        logging.info('TSRC search')
        if not self.tsrc_session.cookies.get('PHPSESSID'):
            self.tsrc_session.cookies.set('PHPSESSID', self.tsrc_cookie)
        elif self.tsrc_session.cookies.get('PHPSESSID') != self.tsrc_cookie:
            self.tsrc_cookie = self.tsrc_session.cookies.get('PHPSESSID')
            logging.info('TSRC update cookie PHPSESSID={}'.format(self.tsrc_cookie))
        res = self.tsrc_session.get(homepage)
        site = etree.HTML(res.content)
        if not site.xpath('//span[@class="user_username"]/text()'):
            logging.error('TSRC not login')
            return
        unread_message_num_now = site.xpath('//i[@class="i-header-message"]/text()')
        unread_message_num_now = int(unread_message_num_now[0]) if unread_message_num_now else 0
        if unread_message_num_now > self.tsrc_unread_message_num:
            logging.info('TSRC unread message {}'.format(unread_message_num_now))
            self.send_message({'name': name, 'homepage': homepage, 'num': unread_message_num_now})
        self.tsrc_unread_message_num = unread_message_num_now

    def bsrc(self):
        name = '百度安全应急响应中心'
        homepage = 'https://bsrc.baidu.com/'
        logging.info('BSRC search')
        if not self.bsrc_session.cookies.get('BDUSS'):
            self.bsrc_session.cookies.set('BDUSS', self.bsrc_cookie)
        elif self.bsrc_session.cookies.get('BDUSS') != self.bsrc_cookie:
            self.bsrc_cookie = self.bsrc_session.cookies.get('BDUSS')
            logging.info('BSRC update cookie BDUSS={}'.format(self.bsrc_cookie))
        res = self.bsrc_session.get(homepage + 'v2/api/info').json()
        if res['retcode'] != 0:
            logging.error('BSRC not login')
            return
        unread_message_num_now = res['retdata']['unread']
        if unread_message_num_now > self.bsrc_unread_message_num:
            logging.info('BSRC unread message {}'.format(unread_message_num_now))
            self.send_message({'name': name, 'homepage': homepage, 'num': unread_message_num_now})
        self.bsrc_unread_message_num = unread_message_num_now

    def run(self):
        while True:
            try:
                self.tsrc()
                self.bsrc()
                time.sleep(600)
            except Exception as e:
                logging.error(e)
                time.sleep(30)
                continue


if __name__ == '__main__':
    sm = SRCMonitor()
    sm.run()
