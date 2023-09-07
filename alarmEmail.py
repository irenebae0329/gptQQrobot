import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import config 

cfg=config()


def sendAlarmEmail(content):
   msg=MIMEMultipart()
   msg.attach(MIMEText(content,'plain','utf-8'))
   msg['Subject']=cfg.QQ_MAIL_SUBJECT
   msg['From']=cfg.QQ_MAIL_ADDR
   password = cfg.QQ_MAIL_VERIFY_CODE #16位授权码
   smtp = smtplib.SMTP_SSL(cfg.QQ_MAIL_SERVER,cfg.QQ_MAIL_SERVER_PORT)
   smtp.login(cfg.QQ_MAIL_ADDR,password)
   smtp.sendmail(cfg.QQ_MAIL_ADDR,cfg.QQ_MAIL_ADDR,msg.as_string())