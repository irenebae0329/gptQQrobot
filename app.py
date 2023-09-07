import datetime
import json
from flask import Flask 
import requests
import config
import logging
from collections import deque,defaultdict
import time
import sys
import traceback
from alarmEmail import sendAlarmEmail
def global_exception_process(type,value,tb):
    trace_details="\n".join(traceback.format_exception(type,value,tb))
    presenttime=datetime.datetime.now()
    msg = f"caller: {' '.join(sys.argv)}\n{type}: {value}\n{trace_details}\n'时间':{str(presenttime)}" 
    sendAlarmEmail(msg) 
'''
   二次封装requests内的两种请求
'''
def makeReply(target2Msg):
    global bot
    openai_url=cfg.OPENAI_PROXY+'v1/chat/completions'
    target,query,quote,msgType=target2Msg
    header={'Authorization':'Bearer '+cfg.OPENAI_KEY,'Content-Type': 'application/json'} 
    UserDict[target].append({'role':'user','content':query})
    messages=UserDict[target]
    data=json.dumps({'model':cfg.MODEL_TYPE,'messages':messages})
    try:
       res=myrequest(url=openai_url,type='post',data=data,header=header,server='openai')
       reMsg=json.loads(res)['choices'][0]['message']
       UserDict[target].append(reMsg)
       reply=reMsg['content']
    except:
       res=cfg.ERROR_RETRY_MSG
       reMsg=json.loads(res)
       reply=reMsg
    for i in range(cfg.RETRY_TIMES):
        verify,response_code=bot.replyMsg(target,reply,msgType,quote) 
        bot.release(verify)
        if response_code!=-1:
            break
        elif i==cfg.RETRY_TIMES-1:
            bot.replyMsg(target,reply,cfg.MSG_TYPE_GROUP)
def notifyAllUser():
    global bot
    global UserDict
    for qq in UserDict.keys():
        try:
          bot.replyMsg(target=qq,content=cfg.NOTIFY_MSG,type=cfg.MSG_TYPE_FRIEND)
        except:
          bot.replyMsg(target=qq,content=cfg.NOTIFY_MSG,type=cfg.MSG_TYPE_GROUP)
     
def parseMessage(Object_list):
    global bot
    for Object in Object_list:
        flag=False
        if Object['type']=='FriendMessage':
           key=Object['sender']['id']
           msgChain=Object['messageChain'] 
           msgType=cfg.MSG_TYPE_FRIEND
        elif Object['type']=='GroupMessage':
            key=Object['sender']['group']['id']
            msgChain=Object['messageChain']
            msgType=cfg.MSG_TYPE_GROUP
        else:
            continue
        if not msgChain:
            continue
        for msg in msgChain:
             if msg['type'][:5]=='Group':
                 continue
             elif msg['type'][:3]=='Bot':
                 continue
             else:
                 if msg['type'].count('Event'): 
                     continue
                 elif msg['type']=='Source':
                     source=msg['id']
                 elif msg['type']=='Plain':
                     if msgType==cfg.MSG_TYPE_GROUP:
                       text=msg['text']
                       if text[:2]==cfg.BOT_KICKNAME:
                           flag=True
                           queryText=text[3:]  
                           replyQueue.appendleft((key,queryText,source,msgType))
                     elif msgType==cfg.MSG_TYPE_FRIEND:
                        replyQueue.appendleft((key,msg['text'],source,msgType))
                 else:
                     if not flag:
                         continue 
                     while replyQueue and replyQueue[0][0]==key:
                        replyQueue.popleft()
                     bot.replyMsg(target=key,content=cfg.NotImplemented_MSG,type=msgType,quote=source)
                     break
    
