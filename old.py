#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import cookielib
import urllib
import urllib2
import time
import sys
import re
from bs4 import BeautifulSoup
import ConfigParser
import codecs
import random
import logging

# Global variables
stations = []

# Set default encoding to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

#------------------------------------------------------------------------------
# Print delimiter
def printDelimiter():
  print '-'*100

#------------------------------------------------------------------------------
# Station init
# 全部站点, 数据来自: https://dynamic.12306.cn/otsweb/js/common/station_name.js
# 每个站的格式如下:
# @bji|北京|BJP|beijing|bj|2   ---> @拼音缩写三位|站点名称|编码|拼音|拼音缩写|序号
def stationInit():
  url = "https://dynamic.12306.cn/otsweb/js/common/station_name.js"
  referer = "https://dynamic.12306.cn/otsweb/"
  resp = sendGetRequest(url, referer)
  try:
    respInfo = resp.read().decode("utf-8","ignore")
    if respInfo.find("'@") != -1:
      station_names = respInfo[respInfo.find("'@"):]
    else:
      print(u"stationInit() error, station_names is empty")
      return {}
  except:
    print(u"stationInit()->sendGetRequest()->resp.read() exception")
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
# Get current time and convert to string
def getTime():
  return time.strftime("%Y-%m-%d %X",time.localtime())

#------------------------------------------------------------------------------
# Card type
# 证件类型: 
# 1->二代身份证
# 2->一代身份证
# C->港澳通行证
# G->台湾通行证
# B->护照
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
# Seat type
# 席别: 
# 1->硬座/无座
# 3->硬卧
# 4->软卧
# 7->一等软座
# 8->二等软座
# 9->商务座
# M->一等座
# O->二等座
# P->特等座
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
# Ticket type
# 票种类型
# 1->成人票
# 2->儿童票
# 3->学生票
# 4->残军票
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
  m = re.match(r'^\d{4}-\d{2}-\d{2}$',date) # 2013-01-10

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
      print u"格式错误,请重新输入有效的乘车日期,如2013-02-01:"

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
def sendPostRequest(url, data, referer="https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init"):
  #print("Start post %s at %s"%(url,getTime()))
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
  #print("Stop post %s at %s"%(url,getTime()))
  return resp

#------------------------------------------------------------------------------
# Send get request
def sendGetRequest(url,referer="https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init"):
  #print("Start get %s at %s"%(url,getTime()))
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
  #print("Stop get %s at %s"%(url,getTime()))
  return resp

#------------------------------------------------------------------------------
# Save picture code
# 请求验证图片, 并保存到本地
def getCaptcha(url):
  originUrl = url;
  captcha = ''
  while 1:
    f = open("captcha.jpg","wb")
    f.write(urllib2.urlopen(url).read())
    f.close()
    print u"请输入4位图片验证码(直接回车刷新):"
    url = "%s&%1.16f"%(originUrl, random.random())
    captcha = raw_input("")
    if len(captcha) == 4:
      return captcha

#------------------------------------------------------------------------------
# Check login result
def checkLoginResult(respInfo):
  key = 'isLogin= true'
  if respInfo.find(key) != -1:
    return 1
  else:
    return 0

