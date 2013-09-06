#!/usr/bin/python
# -*- coding: utf-8 -*-

import cookielib
import urllib
import urllib2
import time
import sys
import re
from bs4 import BeautifulSoup
from stationName import stationName2Telecode
import ConfigParser
import codecs
import random
import logging

reload(sys)
sys.setdefaultencoding('utf-8')

#------------------------------------------------------------------------------
# Just for print delimiter
def printDelimiter():
    print '-'*100

#------------------------------------------------------------------------------
#Get current time and convert to string
def getTime():
    return time.strftime("%Y-%m-%d %X",time.localtime())

#------------------------------------------------------------------------------
# Card type
#证件类型:
#1->二代身份证
#2->一代身份证
#C->港澳通行证
#G->台湾通行证
#B->护照
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
#席别:
#1->硬座/无座
#3->硬卧
#4->软卧
#7->一等软座
#8->二等软座
#9->商务座
#M->一等座
#O->二等座
#P->特等座
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
#票种类型:
#1->成人票
#2->儿童票
#3->学生票
#4->残军票
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
    m = re.match(r'^\d{4}-\d{2}-\d{2}$',date)#2013-01-10
    if m:
        return 1

    return 0

#------------------------------------------------------------------------------
# Input date
def inputDate():
    train_date = ''
    while 1:
        train_date = raw_input("")
        if checkDate(train_date):
            break
        else:
            print u"格式错误,请重新输入有效的乘车日期,如2013-02-01:"

    return train_date

#------------------------------------------------------------------------------
# Input station
def inputStation():
    station = ''
    while 1:
        station = raw_input("").decode("gb2312","ignore")
        telecode = stationName2Telecode(station)
        if telecode:
            break
        else:
            print u"站点错误,没有站点'%s',请重新输入:"%(station)

    return {"name":station,"telecode":telecode}

#------------------------------------------------------------------------------
# Check order result
def checkOrderResult(respInfo):
    key = u'席位已成功锁定'
    if respInfo.find(key) != -1:
        return 1
    key = u'待支付'
    if respInfo.find(key) != -1:
        return 1

    return 0

#------------------------------------------------------------------------------
# Send post request
def sendPostRequest(url,data,referer="https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init"):
    print("Start post %s at %s"%(url,getTime()))
    post_timeout = 300
    req = urllib2.Request(url, data)
    req.add_header('Content-Type', "application/x-www-form-urlencoded")
    req.add_header('Referer',referer)
    resp = None
    tries = 0
    max_tries = 3
    while tries < max_tries:
        tries += 1
        try:
            resp = urllib2.urlopen(req,timeout=post_timeout*tries)
        except urllib2.HTTPError,e:
            print("Post %d times %s exception HTTPError code:"%(tries,url),e.code)
        except urllib2.URLError,e:
            print("Post %d times %s exception URLError reason:"%(tries,url),e.reason)
        except:
            print("Post %d times %s exception other"%(tries,url))
        if resp:
            break
    print("Stop post %s at %s"%(url,getTime()))
    return resp

#------------------------------------------------------------------------------
# Send get request
def sendGetRequest(url,referer="https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init"):
    print("Start get %s at %s"%(url,getTime()))
    get_timeout = 150
    req = urllib2.Request(url)
    req.add_header('Referer',referer)
    resp = None
    tries = 0
    max_tries = 3
    while tries < max_tries:
        tries += 1
        try:
            resp = urllib2.urlopen(req,timeout=get_timeout*tries)
        except urllib2.HTTPError,e:
            print("Get %d times %s exception HTTPError code:"%(tries,url),e.code)
        except urllib2.URLError,e:
            print("Get %d times %s exception URLError reason:"%(tries,url),e.reason)
        except:
            print("Get %d times %s exception other"%(tries,url))
        if resp:
            break
    print("Stop get %s at %s"%(url,getTime()))
    return resp

#------------------------------------------------------------------------------
# Save picture code
#请求验证图片,并保存到本地pic-code.jpeg
#需要手动打开该图片识别验证码并输入给执行界面
def savePicCode(url):
    print("Start savePicCode %s at %s"%(url,getTime()))
    f = open("pic-code.jpeg","wb")
    f.write(urllib2.urlopen(url).read())
    f.close()
    print("Stop savePicCode %s at %s"%(url,getTime()))

#------------------------------------------------------------------------------
# Check login result
def checkLoginResult(respInfo):
    key = 'isLogin= true'
    if respInfo.find(key) != -1:
        return 1

    return 0

