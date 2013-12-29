#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import cookielib
import urllib
import urllib2
import json
import time
import sys
import re
import ConfigParser
import codecs
import random
#import logging

# Global variables
stations = []
RET_OK = 0
RET_ERR = -1

# Set default encoding to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

#------------------------------------------------------------------------------
# 分隔线
def printDelimiter():
  print '-'*100

#------------------------------------------------------------------------------
# 火车站点数据库初始化
# 全部站点, 数据来自: https://kyfw.12306.cn/otn/resources/js/framework/station_name.js
# 每个站的格式如下:
# @bji|北京|BJP|beijing|bj|2   ---> @拼音缩写三位|站点名称|编码|拼音|拼音缩写|序号
def stationInit():
  url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
  referer = "https://kyfw.12306.cn/otn/"
  resp = sendGetRequest(url, referer)
  try:
    respInfo = resp.read().decode("utf-8","ignore")
    if respInfo.find("'@") != -1:
      station_names = respInfo[respInfo.find("'@"):]
    else:
      print(u"读取站点信息失败")
      return {}
  except:
    print(u"读取站点信息异常")
  station_list = station_names.split('@')
  station_list = station_list[1:] # The first one is empty, skip it

  for station in station_list:
    items = station.split('|') # bjb|北京北|VAP|beijingbei|bjb|0
    stations.append({'abbr':items[0], 'name':items[1], 'telecode':items[2], 'pinyin':items[4]})

  return stations

#------------------------------------------------------------------------------
# Convert station object by name or abbr or pinyin
def getStationByName(name):
  matched_stations = []
  for station in stations:
    if station['name'] == name or station['abbr'].find(name.lower()) != -1 or station['pinyin'].find(name.lower()) != -1:
      matched_stations.append(station)
  count = len(matched_stations)
  if not count:
    return None
  elif count == 1:
    return matched_stations[0]
  else:
    for i in xrange(0,count):
      print(u'%d:\t%s'%(i+1, matched_stations[i]['name']))
    print(u"请选择站点(1~%d)"%(count))
    index = raw_input()
    if not index.isdigit():
      print(u"只能输入数字序号(1~%d)"%(count))
      return None
    index = int(index)
    if index<1 or index>count:
      print(u"输入的序号无效(1~%d)"%(count))
      return None
    else:
      return matched_stations[index-1]

#------------------------------------------------------------------------------
# Get current time with format 2014-01-01 12:00:00
def getTime():
  return time.strftime("%Y-%m-%d %X",time.localtime())

#------------------------------------------------------------------------------
# Get current date with format 2014-01-01
def getDate():
  return time.strftime("%Y-%m-%d",time.localtime())

# Convert '2014-01-01' to 'Wed Jan 01 00:00:00 UTC+0800 2014'
def trainDate(d):
  t = time.strptime(d,'%Y-%m-%d') # time.struct_time(tm_year=2014, tm_mon=1, tm_mday=1, tm_hour=0, tm_min=0, tm_sec=0, tm_wday=2, tm_yday=1, tm_isdst=-1)
  asc = time.asctime(t) # 'Wed Jan 01 00:00:00 2014'
  return (asc[0:-4] + 'UTC+0800 ' + asc[-4:]) # 'Wed Jan 01 00:00:00 UTC+0800 2014'

#------------------------------------------------------------------------------
# 证件类型
def getCardType(cardtype):
  d = {
    '1':u"二代身份证",
    '2':u"一代身份证",
    'C':u"港澳通行证",
    'G':u"台湾通行证",
    'B':u"护照"
  }

  if d.has_key(cardtype):
    return d[cardtype]
  else:
    return u"未知证件类型"

#------------------------------------------------------------------------------
# 席别:
def getSeatType(seattype):
  d = {
    '1':u"硬座",#硬座/无座
    '3':u"硬卧",
    '4':u"软卧",
    '7':u"一等软座",
    '8':u"二等软座",
    '9':u"商务座",
    'M':u"一等座",
    'O':u"二等座",
    'P':u"特等座"
  }

  if d.has_key(seattype):
    return d[seattype]
  else:
    return u"未知席别"

