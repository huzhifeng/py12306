#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 标准库
import argparse
import urllib
import time
import datetime
import sys
import re
import ConfigParser
import random
import smtplib
from email.mime.text import MIMEText

# 第三方库
import requests
from huzhifeng import dumpObj, hasKeys

# Set default encoding to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')
requests.packages.urllib3.disable_warnings()

# 全局变量
RET_OK = 0
RET_ERR = -1
MAX_TRIES = 3
MAX_DAYS = 60
stations = []
seatMaps = [
    ('1', u'硬座'),  # 硬座/无座
    ('3', u'硬卧'),
    ('4', u'软卧'),
    ('7', u'一等软座'),
    ('8', u'二等软座'),
    ('9', u'商务座'),
    ('M', u'一等座'),
    ('O', u'二等座'),
    ('B', u'混编硬座'),
    ('P', u'特等座')
]


# 全局函数
def printDelimiter():
    print('-' * 64)


def getTime():
    return time.strftime('%Y-%m-%d %X', time.localtime())  # 2014-01-01 12:00:00


def date2UTC(d):
    # Convert '2014-01-01' to 'Wed Jan 01 00:00:00 UTC+0800 2014'
    t = time.strptime(d, '%Y-%m-%d')
    asc = time.asctime(t)  # 'Wed Jan 01 00:00:00 2014'
    # 'Wed Jan 01 00:00:00 UTC+0800 2014'
    return (asc[0:-4] + 'UTC+0800 ' + asc[-4:])


def getCardType(key):
    d = {
        '1': u'二代身份证',
        '2': u'一代身份证',
        'C': u'港澳通行证',
        'G': u'台湾通行证',
        'B': u'护照'
    }
    return d[key] if key in d else u'未知证件类型'


def getTicketType(key):
    d = {
        '1': u'成人票',
        '2': u'儿童票',
        '3': u'学生票',
        '4': u'残军票'
    }
    return d[key] if key in d else u'未知票种'


def getSeatType(key):
    d = dict(seatMaps)
    return d[key] if key in d else u'未知席别'


def selectSeatType():
    key = '1'  # 默认硬座
    while True:
        print(u'请选择席别编码(即左边第一个英文字母):')
        for xb in seatMaps:
            print(u'%s: %s' % (xb[0], xb[1]))
        key = raw_input().upper()
        d = dict(seatMaps)
        if key in d:
            return key
        else:
            print(u'无效的席别类型!')


def checkDate(date):
    m = re.match(r'^\d{4}-\d{2}-\d{2}$', date)  # 2014-01-01
    if m:
        today = datetime.datetime.now()
        fmt = '%Y-%m-%d'
        today = datetime.datetime.strptime(today.strftime(fmt), fmt)
        train_date = datetime.datetime.strptime(m.group(0), fmt)
        delta = train_date - today
        if delta.days < 0:
            print(u'乘车日期%s无效, 只能预订%s以后的车票' % (
                train_date.strftime(fmt),
                today.strftime(fmt)))
            return False
        else:
            return True
    else:
        return False


def selectDate():
    fmt = '%Y-%m-%d'
    week_days = [u'星期一', u'星期二', u'星期三', u'星期四', u'星期五', u'星期六', u'星期天']
    now = datetime.datetime.now()
    available_date = [(now + datetime.timedelta(days=i)) for i in xrange(MAX_DAYS)]
    for i in xrange(0, MAX_DAYS, 2):
        print(u'第%2d天: %s(%s)' % (
            i + 1, available_date[i].strftime(fmt), week_days[available_date[i].weekday()])),
        if i + 1 < MAX_DAYS:
            print(u'\t\t第%2d天: %s(%s)' % (
                i + 2, available_date[i + 1].strftime(fmt), week_days[available_date[i + 1].weekday()]))
        else:
            print('')
    while True:
        print(u'请选择乘车日期(1~%d)' % (MAX_DAYS))
        index = raw_input()
        if not index.isdigit():
            print(u'只能输入数字序号, 请重新选择乘车日期(1~%d)' % (MAX_DAYS))
            continue
        index = int(index)
        if index < 1 or index > MAX_DAYS:
            print(u'输入的序号无效, 请重新选择乘车日期(1~%d)' % (MAX_DAYS))
            continue
        index -= 1
        train_date = available_date[index].strftime(fmt)
        return train_date


def getStationByName(name):
    matched_stations = []
    for station in stations:
        if (
                station['name'] == name
                or station['abbr'].find(name.lower()) != -1
                or station['pinyin'].find(name.lower()) != -1
                or station['pyabbr'].find(name.lower()) != -1):
            matched_stations.append(station)
    count = len(matched_stations)
    if count <= 0:
        return None
    elif count == 1:
        return matched_stations[0]
    else:
        for i in xrange(0, count):
            print(u'%d:\t%s' % (i + 1, matched_stations[i]['name']))
        print(u'请选择站点(1~%d)' % (count))
        index = raw_input()
        if not index.isdigit():
            print(u'只能输入数字序号(1~%d)' % (count))
            return None
        index = int(index)
        if index < 1 or index > count:
            print(u'输入的序号无效(1~%d)' % (count))
            return None
        else:
            return matched_stations[index - 1]


def inputStation():
    while True:
        print(u'支持中文, 拼音和拼音缩写(如: 北京,beijing,bj)')
        name = raw_input().decode('gb2312', 'ignore')
        station = getStationByName(name)
        if station:
            return station
        else:
            print(u'站点错误, 没有站点"%s", 请重新输入.' % (name))


def selectTrain(trains):
    trains_num = len(trains)
    index = 0
    while True:  # 必须选择有效的车次
        index = raw_input()
        if not index.isdigit():
            print(u'只能输入数字序号,请重新选择车次(1~%d)' % (trains_num))
            continue
        index = int(index)
        if index < 1 or index > trains_num:
            print(u'输入的序号无效,请重新选择车次(1~%d)' % (trains_num))
            continue
        if trains[index - 1]['queryLeftNewDTO']['canWebBuy'] != 'Y':
            print(u'您选择的车次%s没票啦,请重新选择车次' % (
                trains[index - 1]['queryLeftNewDTO']['station_train_code']))
            continue
        else:
            break

    return index