#------------------------------------------------------------------------------
# Login process
def login(username,password):
    #访问主页,自动保存Cookie信息
    url = "https://dynamic.12306.cn/otsweb/"
    referer = "https://dynamic.12306.cn/otsweb/"
    resp = sendGetRequest(url,referer)

    #图片验证码
    savePicCode("https://dynamic.12306.cn/otsweb/passCodeAction.do?rand=sjrand")
    print u"请输入4位图片验证码登陆:"
    picCode = raw_input("")

    #获取loginRand,该值是随后的模拟登陆post的一个必要参数,由服务器返回,每次都不相同
    url = "https://dynamic.12306.cn/otsweb/loginAction.do?method=loginAysnSuggest"
    referer = "https://dynamic.12306.cn/otsweb/loginAction.do?method=init"
    resp = sendPostRequest(url,{},referer)
    try:
        respInfo = resp.read()#{"loginRand":"752","randError":"Y"}
    except:
        print(u"login()->sendPostRequest(%s)->resp.read() exception"%(url))
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

    #模拟登陆
    url = "https://dynamic.12306.cn/otsweb/loginAction.do?method=login"
    referer = "https://dynamic.12306.cn/otsweb/loginAction.do?method=init"
    postDict = {
        'loginRand'             :loginRand,
        'refundLogin'           :"N",
        'refundFlag'            :"Y",
        'loginUser.user_name'   :username,
        'nameErrorFocus'       :"",
        'user.password'         :password,
        'passwordErrorFocus'   :"",
        'randCode'              :picCode,
        'randErrorFocus'       :"",
    }
    postData = urllib.urlencode(postDict)
    resp = sendPostRequest(url,postData,referer)
    try:
        respInfo = resp.read()
    except:
        print(u"login()->sendPostRequest(%s)->resp.read() exception"%(url))
        return 0

    #判断登陆是否成功
    return checkLoginResult(respInfo)

#------------------------------------------------------------------------------
# Pares trains detail information and left tickets information
'''内容如下
0,<span id='id_65000K905206' class='base_txtdiv' onmouseover=javascript:onStopHover('65000K905206#BJQ#EHQ') onmouseout='onStopOut()'>K9052</span>,<img src='/otsweb/images/tips/first.gif'>&nbsp;&nbsp;&nbsp;&nbsp;深圳东&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;14:52,&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;新化&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;03:19,12:27,--,--,--,--,--,<font color='darkgray'>无</font>,<font color='darkgray'>无</font>,--,<font color='#008800'>有</font>,<font color='#008800'>有</font>,--,<a name='btn130_2' class='btn130_2' style='text-decoration:none;' onclick=javascript:getSelected('K9052#12:27#14:52#65000K905206#BJQ#EHQ#03:19#深圳东#新化#01#11#1*****32294*****00001*****02013*****0000#588B3DF36F4F9361DFDF720E39102660E0C287359DE0ADD326C8EA76#Q6')>预&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;订</a>\n
1,<span id='id_69000K90560A' class='base_txtdiv' onmouseover=javascript:onStopHover('69000K90560A#OSQ#EHQ') onmouseout='onStopOut()'>K9056</span>,<img src='/otsweb/images/tips/first.gif'>&nbsp;&nbsp;&nbsp;&nbsp;深圳西&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;18:15,&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;新化&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;06:41,12:26,--,--,--,--,--,--,<font color='darkgray'>无</font>,--,<font color='#008800'>有</font>,<font color='#008800'>有</font>,--,<a name='btn130_2' class='btn130_2' style='text-decoration:none;' onclick=javascript:getSelected('K9056#12:26#18:15#69000K90560A#OSQ#EHQ#06:41#深圳西#新化#01#09#1*****32341*****02273*****0000#EED7E70D73F3DED7D76D177AC7FA3AB03496C7031A89F39B3A909BE4#Q6')>预&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;订</a>\n
2,<span id='id_69000K906007' class='base_txtdiv' onmouseover=javascript:onStopHover('69000K906007#OSQ#EHQ') onmouseout='onStopOut()'>K9060</span>,<img src='/otsweb/images/tips/first.gif'>&nbsp;&nbsp;&nbsp;&nbsp;深圳西&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;19:08,&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;新化&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;08:30,13:22,--,--,--,--,--,--,<font color='darkgray'>无</font>,--,<font color='#008800'>有</font>,<font color='#008800'>有</font>,--,<a name='btn130_2' class='btn130_2' style='text-decoration:none;' onclick=javascript:getSelected('K9060#13:22#19:08#69000K906007#OSQ#EHQ#08:30#深圳西#新化#01#13#1*****36441*****02533*****0000#94453820654E62799A73E69F3BF26FD5CE9A65B497EB45A2D2A81285#Q6')>预&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;订</a>
'''
def getTrainsDetailInfo(h):
    h = h.replace("&nbsp;","")#删除&nbsp;
    h = h.decode("utf-8","ignore")#使用decode("gb2312","ignore")会乱码,因为网页内容是 utf-8 编码的
    all_trains = h.split(",<span")
    all_trains = all_trains[1:]
    trains = []
    cols = [u"车次",u"发站",u"到站",u"历时",u"商务座",u"特等座",u"一等座",u"二等座",u"高级软卧",u"软卧",u"硬卧",u"软座",u"硬座",u"无座",u"其它",u"购票"]
    for train in all_trains:
        c = train.split(",")
        s = c[0].find(">")
        e = c[0].find("<")
        c[0] = c[0][s+1:e]#车次# id='id_65000K905206' class='base_txtdiv' onmouseover=javascript:onStopHover('65000K905206#BJQ#EHQ') onmouseout='onStopOut()'>K9052</span>
        key = "<img src='/otsweb/images/tips/first.gif'>"
        s = c[1].find(key)
        s = 0 if s == -1 else  s + len(key)
        e = c[1].find("<br>")
        c[1] = c[1][s:e] + c[1][-5:]#发站#<img src='/otsweb/images/tips/first.gif'>深圳东<br>14:52 或 #深圳东<br>14:52
        key = "<img src='/otsweb/images/tips/last.gif'>"
        s = c[2].find(key)
        s = 0 if s == -1 else  s + len(key)
        e = c[2].find("<br>")
        c[2] = c[2][s:e] + c[2][-5:]#到站#<img src='/otsweb/images/tips/last.gif'>怀化<br>03:19 或 #新化<br>03:19
        c[3] = c[3]#历时#12:27
        for i in xrange(4,15):
            s = c[i].find(">")
            e = c[i].find("</font>")
            if s == -1:
                s = 0
                e = len(c[i])
            else:
                s += 1
            c[i] = c[i][s:e]
        d = dict(zip(cols, c))
        if c[15].find("btn130_2") != -1:#btn130_2表示预定按钮可以点击,btn130表示预订按钮灰显
            d[u"预订"] = 1
        else:
            d[u"预订"] = 0
        trains.append(d)
    return trains