#------------------------------------------------------------------------------
# Login process
def login(username,password):
  #访问主页, 自动保存Cookie信息
  url = "https://dynamic.12306.cn/otsweb/"
  referer = "https://dynamic.12306.cn/otsweb/"
  resp = sendGetRequest(url, referer)

  url = "https://dynamic.12306.cn/otsweb/loginAction.do?method=init"
  referer = "https://dynamic.12306.cn/otsweb/"
  resp = sendGetRequest(url, referer)
  '''
  try:
    respInfo = resp.read()
    v0 = respInfo.find('jsversion=')
    v1 = respInfo.find('&method=loginJs')
    ver = respInfo[v0+len('jsversion='):v1]
    url = "https://dynamic.12306.cn/otsweb/dynamicJsAction.do?jsversion=" + ver + "&method=loginJs" # "https://dynamic.12306.cn/otsweb/dynamicJsAction.do?jsversion=3490&method=loginJs"
    referer = "https://dynamic.12306.cn/otsweb/loginAction.do?method=init"
    resp = sendPostRequest(url, {}, referer)
  except:
    print(u"login()->sendPostRequest()->resp.read() exception")
    return 0
  '''

  print(u"接收验证码...")
  # 图片验证码
  captcha = getCaptcha("https://dynamic.12306.cn/otsweb/passCodeNewAction.do?module=login&rand=sjrand")

  # 获取loginRand
  url = "https://dynamic.12306.cn/otsweb/loginAction.do?method=loginAysnSuggest"
  referer = "https://dynamic.12306.cn/otsweb/loginAction.do?method=init#"
  resp = sendPostRequest(url, {}, referer)
  try:
    respInfo = resp.read() # {"loginRand":"752","randError":"Y"}
  except:
    print(u"login()->sendPostRequest()->resp.read() exception")
    return 0
  try:
    respDict = eval(respInfo)
  except:
    print(u"login()->eval(respInfo) exception")
    return 0
  loginRand = ''
  if respDict.has_key("loginRand"):
    loginRand = respDict['loginRand']
  else:
    print u"请求 loginRand 失败"
    return 0

  print(u"登陆中...")
  # 模拟登陆
  url = "https://dynamic.12306.cn/otsweb/loginAction.do?method=login"
  referer = "https://dynamic.12306.cn/otsweb/loginAction.do?method=init"
  # 参数顺序可能导致登陆失败
  parameters = [
    ('loginRand'       ,loginRand),
    ('refundLogin'       ,"N"),
    ('refundFlag'      ,"Y"),
    ('isClick'      ,""),
    ('from_tk'      ,"null"),
    ('loginUser.user_name'   ,username),
    ('nameErrorFocus'     ,""),
    ('user.password'     ,password),
    ('passwordErrorFocus'   ,""),
    ('randCode'        ,captcha),
    ('randErrorFocus'     ,""),
    ('NDE1MzYzNQ=='    ,"NzkxOGIzOWI3NmVjYWFmOA=="),
    ('myversion'     ,"undefined"),
  ]
  postData = urllib.urlencode(parameters)

  resp = sendPostRequest(url, postData, referer)
  try:
    respInfo = resp.read()
  except:
    print(u"login()->sendPostRequest()->resp.read() exception")
    return 0

  # 判断登陆是否成功
  return checkLoginResult(respInfo)