class MyOrder(object):

    '''docstring for MyOrder'''

    def __init__(
            self,
            username='',
            password='',
            train_date='',
            from_city_name='',
            to_city_name=''):
        super(MyOrder, self).__init__()
        self.username = username  # 账号
        self.password = password  # 密码
        self.train_date = train_date  # 乘车日期[2014-01-01]
        today = datetime.datetime.now()
        self.back_train_date = today.strftime('%Y-%m-%d')  # 返程日期[2014-01-01]
        self.tour_flag = 'dc'  # 单程dc/往返wf
        self.purpose_code = 'ADULT'  # 成人票
        self.from_city_name = from_city_name  # 对应查询界面'出发地'输入框中的内容
        self.to_city_name = to_city_name  # 对应查询界面'目的地'输入框中的内容
        self.from_station_telecode = ''  # 出发站编码
        self.to_station_telecode = ''  # 目的站编码
        self.passengers = []  # 乘车人列表,最多5人
        self.normal_passengers = []  # 我的联系人列表
        self.trains = []  # 列车列表, 查询余票后自动更新
        self.current_train_index = 0  # 当前选中的列车索引序号
        self.captcha = ''  # 图片验证码
        self.orderId = ''  # 订单流水号
        self.canWebBuy = False  # 可预订
        self.notify = {
            'mail_enable': 0,
            'mail_username': '',
            'mail_password': '',
            'mail_server': '',
            'mail_to': [],
            'dates': [],
            'trains': [],
            'xb': [],
            'focus': {}
        }

    def initSession(self):
        self.session = requests.Session()
        self.session.headers = {
            'Accept': 'application/x-ms-application, image/jpeg, application/xaml+xml, image/gif, image/pjpeg, application/x-ms-xbap, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C)',
            'Referer': 'https://kyfw.12306.cn/otn/index/init',
            'Host': 'kyfw.12306.cn',
            'Connection': 'Keep-Alive'
        }

    def updateHeaders(self, url):
        d = {
            'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/'
            },
            'https://kyfw.12306.cn/otn/login/init': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/'
            },
            'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=login&rand=sjrand&': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/login/init'
            },
            'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=passenger&rand=randp&': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
            },
            'https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/login/init',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/login/loginAysnSuggest': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/login/init',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/login/userLogin': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/login/init'
            },
            'https://kyfw.12306.cn/otn/index/init': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/login/init'
            },
            'https://kyfw.12306.cn/otn/leftTicket/init': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/index/init',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            'https://kyfw.12306.cn/otn/leftTicket/log?': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
                'x-requested-with': 'XMLHttpRequest',
                'Cache-Control': 'no-cache',
                'If-Modified-Since': '0'
            },
            'https://kyfw.12306.cn/otn/leftTicket/query?': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
                'x-requested-with': 'XMLHttpRequest',
                'Cache-Control': 'no-cache',
                'If-Modified-Since': '0'
            },
            'https://kyfw.12306.cn/otn/leftTicket/queryT?': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
                'x-requested-with': 'XMLHttpRequest',
                'Cache-Control': 'no-cache',
                'If-Modified-Since': '0'
            },
            'https://kyfw.12306.cn/otn/login/checkUser': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
                'Cache-Control': 'no-cache',
                'If-Modified-Since': '0',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/initDc': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cache-Control': 'no-cache'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'x-requested-with': 'XMLHttpRequest'
            },
            'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            },
            'https://kyfw.12306.cn/otn//payOrder/init?': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc',
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            'https://kyfw.12306.cn/otn/queryOrder/initNoComplete': {
                'method': 'GET',
                'Referer': 'https://kyfw.12306.cn/otn//payOrder/init?random=1417862054369'
            },
            'https://kyfw.12306.cn/otn/queryOrder/queryMyOrderNoComplete': {
                'method': 'POST',
                'Referer': 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete',
                'Cache-Control': 'no-cache',
                'x-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }
        }
        l = [
            'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=login&rand=sjrand&',
            'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=passenger&rand=randp&',
            'https://kyfw.12306.cn/otn/leftTicket/log?',
            'https://kyfw.12306.cn/otn/leftTicket/query?',
            'https://kyfw.12306.cn/otn/leftTicket/queryT?',
            'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?',
            'https://kyfw.12306.cn/otn//payOrder/init?'
        ]
        for s in l:
            if url.find(s) == 0:
                url = s
        if not url in d:
            print(u'未知 url: %s' % url)
            return RET_ERR
        self.session.headers.update({'Referer': d[url]['Referer']})
        keys = [
            'Referer',
            'Cache-Control',
            'x-requested-with',
            'Content-Type'
        ]
        for key in keys:
            if key in d[url]:
                self.session.headers.update({key: d[url][key]})
            else:
                self.session.headers.update({key: None})
    def get(self, url):
        self.updateHeaders(url)
        tries = 0
        while tries < MAX_TRIES:
            tries += 1
            try:
                r = self.session.get(url, verify=False, timeout=16)
            except requests.exceptions.ConnectionError as e:
                print('ConnectionError(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.Timeout as e:
                print('Timeout(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.TooManyRedirects as e:
                print('TooManyRedirects(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.HTTPError as e:
                print('HTTPError(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.RequestException as e:
                print('RequestException(%s): e=%s' % (url, e))
                continue
            except:
                print('Unknown exception(%s)' % (url))
                continue
            if r.status_code != 200:
                print('Request %s failed %d times, status_code=%d' % (
                    url,
                    tries,
                    r.status_code))
            else:
                return r
        else:
            return None

    def post(self, url, payload):
        self.updateHeaders(url)
        if url == 'https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn':
            if payload.find('REPEAT_SUBMIT_TOKEN') != -1:
                self.session.headers.update({'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'})
            else:
                self.session.headers.update({'Referer': 'https://kyfw.12306.cn/otn/login/init'})
        tries = 0
        while tries < MAX_TRIES:
            tries += 1
            try:
                r = self.session.post(url, data=payload, verify=False, timeout=16)
            except requests.exceptions.ConnectionError as e:
                print('ConnectionError(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.Timeout as e:
                print('Timeout(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.TooManyRedirects as e:
                print('TooManyRedirects(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.HTTPError as e:
                print('HTTPError(%s): e=%s' % (url, e))
                continue
            except requests.exceptions.RequestException as e:
                print('RequestException(%s): e=%s' % (url, e))
                continue
            except:
                print('Unknown exception(%s)' % (url))
                continue
            if r.status_code != 200:
                print('Request %s failed %d times, status_code=%d' % (
                    url,
                    tries,
                    r.status_code))
            else:
                return r
        else:
            return None

    def getCaptcha(self, url):
        self.updateHeaders(url)
        r = self.session.get(url, verify=False, stream=True, timeout=16)
        with open('captcha.gif', 'wb') as fd:
            for chunk in r.iter_content():
                fd.write(chunk)
        print(u'请输入4位图片验证码(回车刷新验证码):')
        captcha = raw_input()
        if len(captcha) == 4:
            return captcha
        elif len(captcha) != 0:
            print(u'%s是无效的图片验证码, 必须是4位' % (captcha))
            return None
        else:
            return 1  # 刷新

    def initStation(self):
        url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js'
        r = self.get(url)
        if not r:
            print(u'站点数据库初始化失败, 请求异常')
            return None
        data = r.text
        station_list = data.split('@')
        if len(station_list) < 1:
            print(u'站点数据库初始化失败, 数据异常')
            return None
        station_list = station_list[1:]
        for station in station_list:
            items = station.split('|')  # bji|北京|BJP|beijing|bj|2
            if len(items) < 5:
                print(u'忽略无效站点: %s' % (items))
                continue
            stations.append({'abbr': items[0],
                             'name': items[1],
                             'telecode': items[2],
                             'pinyin': items[3],
                             'pyabbr': items[4]})
        return stations

    def readConfig(self, config_file='config.ini'):
        cp = ConfigParser.ConfigParser()
        try:
            cp.readfp(open(config_file, 'r'))
        except IOError as e:
            print(u'打开配置文件"%s"失败啦, 请先创建或者拷贝一份配置文件config.ini' % (config_file))
            raw_input('Press any key to continue')
            sys.exit()
        self.username = cp.get('login', 'username')
        self.password = cp.get('login', 'password')
        self.train_date = cp.get('train', 'date')
        self.from_city_name = cp.get('train', 'from')
        self.to_city_name = cp.get('train', 'to')
        self.notify['mail_enable'] = int(cp.get('notify', 'mail_enable'))
        self.notify['mail_username'] = cp.get('notify', 'mail_username')
        self.notify['mail_password'] = cp.get('notify', 'mail_password')
        self.notify['mail_server'] = cp.get('notify', 'mail_server')
        self.notify['mail_to'] = cp.get('notify', 'mail_to').split(',')
        self.notify['dates'] = cp.get('notify', 'dates').split(',')
        self.notify['trains'] = cp.get('notify', 'trains').split(',')
        self.notify['xb'] = cp.get('notify', 'xb').split(',')

        for t in self.notify['trains']:
            self.notify['focus'][t] = self.notify['xb']
        # 检查出发站
        station = getStationByName(self.from_city_name)
        if not station:
            print(u'出发站错误, 请重新输入')
            station = inputStation()
        self.from_city_name = station['name']
        self.from_station_telecode = station['telecode']
        # 检查目的站
        station = getStationByName(self.to_city_name)
        if not station:
            print(u'目的站错误,请重新输入')
            station = inputStation()
        self.to_city_name = station['name']
        self.to_station_telecode = station['telecode']
        # 检查乘车日期
        if not checkDate(self.train_date):
            print(u'乘车日期无效, 请重新选择')
            self.train_date = selectDate()
        # 分析乘客信息
        self.passengers = []
        index = 1
        passenger_sections = ['passenger%d' % (i) for i in xrange(1, 6)]
        sections = cp.sections()
        for section in passenger_sections:
            if section in sections:
                passenger = {}
                passenger['index'] = index
                passenger['name'] = cp.get(section, 'name')  # 必选参数
                passenger['cardtype'] = cp.get(
                    section,
                    'cardtype') if cp.has_option(
                    section,
                    'cardtype') else '1'  # 证件类型:可选参数,默认值1,即二代身份证
                passenger['id'] = cp.get(section, 'id')  # 必选参数
                passenger['phone'] = cp.get(
                    section,
                    'phone') if cp.has_option(
                    section,
                    'phone') else '13800138000'  # 手机号码
                passenger['seattype'] = cp.get(
                    section,
                    'seattype') if cp.has_option(
                    section,
                    'seattype') else '1'  # 席别:可选参数, 默认值1, 即硬座
                passenger['tickettype'] = cp.get(
                    section,
                    'tickettype') if cp.has_option(
                    section,
                    'tickettype') else '1'  # 票种:可选参数, 默认值1, 即成人票
                self.passengers.append(passenger)
                index += 1

    def printConfig(self):
        printDelimiter()
        print(u'订票信息:\n%s\t%s\t%s--->%s' % (
            self.username,
            self.train_date,
            self.from_city_name,
            self.to_city_name))
        printDelimiter()
        th = [u'序号', u'姓名', u'证件类型', u'证件号码', u'席别', u'票种']
        print(u'%s\t%s\t%s\t%s\t%s\t%s' % (
            th[0].ljust(2), th[1].ljust(4), th[2].ljust(5),
            th[3].ljust(12), th[4].ljust(2), th[5].ljust(3)))
        for p in self.passengers:
            print(u'%s\t%s\t%s\t%s\t%s\t%s' % (
                p['index'],
                p['name'].decode('utf-8', 'ignore').ljust(4),
                getCardType(p['cardtype']).ljust(5),
                p['id'].ljust(20),
                getSeatType(p['seattype']).ljust(2),
                getTicketType(p['tickettype']).ljust(3)))

    def checkRandCodeAnsyn(self, module):
        d = {
            'login': {  # 登陆验证码
                'rand': 'sjrand',
                'referer': 'https://kyfw.12306.cn/otn/login/init'
            },
            'passenger': {  # 订单验证码
                'rand': 'randp',
                'referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
            }
        }
        if not module in d:
            print(u'无效的 module: %s' % (module))
            return RET_ERR
        tries = 0
        while tries < MAX_TRIES:
            tries += 1
            url = 'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=%s&rand=%s&' % (module, d[module]['rand'])
            if tries > 1:
                url = '%s%1.16f' % (url, random.random())
            print(u'正在等待验证码...')
            self.captcha = self.getCaptcha(url)
            if not self.captcha:
                continue
            if self.captcha == 1:  # 刷新不计数
                tries -= 1
                continue
            url = 'https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn'
            parameters = [
                ('randCode', self.captcha),
                ('rand', d[module]['rand'])
            ]
            if module == 'login':
                parameters.append(('randCode_validate', ''))
            else:
                parameters.append(('_json_att', ''))
                parameters.append(('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken))
            payload = urllib.urlencode(parameters)
            print(u'正在校验验证码...')
            r = self.post(url, payload)
            if not r:
                print(u'校验验证码异常')
                continue
            # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"result":"1","msg":"randCodeRight"},"messages":[],"validateMessages":{}}
            obj = r.json()
            if (
                    hasKeys(obj, ['status', 'httpstatus', 'data'])
                    and hasKeys(obj['data'], ['result', 'msg'])
                    and (obj['data']['result'] == '1')):
                print(u'校验验证码成功')
                return RET_OK
            else:
                print(u'校验验证码失败')
                dumpObj(obj)
                continue
        else:
            return RET_ERR

    def login(self):
        url = 'https://kyfw.12306.cn/otn/login/init'
        r = self.get(url)
        if not r:
            print(u'登录失败, 请求异常')
            return RET_ERR
        if self.session.cookies:
            cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
            if cookies['JSESSIONID']:
                self.jsessionid = cookies['JSESSIONID']

        if self.checkRandCodeAnsyn('login') == RET_ERR:
            return RET_ERR

        print(u'正在登录...')
        url = 'https://kyfw.12306.cn/otn/login/loginAysnSuggest'
        parameters = [
            ('loginUserDTO.user_name', self.username),
            ('userDTO.password', self.password),
            ('randCode', self.captcha),
            ('randCode_validate', ''),
            #('ODg3NzQ0', 'OTIyNmFhNmQwNmI5ZmQ2OA%3D%3D'),
            ('myversion', 'undefined')
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'登录失败, 请求异常')
            return RET_ERR
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"loginCheck":"Y"},"messages":[],"validateMessages":{}}
        obj = r.json()
        if (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['loginCheck'])
                and (obj['data']['loginCheck'] == 'Y')):
            print(u'登陆成功^_^')
            url = 'https://kyfw.12306.cn/otn/login/userLogin'
            parameters = [
                ('_json_att', ''),
            ]
            payload = urllib.urlencode(parameters)
            r = self.post(url, payload)
            return RET_OK
        else:
            print(u'登陆失败啦!重新登陆...')
            dumpObj(obj)
            return RET_ERR

    def getPassengerDTOs(self):
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs'
        parameters = [
            ('', ''),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'获取乘客信息异常')
            return RET_ERR
        obj = r.json()
        if (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['normal_passengers'])
                and obj['data']['normal_passengers']):
            self.normal_passengers = obj['data']['normal_passengers']
            return RET_OK
        else:
            print(u'获取乘客信息失败')
            if hasKeys(obj, ['messages']):
                dumpObj(obj['messages'])
            if hasKeys(obj, ['data']) and hasKeys(obj['data'], ['exMsg']):
                dumpObj(obj['data']['exMsg'])
            return RET_ERR

    def selectPassengers(self, prompt):
        if prompt == 1:
            print(u'是否重新选择乘客?(如需选择请输入y或者yes, 默认使用配置文件提供的乘客信息)')
            act = raw_input()
            act = act.lower()
            if act != 'y' and act != 'yes':
                self.printConfig()
                return RET_OK
        if not (self.normal_passengers and len(self.normal_passengers)):
            tries = 0
            while tries < MAX_TRIES:
                tries += 1
                if self.getPassengerDTOs() == RET_OK:
                    break
            else:
                print(u'获取乘客信息失败次数太多, 使用配置文件提供的乘客信息')
                return RET_ERR
        num = len(self.normal_passengers)
        for i in xrange(0, num):
            p = self.normal_passengers[i]
            print(u'%d.%s  \t' % (i + 1, p['passenger_name'])),
            if (i + 1) % 5 == 0:
                print('')
        while True:
            print(u'\n请选择乘车人(最多选择5个, 以逗号隔开, 如:1,2,3,4,5, 直接回车不选择, 使用配置文件中的乘客信息)')
            buf = raw_input()
            if not buf:
                return RET_ERR
            pattern = re.compile(r'^[0-9,]*\d$')  # 只能输入数字和逗号, 并且必须以数字结束
            if pattern.match(buf):
                break
            else:
                print(u'输入格式错误, 只能输入数字和逗号, 并且必须以数字结束, 如:1,2,3,4,5')

        ids = buf.split(',')
        if not (ids and 1 <= len(ids) <= 5):
            return RET_ERR

        seattype = selectSeatType()

        ids = [int(id) for id in ids]
        del self.passengers[:]
        for id in ids:
            if id < 1 or id > num:
                print(u'不存在的联系人, 忽略')
            else:
                passenger = {}
                id = id - 1
                passenger['index'] = len(self.passengers) + 1
                passenger['name'] = self.normal_passengers[id]['passenger_name']
                passenger['cardtype'] = self.normal_passengers[id]['passenger_id_type_code']
                passenger['id'] = self.normal_passengers[id]['passenger_id_no']
                passenger['phone'] = self.normal_passengers[id]['mobile_no']
                passenger['seattype'] = seattype
                passenger['tickettype'] = self.normal_passengers[id]['passenger_type']
                self.passengers.append(passenger)
        self.printConfig()
        return RET_OK

    def queryTickets(self):
        self.canWebBuy = False
        url = 'https://kyfw.12306.cn/otn/leftTicket/init'
        parameters = [
            ('_json_att', ''),
            ('leftTicketDTO.from_station_name', self.from_city_name),
            ('leftTicketDTO.to_station_name', self.to_city_name),
            ('leftTicketDTO.from_station', self.from_station_telecode),
            ('leftTicketDTO.to_station', self.to_station_telecode),
            ('leftTicketDTO.train_date', self.train_date),
            ('back_train_date', self.back_train_date),
            ('purpose_codes', self.purpose_code),
            ('pre_step_flag', 'index')
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'查询车票异常')

        url = 'https://kyfw.12306.cn/otn/leftTicket/log?'
        parameters = [
            ('leftTicketDTO.train_date', self.train_date),
            ('leftTicketDTO.from_station', self.from_station_telecode),
            ('leftTicketDTO.to_station', self.to_station_telecode),
            ('purpose_codes', self.purpose_code),
        ]
        url += urllib.urlencode(parameters)
        r = self.get(url)
        if not r:
            print(u'查询车票异常')

        url = 'https://kyfw.12306.cn/otn/leftTicket/queryT?'
        parameters = [
            ('leftTicketDTO.train_date', self.train_date),
            ('leftTicketDTO.from_station', self.from_station_telecode),
            ('leftTicketDTO.to_station', self.to_station_telecode),
            ('purpose_codes', self.purpose_code),
        ]
        url += urllib.urlencode(parameters)
        r = self.get(url)
        if not r:
            print(u'查询车票异常')
            return RET_ERR
        obj = r.json()
        if (hasKeys(obj, ['status', 'httpstatus', 'data']) and len(obj['data'])):
            self.trains = obj['data']
            return RET_OK
        else:
            print(u'查询车票失败')
            if hasKeys(obj, ['messages']):
                dumpObj(obj['messages'])
            return RET_ERR

    def sendMailNotification(self):
        print(u'正在发送邮件提醒...')
        me = u'订票提醒<%s>' % (self.notify['mail_username'])
        msg = MIMEText(
            self.notify['mail_content'],
            _subtype='plain',
            _charset='gb2312')
        msg['Subject'] = u'余票信息'
        msg['From'] = me
        msg['To'] = ';'.join(self.notify['mail_to'])
        try:
            server = smtplib.SMTP()
            server.connect(self.notify['mail_server'])
            server.login(
                self.notify['mail_username'],
                self.notify['mail_password'])
            server.sendmail(me, self.notify['mail_to'], msg.as_string())
            server.close()
            print(u'发送邮件提醒成功')
            return True
        except Exception as e:
            print(u'发送邮件提醒失败, %s' % str(e))
            return False

    def printTrains(self):
        printDelimiter()
        print(u'余票查询结果如下:')
        print(u"%s\t%s--->%s\n'有':票源充足  '无':票已售完  '*':未到起售时间  '--':无此席别" % (
            self.train_date,
            self.from_city_name,
            self.to_city_name))
        printDelimiter()
        print(u'序号/车次\t乘车站\t目的站\t一等\t二等\t软卧\t硬卧\t硬座\t无座')
        seatTypeCode = {
            'swz': '商务座',
            'tz': '特等座',
            'zy': '一等座',
            'ze': '二等座',
            'gr': '高级软卧',
            'rw': '软卧',
            'yw': '硬卧',
            'rz': '软座',
            'yz': '硬座',
            'wz': '无座',
            'qt': '其它',
        }
        # TODO 余票数量和票价 https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=770000K77505&from_station_no=09&to_station_no=13&seat_types=1431&train_date=2014-01-01
        # yp_info=4022300000301440004610078033421007800536 代表
        # 4022300000 软卧0
        # 3014400046 硬卧46
        # 1007803342 无座342
        # 1007800536 硬座536
        index = 1
        self.notify['mail_content'] = ''
        for train in self.trains:
            t = train['queryLeftNewDTO']
            status = '售完' if t['canWebBuy'] == 'N' else '预定'
            i = 0
            ypInfo = {
                'wz': {  # 无座
                    'price': 0,
                    'left': 0
                },
                'yz': {  # 硬座
                    'price': 0,
                    'left': 0
                },
                'yw': {  # 硬卧
                    'price': 0,
                    'left': 0
                },
                'rw': {  # 软卧
                    'price': 0,
                    'left': 0
                },
            }
            # 分析票价和余票数量
            while i < (len(t['yp_info']) / 10):
                tmp = t['yp_info'][i * 10:(i + 1) * 10]
                price = int(tmp[1:5])
                left = int(tmp[-3:])
                if tmp[0] == '1':
                    if tmp[6] == '3':
                        ypInfo['wz']['price'] = price
                        ypInfo['wz']['left'] = left
                    else:
                        ypInfo['yz']['price'] = price
                        ypInfo['yz']['left'] = left
                elif tmp[0] == '3':
                    ypInfo['yw']['price'] = price
                    ypInfo['yw']['left'] = left
                elif tmp[0] == '4':
                    ypInfo['rw']['price'] = price
                    ypInfo['rw']['left'] = left
                i = i + 1
            yz_price = u'硬座%s' % (
                ypInfo['yz']['price']) if ypInfo['yz']['price'] else ''
            yw_price = u'硬卧%s' % (
                ypInfo['yw']['price']) if ypInfo['yw']['price'] else ''
            print(u'(%d)   %s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' % (
                index,
                t['station_train_code'],
                t['from_station_name'][0:3],  # 最多保留3个中文
                t['to_station_name'][0:3],  # 最多保留3个中文
                t['zy_num'],
                t['ze_num'],
                ypInfo['rw']['left'] if ypInfo['rw']['left'] else t['rw_num'],
                ypInfo['yw']['left'] if ypInfo['yw']['left'] else t['yw_num'],
                #t['rz_num'],
                ypInfo['yz']['left'] if ypInfo['yz']['left'] else t['yz_num'],
                ypInfo['wz']['left'] if ypInfo['wz']['left'] else t['wz_num'],
                #yz_price,
                #yw_price
            ))
            if t['canWebBuy'] == 'Y':
                self.canWebBuy = True
            index += 1
            if self.notify['mail_enable'] == 1 and t['canWebBuy'] == 'Y':
                msg = ''
                prefix = u'[%s]车次%s[%s/%s->%s/%s, 历时%s]现在有票啦\n' % (
                    t['start_train_date'],
                    t['station_train_code'],
                    t['from_station_name'],
                    t['start_time'],
                    t['to_station_name'],
                    t['arrive_time'],
                    t['lishi'])
                if 'all' in self.notify['focus']:  # 任意车次
                    if self.notify['focus']['all'][0] == 'all':  # 任意席位
                        msg = prefix
                    else:  # 指定席位
                        for seat in self.notify['focus']['all']:
                            if seat in ypInfo and ypInfo[seat]['left']:
                                msg += u'座位类型:%s, 剩余车票数量:%s, 票价:%s \n' % (
                                    seat if seat not in seatTypeCode else seatTypeCode[seat],
                                    ypInfo[seat]['left'],
                                    ypInfo[seat]['price'])
                        if msg:
                            msg = prefix + msg + u'\n'
                elif t['station_train_code'] in self.notify['focus']:  # 指定车次
                    # 任意席位
                    if self.notify['focus'][t['station_train_code']][0] == 'all':
                        msg = prefix
                    else:  # 指定席位
                        for seat in self.notify['focus'][t['station_train_code']]:
                            if seat in ypInfo and ypInfo[seat]['left']:
                                msg += u'座位类型:%s, 剩余车票数量:%s, 票价:%s \n' % (
                                    seat if seat not in seatTypeCode else seatTypeCode[seat],
                                    ypInfo[seat]['left'],
                                    ypInfo[seat]['price'])
                        if msg:
                            msg = prefix + msg + u'\n'
                self.notify['mail_content'] += msg
        printDelimiter()
        if self.notify['mail_enable'] == 1:
            if self.notify['mail_content']:
                self.sendMailNotification()
                return RET_OK
            else:
                length = len(self.notify['dates'])
                if length > 1:
                    self.train_date = self.notify['dates'][
                        random.randint(
                            0,
                            length -
                            1)]
                return RET_ERR
        else:
            return RET_OK

    # -1->重新查询/0->退出程序/1~len->车次序号
    def selectAction(self):
        ret = -1
        self.current_train_index = 0
        trains_num = len(self.trains)
        print(u'您可以选择:')
        if self.canWebBuy:
            print(u'1~%d.选择车次开始订票' % (trains_num))
        print(u'p.更换乘车人')
        print(u's.更改席别')
        print(u'd.更改乘车日期')
        print(u'f.更改出发站')
        print(u't.更改目的站')
        print(u'a.同时更改乘车日期,出发站和目的站')
        print(u'u.查询未完成订单')
        print(u'c.查看订票信息')
        print(u'r.刷票模式')
        print(u'n.普通模式')
        print(u'q.退出')
        print(u'刷新车票请直接回车')
        printDelimiter()
        select = raw_input()
        select = select.lower()
        if select.isdigit():
            if not self.canWebBuy:
                print(u'没有可预订的车次, 请刷新车票或者更改查询条件')
                return -1
            index = int(select)
            if index < 1 or index > trains_num:
                print(u'输入的序号无效,请重新选择车次(1~%d)' % (trains_num))
                index = selectTrain(self.trains)
            if self.trains[index - 1]['queryLeftNewDTO']['canWebBuy'] != 'Y':
                print(u'您选择的车次%s没票啦,请重新选择车次' % (self.trains[index - 1]['queryLeftNewDTO']['station_train_code']))
                index = selectTrain(self.trains)
            ret = index
            self.current_train_index = index - 1
        elif select == 'p':
            self.selectPassengers(0)
        elif select == 's':
            seattype = selectSeatType()
            for p in self.passengers:
                p['seattype'] = seattype
            self.printConfig()
        elif select == 'd':
            self.train_date = selectDate()
        elif select == 'f':
            print(u'请输入出发站:')
            station = inputStation()
            self.from_city_name = station['name']
            self.from_station_telecode = station['telecode']
        elif select == 't':
            print(u'请输入目的站:')
            station = inputStation()
            self.to_city_name = station['name']
            self.to_station_telecode = station['telecode']
        elif select == 'a':
            self.train_date = selectDate()
            print(u'请输入出发站:')
            station = inputStation()
            self.from_city_name = station['name']
            self.from_station_telecode = station['telecode']
            print(u'请输入目的站:')
            station = inputStation()
            self.to_city_name = station['name']
            self.to_station_telecode = station['telecode']
        elif select == 'u':
            ret = self.queryMyOrderNotComplete()
            ret = self.selectAction()
        elif select == 'c':
            ret = self.printConfig()
            ret = self.selectAction()
        elif select == 'r':
            self.notify['mail_enable'] = 1
            ret = -1
        elif select == 'n':
            self.notify['mail_enable'] = 0
            ret = -1
        elif select == 'q':
            ret = 0

        return ret

    def initOrder(self):
        url = 'https://kyfw.12306.cn/otn/login/checkUser'
        parameters = [
            ('_json_att', ''),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'初始化订单异常')

        print(u'准备下单喽')
        url = 'https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest'
        parameters = [
            #('ODA4NzIx', 'MTU0MTczYmQ2N2I3MjJkOA%3D%3D'),
            ('myversion', 'undefined'),
            ('secretStr', self.trains[self.current_train_index]['secretStr']),
            ('train_date', self.train_date),
            ('back_train_date', self.back_train_date),
            ('tour_flag', self.tour_flag),
            ('purpose_codes', self.purpose_code),
            ('query_from_station_name', self.from_city_name),
            ('query_to_station_name', self.to_city_name),
            ('undefined', '')
        ]
        # TODO 注意:此处post不需要做urlencode, 比较奇怪, 不能用urllib.urlencode(parameters)
        payload = ''
        length = len(parameters)
        for i in range(0, length):
            payload += parameters[i][0] + '=' + parameters[i][1]
            if i < (length - 1):
                payload += '&'
        r = self.post(url, payload)
        if not r:
            print(u'下单异常')
            return RET_ERR
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"messages":[],"validateMessages":{}}
        obj = r.json()
        if not (hasKeys(obj, ['status', 'httpstatus'])
                and obj['status']):
            print(u'下单失败啦')
            dumpObj(obj)
            return RET_ERR

        print(u'订单初始化...')
        self.session.close()  # TODO
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
        parameters = [
            ('_json_att', ''),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'订单初始化异常')
            return RET_ERR
        data = r.text
        s = data.find('globalRepeatSubmitToken')  # TODO
        e = data.find('global_lang')
        if s == -1 or e == -1:
            print(u'找不到 globalRepeatSubmitToken')
            return RET_ERR
        buf = data[s:e]
        s = buf.find("'")
        e = buf.find("';")
        if s == -1 or e == -1:
            print(u'很遗憾, 找不到 globalRepeatSubmitToken')
            return RET_ERR
        self.repeatSubmitToken = buf[s + 1:e]

        s = data.find('key_check_isChange')
        e = data.find('leftDetails')
        if s == -1 or e == -1:
            print(u'找不到 key_check_isChange')
            return RET_ERR
        self.keyCheckIsChange = data[s + len('key_check_isChange') + 3:e - 3]

        return RET_OK

    def checkOrderInfo(self):
        if self.checkRandCodeAnsyn('passenger') == RET_ERR:
            return RET_ERR

        passengerTicketStr = ''
        oldPassengerStr = ''
        passenger_seat_detail = '0'  # TODO [0->随机][1->下铺][2->中铺][3->上铺]
        for p in self.passengers:
            if p['index'] != 1:
                passengerTicketStr += 'N_'
                oldPassengerStr += '1_'
            passengerTicketStr += '%s,%s,%s,%s,%s,%s,%s,' % (
                p['seattype'],
                passenger_seat_detail,
                p['tickettype'],
                p['name'],
                p['cardtype'],
                p['id'],
                p['phone'])
            oldPassengerStr += '%s,%s,%s,' % (
                p['name'],
                p['cardtype'],
                p['id'])
        passengerTicketStr += 'N'
        oldPassengerStr += '1_'
        self.passengerTicketStr = passengerTicketStr
        self.oldPassengerStr = oldPassengerStr

        print(u'检查订单...')
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo'
        parameters = [
            ('cancel_flag', '2'),  # TODO
            ('bed_level_order_num', '000000000000000000000000000000'),  # TODO
            ('passengerTicketStr', self.passengerTicketStr),
            ('oldPassengerStr', self.oldPassengerStr),
            ('tour_flag', self.tour_flag),
            ('randCode', self.captcha),
            #('NzA4MTc1', 'NmYyYzZkYWY2OWZkNzg2YQ%3D%3D'),  # TODO
            ('_json_att', ''),
            ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'检查订单异常')
            return RET_ERR
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"submitStatus":true},"messages":[],"validateMessages":{}}
        obj = r.json()
        if (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['submitStatus'])
                and obj['status']
                and obj['data']['submitStatus']):
            print(u'检查订单成功')
            return RET_OK
        else:
            print(u'检查订单失败')
            dumpObj(obj)
            return RET_ERR

    def getQueueCount(self):
        print(u'查询排队情况...')
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount'
        t = self.trains[self.current_train_index]['queryLeftNewDTO']
        parameters = [
            ('train_date', date2UTC(self.train_date)),
            ('train_no', t['train_no']),
            ('stationTrainCode', t['station_train_code']),
            ('seatType', '1'),  # TODO
            ('fromStationTelecode', t['from_station_telecode']),
            ('toStationTelecode', t['to_station_telecode']),
            ('leftTicket', t['yp_info']),
            ('purpose_codes', '00'),  # TODO
            ('_json_att', ''),
            ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken)
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'查询排队情况异常')
            return RET_ERR
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"count":"0","ticket":"100985109710098535003021350212","op_2":"false","countT":"0","op_1":"false"},"messages":[],"validateMessages":{}}
        obj = r.json()
        if not (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['op_1', 'op_2'])
                and obj['status']):
            print(u'查询排队情况失败')
            dumpObj(obj)
            return RET_ERR
        if obj['data']['op_1'] != 'false':
            print(u'已有人先于您提交相同的购票需求, 到处理您的需求时可能已无票, 建议根据当前余票确定是否排队.')
        if obj['data']['op_2'] != 'false':
            print(u'目前排队人数已经超过余票张数，请您选择其他席别或车次，特此提醒。')
        if 'ticket' in obj['data']:
            print(u'排队详情:%s' % (obj['data']['ticket']))  # TODO

        return RET_OK

    def confirmSingleForQueue(self):
        print(u'提交订单排队...')
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
        t = self.trains[self.current_train_index]['queryLeftNewDTO']
        parameters = [
            ('passengerTicketStr', self.passengerTicketStr),
            ('oldPassengerStr', self.oldPassengerStr),
            ('randCode', self.captcha),
            ('purpose_codes', '00'),  # TODO
            ('key_check_isChange', self.keyCheckIsChange),
            ('leftTicketStr', t['yp_info']),
            ('train_location', t['location_code']),
            ('_json_att', ''),
            ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'提交订单排队异常')
            return RET_ERR
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"submitStatus":true},"messages":[],"validateMessages":{}}
        obj = r.json()
        if (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['submitStatus'])
                and obj['status'] and obj['data']['submitStatus']):
            print(u'订单排队中...')
            return RET_OK
        else:
            print(u'提交订单排队失败')
            dumpObj(obj)
            return RET_ERR

    def queryOrderWaitTime(self):
        print(u'等待订单流水号...')
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=%13d&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN=%s' % (
            random.randint(1000000000000, 1999999999999), self.repeatSubmitToken)
        r = self.get(url)
        if not r:
            print(u'等待订单流水号异常')
            return RET_ERR
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"queryOrderWaitTimeStatus":true,"count":0,"waitTime":4,"requestId":5944637152210732219,"waitCount":2,"tourFlag":"dc","orderId":null},"messages":[],"validateMessages":{}}
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"queryOrderWaitTimeStatus":true,"count":0,"waitTime":-1,"requestId":5944637152210732219,"waitCount":0,"tourFlag":"dc","orderId":"E739900792"},"messages":[],"validateMessages":{}}
        obj = r.json()
        if not (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['orderId'])
                and obj['status']
                and obj['data']['orderId']):
            print(u'等待订单流水号失败')
            dumpObj(obj)
            return RET_ERR
        self.orderId = obj['data']['orderId']
        if (self.orderId and self.orderId != 'null'):
            print(u'订单流水号为:')
            print(self.orderId)
            return RET_OK
        else:
            print(u'等待订单流水号失败')
            return RET_ERR

    def payOrder(self):
        print(u'等待订票结果...')
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue'
        parameters = [
            ('orderSequence_no', self.orderId),
            ('_json_att', ''),
            ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'等待订票结果异常')
            return RET_ERR
        # {'validateMessagesShowId':'_validatorMessage','status':true,'httpstatus':200,'data':{'submitStatus':true},'messages':[],'validateMessages':{}}
        # {'validateMessagesShowId':'_validatorMessage','status':true,'httpstatus':200,'data':{'errMsg':'获取订单信息失败，请查看未完成订单，继续支付！','submitStatus':false},'messages':[],'validateMessages':{}}
        obj = r.json()
        if not (
                hasKeys(obj, ['status', 'httpstatus', 'data'])
                and hasKeys(obj['data'], ['submitStatus'])
                and obj['status']
                and obj['data']['submitStatus']):
            print(u'等待订票结果失败')
            dumpObj(obj)
            return RET_ERR

        url = 'https://kyfw.12306.cn/otn//payOrder/init?random=%13d' % (
            random.randint(1000000000000, 1999999999999))
        parameters = [
            ('_json_att', ''),
            ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'请求异常')
            return RET_ERR
        data = r.text
        if data.find(u'席位已锁定') != -1:
            print(u'订票成功^_^请在45分钟内完成网上支付,否则系统将自动取消')
            return RET_OK
        else:
            return RET_ERR

    def queryMyOrderNotComplete(self):
        print(u'正在查询未完成订单...')
        url = 'https://kyfw.12306.cn/otn/queryOrder/queryMyOrderNoComplete'
        parameters = [
            ('_json_att', ''),
        ]
        payload = urllib.urlencode(parameters)
        r = self.post(url, payload)
        if not r:
            print(u'查询未完成订单异常')
            return RET_ERR
        obj = r.json()
        if not (hasKeys(obj, ['status', 'httpstatus', 'data']) and obj['status']):
            print(u'查询未完成订单失败')
            dumpObj(obj)
            return RET_ERR
        if (hasKeys(obj['data'], ['orderDBList']) and len(obj['data']['orderDBList'])):
            print(u'查询到有未完成订单，请先处理')
            return RET_OK
        if (
                hasKeys(obj['data'], ['orderCacheDTO'])
                and obj['data']['orderCacheDTO']
                and hasKeys(obj['data']['orderCacheDTO'], ['status'])):
            if obj['data']['orderCacheDTO']['status'] == 0:
                print(u'查询到cache有未完成订单，请先处理')
                return RET_OK
            else:
                if (hasKeys(obj['data']['orderCacheDTO'], ['message'])):
                    dumpObj(obj['data']['orderCacheDTO']['message'])

        return RET_ERR