#------------------------------------------------------------------------------
# Print trains
def printTrains(trains,cfg):
    printDelimiter()
    print u"%s\t%s--->%s    '有':票源充足  '无':票已售完  '*':未到起售时间  '--':无此席别"%(cfg.train_date,cfg.from_city_name,cfg.to_city_name)
    printDelimiter()
    print u"序号/车次\t发站\t\t到站\t\t一等座\t二等座\t软卧\t硬卧\t软座\t硬座\t无座"
    printDelimiter()
    index = 1
    for t in trains:
        print u"(%d)   %s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(index,t[u"车次"],t[u"发站"],t[u"到站"],t[u"一等座"],t[u"二等座"],t[u"软卧"],t[u"硬卧"],t[u"软座"],t[u"硬座"],t[u"无座"])
        index += 1
    printDelimiter()

#------------------------------------------------------------------------------
# Query tickets
def queryTickets(cfg):
    #查询初始化可以省略
    #url = "https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=init"
    #referer = "https://dynamic.12306.cn/otsweb/"
    #resp = sendGetRequest(url,referer)

    #https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=queryLeftTicket&orderRequest.train_date=2013-01-25&orderRequest.from_station_telecode=HHQ&orderRequest.to_station_telecode=HYQ&orderRequest.train_no=&trainPassType=QB&trainClass=QB#D#Z#T#K#QT#&includeStudent=00&seatTypeAndNum=&orderRequest.start_time_str=00:00--24:00
    url = "https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=queryLeftTicket"
    referer = "https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=init"
    '''
    parameters = {
        'orderRequest.train_date'           :cfg.train_date,
        'orderRequest.from_station_telecode':cfg.from_station_telecode,
        'orderRequest.to_station_telecode'  :cfg.to_station_telecode,
        'orderRequest.train_no'             :"",#车次,K9060对应的车次为69000K906007,留空表示查询全部,建议留空
        'trainPassType'                     :"QB",#GL过路#SF始发#QB全部
        'trainClass'                        :"QB#D#Z#T#K#QT#",#QB全部#D动车#Z字头#T字头#K字头#QT其它
        'includeStudent'                    :"00",#隐含选项,乘客中包含学生,使用默认值00即可
        'seatTypeAndNum'                    :"",#隐含选项,使用默认值""即可
        'orderRequest.start_time_str'       :"00:00--24:00"#发出时间段,不用修改
    }
    url += urllib.urlencode(parameters)
    '''
    #2013-01-26日升级到v5.67后需要保证顺序才能正确返回数据
    params = [
        {'orderRequest.train_date'           :cfg.train_date},
        {'orderRequest.from_station_telecode':cfg.from_station_telecode},
        {'orderRequest.to_station_telecode'  :cfg.to_station_telecode},
        {'orderRequest.train_no'             :""},
        {'trainPassType'                     :"QB"},
        {'trainClass'                        :"QB#D#Z#T#K#QT#"},
        {'includeStudent'                    :"00"},
        {'seatTypeAndNum'                    :""},
        {'orderRequest.start_time_str'       :"00:00--24:00"}
    ]
    for param in params:
        url += "&" + urllib.urlencode(param)
    resp = sendGetRequest(url,referer)
    try:
        respInfo = resp.read()
    except:
        print(u"queryTickets()->sendGetRequest(%s)->resp.read() exception"%(url))
        return []

    #各车次余票详情
    trains = getTrainsDetailInfo(respInfo)
    printTrains(trains,cfg)
    return trains