#------------------------------------------------------------------------------
# Pares trains detail information and left tickets information
'''内容如下
0,<span id='id_65000K905207' class='base_txtdiv' onmouseover=javascript:onStopHover('65000K905207#BJQ#EHQ') onmouseout='onStopOut()'>K9052</span>,<img src='/otsweb/images/tips/first.gif'>&nbsp;&nbsp;&nbsp;&nbsp;深圳东&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;14:52,&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;新化&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;03:19,12:27,--,--,--,--,--,4,<font color='darkgray'>无</font>,--,<font color='#008800'>有</font>,<font color='#008800'>有</font>,--,<a name='btn130_2' class='btn130_2' style='text-decoration:none;' onclick=javascript:getSelected('K9052#12:27#14:52#65000K905207#BJQ#EHQ#03:19#深圳东#新化#01#11#1*****32544*****00041*****03343*****0000#MDZERjM0NzY4Qjk2ODIzQTkwNkVFRDREMDVGMUM4Rjc2MDQ1MkJBMTdBNzA0MTVGMDA1MTAyMDM6Ojo6MTM4MzMxNTU4ODcwNw==#Q6')>预&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;订</a>\n
1,<span id='id_69000K906007' class='base_txtdiv' onmouseover=javascript:onStopHover('69000K906007#OSQ#EHQ') onmouseout='onStopOut()'>K9060</span>,<img src='/otsweb/images/tips/first.gif'>&nbsp;&nbsp;&nbsp;&nbsp;深圳西&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;19:08,&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;新化&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;08:30,13:22,--,--,--,--,--,--,<font color='#008800'>有</font>,--,<font color='#008800'>有</font>,<font color='#008800'>有</font>,--,<a name='btn130_2' class='btn130_2' style='text-decoration:none;' onclick=javascript:getSelected('K9060#13:22#19:08#69000K906007#OSQ#EHQ#08:30#深圳西#新化#01#13#1*****36801*****10883*****0157#QkJGREVBRjY0NDQ2OTdFQTdGOUMzN0NBMzU3QUE0NTU0MzA1QTQwMTA4NjNDMjcyMDEzQkRDMDY6Ojo6MTM4MzMxNTU4ODcwNw==#Q7')>预&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;订</a>
'''
def getTrainsDetailInfo(h):
  h = h.replace("&nbsp;","") # 删除&nbsp;
  h = h.decode("utf-8","ignore") # 使用decode("gb2312","ignore")会乱码, 因为网页内容是 utf-8 编码的
  all_trains = h.split("\\n")
  trains = []
  seats = [u"商务座",u"特等座",u"一等座",u"二等座",u"高级软卧",u"软卧",u"硬卧",u"软座",u"硬座",u"无座",u"其它"]
  for train in all_trains:
    t = {'origin_data': train}
    c = train.split(",")
    if len(c) < 17:
      print(u'数据不完整,len<17')
      continue

    keyword = "getSelected('"
    s = c[16].find(keyword)
    if s == -1: # 不可预订
      continue
    keyword = "')"
    e = c[16].find(keyword)
    ss = c[16][s+len("getSelected('"):e]
    cc = ss.split("#")
    if len(cc) < 14:
      print(u'数据不完整,len<14')
      continue

    t['station_train_code'] = cc[0] # 车次[K9060]
    t['lishi'] = cc[1] # 历时[13:22]
    t['train_start_time'] = cc[2] # 发出时间[19:08]
    t['trainno4'] = cc[3] # 车次编码[69000K906007]
    t['from_station_telecode'] = cc[4] # 出发站编码[OSQ]
    t['to_station_telecode'] = cc[5] # 目的站编码[EHQ]
    t['arrive_time'] = cc[6] # 到达时间[08:30]
    t['from_station_name'] = cc[7] # 出发站名称[深圳西]
    t['to_station_name'] = cc[8] # 目的站名称[新化]
    t['from_station_no'] = cc[9] # 出发站是第几站[01]
    t['to_station_no'] = cc[10] # 目的站是第几站[3]
    t['ypInfoDetail'] = cc[11] # 余票详情[1*****36601*****08953*****0000]
    t['mmStr'] = cc[12] # 6D10DCDFCFD7BFC946029BADC0C7DFD166BD121BC8972AC7B931556A
    t['locationCode'] = cc[13] # Q6

    for i in xrange(5,16):
      s = c[i].find(">")
      e = c[i].find("</font>")
      if s == -1:
        s = 0
        e = len(c[i])
      else:
        s += 1
      t[seats[i-5]] = c[i][s:e]

    if c[16].find("btn130_2") != -1: # btn130_2 表示预定按钮可以点击, btn130 表示预订按钮灰显
      t[u"预订"] = 1
    else:
      t[u"预订"] = 0
    trains.append(t)
  return trains

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
    if not trains[index-1][u"预订"]:
      print u"您选择的车次%s没票啦,请重新选择车次"%(trains[index-1][u"车次"])
      continue
    else:
      break

  return index

