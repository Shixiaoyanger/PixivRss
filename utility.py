# -*- coding: utf-8 -*-
import re, platform, os, sys, time, datetime, json, logging
import requests
from pixivpy3 import *
from config import *

aapi = AppPixivAPI()

ABS_PATH     = sys.path[0]
TEMP_PATH    = os.path.join(ABS_PATH, 'temp')
PREVIEW_PATH = os.path.join(ABS_PATH, 'previews')
RSS_PATH     = os.path.join(ABS_PATH, 'rss')
LOG_PATH     = os.path.join(ABS_PATH, 'log')

COOKIE_FILE  = os.path.join(ABS_PATH, 'pixiv.cookie.txt')
TOKEN_FILE   = os.path.join(ABS_PATH, 'pixiv.token.txt')
EXIST_FILE   = os.path.join(ABS_PATH, 'exist', '%s.json')

MODE = {
    'daily'     : u'每日',
    'weekly'    : u'每周',
    'monthly'   : u'每月',
    'rookie'    : u'新人',
    'original'  : u'原创',
    'male'      : u'男性向作品',
    'female'    : u'女性向作品',
    
    # r18
    'daily_r18' : u'每日R-18',
    'weekly_r18': u'每周R-18',
    'male_r18'  : u'男性向R-18',
    'female_r18': u'女性向R-18',
    'r18g'      : u'每日R-18G',
}

WEIBO_MANUAL_REVIEW = 'WEIBO_MANUAL_REVIEW'

# 这个id是保存上榜log时用的
MODE_ID = {
    'daily'     : 1,
    'weekly'    : 2,
    'monthly'   : 3,
    'rookie'    : 4,
    'original'  : 5,
    'male'      : 6,
    'female'    : 7,
}

if DEBUG and DEBUG_SHOW_REQUEST_DETAIL:
    import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

def FormatTime( time_original, format_original = '%Y年%m月%d日 %H:%M' ):
    date = datetime.datetime.strptime(time_original, format_original)
    return date.strftime('%a, %d %b %Y %H:%M:%S +8000')

def GetCurrentTime():
    return time.strftime('%a, %d %b %Y %H:%M:%S +8000', time.localtime(time.time()))

def escape(text):
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

def Get(url, refer = 'http://www.pixiv.net/'):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'Accept-Charset': 'UTF-8,*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }

    if refer != '':
        headers['Referer'] = refer

    proxies = {}

    # pixiv登录状态
    if 'pixiv.net' in url or 'pximg.net' in url:
        cookie_file = open(COOKIE_FILE, 'r')
        cookies = json.load(cookie_file)
        cookie_file.close()
        cookies['p_ab_id'] = '1'

        # apply proxy for pixiv
        if 'proxy' in CONFIG:
            proxies = CONFIG['proxy']

    # 防止海外访问weibo变英文版
    elif 'weibo.com' in url:
        cookies = {
            'lang': 'zh-cn',
            'SUB': 'Af3TZPWScES9bnItTjr2Ahd5zd6Niw2rzxab0hB4mX3uLwL2MikEk1FZIrAi5RvgAfCWhPyBL4jbuHRggucLT4hUQowTTAZ0ta7TYSBaNttSmZr6c7UIFYgtxRirRyJ6Ww%3D%3D',
            'UV5PAGE': 'usr512_114',
            'UV5': 'usrmdins311164'
        }

    debug('[Network] new http request: get ' + url)
    try:
        r = requests.get(url, headers = headers, cookies = cookies, proxies = proxies, timeout = TIMEOUT)
        debug('[Network] response status code: %s' % r.status_code)
    except Exception, e:
        log(-1, 'unable to get %s, error message:' % url)
        log(-1, e)
        return False

    # 判断返回内容是不是纯文本
    if 'text/html' in r.headers['Content-Type']:
        return r.text
    else:
        return r.content

# 输出文件
def download(fname, url, refer = 'http://www.pixiv.net/ranking.php'):
    # 检查文件是否存在
    if os.path.exists(fname):
        # 检查是否为空
        if os.path.getsize(fname) != 0:
            # 不为空说明已存在，返回True
            return True
        else:
            # 为空说明文件有问题，需要重新下载
            os.remove(fname)

    # 下载
    data = Get(url, refer = refer)

    # 检查
    if not data:
        return False

    # 写入
    try:
        f = open(fname, 'wb')
        f.write(data)
        f.close()
        return True
    except Exception, err:
        log(url, err)
        return False

# DEBUG
def debug(message):
    global DEBUG
    if not DEBUG : return
    print message

def log(pixiv_id, message = None):
    if not message:
        message = pixiv_id
        pixiv_id = -1
    try:
        f = open(os.path.join(LOG_PATH, time.strftime('%Y-%m-%d.log', time.localtime(time.time()))), 'a+')
    except:
        f = open(os.path.join(LOG_PATH, time.strftime('%Y-%m-%d.log', time.localtime(time.time()))), 'w+')
    finally:
        debug(message)
        f.write('%s %s, %s\n' % (time.strftime('[%H:%M:%S] ',time.localtime(time.time())), pixiv_id, message))
        f.close()

# 读取exist.json
def ReadExist(mode):
    try:
        exist_file = open(EXIST_FILE % mode, 'r')
        exist_list = json.load(exist_file)
    except:
        exist_file = open(EXIST_FILE % mode, 'w')
        exist_list = {}
    finally:
        exist_file.close()
        return exist_list

# 更新exist.json
def UpdateExist(mode, exist_list):
    exist_json = json.dumps(exist_list)
    exist_file = open(EXIST_FILE % mode, 'w')
    exist_file.write(exist_json)
    exist_file.close()

def ReadToken():
    try:
        f = open(TOKEN_FILE, 'r')
        tokens = json.load(f)
    except:
        f = open(TOKEN_FILE, 'w')
        tokens = None
    finally:
        f.close()
        return tokens

def SaveToken(token):
    f = open(TOKEN_FILE, 'w')
    f.write(json.dumps(token))
    f.close()


# 数据库操作
class DB:
    # 构造函数时连接数据库
    def __init__(self):
        try:
            self._ = MySQLdb.connect( CONFIG['DB_HOST'], CONFIG['DB_USER'], CONFIG['DB_PASS'], CONFIG['DB_NAME'], charset="utf8" )
            self.c  = self._.cursor( MySQLdb.cursors.DictCursor ) # 使fetchall的返回值为带key的字典形式
        except Exception, e:
            log(-1, '数据库连接出错 : %s' % e)
            exit(1)

    # 析构时关闭数据库
    def __del__(self):
        self.c.close()
        self._.close()

    # 查询
    def Query( self, sql, data = None):
        try:
            if data : 
                self.c.execute( sql, data )
            else : 
                self.c.execute( sql )

            return self.c.fetchall()
        except Exception, e:
            log(0,  str(e[0]) + ' : ' + e[1])
            return False

    # 执行
    def Run( self, sql, data ):
        try:
            self.c.execute( sql, data )
            return self._.insert_id()
        except Exception, e:
            log(0,  str(e[0]) + ' : ' + e[1])
            return False