#------------------------------------------------------------------------------
# Select train
def selectTrain(trains):
    trains_num = len(trains)
    index = 0
    while 1:#必须选择有效的车次
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
# Select Actions
#-1->重新查询/0->退出程序/1~len->车次序号
def selectAction(trains,cfg):
    ret = -1
    trains_num = len(trains)
    print u"您可以选择:\n1~%d.选择车次开始订票\nd.更改乘车日期\nf.更改出发站\nt.更改目的站\ns.同时更改出发站和目的站\na.同时更改乘车日期,出发站和目的站\nq.退出\n刷新车票请直接回车"%(trains_num)
    printDelimiter()
    select = raw_input("")
    if select.isdigit():
        index = int(select)
        if index<1 or index>trains_num:
            print u"输入的序号无效,请重新选择车次(1~%d)"%(trains_num)
            index = selectTrain(trains)
        if not trains[index-1][u"预订"]:
            print u"您选择的车次%s没票啦,请重新选择车次"%(trains[index-1][u"车次"])
            index = selectTrain(trains)
        ret = index
    elif select == "d" or select == "D":
        print u"请输入乘车日期:"
        cfg.train_date = inputDate()
    elif select == "f" or select == "F":
        print u"请输入出发站:"
        station = inputStation()
        cfg.from_city_name = station['name']
        cfg.from_station_telecode = station['telecode']#车站编码#例如深圳对应的编码是SZQ
    elif select == "t" or select == "T":
        print u"请输入目的站:"
        station = inputStation()
        cfg.to_city_name = station['name']
        cfg.to_station_telecode = station['telecode']
    elif select == "s" or select == "S":
        print u"请输入出发站:"
        station = inputStation()
        cfg.from_city_name = station['name']
        cfg.from_station_telecode = station['telecode']
        print u"请输入目的站:"
        station = inputStation()
        cfg.to_city_name = station['name']
        cfg.to_station_telecode = station['telecode']
    elif select == "a" or select == "A":
        print u"请输入乘车日期:"
        cfg.train_date = inputDate()
        print u"请输入出发站:"
        station = inputStation()
        cfg.from_city_name = station['name']
        cfg.from_station_telecode = station['telecode']
        print u"请输入目的站:"
        station = inputStation()
        cfg.to_city_name = station['name']
        cfg.to_station_telecode = station['telecode']
    elif select == "q" or select == "Q":
        ret = 0

    return ret

def parseOnClick(train,cfg):
    soup = BeautifulSoup(train[u"购票"])
    tag_a = soup.find("a", class_=["btn130_2", "btn130"])
    onclick = tag_a['onclick']
    itemList = onclick.split('#')
    station_train_code = itemList[0][len("javascript:getSelected('"):]#车次#K9060
    lishi = itemList[1]#历时#13:22
    train_start_time = itemList[2]#发出时间#19:08
    trainno4 = itemList[3]#车次编码#69000K906007
    from_station_telecode = itemList[4]#出发站编码#OSQ
    to_station_telecode = itemList[5]#目的站编码#EHQ
    arrive_time = itemList[6]#到达时间#08:30
    from_station_name = itemList[7]#出发站名称#深圳西
    to_station_name = itemList[8]#目的站名称#新化
    from_station_no = itemList[9]#出发站是第几站#01
    to_station_no = itemList[10]#目的站是第几站#13
    ypInfoDetail = itemList[11]#余票详情#1*****36601*****08953*****0000
    mmStr = itemList[12]#6D10DCDFCFD7BFC946029BADC0C7DFD166BD121BC8972AC7B931556A
    locationCode = itemList[13][:-len("')")]#Q6
    postDict = {
        'station_train_code'        :station_train_code,#"K9060",
        'train_date'                :cfg.train_date,#"2013-01-10",
        'seattype_num'              :"",#隐含选项,使用默认值""即可
        'from_station_telecode'     :from_station_telecode,#"OSQ",
        'to_station_telecode'       :to_station_telecode,#"EHQ",
        'include_student'           :"00",#隐含选项,乘客中包含学生,使用默认值00即可
        'from_station_telecode_name':cfg.from_city_name,#u"深圳",#对应查询界面'出发地'输入框中的内容
        'to_station_telecode_name'  :cfg.to_city_name,#u"新化",#对应查询界面'目的地'输入框中的内容
        'round_train_date'          :cfg.train_date,#"2013-01-10",
        'round_start_time_str'      :"00:00--24:00",#发出时间段,不用修改
        'single_round_type'         :"1",
        'train_pass_type'           :"QB",#GL过路#SF始发#QB全部
        'train_class_arr'           :"QB#D#Z#T#K#QT#",#QB全部#D动车#Z字头#T字头#K字头#QT其它
        'start_time_str'            :"00:00--24:00",#发出时间段,不用修改
        'lishi'                     :lishi,#"13:22",
        'train_start_time'          :train_start_time,#"19:08",
        'trainno4'                  :trainno4,#"69000K906007",
        'arrive_time'               :arrive_time,#"08:30",
        'from_station_name'         :from_station_name,#"深圳西",
        'to_station_name'           :to_station_name,#"新化",
        'from_station_no'           :from_station_no,#"01",
        'to_station_no'             :to_station_no,#"13",
        'ypInfoDetail'              :ypInfoDetail,
        'mmStr'                     :mmStr,
        'locationCode'              :locationCode
    }

    return postDict