#------------------------------------------------------------------------------
# 票种类型
def getTicketType(tickettype):
  d = {
    '1':u"成人票",
    '2':u"儿童票",
    '3':u"学生票",
    '4':u"残军票"
  }

  if d.has_key(tickettype):
    return d[tickettype]
  else:
    return u"未知票种"

#------------------------------------------------------------------------------
# Check date format
def checkDate(date):
  m = re.match(r'^\d{4}-\d{2}-\d{2}$',date) # 2014-01-01

  if m:
    return 1
  else:
    return 0

#------------------------------------------------------------------------------
# Input date
def inputDate(prompt=u"请输入乘车日期:"):
  train_date = ''

  while 1:
    train_date = raw_input(prompt)
    if checkDate(train_date):
      break
    else:
      print u"格式错误,请重新输入有效的乘车日期,如2014-02-01:"

  return train_date

#------------------------------------------------------------------------------
# Input station
def inputStation(prompt=''):
  station = None
  print prompt,
  print u'(支持中文,拼音和拼音缩写,如:北京,beijing,bj)'

  while 1:
    name = raw_input().decode("gb2312","ignore")
    station = getStationByName(name)
    if station:
      return station
    else:
      print u"站点错误,没有站点'%s',请重新输入:"%(name)

#------------------------------------------------------------------------------
# Send post request
def sendPostRequest(url, data, referer='https://kyfw.12306.cn/otn/index/init'):
  post_timeout = 300
  req = urllib2.Request(url, data)
  req.add_header('Content-Type', "application/x-www-form-urlencoded")
  req.add_header('Referer', referer)

  resp = None
  tries = 0
  max_tries = 3
  while tries < max_tries:
    tries += 1
    try:
      resp = urllib2.urlopen(req, timeout=post_timeout*tries)
    except urllib2.HTTPError,e:
      print("Post %d times %s exception HTTPError code:"%(tries, url), e.code)
    except urllib2.URLError,e:
      print("Post %d times %s exception URLError reason:"%(tries, url), e.reason)
    except:
      print("Post %d times %s exception other"%(tries, url))
    if resp:
      break
  return resp

#------------------------------------------------------------------------------
# Send get request
def sendGetRequest(url,referer='https://kyfw.12306.cn/otn/index/init'):
  get_timeout = 150
  req = urllib2.Request(url)
  req.add_header('Referer', referer)

  resp = None
  tries = 0
  max_tries = 3
  while tries < max_tries:
    tries += 1
    try:
      resp = urllib2.urlopen(req,timeout=get_timeout*tries)
    except urllib2.HTTPError,e:
      print("Get %d times %s exception HTTPError code:"%(tries, url), e.code)
    except urllib2.URLError,e:
      print("Get %d times %s exception URLError reason:"%(tries, url), e.reason)
    except:
      print("Get %d times %s exception other"%(tries, url))
    if resp:
      break
  return resp

#------------------------------------------------------------------------------
# 保存验证码图片到本地, 再手动输入
def getCaptcha(url, module, rand):
  randUrl = 'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do?module=%s&rand=%s'%(module, rand);
  captcha = ''
  while 1:
    f = open("captcha.jpg","wb")
    f.write(urllib2.urlopen(url).read())
    f.close()
    print u"请输入4位图片验证码(直接回车刷新):"
    url = "%s&%1.16f"%(randUrl, random.random())
    captcha = raw_input("")
    if len(captcha) == 4:
      return captcha

#------------------------------------------------------------------------------
# Convert json string to dict object
def data2Json(data, keys):
  obj = json.loads(data);
  if not (obj and set(keys).issubset(obj)):
    print(u'data2Json() failed')
    return {}
  #print json.dumps(obj, indent=2)
  return obj

#------------------------------------------------------------------------------
# Select train
def selectTrain(trains):
  trains_num = len(trains)
  index = 0
  while 1: # 必须选择有效的车次
    index = raw_input("")
    if not index.isdigit():
      print u"只能输入数字序号,请重新选择车次(1~%d)"%(trains_num)
      continue
    index = int(index)
    if index<1 or index>trains_num:
      print u"输入的序号无效,请重新选择车次(1~%d)"%(trains_num)
      continue
    if trains[index-1]['queryLeftNewDTO']['canWebBuy'] != 'Y':
      print u"您选择的车次%s没票啦,请重新选择车次"%(trains[index-1]['queryLeftNewDTO']['station_train_code'])
      continue
    else:
      break

  return index