#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Get hidden item
def getHiddenItem(respInfo):
  if not respInfo:
    return 0
  soup = BeautifulSoup(respInfo)
  tag = soup.find(attrs={"name": "org.apache.struts.taglib.html.TOKEN", "type":"hidden"})
  if not tag:
    return 0
  token = tag['value']
  tag = soup.find(attrs={"name":"leftTicketStr", "type":"hidden", "id":"left_ticket"})
  if not tag:
    return 0
  leftTicketStr = tag['value']
  tag = soup.find(attrs={"name":"textfield", "type":"text", "id":"passenger_filter_input"})
  if not tag:
    return 0
  textfield = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.train_date", "type":"hidden", "id":"start_date"})
  if not tag:
    return 0
  train_date = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.train_no", "type":"hidden", "id":"train_no"})
  if not tag:
    return 0
  train_no = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.station_train_code", "type":"hidden", "id":"station_train_code"})
  if not tag:
    return 0
  station_train_code = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.from_station_telecode", "type":"hidden", "id":"from_station_telecode"})
  if not tag:
    return 0
  from_station_telecode = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.to_station_telecode", "type":"hidden", "id":"to_station_telecode"})
  if not tag:
    return 0
  to_station_telecode = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.seat_type_code", "type":"hidden", "id":"seat_type_code"})
  if not tag:
    return 0
  seat_type_code = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.ticket_type_order_num", "type":"hidden", "id":"ticket_type_order_num"})
  if not tag:
    return 0
  ticket_type_order_num = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.bed_level_order_num", "type":"hidden", "id":"bed_level_order_num"})
  if not tag:
    return 0
  bed_level_order_num = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.start_time", "type":"hidden", "id":"orderRequest_start_time"})
  if not tag:
    return 0
  start_time = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.end_time", "type":"hidden", "id":"orderRequest_end_time"})
  if not tag:
    return 0
  end_time = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.from_station_name", "type":"hidden", "id":"orderRequest_from_station_name"})
  if not tag:
    return 0
  from_station_name = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.to_station_name", "type":"hidden", "id":"orderRequest_to_station_name"})
  if not tag:
    return 0
  to_station_name = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.cancel_flag", "type":"hidden", "id":"cancel_flag"})
  if not tag:
    return 0
  cancel_flag = tag['value']
  tag = soup.find(attrs={"name":"orderRequest.id_mode", "type":"hidden", "id":"orderRequest_id_mode"})
  if not tag:
    return 0
  id_mode = tag['value']

  # 通用的POST数据, 来自于之前init的响应数据
  hiddenDict = {
    'org.apache.struts.taglib.html.TOKEN'   :token,
    'leftTicketStr'           :leftTicketStr,
    'textfield'             :textfield,
    'checkbox2'             :"2",
    'checkbox3'             :"3",
    'checkbox4'             :"4",
    'checkbox5'             :"5",
    'checkbox6'             :"6",
    'orderRequest.train_date'       :train_date,
    'orderRequest.train_no'       :train_no,
    'orderRequest.station_train_code'   :station_train_code,
    'orderRequest.from_station_telecode':from_station_telecode,
    'orderRequest.to_station_telecode'  :to_station_telecode,
    'orderRequest.seat_type_code'     :seat_type_code,
    'orderRequest.ticket_type_order_num':ticket_type_order_num,
    'orderRequest.bed_level_order_num'  :bed_level_order_num,
    'orderRequest.start_time'       :start_time,
    'orderRequest.end_time'       :end_time,
    'orderRequest.from_station_name'  :from_station_name,
    'orderRequest.to_station_name'    :to_station_name,
    'orderRequest.cancel_flag'      :cancel_flag,
    'orderRequest.id_mode'        :id_mode,
  }
  hiddenList = [
    ('org.apache.struts.taglib.html.TOKEN'   ,token),
    ('leftTicketStr'           ,leftTicketStr),
    ('textfield'             ,textfield),
    ('checkbox2'             ,"2"),
    ('checkbox3'             ,"3"),
    ('checkbox4'             ,"4"),
    ('checkbox5'             ,"5"),
    ('checkbox6'             ,"6"),
    ('orderRequest.train_date'       ,train_date),
    ('orderRequest.train_no'       ,train_no),
    ('orderRequest.station_train_code'   ,station_train_code),
    ('orderRequest.from_station_telecode',from_station_telecode),
    ('orderRequest.to_station_telecode'  ,to_station_telecode),
    ('orderRequest.seat_type_code'     ,seat_type_code),
    ('orderRequest.ticket_type_order_num',ticket_type_order_num),
    ('orderRequest.bed_level_order_num'  ,bed_level_order_num),
    ('orderRequest.start_time'       ,start_time),
    ('orderRequest.end_time'       ,end_time),
    ('orderRequest.from_station_name'  ,from_station_name),
    ('orderRequest.to_station_name'    ,to_station_name),
    ('orderRequest.cancel_flag'      ,cancel_flag),
    ('orderRequest.id_mode'        ,id_mode)
  ]
  return (hiddenDict,hiddenList)