#------------------------------------------------------------------------------
# Order Init
def orderInit(onClickDict):
    url = "https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=submutOrderRequest"
    referer = "https://dynamic.12306.cn/otsweb/order/querySingleAction.do?method=init"
    postData = urllib.urlencode(onClickDict)
    resp = sendPostRequest(url,postData,referer)#服务器会返回302,重定向到 https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init
    respInfo = None
    try:
        respInfo = resp.read()
    except:
        print(u"orderInit()->sendPostRequest(%s)->resp.read() exception"%(url))
    #logging.debug('orderInit submutOrderRequest respInfo:%s'%(respInfo))
    if not respInfo:
        url = "https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=init"
        resp = sendPostRequest(url,postData,referer)
        try:
            respInfo = resp.read()
        except:
            print(u"orderInit()->sendPostRequest(%s)->resp.read() exception"%(url))
        #logging.debug('orderInit init respInfo:%s'%(respInfo))
    return respInfo

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

    #通用的POST数据,来自于之前init的响应数据
    hiddenDict = {
        'org.apache.struts.taglib.html.TOKEN'   :token,
        'leftTicketStr'                     :leftTicketStr,
        'textfield'                         :textfield,
        'checkbox2'                         :"2",
        'checkbox3'                         :"3",
        'checkbox4'                         :"4",
        'checkbox5'                         :"5",
        'checkbox6'                         :"6",
        'orderRequest.train_date'           :train_date,
        'orderRequest.train_no'             :train_no,
        'orderRequest.station_train_code'   :station_train_code,
        'orderRequest.from_station_telecode':from_station_telecode,
        'orderRequest.to_station_telecode'  :to_station_telecode,
        'orderRequest.seat_type_code'       :seat_type_code,
        'orderRequest.ticket_type_order_num':ticket_type_order_num,
        'orderRequest.bed_level_order_num'  :bed_level_order_num,
        'orderRequest.start_time'           :start_time,
        'orderRequest.end_time'             :end_time,
        'orderRequest.from_station_name'    :from_station_name,
        'orderRequest.to_station_name'      :to_station_name,
        'orderRequest.cancel_flag'          :cancel_flag,
        'orderRequest.id_mode'              :id_mode,
    }
    hiddenList = [
        ('org.apache.struts.taglib.html.TOKEN'   ,token),
        ('leftTicketStr'                     ,leftTicketStr),
        ('textfield'                         ,textfield),
        ('checkbox2'                         ,"2"),
        ('checkbox3'                         ,"3"),
        ('checkbox4'                         ,"4"),
        ('checkbox5'                         ,"5"),
        ('checkbox6'                         ,"6"),
        ('orderRequest.train_date'           ,train_date),
        ('orderRequest.train_no'             ,train_no),
        ('orderRequest.station_train_code'   ,station_train_code),
        ('orderRequest.from_station_telecode',from_station_telecode),
        ('orderRequest.to_station_telecode'  ,to_station_telecode),
        ('orderRequest.seat_type_code'       ,seat_type_code),
        ('orderRequest.ticket_type_order_num',ticket_type_order_num),
        ('orderRequest.bed_level_order_num'  ,bed_level_order_num),
        ('orderRequest.start_time'           ,start_time),
        ('orderRequest.end_time'             ,end_time),
        ('orderRequest.from_station_name'    ,from_station_name),
        ('orderRequest.to_station_name'      ,to_station_name),
        ('orderRequest.cancel_flag'          ,cancel_flag),
        ('orderRequest.id_mode'              ,id_mode)
    ]
    return (hiddenDict,hiddenList)

#------------------------------------------------------------------------------
# Generate common data
def genCommonData(hiddenDict,cfg,picCode):
    #乘客信息
    passenger_seat_detail = "0"#0->随机#1->下铺#2->中铺#3->上铺
    all_passengers = [
        {
            'passengerTickets'                  :"%s,%s,%s,%s,%s,%s,%s,%s"%(p['seattype'],passenger_seat_detail,p['tickettype'],p['name'],p['cardtype'],p['id'],p['phone'],"Y"),#"席别,随机,票种,姓名,证件类型,证件号码,手机号码,保存到常用联系人"
            'oldPassengers'                     :"%s,%s,%s"%(p['name'],p['cardtype'],p['id']),#"姓名,证件类型,身证件号码"
            'passenger_%d_seat'%(p['index'])          :p['seattype'],#1->硬座#3->硬卧
            'passenger_%d_ticket'%(p['index'])        :p['tickettype'],#1->成人票#2->儿童票#3->学生票#4->残军票
            'passenger_%d_name'%(p['index'])          :p['name'],#乘客姓名
            'passenger_%d_cardtype'%(p['index'])      :p['cardtype'],#证件类型:#1->二代身份证#2->一代身份证#C->港澳通行证#G->台湾通行证#B->护照
            'passenger_%d_cardno'%(p['index'])        :p['id'],#证件号码
            'passenger_%d_mobileno'%(p['index'])      :p['phone'],#手机号码
            'checkbox9'                         :"Y"#保存到常用联系人
        }
        for p in cfg.passengers
    ]
    commonPostData = urllib.urlencode(hiddenDict)
    for p in all_passengers:
        commonPostData = commonPostData + '&' + urllib.urlencode(p)

    d = {
        'randCode'                          :picCode,
        'orderRequest.reserve_flag'         :"A"#A网上支付#B网上预订,默认选择A
    }
    commonPostData = commonPostData + '&' + urllib.urlencode(d)

    return commonPostData