class MyOrder(object):
  """docstring for MyOrder"""
  def __init__(self, username='', password='', train_date='', from_city_name='', to_city_name=''):
    super(MyOrder, self).__init__()
    self.username = username # 账号
    self.password = password # 密码
    self.train_date = train_date # 乘车日期[2014-01-01]
    self.back_train_date = getDate() # 返程日期[2014-01-01]
    self.tour_flag = 'dc' # 单程dc/往返wf
    self.purpose_code = 'ADULT' # 成人票
    self.from_city_name = from_city_name # 对应查询界面'出发地'输入框中的内容
    self.to_city_name = to_city_name # 对应查询界面'目的地'输入框中的内容
    self.from_station_telecode = '' # 出发站编码
    self.to_station_telecode = '' # 目的站编码
    self.passengers = [] # 乘客列表
    self.trains = [] # 列车列表, 查询余票后自动更新
    self.current_train_index = 0 # 当前选中的列车索引序号
    self.captcha = '' # 图片验证码
    self.orderId = '' # 订单流水号

  def readConfig(self,config_file='config.ini'):
    # 从配置文件读取订票信息
    cp = ConfigParser.ConfigParser()
    try:
      cp.readfp(codecs.open(config_file, 'r','utf-8-sig'))
    except IOError as e:
      print u"打开配置文件'%s'失败啦!,请先创建或者拷贝一份配置文件config.ini"%(config_file)
      if raw_input('Press any key to continue'):
        sys.exit()
    self.username = cp.get("login","username")
    self.password = cp.get("login","password")
    self.train_date = cp.get("train","date");
    self.from_city_name = cp.get("train","from")
    self.to_city_name = cp.get("train","to")
    # 检查出发站
    station = getStationByName(self.from_city_name)
    if not station:
      station = inputStation(u"出发站错误,请重新输入:")
    self.from_city_name = station['name']
    self.from_station_telecode = station['telecode']
    # 检查目的站
    station = getStationByName(self.to_city_name)
    if not station:
      station = inputStation(u"目的站错误,请重新输入:")
    self.to_city_name = station['name']
    self.to_station_telecode = station['telecode']
    # 检查乘车日期
    if not checkDate(self.train_date):
      self.train_date = inputDate(u"乘车日期错误,请重新输入:")
    # 分析乘客信息
    self.passengers = []
    index = 1
    passenger_sections = ["passenger%d"%(i) for i in xrange(1,6)]
    sections = cp.sections()
    for section in passenger_sections:
      if section in sections:
        passenger = {}
        passenger['index'] = index
        passenger['name'] = cp.get(section,"name") # 必选参数
        passenger['cardtype'] = cp.get(section,"cardtype") if cp.has_option(section,"cardtype") else "1" # 证件类型:可选参数,默认值1,即二代身份证
        passenger['id'] = cp.get(section,"id") # 必选参数
        passenger['phone'] = cp.get(section,"phone") if cp.has_option(section,"phone") else "13800138000" # 手机号码
        passenger['seattype'] = cp.get(section,"seattype") if cp.has_option(section,"seattype") else "1" # 席别:可选参数, 默认值1, 即硬座
        passenger['tickettype'] = cp.get(section,"tickettype") if cp.has_option(section,"tickettype") else "1" #票种:可选参数, 默认值1, 即成人票
        self.passengers.append(passenger)
        index += 1

  def printConfig(self):
    printDelimiter()
    print u"订票信息:"
    print u"%s\t%s\t%s--->%s"%(self.username,self.train_date,self.from_city_name,self.to_city_name)
    printDelimiter()
    print u"序号 姓名\t证件类型\t证件号码\t\t手机号码\t席别\t票种\t"
    for p in self.passengers:
      print u"%d  %s\t%s\t%s\t%s\t%s\t%s"%(p['index'],p['name'].decode("utf-8","ignore"),getCardType(p['cardtype']),p['id'],p['phone'],getSeatType(p['seattype']),getTicketType(p['tickettype']))

  def initCookieJar(self):
    self.cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
    opener.addheaders = [
      ('Accept', 'image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/x-shockwave-flash, application/vnd.ms-excel, application/vnd.ms-powerpoint, application/msword, */*'),
      ('Accept-Encoding', 'deflate'),
      ('Accept-Language', 'zh-CN'),
      ('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/6.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET4.0C; .NET4.0E; MALC)'),
      ('Referer', 'https://kyfw.12306.cn/otn/index/init'),
      ('Host', "kyfw.12306.cn"),
      ('Connection', 'Keep-Alive'),
    ]
    urllib2.install_opener(opener)

  def login(self):
    url = "https://kyfw.12306.cn/otn/login/init"
    referer = "https://kyfw.12306.cn/otn/"
    resp = sendGetRequest(url, referer)

    print(u"接收登录验证码...")
    url = 'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=login&rand=sjrand'
    if self.cj._cookies['kyfw.12306.cn']['/otn']['JSESSIONID'].value:
      url = 'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew;jsessionid=%s?module=login&rand=sjrand'%(self.cj._cookies['kyfw.12306.cn']['/otn']['JSESSIONID'].value)
    self.captcha = getCaptcha(url, 'login', 'sjrand')

    print(u"正在校验登录验证码...")
    url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
    referer = "https://kyfw.12306.cn/otn/login/init"
    parameters = [
      ('randCode', self.captcha),
      ('rand', "sjrand"),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":"Y","messages":[],"validateMessages":{}}
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":"N","messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and (obj['data'] == 'Y')):
      print(u"校验登录验证码失败")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR
    print(u"校验登录验证码成功")

    print(u"正在登录...")
    url = "https://kyfw.12306.cn/otn/login/loginAysnSuggest"
    referer = "https://kyfw.12306.cn/otn/login/init"
    parameters = [
      ('loginUserDTO.user_name', self.username),
      ('userDTO.password', self.password),
      ('randCode', self.captcha),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{},"messages":["密码输入错误,您还有3次机会!"],"validateMessages":{}}
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"loginCheck":"Y"},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['data'].has_key('loginCheck') and (obj['data']['loginCheck'] == 'Y')):
      print(u"登陆失败啦!重新登陆...")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR

    # 可以省略的步骤
    '''
    url = "https://kyfw.12306.cn/otn/login/userLogin"
    referer = "https://kyfw.12306.cn/otn/login/init"
    parameters = [
      ('_json_att', ""),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    '''

    print(u"登陆成功^_^")
    return RET_OK

  def loginProc(self):
    tries = 0
    while tries < 3:
      tries += 1
      printDelimiter()
      if self.login() == RET_OK:
        break
    else:
      print u"失败次数太多,自动退出程序"
      sys.exit()

  def queryTickets(self):
    # 可以省略的步骤
    '''
    url = 'https://kyfw.12306.cn/otn/index/init'
    referer = 'https://kyfw.12306.cn/otn/login/init'
    resp = sendGetRequest(url, referer)
    '''

    # 可以省略的步骤
    '''
    url = "https://kyfw.12306.cn/otn/leftTicket/init"
    referer = "https://kyfw.12306.cn/otn/index/init"
    parameters = [
      ('_json_att', ''),
      ('leftTicketDTO.from_station_name', self.from_city_name),
      ('leftTicketDTO.to_station_name', self.to_city_name),
      ('leftTicketDTO.from_station', self.from_station_telecode),
      ('leftTicketDTO.to_station', self.to_station_telecode),
      ('leftTicketDTO.train_date', self.train_date),
      ('back_train_date', self.back_train_date),
      ('flag', self.tour_flag),
      ('purpose_code', self.purpose_code),
      ('pre_step_flag', 'index'),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    resp.read()
    '''

    # 可以省略的步骤
    #self.captcha = getCaptcha('https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=login&rand=sjrand', 'login', 'sjrand')

    url = 'https://kyfw.12306.cn/otn/leftTicket/query?'
    referer = 'https://kyfw.12306.cn/otn/leftTicket/init'
    parameters = [
      ('leftTicketDTO.train_date', self.train_date),
      ('leftTicketDTO.from_station', self.from_station_telecode),
      ('leftTicketDTO.to_station', self.to_station_telecode),
      ('purpose_codes', self.purpose_code),
    ]
    url += urllib.urlencode(parameters)
    resp = sendGetRequest(url, referer)
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and len(obj['data'])):
      print(u'查询车票失败')
      return RET_ERR
    else:
      self.trains = obj['data']
      return RET_OK

  def printTrains(self):
    printDelimiter()
    print u"%s\t%s--->%s  '有':票源充足  '无':票已售完  '*':未到起售时间  '--':无此席别"%(self.train_date,self.from_city_name,self.to_city_name)
    print u"余票查询结果如下:"
    printDelimiter()
    print u"序号/车次\t乘车站\t目的站\t一等座\t二等座\t软卧\t硬卧\t软座\t硬座\t无座\t价格"
    '''
    seatTypeCode = {
      'swz':'商务座',
      'tz':'特等座',
      'zy':'一等座',
      'ze':'二等座',
      'gr':'高级软卧',
      'rw':'软卧',
      'yw':'硬卧',
      'rz':'软座',
      'yz':'硬座',
      'wz':'无座',
      'qt':'其它',
    }
    '''
    printDelimiter()
    # TODO 余票数量和票价 https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=770000K77505&from_station_no=09&to_station_no=13&seat_types=1431&train_date=2014-01-01
    # yp_info=4022300000301440004610078033421007800536 代表
    # 4022300000 软卧0
    # 3014400046 硬卧46
    # 1007803342 无座342
    # 1007800536 硬座536
    index = 1
    for train in self.trains:
      t = train['queryLeftNewDTO']
      status = '售完' if t['canWebBuy']=='N' else '预定'
      i = 0
      ypInfo = {
        'wz':{ # 无座
          'price':0,
          'left':0
          },
        'yz':{ # 硬座
          'price':0,
          'left':0
          },
        'yw':{ # 硬卧
          'price':0,
          'left':0
          },
        'rw':{ # 软卧
          'price':0,
          'left':0
          },
      }
      # 分析票价和余票数量
      while i < (len(t['yp_info']) / 10):
        tmp = t['yp_info'][i*10:(i+1)*10]
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
      yz_price = u'硬座%s'%(ypInfo['yz']['price']) if ypInfo['yz']['price'] else ''
      yw_price = u'硬卧%s'%(ypInfo['yw']['price']) if ypInfo['yw']['price'] else ''
      print u"(%d)   %s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s%s"%(index,
        t['station_train_code'],
        t['from_station_name'],
        t['to_station_name'],
        t["zy_num"],
        t["ze_num"],
        ypInfo['rw']['left'] if ypInfo['rw']['left'] else t["rw_num"],
        ypInfo['yw']['left'] if ypInfo['yw']['left'] else t["yw_num"],
        t["rz_num"],
        ypInfo['yz']['left'] if ypInfo['yz']['left'] else t["yz_num"],
        ypInfo['wz']['left'] if ypInfo['wz']['left'] else t["wz_num"],
        yz_price,
        yw_price)
      index += 1
    printDelimiter()

  # -1->重新查询/0->退出程序/1~len->车次序号
  def selectAction(self):
    ret = -1
    self.current_train_index = 0
    trains_num = len(self.trains)
    print u"您可以选择:\n1~%d.选择车次开始订票\nd.更改乘车日期\nf.更改出发站\nt.更改目的站\ns.同时更改出发站和目的站\na.同时更改乘车日期,出发站和目的站\nq.退出\n刷新车票请直接回车"%(trains_num)
    printDelimiter()
    select = raw_input("")
    if select.isdigit():
      index = int(select)
      if index<1 or index>trains_num:
        print u"输入的序号无效,请重新选择车次(1~%d)"%(trains_num)
        index = selectTrain(self.trains)
      if self.trains[index-1]['queryLeftNewDTO']['canWebBuy'] != 'Y':
        print u"您选择的车次%s没票啦,请重新选择车次"%(self.trains[index-1]['queryLeftNewDTO']['station_train_code'])
        index = selectTrain(self.trains)
      ret = index
      self.current_train_index = index - 1
    elif select == "d" or select == "D":
      self.train_date = inputDate()
    elif select == "f" or select == "F":
      station = inputStation(u"请输入出发站:")
      self.from_city_name = station['name']
      self.from_station_telecode = station['telecode']
    elif select == "t" or select == "T":
      station = inputStation(u"请输入目的站:")
      self.to_city_name = station['name']
      self.to_station_telecode = station['telecode']
    elif select == "s" or select == "S":
      station = inputStation(u"请输入出发站:")
      self.from_city_name = station['name']
      self.from_station_telecode = station['telecode']
      station = inputStation(u"请输入目的站:")
      self.to_city_name = station['name']
      self.to_station_telecode = station['telecode']
    elif select == "a" or select == "A":
      self.train_date = inputDate()
      station = inputStation(u"请输入出发站:")
      self.from_city_name = station['name']
      self.from_station_telecode = station['telecode']
      station = inputStation(u"请输入目的站:")
      self.to_city_name = station['name']
      self.to_station_telecode = station['telecode']
    elif select == "q" or select == "Q":
      ret = 0

    return ret

  def initOrder(self):
    # 可以省略的步骤
    # 检查登录
    '''
    url = 'https://kyfw.12306.cn/otn/login/checkUser'
    referer = 'https://kyfw.12306.cn/otn/leftTicket/init'
    parameters = [
      ('_json_att', ''),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"flag":true},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['data'].has_key('flag') and obj['data']['flag']):
      print(u"你好像还没有登录哦")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR
    '''

    print(u"准备下单喽")
    url = 'https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest'
    referer = 'https://kyfw.12306.cn/otn/leftTicket/init'
    parameters = [
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
    postData = ''
    length = len(parameters);
    for i in range(0, length):
      postData += parameters[i][0] + '=' + parameters[i][1]
      if i < (length - 1):
        postData += '&'
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus'))
    if not (obj and obj['status']):
      print(u"下单失败啦")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
        #print ','.join(obj['messages'])
      return RET_ERR

    print(u"订单初始化...")
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    referer = 'https://kyfw.12306.cn/otn/leftTicket/init'
    parameters = [
      ('_json_att', ''),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    respInfo = resp.read()
    s = respInfo.find('globalRepeatSubmitToken') # TODO
    e = respInfo.find('global_lang')
    if s == -1 or e == -1:
      print(u'找不到 globalRepeatSubmitToken')
      return RET_ERR
    buf = respInfo[s:e]
    s = buf.find("'")
    e = buf.find("';")
    if s == -1 or e == -1:
      print(u'很遗憾, 找不到 globalRepeatSubmitToken')
      return RET_ERR
    self.repeatSubmitToken = buf[s+1:e]

    s = respInfo.find('key_check_isChange')
    e = respInfo.find('leftDetails')
    if s == -1 or e == -1:
      print(u'找不到 key_check_isChange')
      return RET_ERR
    self.keyCheckIsChange = respInfo[s+len('key_check_isChange')+3:e-3]

    return RET_OK

  def checkOrderInfo(self):
    print(u"接收订单验证码...")
    self.captcha = getCaptcha("https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=passenger&rand=randp", 'passenger', 'randp')

    # 可以省略的步骤
    '''
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs'
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    parameters = [
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    '''

    print(u"正在校验订单验证码...")
    url = 'https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn'
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    parameters = [
      ('randCode', self.captcha),
      ('rand', 'randp'),
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":"Y","messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and (obj['data'] == 'Y')):
      print(u"校验订单验证码失败")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR
    print(u"校验订单验证码成功")

    passengerTicketStr = ''
    oldPassengerStr = ''
    passenger_seat_detail = "0" # [0->随机][1->下铺][2->中铺][3->上铺]
    for p in self.passengers:
      if p['index'] != 1:
        passengerTicketStr += 'N_'
        oldPassengerStr += '1_'
      passengerTicketStr += '%s,%s,%s,%s,%s,%s,%s,'%(p['seattype'],passenger_seat_detail,p['tickettype'],p['name'],p['cardtype'],p['id'],p['phone'])
      oldPassengerStr += '%s,%s,%s,'%(p['name'],p['cardtype'],p['id'])
    passengerTicketStr += 'N'
    oldPassengerStr += '1_'
    self.passengerTicketStr = passengerTicketStr
    self.oldPassengerStr = oldPassengerStr

    print(u"检查订单...")
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo'
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    parameters = [
      ('cancel_flag', '2'), # TODO
      ('bed_level_order_num', '000000000000000000000000000000'), # TODO
      ('passengerTicketStr', self.passengerTicketStr),
      ('oldPassengerStr', self.oldPassengerStr),
      ('tour_flag', self.tour_flag),
      ('randCode', self.captcha),
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"submitStatus":true},"messages":[],"validateMessages":{}}
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"errMsg":"非法的席别，请重新选择！","submitStatus":false},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and obj['data'].has_key('submitStatus') and obj['data']['submitStatus']):
      print(u"检查订单失败")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      if obj['data'].has_key('errMsg') and obj['data']['errMsg']: # 打印错误信息
        print json.dumps(obj['data']['errMsg'], ensure_ascii=False, indent=2)
      return RET_ERR

    return RET_OK

  def getQueueCount(self):
    print(u"查询排队情况...")
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount'
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    t = self.trains[self.current_train_index]['queryLeftNewDTO']
    parameters = [
      ('train_date', trainDate(self.train_date)),
      ('train_no', t['train_no']),
      ('stationTrainCode', t['station_train_code']),
      ('seatType', '1'), # TODO
      ('fromStationTelecode', t['from_station_telecode']),
      ('toStationTelecode', t['to_station_telecode']),
      ('leftTicket', t['yp_info']),
      ('purpose_codes', '00'), # TODO
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken)
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"count":"0","ticket":"1007803168402230000010078003803014400024","op_2":"false","countT":"0","op_1":"false"},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and obj['data'].has_key('op_1') and obj['data'].has_key('op_2')):
      print(u"查询排队情况失败")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR
    if obj['data']['op_1'] != "false":
      print(u'目前排队人数已经超过余票张数，特此提醒。今日已有人先于您提交相同的购票需求，到处理您的需求时可能已无票，建议你们根据当前余票确定是否排队。')
    if obj['data']['op_2'] != "false":
      print(u'目前排队人数已经超过余票张数，请您选择其他席别或车次，特此提醒。')
    if obj['data'].has_key('ticket'):
      print(u'排队详情:%s'%(obj['data']['ticket'])) # TODO

    return RET_OK

  def confirmSingleForQueue(self):
    print(u"提交订单排队...")
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    t = self.trains[self.current_train_index]['queryLeftNewDTO']
    parameters = [
      ('passengerTicketStr', self.passengerTicketStr),
      ('oldPassengerStr', self.oldPassengerStr),
      ('randCode', self.captcha),
      ('purpose_codes', '00'), # TODO
      ('key_check_isChange', self.keyCheckIsChange),
      ('leftTicketStr', t['yp_info']),
      ('train_location', t['location_code']),
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"submitStatus":true},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and obj['data'].has_key('submitStatus') and obj['data']['submitStatus']):
      print(u"提交订单排队失败")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR

    print(u"订单排队中, 先别激动，接下来看你的运气和人品了")
    return RET_OK

  def queryOrderWaitTime(self):
    print(u"等待订票流水号...")
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=%13d&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN=%s'%(random.randint(1000000000000,1999999999999), self.repeatSubmitToken)
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    resp = sendGetRequest(url, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"queryOrderWaitTimeStatus":true,"count":0,"waitTime":4,"requestId":5820530635606607035,"waitCount":1,"tourFlag":"dc","orderId":null},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and obj['data'].has_key('orderId') and obj['data']['orderId']):
      print(u"等待订票流水号失败")
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      return RET_ERR
    self.orderId = obj['data']['orderId']
    print(u"订票流水号为:")
    print(self.orderId)
    return RET_OK

  def payOrder(self):
    print(u"等待订票结果...")
    url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue'
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    parameters = [
      ('orderSequence_no', self.orderId),
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"submitStatus":true},"messages":[],"validateMessages":{}}
    # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"errMsg":"获取订单信息失败，请查看未完成订单，继续支付！","submitStatus":false},"messages":[],"validateMessages":{}}
    obj = data2Json(resp.read(), ('status', 'httpstatus', 'data'))
    if not (obj and obj['status'] and obj['data'].has_key('submitStatus') and obj['data']['submitStatus']):
      if obj.has_key('messages') and obj['messages']: # 打印错误信息
        print json.dumps(obj['messages'], ensure_ascii=False, indent=2)
      if obj['data'].has_key('errMsg') and obj['data']['errMsg']: # 打印错误信息
        print json.dumps(obj['data']['errMsg'], ensure_ascii=False, indent=2)
      return RET_ERR

    url = 'https://kyfw.12306.cn/otn//payOrder/init?random=%13d'%(random.randint(1000000000000,1999999999999))
    referer = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    parameters = [
      ('_json_att', ''),
      ('REPEAT_SUBMIT_TOKEN', self.repeatSubmitToken),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)

    try:
      respInfo = resp.read()
    except:
      print(u"请求异常")
      return RET_ERR
    if respInfo.find(u'席位已锁定') != -1:
      print u"订票成功^_^请在45分钟内完成网上支付,否则系统将自动取消"
      return RET_OK
    else:
      return RET_ERR

  def queryMyOrderNotComplete(self):
    # 可以省略的步骤
    '''
    url = 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete'
    referer = 'https://kyfw.12306.cn/otn//payOrder/init?random=%13d'%(random.randint(1000000000000,1999999999999))
    resp = sendGetRequest(url, referer)
    try:
      respInfo = resp.read()
    except:
      print(u"请求异常")
      return RET_ERR
    if respInfo.find(u'总张数') != -1 and respInfo.find(u'待支付金额') != -1:
      print u"订票成功^_^请在45分钟内完成订单,否则系统将自动取消"
      return RET_OK
    '''

    url = 'https://kyfw.12306.cn/otn/queryOrder/queryMyOrderNoComplete'
    referer = 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete'
    parameters = [
      ('_json_att', ''),
    ]
    postData = urllib.urlencode(parameters)
    resp = sendPostRequest(url, postData, referer)
    obj = data2Json(resp.read(), ('status', 'httpstatus'))
    if not (obj and obj['status'] and obj.has_key('data')):
      #print u"查询未完成订单失败"
      return RET_ERR
    if (obj['data'].has_key('orderDBList') and obj['data']['orderDBList']) or (obj['data'].has_key('orderCacheDTO') and obj['data']['orderCacheDTO']):
      print u"查询到有未完成订单，请先处理"
      return RET_OK

