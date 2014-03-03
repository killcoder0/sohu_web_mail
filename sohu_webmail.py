# -*- coding: utf-8 -*-

import base
import session.session as session
import xhttp.xhttp_server as xserver
import mail_addr_provider
import content_provider
import random
import time
import copy
import tornado.ioloop
import json
import urllib
import md5

add_header = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.117 Safari/537.36",
                      }

class SohuMailbox(object):
    def __init__(self,username,password,back_action,virtual_ip=""):
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
        self.__back_action = back_action
        self.__action = ""
        state[self.__username] = (self.__count,self.__ok)

    def on_login(self,response):
        if response.error:
            deadline = time.time() + 10
            tornado.ioloop.IOLoop.instance().add_timeout(deadline,self.login)
        else:
            #self.sendmail()
            self.__browser.fetch("http://mail.sohu.com/","GET",self.__add_header,None,self.on_browser_redirect_page)

    def on_browser_redirect_page(self,response):
        action = response.effective_url
        if action.find("main") == -1:
            self.__action = self.__back_action
        else:
            self.__action = action.replace("main","mail")
        html = response.body
        if html:
            key_seg = 'name="csrf-token"'
            pos = html.find(key_seg)
            if pos != -1:
                key_seg = 'content="'
                pos = html.rfind(key_seg,0,pos-1)
                if pos != -1:
                    pos = pos + len(key_seg)
                    end = html.find('"',pos)
                    if end != -1:
                        self.__add_header["X-CSRF-Token"] = html[pos:end]
                        self.sendmail()
                        return
        deadline = time.time() + 1200
        tornado.ioloop.IOLoop.instance().add_timeout(deadline,self.login)
                  
    def login(self):
        self.__browser.clear()
        user_field = {"userid":self.__username}
        user_arg = urllib.urlencode(user_field)
        action = "https://passport.sohu.com/sso/login.jsp?%s&password=%s&appid=1113&persistentcookie=0&s=%d&b=7&w=1920&pwdtype=1&v=26" %(
                   user_arg,md5.new(self.__password).hexdigest(),int(time.time()*1000))
        self.__browser.fetch(action,"GET",self.__add_header,None,self.on_login)

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
        global state
        state[self.__username] = (self.__count,self.__ok)
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
        if random.randint(1,5) == 5:
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
            'env'                : '{"attach": [], "disposition_notifier": 0, "original_id": 0, "draft_type": 0, "message_id": "", "references": [], "reply_to": [], "in_reply_to": [], "mail_followup_to": [], "save_after_send": 1, "save_to_addressbook": 1, "thread": 0, "urgent_mail": 0}',
            'single'             : '0',
            'xfrom': self.__username,
            '_method'            : 'put',
            '_'                  : ''
            }
        return mail

ip_list = []
state = {}

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

def get_mail_state(request):
    global state
    body = json.dumps(state)
    return body

if __name__ == "__main__":
    account_file = open("sohu_mail.txt","r")
    timespan = 0
    times = 0
    for line in account_file:
        if times == 10:
            break
        line = line.strip()
        seg_list = line.split(" ")
        username = seg_list[0]
        password = seg_list[1]
        action = seg_list[2]
        #username,password = "game_works_003","abc123"
        virtual_ip = get_virtual_ip()
        box = SohuMailbox("%s@sohu.com"%username,password,action,virtual_ip)
        tornado.ioloop.IOLoop().instance().add_timeout(time.time()+timespan,box.login)
        timespan += 10
        times += 1
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
    url_map = {"/mgmt/get_mail_state":get_mail_state}
    xserver.start(8890,url_map)
    print "the server is running..."
    tornado.ioloop.IOLoop().instance().start()