#------------------------------------------------------------------------------
# Generate common data
def genCommonDataOneByOne(hiddenDict,cfg,picCode):
    #乘客信息
    passenger_seat_detail = "0"#0->随机#1->下铺#2->中铺#3->上铺
    all_passengers = [
        [
            ('passengerTickets'                  ,"%s,%s,%s,%s,%s,%s,%s,%s"%(p['seattype'],passenger_seat_detail,p['tickettype'],p['name'],p['cardtype'],p['id'],p['phone'],"Y")),#"席别,随机,票种,姓名,证件类型,证件号码,手机号码,保存到常用联系人"
            ('oldPassengers'                     ,"%s,%s,%s"%(p['name'],p['cardtype'],p['id'])),#"姓名,证件类型,身证件号码"
            ('passenger_%d_seat'%(p['index'])          ,p['seattype']),#1->硬座#3->硬卧
            ('passenger_%d_ticket'%(p['index'])        ,p['tickettype']),#1->成人票#2->儿童票#3->学生票#4->残军票
            ('passenger_%d_name'%(p['index'])          ,p['name']),#乘客姓名
            ('passenger_%d_cardtype'%(p['index'])      ,p['cardtype']),#证件类型:#1->二代身份证#2->一代身份证#C->港澳通行证#G->台湾通行证#B->护照
            ('passenger_%d_cardno'%(p['index'])        ,p['id']),#证件号码
            ('passenger_%d_mobileno'%(p['index'])      ,p['phone']),#手机号码
            ('checkbox9'                         ,"Y")#保存到常用联系人
        ]
        for p in cfg.passengers
    ]
    commonPostData = urllib.urlencode(hiddenDict)
    for p in all_passengers:
        commonPostData = commonPostData + '&' + urllib.urlencode(p)

    d = [
        ('randCode'                          ,picCode),
        ('orderRequest.reserve_flag'         ,"A")#A网上支付#B网上预订,默认选择A
    ]
    commonPostData = commonPostData + '&' + urllib.urlencode(d)

    return commonPostData

#------------------------------------------------------------------------------
# Get Passenger Infomation
def getPassengerJson():
    url = "https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=getpassengerJson"
    resp = sendPostRequest(url,{})

#------------------------------------------------------------------------------
# Check order info
# 1->OK/0->Fail/-1->errMsg
def checkOrderInfo(commonPostData,picCode):
    url = "https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=checkOrderInfo&rand=" + picCode
    tFlagDict = {'tFlag':"dc"}#dc单程#wc往程#fc返程#gc改签
    postData = commonPostData + '&' + urllib.urlencode(tFlagDict)
    resp = sendPostRequest(url,postData)
    respInfo = None
    try:
        respInfo = resp.read()
    except:
        print(u"checkOrderInfo()->sendPostRequest(%s)->resp.read() exception"%(url))
        return 0
    #{"checkHuimd":"Y","check608":"Y","msg":"","errMsg":"Y"}
    #参数解释参考https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js?version=5.37
    #checkHuimd":"N"#"对不起，由于您取消次数过多，今日将不能继续受理您的订票请求！"
    #"check608":"N"#"本车为实名制列车，实行一日一车一证一票制！"
    logging.debug('checkOrderInfo respInfo:%s'%(respInfo))
    respDict = {}
    try:
        respDict = eval(respInfo)
    except:
        print(u"checkOrderInfo(%s)->eval(respInfo) exception"%(url))
        return 0
    if respDict.has_key("errMsg"):
        if respDict['errMsg'] != "Y":
            print u'检查订单信息,服务器返回错误errMsg:%s'%(respDict['errMsg'])
            return -1
    elif respDict.has_key("msg"):
        if respDict['msg'] != "":
            print u'检查订单信息,服务器返回错误msg:%s'%(respDict['msg'])
            return 0
    elif respDict.has_key("checkHuimd"):
        if respDict['checkHuimd'] != "Y":
            print u'检查订单信息,服务器返回错误checkHuimd:%s'%(respDict['checkHuimd'])
            return 0
    elif respDict.has_key("check608"):
        if respDict['check608'] != "Y":
            print u'检查订单信息,服务器返回错误check608:%s'%(respDict['check608'])
            return 0
    return 1

#------------------------------------------------------------------------------
# Get queue count
# 1->OK/0->Fail/-1->errMsg
def getQueueCount(hiddenDict):
    #https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=getQueueCount&train_date=2013-01-25&train_no=770000K81303&station=K812&seat=3&from=HHQ&to=HYQ&ticket=1007803081402230000010078000733014400046
    url = "https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=getQueueCount&"
    parameters = {
        'train_date':hiddenDict['orderRequest.train_date'],
        'train_no'  :hiddenDict['orderRequest.train_no'],
        'station'   :hiddenDict['orderRequest.station_train_code'],
        'seat'      :"1" if not hiddenDict['orderRequest.seat_type_code'] else hiddenDict['orderRequest.seat_type_code'],
        'from'      :hiddenDict['orderRequest.from_station_telecode'],
        'to'        :hiddenDict['orderRequest.to_station_telecode'],
        'ticket'    :hiddenDict['leftTicketStr']
    }
    parameters = [
        ('train_date',hiddenDict['orderRequest.train_date']),
        ('train_no'  ,hiddenDict['orderRequest.train_no']),
        ('station'   ,hiddenDict['orderRequest.station_train_code']),
        ('seat'      ,"1" if not hiddenDict['orderRequest.seat_type_code'] else hiddenDict['orderRequest.seat_type_code']),
        ('from'      ,hiddenDict['orderRequest.from_station_telecode']),
        ('to'        ,hiddenDict['orderRequest.to_station_telecode']),
        ('ticket'    ,hiddenDict['leftTicketStr'])
    ]
    url += urllib.urlencode(parameters)
    resp = sendGetRequest(url)
    try:
        respInfo = resp.read()
    except:
        print(u"getQueueCount()->sendGetRequest(%s)->resp.read() exception"%(url))
        return 0
    #{"countT":0,"count":1,"ticket":"1*****36601*****09683*****0067","op_1":false,"op_2":false}
    #参数解释参考#https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js?version=5.37
    #"countT":0#目前排队人数
    #"count":1#在你之前的排队人数
    #"ticket":"1*****36601*****09683*****0067"#其中36601代表无座有660张, 09683代码座位票有968张,0067代表卧铺票有67张,纯属推测
    #"op_1":true#"目前排队人数已经超过余票张数，特此提醒。"
    #"op_2":true#"目前排队人数已经超过余票张数，请您选择其他席别或车次，特此提醒。"
    logging.debug('getQueueCount respInfo:%s'%(respInfo))
    return 1

