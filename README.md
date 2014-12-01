py12306
======
py12306 是一个 Python 版的[12306.cn](http://www.12306.cn)订票程序。

Usage
------
<pre>
'-c', '--config', '可选参数, 指定配置文件, 默认使用 config.ini'  
'-u', '--username', '可选参数, 登陆账号'  
'-p', '--password', '可选参数, 登陆密码'  
'-d', '--date', '可选参数, 指定乘车日期, 日期格式如: 2014-01-01, 默认使用配置文件的乘车日期'  
'-m', '--mail', '可选参数, 开启邮件提醒(用于节假日抢票时自动刷票提醒)'
</pre>  

安装依赖包:
`pip install huzhifeng`

直接运行:   
`python py12306.py`  
或者指定参数:  
`python py12306.py -u username -p password -c config.ini -d date -m 1`

Config
------
最简单的方法是复制一份 config-sample.ini 为 config.ini， 然后填写自己的乘车信息， 乘客信息可以只填姓名和证件号码， 有几个乘客就填几项[passengerX]， 这些配置都可以在运行期间进行修改。
<pre>
#登陆账号和密码
[login]
username=yourusername
password=yourpassword
#乘车信息, 出发站, 目的站, 乘车日期
[train]
from=出发站
to=目的站
date=2014-01-01
#乘客信息
#name: 必选参数, 姓名
#cardtype: 可选参数, 证件类型, 默认值1, 即二代身份证, 有效值如下:
#1->二代身份证
#2->一代身份证
#C->港澳通行证
#G->台湾通行证
#B->护照
#id: 必选参数, 证件号码
#phone: 可选参数, 手机号码
#seattype: 可选参数, 席别, 默认值1, 即硬座, 有效值如下:
#1->硬座/无座
#3->硬卧
#4->软卧
#7->一等软座
#8->二等软座
#9->商务座
#M->一等座
#O->二等座
#P->特等座
#B->混编硬座
#tickettype: 可选参数, 票种, 默认值1, 即成人票, 有效值如下:
#1->成人票
#2->儿童票
#3->学生票
#4->残军票
[passenger1]
name=张三
cardtype=1
id=123456190001010001
phone=13800138000
seattype=1
tickettype=1
[passenger2]
name=李四
id=123456190001010002
[passenger3]
name=王五
id=123456190001010003
[passenger4]
name=赵六
id=123456190001010004
[passenger5]
name=吴七
id=123456190001010005
</pre>

LICENSE
------
[GNU General Public License, version 2](http://www.gnu.org/licenses/gpl-2.0.html)