def Dingpiao51():
  print(getTime())
  '''
  logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s %(filename)s %(funcName)s[line:%(lineno)d] %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %X',
            filename='log.txt',
            filemode='w')
  logging.debug('Start')
  '''

  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', help='Specify config file, default is config.ini')
  parser.add_argument('-u', '--username', help='Specify username to login')
  parser.add_argument('-p', '--password', help='Specify password to login')
  parser.add_argument('-d', '--date', help='Specify train date, 2014-01-01')
  args = parser.parse_args()

  stationInit()

  order = MyOrder()
  if args.config:
    order.readConfig(args.config) # 使用指定的配置文件
  else:
    order.readConfig() # 使用默认的配置文件config.ini
  if args.username:
    order.username = args.username # 使用指定的账号代替配置文件中的账号
  if args.password:
    order.password = args.password # 使用指定的密码代替配置文件中的密码
  if args.date:
    if checkDate(args.date):
      order.train_date = args.date  # 使用指定的乘车日期代替配置文件中的乘车日期
    else:
      order.train_date = inputDate(u"乘车日期错误,请重新输入:")

  order.printConfig()
  order.initCookieJar()
  order.loginProc()
  print(getTime())

  while 1:
    if order.queryMyOrderNotComplete() == RET_OK:
      break
    # 查询车票
    if order.queryTickets() != RET_OK:
      continue
    # 显示查询结果
    order.printTrains()
    # 选择菜单列举的动作之一
    action = order.selectAction()
    if action == -1:
      continue
    elif action == 0:
      sys.exit()
    # 订单初始化
    if order.initOrder() != RET_OK:
      continue
    # 检查订单信息
    if order.checkOrderInfo() != RET_OK:
      continue
    # 查询排队和余票情况
    if order.getQueueCount() != RET_OK:
      continue
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
      break

  raw_input('Press any key to continue')
  #logging.debug('End')
  print(getTime())

if __name__=="__main__":
  Dingpiao51()

# EOF