#------------------------------------------------------------------------------
# Confirm single for queue
# 1->OK/0->Fail/-1->errMsg
def confirmSingleForQueue(commonPostData):
    url = "https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=confirmSingleForQueue"
    resp = sendPostRequest(url,commonPostData)
    try:
        respInfo = resp.read()#{"errMsg":"Y"}
    except:
        print(u"confirmSingleForQueue()->sendPostRequest(%s)->resp.read() exception"%(url))
        return 0
    logging.debug('confirmSingleForQueue respInfo:%s'%(respInfo))
    try:
        respDict = eval(respInfo)
    except:
        print(u"confirmSingleForQueue(%s)->eval(respInfo) exception"%(url))
        return 0
    if respDict.has_key("errMsg"):
        if respDict['errMsg'] != "Y":
            print u'订单入队,服务器返回错误:%s'%(respDict['errMsg'])
            return -1
    return 1

#------------------------------------------------------------------------------
# Query order wait time and return orderId
def queryOrderWaitTime():
    url = "https://dynamic.12306.cn/otsweb/order/myOrderAction.do?method=queryOrderWaitTime&tourFlag=dc"
    resp = sendGetRequest(url)
    orderId = ''
    try:
        respInfo = resp.read()
    except:
        print(u"queryOrderWaitTime()->sendGetRequest(%s)->resp.read() exception"%(url))
    #{"tourFlag":"dc","waitTime":5,"waitCount":1,"requestId":5691791102757848251,"count":0}
    #参数解释参考https://dynamic.12306.cn/otsweb/js/order/save_passenger_info.js?version=5.37
    #"tourFlag":"dc"#单程
    #"waitTime":5#排队等待时间
    #"waitCount":1#排队人数
    #"requestId":5691791102757848251#
    #获取orderId
    try:
        respDict = eval(respInfo)
    except:
        print(u"queryOrderWaitTime(%s)->eval(respInfo) exception"%(url))
        respDict = {}
    if respDict.has_key("orderId"):
        orderId = respDict["orderId"]

    #如果上一次没有返回 orderId, 则再次重复一遍
    if orderId == '':
        resp = sendGetRequest(url)
        try:
            respInfo = resp.read()
        except:
            print(u"queryOrderWaitTime()->sendGetRequest(%s)->resp.read() exception"%(url))
        #获取orderId
        try:
            respDict = eval(respInfo)
        except:
            print(u"queryOrderWaitTime(%s)->eval(respInfo) exception"%(url))
            respDict = {}
        orderId = ''
        if respDict.has_key("orderId"):
            orderId = respDict["orderId"]
    logging.debug('queryOrderWaitTime respInfo:%s'%(respInfo))
    return orderId

class Config:
    username = ''#账号
    password = ''#密码
    train_date = ''#乘车日期#格式为2013-02-01
    from_city_name = ''#u'深圳'#对应查询界面'出发地'输入框中的内容
    to_city_name = ''  #u'新化'#对应查询界面'目的地'输入框中的内容
    from_station_telecode = ''#出发站编码#例如深圳对应的编码是SZQ
    to_station_telecode = ''  #目的站编码#例如新化对应的编码是EHQ
    passengers = []#乘客列表
    def readConfig(self,config_file='config.ini'):
        #从配置文件读取订票信息
        cp = ConfigParser.ConfigParser()
        try:
            cp.readfp(codecs.open(config_file, 'r','utf-8-sig'))
        except IOError as e:
            print u"打开配置文件'%s'失败啦!"%(config_file)
            return
        Config.username = cp.get("login","username")
        Config.password = cp.get("login","password")
        Config.train_date = cp.get("train","date");
        Config.from_city_name = cp.get("train","from")
        Config.to_city_name = cp.get("train","to")
        Config.from_station_telecode = stationName2Telecode(Config.from_city_name)
        Config.to_station_telecode = stationName2Telecode(Config.to_city_name)
        #检查出发站,目的站和乘车日期
        if not Config.from_station_telecode:
            print u"出发站错误,请重新输入:"
            station = inputStation()
            Config.from_city_name = station['name']
            Config.from_station_telecode = station['telecode']
        if not Config.to_station_telecode:
            print u"目的站错误,请重新输入:"
            station = inputStation()
            Config.to_city_name = station['name']
            Config.to_station_telecode = station['telecode']
        if not checkDate(Config.train_date):
            print u"乘车日期错误,请重新输入:"
            Config.train_date = inputDate()
        #分析乘客信息
        Config.passengers = []
        index = 1
        passenger_sections = ["passenger%d"%(i) for i in xrange(1,6)]
        sections = cp.sections()
        for section in passenger_sections:
            if section in sections:
                passenger = {}
                passenger['index'] = index
                passenger['name'] = cp.get(section,"name")#必选参数
                passenger['cardtype'] = cp.get(section,"cardtype") if cp.has_option(section,"cardtype") else "1"#证件类型:可选参数,默认值1,即二代身份证
                passenger['id'] = cp.get(section,"id")#必选参数
                passenger['phone'] = cp.get(section,"phone") if cp.has_option(section,"phone") else "13751119427"#手机号码
                passenger['seattype'] = cp.get(section,"seattype") if cp.has_option(section,"seattype") else "1"#席别:可选参数,默认值1,即硬座
                passenger['tickettype'] = cp.get(section,"tickettype") if cp.has_option(section,"tickettype") else "1"#票种:可选参数,默认值1,即成人票
                Config.passengers.append(passenger)
                index += 1
    def printConfig(self):
        printDelimiter()
        print u"订票信息:"
        print u"%s\t%s\t%s--->%s"%(Config.username,Config.train_date,Config.from_city_name,Config.to_city_name)
        printDelimiter()
        print u"序号 姓名\t证件类型\t证件号码\t\t手机号码\t席别\t票种\t"
        for p in Config.passengers:
            print u"%d    %s\t%s\t%s\t%s\t%s\t%s"%(p['index'],p['name'].decode("utf-8","ignore"),getCardType(p['cardtype']),p['id'],p['phone'],getSeatType(p['seattype']),getTicketType(p['tickettype']))#使用decode("gb2312","ignore")会乱码,因为文件是保存为 utf-8 编码的

