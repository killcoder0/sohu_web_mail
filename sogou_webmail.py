# -*- coding: utf-8 -*-

import base
import session.session as session
import mail_addr_provider
import content_provider
import random
import time
import copy
import tornado.ioloop
import json

add_header = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36",
                      }

class SogouMailbox(object):
    def __init__(self,username,password,virtual_ip=""):
#        self.__browser = session.AsyncSession()
        self.__browser = session.AsyncSession()
        global add_header
        self.__username = username
        self.__password = password
        self.__add_header = copy.copy(add_header)
        if virtual_ip:
            self.__add_header["X-Forwarded-For"] = virtual_ip
            self.__add_header["X-Real-IP"] = virtual_ip
        self.__count = 0
        self.__ok = 0
        self.__last_mail = None
        self.__action = ""

    def on_login(self,response):
        if response.error:
            deadline = time.time() + 10
            tornado.ioloop.IOLoop.instance().add_timeout(deadline,self.login)
        else:
            #self.sendmail()
            self.__browser.fetch("http://mail.sogou.com/","GET",self.__add_header,None,self.on_browser_redirect_page)

    def on_browser_redirect_page(self,response):
        self.__action = response.effective_url.replace("main","mail")
        self.sendmail()

    def login(self):
        self.__browser.clear()
        action = "https://account.sogou.com/web/login"
        data = {
                "username":self.__username,
                "password":self.__password,
                "captcha":"",
                "autoLogin":"0",
                "client_id":"1014",
                "xd":"http://mail.sogou.com/jump.htm",
                "token":""
                }
        self.__browser.send_form(action,"POST",data,self.on_login,self.__add_header)

    def sendmail(self):
        if self.__last_mail:
            mail_data = self.__last_mail
        else:
            mail_data = self._create_mail()
        self.__browser.send_form(self.__action,"POST",mail_data,self.on_sendmail,self.__add_header)
        self.__last_mail = mail_data
#        resp = self.__browser.send_form(action,"POST",mail_data,self.__add_header)

    def on_sendmail(self,response):
        if response.error:
            deadline = time.time() + 10
            tornado.ioloop.IOLoop.instance().add_timeout(deadline,self.sendmail)
            return
        self.__count += 1
        ret = response.body
        success = False
        message = ""
        try:
            info = json.loads(ret)
            if info["is_success"]:
                success = True
                self.__ok += 1
        except Exception,e:
            message = "not response with json"
        print "%s ::: total:%d,ok:%d,message:%s" % (self.__username,self.__count,self.__ok,message)
        if not success:
            deadline = time.time() + 1200
            tornado.ioloop.IOLoop.instance().add_timeout(deadline,self.login)
        else:
            deadline = time.time() + 60*5
            tornado.ioloop.IOLoop.instance().add_timeout(deadline,self.sendmail)
            self.__last_mail = None

    def _create_mail(self):
        subject,content = content_provider.get_new_mail_content("nighteyes.games.takeoff")
        subject = subject.encode("utf8")
        content = content.encode("utf8")
        mail_to_list = mail_addr_provider.get_addr_provider(19)
        import random
        if random.randint(5,5) == 5:
            mail_to_list.append("151916524@qq.com")
        receive_segs = mail_to_list[0]
        for to in mail_to_list[1:]:
            receive_segs += "," + to
        mail = {'id'       : '0', 
            'stationery'   : '', 
            'is_send'      : '1',    
            'is_html'      : '1',   
            'subject'      : subject,
            'from'         : self.__username,
            'fullname'     : '',
            'to'           : receive_segs,
            'cc'           : '',
            'bcc'          : '',
            'html'         : content,
            'text'         : "",
            'addressbook_use_flag'    :'1',
            'addressbook_use_list'    :'0',
            'deliver_status'          :'2',
            'env'                : '{"attach": [], "disposition_notifier": 0, "original_id": 0, "draft_type": 0, "message_id": "", "references": [], "reply_to": [], "in_reply_to": [], "mail_followup_to": [], "save_after_send": 1, "save_to_addressbook": 1, "thread": 0}',
            'single'             : '0',
            '_method'            : 'put',
            '_'                  : ''
            }
        return mail

ip_list = []

def get_virtual_ip():
    global ip_list
    first = 10
    while True:
        second = random.randint(2,250)
        third = random.randint(2,250)
        fourth = random.randint(2,250)
        ip = "%d.%d.%d.%d" % (first,second,third,fourth)
        if ip not in ip_list:
            ip_list.append(ip)
            break
    return ip

if __name__ == "__main__":
    account_file = open("sogou_mail.txt","r")
    timespan = 0
    for line in account_file:
        line = line.strip()
        pos = line.find(" ")
        username = line[:pos]
        password = line[pos:]
        password = password.strip()
        #username,password = "game_works_003","abc123"
        virtual_ip = get_virtual_ip()
        box = SogouMailbox("%s@sogou.com"%username,password,virtual_ip)
        tornado.ioloop.IOLoop().instance().add_timeout(time.time()+timespan,box.login)
        timespan += 10
    #while True:
    #    ret = box.sendmail()
    #    count += 1
    #    seg = "<code>"
    #    pos = ret.find(seg)
    #    success = False
    #    if pos != -1:
    #        start = pos + len(seg)
    #        pos = ret.find("<",start)
    #        if pos != -1:
    #            if ret[start:pos] == "S_OK":
    #                ok += 1
    #                success = True
    #    print "total:%d,ok:%d" % (count,ok)
    #    if not success:
    #        print ret
    #    time.sleep(60*10)
    print "the server is running..."
    tornado.ioloop.IOLoop().instance().start()