def main():
    print(getTime())

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Specify config file')
    parser.add_argument('-u', '--username', help='Specify username to login')
    parser.add_argument('-p', '--password', help='Specify password to login')
    parser.add_argument('-d', '--date', help='Specify train date, 2014-01-01')
    parser.add_argument('-m', '--mail', help='Send email notification')
    args = parser.parse_args()

    order = MyOrder()
    order.initSession()
    order.initStation()
    if args.config:
        order.readConfig(args.config)  # 使用指定的配置文件
    else:
        order.readConfig()  # 使用默认的配置文件config.ini
    if args.username:
        order.username = args.username  # 使用指定的账号代替配置文件中的账号
    if args.password:
        order.password = args.password  # 使用指定的密码代替配置文件中的密码
    if args.date:
        if checkDate(args.date):
            order.train_date = args.date  # 使用指定的乘车日期代替配置文件中的乘车日期
        else:
            print(u'乘车日期无效, 请重新选择')
            order.train_date = selectDate()
    if args.mail:
        # 有票时自动发送邮件通知
        order.notify['mail_enable'] = 1 if args.mail == '1' else 0
    tries = 0
    while tries < MAX_TRIES:
        tries += 1
        if order.login() == RET_OK:
            break
    else:
        print(u'失败次数太多,自动退出程序')
        sys.exit()
    order.selectPassengers(1)

    while True:
        time.sleep(1)
        # 查询车票
        if order.queryTickets() != RET_OK:
            continue
        # 显示查询结果
        if order.printTrains() != RET_OK:
            continue
        # 选择菜单列举的动作之一
        action = order.selectAction()
        if action == -1:
            continue
        elif action == 0:
            break
        # 订单初始化
        if order.initOrder() != RET_OK:
            continue
        # 检查订单信息
        if order.checkOrderInfo() != RET_OK:
            continue
        # 查询排队和余票情况
        # if order.getQueueCount() != RET_OK:
        #  continue
        # 提交订单到队里中
        tries = 0
        while tries < 2:
            tries += 1
            if order.confirmSingleForQueue() == RET_OK:
                break
        # 获取orderId
        tries = 0
        while tries < 2:
            tries += 1
            if order.queryOrderWaitTime() == RET_OK:
                break
        # 正式提交订单
        if order.payOrder() == RET_OK:
            break
        # 访问未完成订单页面检查是否订票成功
        if order.queryMyOrderNotComplete() == RET_OK:
            print(u'订票成功^_^请在45分钟内完成网上支付,否则系统将自动取消')
            break

    print(getTime())
    raw_input('Press any key to continue')

if __name__ == '__main__':
    main()

# EOF