#------------------------------------------------------------------------------
# Main function
def Main12306():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s %(funcName)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %X',
                        filename='log.txt',
                        filemode='w')
    logging.debug('Start')
    cfg = Config()
    cfg.readConfig()
    cfg.printConfig()

    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('Accept',	'text/html'),
                         ('Referer', 'https://dynamic.12306.cn/otsweb/'),
                         ('Accept-Language', 'zh-CN'),
                         ('User-Agent', 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0; MALC'),
                         ('Accept-Encoding', 'deflate'),
                         ('Host', "dynamic.12306.cn"),
                         ('Connection', 'Keep-Alive'),
                        ]
    urllib2.install_opener(opener)
    max_tries = 3
    tries = 0

    while tries < max_tries:
        printDelimiter()
        if login(cfg.username,cfg.password):
            print u"登陆成功^_^"
            break
        else:
            print u"登陆失败啦!重新登陆..."

    if tries >= max_tries:
        print u"失败次数太多,自动退出程序"
        sys.exit()

    while 1:
        trains = queryTickets(cfg)#查询并显示余票情况
        ret = selectAction(trains,cfg)#选择下一步动作
        if ret == -1:#重新查询
            continue
        elif ret == 0:#退出程序
            sys.exit()
        index = ret
        onClickDict = parseOnClick(trains[index-1],cfg)
        respInfo = orderInit(onClickDict)
        ret = getHiddenItem(respInfo)
        if not ret:
            print(u"getHiddenItem() failed")
            continue
        hiddenDict = ret[0]
        hiddenList = ret[1]
        #请求图片验证码
        savePicCode("https://dynamic.12306.cn/otsweb/passCodeAction.do?rand=randp")
        printDelimiter()
        print u"请输入4位图片验证码订票:"
        picCode = raw_input("")
        commonPostData = genCommonDataOneByOne(hiddenList,cfg,picCode)
        #请求乘客信息,可以省略
        #getPassengerJson()
        #检查订单信息,不能省略
        ret = checkOrderInfo(commonPostData,picCode)
        if ret == 0:
            continue
        elif ret == -1:#验证码错误
            savePicCode("https://dynamic.12306.cn/otsweb/passCodeAction.do?rand=randp"+"%1.16f"%(random.random()))
            printDelimiter()
            print u"请重新输入4位图片验证码订票:"
            picCode = raw_input("")
            commonPostData = genCommonDataOneByOne(hiddenList,cfg,picCode)
            ret = checkOrderInfo(commonPostData,picCode)
        #查询排队和余票情况,不能省略
        ret = getQueueCount(hiddenDict)
        #提交订单到队里中
        ret = confirmSingleForQueue(commonPostData)
        #获取队里等待时间,服务器会返回 orderId, orderId 会作为随后的POST参数
        orderId = queryOrderWaitTime()
        #正式提交订单
        url = "https://dynamic.12306.cn/otsweb/order/confirmPassengerAction.do?method=payOrder&orderSequence_no=" + orderId
        resp = sendPostRequest(url,commonPostData)
        try:
            respInfo = resp.read()
        except:
            print(u"Main12306()->sendPostRequest(%s)->resp.read() exception"%(url))
        if checkOrderResult(respInfo):
            print u"订票成功^_^请在45分钟内完成网上支付,否则系统将自动取消"
            break

        #访问未完成订单页面检查是否订票成功
        url = "https://dynamic.12306.cn/otsweb/order/myOrderAction.do?method=queryMyOrderNotComplete&leftmenu=Y"
        resp = sendGetRequest(url)
        try:
            respInfo = resp.read()
        except:
            print(u"Main12306()->sendGetRequest(%s)->resp.read() exception"%(url))
        if checkOrderResult(respInfo):
            print u"订票成功^_^请在45分钟内完成订单,否则系统将自动取消"
            break
        else:
            print u"订票失败啦!请重试"

    raw_input("Press any key to continue")
    logging.debug('End')

if __name__=="__main__":
    Main12306()