def myrequest(url,type,data=None,header=None,server='mirai',logger=True):
    msg='调用 '+url+' 接口'
    if logger:
      app.logger.info(msg)
    if type=='post' and not header:
        response=requests.post(url,data=data)
    elif type=='post' and data and header:
        response=requests.post(url,data=data,headers=header)
    elif type=='get' and data==None:
        response=requests.get(url)
    else:
        raise NameError('不正常的接口调用方式')

    if response.status_code!=200:
        msg+='失败' 
        app.logger.info(msg)
        app.logger.error(response)
        raise ConnectionError('接口响应错误')
    if server=='mirai':
        response=response.json()
        if response['code']==0:
            if logger:
              msg+='成功'
              app.logger.info(msg)
            return response
        elif response['msg']==cfg.ERROR_MSG_1:
            msg+='失败'
            app.logger.error(msg)
        else:
           msg+='失败' 
           app.logger.info(msg)
           app.logger.error(response['msg'])
           raise ConnectionError(msg) 
    elif server=='openai':
        response=response.text
        msg+='成功'
        app.logger.info(msg)
        return response
def test2():
    main_loop()
class QQbot:
    def __init__(self,qq) -> None:
        self.addr='http://'+cfg.SERVER_IP+':'+cfg.SERVER_PORT+'/'
        self.session=None
        self.vcode=cfg.ROBOT_VERIFY_KEY
        self.qq=qq
        self.code=self.verify()
        self.bind(self.code) 
    def updateSession(self):
        code=self.verify()
        self.code=code
        self.bind(self.code)
    def verify(self):
        url=self.addr+'verify' 
        response=myrequest(url,type='post',data=json.dumps({'verifyKey':self.vcode}))
        return response['session']
    def bind(self,verify):
        url = self.addr + 'bind'
        data = json.dumps({"sessionKey":verify, "qq": self.qq})
        myrequest(url,'post',data)
        return 
    def release(self,verify=None):
        url=self.addr+'release' 
        code=self.code if not verify else verify
        data=json.dumps({'sessionKey':code,"qq":self.qq})   
        try:
          myrequest(url,'post',data=data)
        except:
            app.logger.error(f'释放session:{code}时发生错误')
    def fetchLatestMessage(self):
        url = self.addr +'fetchMessage?count=10&sessionKey='+self.code
        response=myrequest(url,'get')
        return response['data']
    def countMessage(self):
        url=self.addr+'countMessage?sessionKey='+self.code
        return myrequest(url,'get',logger=False)['data']
    
    def replyMsg(self,target,content,type='1',quote=None):
        temp_code=self.verify()
        self.bind(temp_code)
        if type==cfg.MSG_TYPE_FRIEND:
          url=self.addr+'sendFriendMessage'
        else:
          url=self.addr+'sendGroupMessage'
        msg={'type':'Plain','text':content}
        if quote:
          form=json.dumps({
          'sessionKey':self.code, 
          'target':target,
          'messageChain':[msg],
           'quote':quote
        })
        else:
            form=json.dumps({
            'sessionKey':self.code, 
          'target':target,
          'messageChain':[msg],
            })
        return temp_code,myrequest(url,'post',form)['messageId']
    def fetchMessage(self):
        url=self.addr+'fetchMessage?sessionKey=%s&count=10'%(self.code)
        myrequest(url,'get')
def main_loop():
    global bot
    global UserDict
    bot=QQbot(1925281306)
    starttime=datetime.datetime.now()
    while 1:
        presenttime=datetime.datetime.now()
        if presenttime-starttime>datetime.timedelta(minutes=cfg.UPDATE_INTERVAL):
            starttime=presenttime
            notifyAllUser()
            bot.updateSession()
            UserDict.clear()
        try:
            unread_msg_count=bot.countMessage()
        except Exception as e:
            app.logger.error(str(e))
            unread_msg_count=0
        if unread_msg_count==0:
            time.sleep(1)
            continue
        parseMessage(bot.fetchLatestMessage())
        while replyQueue:
            replymsg=replyQueue.pop()
            makeReply(replymsg)

        
if __name__ == '__main__':
    app = Flask(__name__)
    sys.excepthook=global_exception_process
    cfg=config.config()
    replyQueue=deque()
    UserDict=defaultdict(list)
    logging.basicConfig(level=logging.DEBUG)
    handler=logging.FileHandler('app.log')
    handler.setLevel(logging.DEBUG)
    formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    test2()