class MyOrder(object):
  """docstring for MyOrder"""
  def __init__(self, username='', password='', train_date='', from_city_name='', to_city_name=''):
    super(MyOrder, self).__init__()
    self.username = username # 账号
    self.password = password # 密码
    self.train_date = train_date # 乘车日期[2013-09-09]
    self.from_city_name = from_city_name # 对应查询界面'出发地'输入框中的内容[u'深圳']
    self.to_city_name = to_city_name # 对应查询界面'目的地'输入框中的内容[u'新化']
    self.from_station_telecode = '' # 出发站编码, 例如深圳对应的编码是 SZQ
    self.to_station_telecode = '' # 目的站编码, 例如新化对应的编码是 EHQ
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
      print u"打开配置文件'%s'失败啦!"%(config_file)
      return
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
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('Accept', 'text/html'),
               ('Referer', 'https://dynamic.12306.cn/otsweb/'),
               ('Accept-Language', 'zh-CN'),
               ('User-Agent', 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0; MALC'),
               ('Accept-Encoding', 'deflate'),
               ('Host', "dynamic.12306.cn"),
               ('Connection', 'Keep-Alive'),
              ]
    urllib2.install_opener(opener)

  def loginProc(self):
    tries = 0
    while tries < 3:
      tries += 1
      printDelimiter()
      if login(self.username,self.password):
        print u"登陆成功^_^"
        break
      else:
        print u"登陆失败啦!重新登陆..."
    else:
      print u"失败次数太多,自动退出程序"
      sys.exit()

  # Return 1 if success, else 0
  def queryTickets(self):
    url = 'https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=queryLeftTicket'
    referer = 'https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=init'
    parameters = [
      ('orderRequest.train_date'       ,self.train_date),
      ('orderRequest.from_station_telecode',self.from_station_telecode),
      ('orderRequest.to_station_telecode'  ,self.to_station_telecode),
      ('orderRequest.train_no'       ,""),
      ('trainPassType'           ,"QB"),
      ('trainClass'            ,"QB#D#Z#T#K#QT#"),
      ('includeStudent'          ,"00"),
      ('seatTypeAndNum'          ,""),
      ('orderRequest.start_time_str'     ,"00:00--24:00")
    ]
    url += '&' + urllib.urlencode(parameters)
    resp = sendGetRequest(url, referer)
    try:
      respInfo = resp.read()
    except:
      print(u"queryTickets()->sendGetRequest()->resp.read() exception")
      self.trains = []
      return 0
    self.trains = getTrainsDetailInfo(respInfo)
    return 1 if self.trains else 0

  def printTrains(self):
    printDelimiter()
    print u"%s\t%s--->%s  '有':票源充足  '无':票已售完  '*':未到起售时间  '--':无此席别"%(self.train_date,self.from_city_name,self.to_city_name)
    print u"余票查询结果如下:"
    printDelimiter()
    print u"序号/车次\t乘车站\t目的站\t一等座\t二等座\t软卧\t硬卧\t软座\t硬座\t无座"
    printDelimiter()
    index = 1
    for t in self.trains:
      print u"(%d)   %s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(index,t['station_train_code'],t['from_station_name'],t['to_station_name'],t[u"一等座"],t[u"二等座"],t[u"软卧"],t[u"硬卧"],t[u"软座"],t[u"硬座"],t[u"无座"])
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
      if not self.trains[index-1][u"预订"]:
        print u"您选择的车次%s没票啦,请重新选择车次"%(self.trains[index-1][u"车次"])
        index = selectTrain(self.trains)
      ret = index
      self.current_train_index = index - 1
    elif select == "d" or select == "D":
      self.train_date = inputDate()
    elif select == "f" or select == "F":
      station = inputStation(u"请输入出发站:")
      self.from_city_name = station['name']
      self.from_station_telecode = station['telecode'] # 车站编码, 例如深圳对应的编码是SZQ
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

  # Return 1 if success, else 0
  def initOrder(self):
    url = 'https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=submutOrderRequest'
    referer = 'https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=init'
    t = self.trains[self.current_train_index]
    parameters = [
      ('station_train_code'    ,t['station_train_code']),
      ('train_date'        ,self.train_date), # 乘车日期 ["2013-01-10",]
      ('seattype_num'        ,""), # 隐含选项, 使用默认值""即可
      ('from_station_telecode'   ,t['from_station_telecode']),
      ('to_station_telecode'     ,t['to_station_telecode']),
      ('include_student'       ,"00"), # 隐含选项, 乘客中包含学生, 使用默认值00即可
      ('from_station_telecode_name',self.from_city_name), # 对应查询界面'出发地'输入框中的内容[u"深圳"]
      ('to_station_telecode_name'  ,self.to_city_name), # 对应查询界面'目的地'输入框中的内容[u"新化"]
      ('round_train_date'      ,self.train_date), # "2013-01-10",
      ('round_start_time_str'    ,"00,00--24,00"), # 发出时间段, 不用修改
      ('single_round_type'     ,"1"),
      ('train_pass_type'       ,"QB"), # [GL->过路][SF->始发][QB->全部]
      ('train_class_arr'       ,"QB#D#Z#T#K#QT#"), # [QB->全部][D->动车][Z->Z字头][T->T字头][K->K字头][QT其它]
      ('start_time_str'      ,"00,00--24,00"), # 发出时间段,不用修改
      ('lishi'           ,t['lishi']),
      ('train_start_time'      ,t['train_start_time']),
      ('trainno4'          ,t['trainno4']),
      ('arrive_time'         ,t['arrive_time']),
      ('from_station_name'     ,t['from_station_name']),
      ('to_station_name'       ,t['to_station_name']),
      ('from_station_no'       ,t['from_station_no']),
      ('to_station_no'       ,t['to_station_no']),
      ('ypInfoDetail'        ,t['ypInfoDetail']),
      ('mmStr'           ,t['mmStr']),
      ('locationCode'        ,t['locationCode']),
      ('Mzc1ODA1NQ=='           ,'Y2E2MDk0YTI4NzgwODgyOA=='), # TODO
      ('myversion'           ,'undefined')
    ]
    postData = urllib.urlencode(parameters)
    print(u"订票初始化...")
    resp = sendPostRequest(url, postData, referer) # 服务器会返回302, 重定向到 https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init
    respInfo = None
    try:
      respInfo = resp.read()
    except:
      print(u"initOrder()->sendPostRequest()->resp.read() exception")
      return 0
    if not respInfo:
      url = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init'
      resp = sendPostRequest(url, postData, referer)
      try:
        respInfo = resp.read()
      except:
        print(u"initOrder()->sendPostRequest()->resp.read() 2 exception")
        return 0
    self.hiddenItems = getHiddenItem(respInfo)
    return 1 if self.hiddenItems else 0

  def getCommonPostData(self):
    passenger_seat_detail = "0" # [0->随机][1->下铺][2->中铺][3->上铺]
    all_passengers = [
      [
        ('passengerTickets'          ,"%s,%s,%s,%s,%s,%s,%s,%s"%(p['seattype'],passenger_seat_detail,p['tickettype'],p['name'],p['cardtype'],p['id'],p['phone'],"Y")),#"席别,随机,票种,姓名,证件类型,证件号码,手机号码,保存到常用联系人"
        ('oldPassengers'           ,"%s,%s,%s"%(p['name'],p['cardtype'],p['id'])), # "姓名,证件类型,身证件号码"
        ('passenger_%d_seat'%(p['index'])      ,p['seattype']), # [1->硬座][3->硬卧]
        ('passenger_%d_ticket'%(p['index'])    ,p['tickettype']), # [1->成人票][2->儿童票][3->学生票][4->残军票]
        ('passenger_%d_name'%(p['index'])      ,p['name']), # 乘客姓名
        ('passenger_%d_cardtype'%(p['index'])    ,p['cardtype']), # 证件类型: [1->二代身份证][2->一代身份证][C->港澳通行证][G->台湾通行证][B->护照]
        ('passenger_%d_cardno'%(p['index'])    ,p['id']), # 证件号码
        ('passenger_%d_mobileno'%(p['index'])    ,p['phone']), # 手机号码
        ('checkbox9'             ,"Y") # 保存到常用联系人
      ]
      for p in self.passengers
    ]
    postData = urllib.urlencode(self.hiddenItems[0])
    for p in all_passengers:
      postData = postData + '&' + urllib.urlencode(p)
    return postData

  # Return 1 if success, else 0
  def checkOrderInfo(self):
    print(u"接收验证码...")
    # 请求图片验证码
    self.captcha = getCaptcha("https://dynamic.12306.cn/otsweb/passCodeNewAction.do?module=passenger&rand=randp")
    print(u"查询排队和余票情况...")
    url = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=checkOrderInfo&rand=' + self.captcha
    referer = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init#'
    d = [
      ('randCode'              ,self.captcha),
      ('orderRequest.reserve_flag'     ,"A"), # A网上支付, B网上预订, 默认选择A
      ('tFlag'                 ,"dc") # [dc->单程][wc->往程][fc->返程][gc->改签]
    ]
    postData = self.getCommonPostData() + '&' + urllib.urlencode(d)
    resp = sendPostRequest(url, postData, referer)
    respInfo = None
    try:
      respInfo = resp.read() # {"checkHuimd":"Y","check608":"Y","msg":"","errMsg":"Y"}
    except:
      print(u"checkOrderInfo()->sendPostRequest()->resp.read() exception")
      return 0
    # 参数解释参考https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js
    # checkHuimd:Y表示正确,N表示"对不起，由于您取消次数过多，今日将不能继续受理您的订票请求！"
    # check608:Y表示正确,N表示"本车为实名制列车，实行一日一车一证一票制！"
    # errMsg:Y表示正确,其它表示错误原因
    logging.debug('checkOrderInfo respInfo:%s'%(respInfo))
    respDict = {}
    try:
      respDict = eval(respInfo)
    except:
      print(u"checkOrderInfo()->eval() exception")
      return 0
    if not set(('checkHuimd', 'check608', 'errMsg')).issubset(respDict):
      print(u'checkOrderInfo():返回数据不完整[%s]'%(respInfo))
      return 0
    if respDict['checkHuimd'] == "N":
      print(u'checkOrderInfo():对不起，由于您取消次数过多，今日将不能继续受理您的订票请求！')
      return 0
    if respDict['check608'] == "N":
      print(u'checkOrderInfo():本车为实名制列车，实行一日一车一证一票制！')
      return 0
    if respDict['errMsg'] != "Y":
      print(u'错误详情:%s'%(respDict['errMsg']))
      return 0
    return 1

  # Return 1 if success, else 0
  def getQueueCount(self):
    url = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=getQueueCount&'
    referer = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init#'
    parameters = [
      ('train_date',self.hiddenItems[0]['orderRequest.train_date']),
      ('train_no'  ,self.hiddenItems[0]['orderRequest.train_no']),
      ('station'   ,self.hiddenItems[0]['orderRequest.station_train_code']),
      ('seat'    ,"1" if not self.hiddenItems[0]['orderRequest.seat_type_code'] else self.hiddenItems[0]['orderRequest.seat_type_code']),
      ('from'    ,self.hiddenItems[0]['orderRequest.from_station_telecode']),
      ('to'    ,self.hiddenItems[0]['orderRequest.to_station_telecode']),
      ('ticket'  ,self.hiddenItems[0]['leftTicketStr'])
    ]
    url += urllib.urlencode(parameters)
    resp = sendGetRequest(url, referer)
    try:
      respInfo = resp.read() # {"countT":0,"count":1,"ticket":"1*****36601*****09683*****0067","op_1":false,"op_2":false}
    except:
      print(u"getQueueCount()->sendGetRequest()->resp.read() exception")
      return 0
    # 参数解释参考https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js
    # countT:目前排队人数
    # count:在你之前的排队人数
    # ticket:余票详情,如"1*****36601*****09683*****0067",其中36601代表无座有660张, 09683代码座位票有968张,0067代表卧铺票有67张,纯属推测
    # op_1:true表示"目前排队人数已经超过余票张数，特此提醒。"
    # op_2:true表示"目前排队人数已经超过余票张数，请您选择其他席别或车次，特此提醒。"
    logging.debug('getQueueCount respInfo:%s'%(respInfo))
    respDict = {}
    try:
      respDict = eval(respInfo.replace("false", "0").replace("true", "1"))
    except:
      print(u"getQueueCount()->eval(respInfo) exception")
      return 0
    if not set(('countT', 'count', 'ticket', 'op_1', 'op_2')).issubset(respDict):
      print(u'getQueueCount():返回数据不完整[%s]'%(respInfo))
      return 0
    print(u"目前排队人数:%d, 在你之前的排队人数:%d, 余票详情:%s"%(respDict['countT'], respDict['count'], respDict['ticket']))
    if respDict['op_1']:
      print(u'getQueueCount():目前排队人数已经超过余票张数，特此提醒。今日已有人先于您提交相同的购票需求，到处理您的需求时可能已无票，建议你们根据当前余票确定是否排队。')
    if respDict['op_2']:
      print(u'getQueueCount():目前排队人数已经超过余票张数，请您选择其他席别或车次，特此提醒。')

    return 1

  # Return 1 if success, else 0
  def confirmSingleForQueue(self):
    print(u"提交订单排队...")
    url = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=confirmSingleForQueue'
    referer = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init#'
    resp = sendPostRequest(url, self.getCommonPostData(), referer)
    try:
      respInfo = resp.read() # {"errMsg":"Y"}
    except:
      print(u"confirmSingleForQueue()->sendPostRequest()->resp.read() exception")
      return 0
    # 参数解释参考https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js
    # errMsg:Y表示正确,其它表示错误原因,如'非法的订票请求！'
    logging.debug('confirmSingleForQueue() respInfo:%s'%(respInfo))
    respDict = {}
    try:
      respDict = eval(respInfo)
    except:
      print(u"confirmSingleForQueue()->eval(respInfo) exception")
      return 0
    if respDict.has_key("errMsg"):
      if respDict['errMsg'] != "Y":
        print u'错误详情:%s'%(respDict['errMsg'])
        return 0
      else:
        return 1
    return 0

  # Return orderId if success, else empty string
  def queryOrderWaitTime(self):
    print(u"等待订票结果...")
    url = 'https://dynamic.12306.cn/otsweb/order/myOrderAction.do?method=queryOrderWaitTime&tourFlag=dc'
    referer = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init#'
    resp = sendGetRequest(url, referer)
    self.orderId = ''
    try:
      # 返回数据有以下3种形式:
      # {"tourFlag":"dc","waitTime":4,"waitCount":1,"requestId":5802046345017312443,"count":0}
      # {"tourFlag":"dc","waitTime":-1,"waitCount":0,"orderId":"E727748596","requestId":5802046345017312443,"count":0}
      # {"tourFlag":"dc","waitTime":-2,"waitCount":0,"requestId":5802944893330576450,"errorcode":"0","msg":"没有足够的票!","count":0}
      respInfo = resp.read()
    except:
      print(u"queryOrderWaitTime()->sendGetRequest()->resp.read() exception")
      return ''
    # 参数解释参考https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js
    # tourFlag:表示单程[dc]/往程[wc]/返程[fc]/改签[gc]
    # waitTime:表示排队等待时间
    # waitCount:未知
    # requestId:未知
    # count:未知
    # errorcode:错误代码
    # msg:错误详情, 如"没有足够的票!"/"很抱歉！当前提交订单用户过多，请您稍后重试。"
    logging.debug('queryOrderWaitTime() respInfo:%s'%(respInfo))
    respDict = {}
    try:
      respDict = eval(respInfo)
    except:
      print(u"queryOrderWaitTime()->eval(respInfo) exception")
      return ''
    if not set(('tourFlag', 'waitTime', 'waitCount', 'requestId', 'count')).issubset(respDict):
      print(u'queryOrderWaitTime():返回数据不完整[%s]'%(respInfo))
      return ''
    if respDict.has_key("errorcode"):
      print u'占座失败，原因:%s'%(respDict['msg'])
      return ''
    if respDict.has_key("orderId"):
      self.orderId = respDict["orderId"]
      return self.orderId
    else:
      return ''

  # Return 1 if success, else 0
  def payOrder(self):
    url = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=payOrder&orderSequence_no=' + self.orderId
    referer = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init'
    resp = sendPostRequest(url, self.getCommonPostData(), referer)
    try:
      respInfo = resp.read()
    except:
      print(u"payOrder()->sendPostRequest()->resp.read() exception")
      return 0
    if respInfo.find(u'席位已成功锁定') != -1:
      print u"订票成功^_^请在45分钟内完成网上支付,否则系统将自动取消"
      return 1
    else:
      return 0

  # Return 1 if success, else 0
  def queryMyOrderNotComplete(self):
    url = 'https://dynamic.12306.cn/otsweb/order/myOrderAction.do?method=queryMyOrderNotComplete&leftmenu=Y'
    referer = 'https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init'
    resp = sendGetRequest(url, referer)
    try:
      respInfo = resp.read()
    except:
      print(u"queryMyOrderNotComplete()->sendGetRequest()->resp.read() exception")
      return 0
    if respInfo.find(u'总张数') != -1 and respInfo.find(u'待支付') != -1:
      print u"订票成功^_^请在45分钟内完成订单,否则系统将自动取消"
      return 1
    else:
      return 0

def Main12306():
  logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s %(filename)s %(funcName)s[line:%(lineno)d] %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %X',
            filename='log.txt',
            filemode='w')
  logging.debug('Start')

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

  while 1:
    # 查询车票
    if not order.queryTickets():
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
    if not order.initOrder():
      continue
    # 检查订单信息
    if not order.checkOrderInfo():
      continue
    # 查询排队和余票情况
    if not order.getQueueCount():
      continue
    # 提交订单到队里中
    tries = 0
    while tries < 2:
      tries += 1
      if order.confirmSingleForQueue():
        break
    # 获取orderId
    tries = 0
    while tries < 2:
      tries += 1
      if order.queryOrderWaitTime():
        break
    if not order.orderId:
      print(u'获取orderId失败, 但仍然继续提交订单')
    # 正式提交订单
    if order.payOrder():
      break
    # 访问未完成订单页面检查是否订票成功
    if order.queryMyOrderNotComplete():
      break
    print u"订票失败啦!请重试"

  raw_input("Press any key to continue")
  logging.debug('End')

if __name__=="__main__":
  Main12306()

# EOF