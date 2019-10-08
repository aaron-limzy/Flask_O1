# # from PIL import Image
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#from json2html import *
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
# import ctypes
import datetime
import json
# #import MySQLdb  # Need to install with the whl file....
import os
import random
import re
import smtplib
import subprocess
import ctypes
import time
import telegram #pip install python-telegram-bot==12.0.0b1 --upgradepymysql

import pymysql

SQL_IP = "192.168.64.73"
SQL_User = "mt4"
SQL_Password = "1qaz2wsx"
SQL_Database = "aaron"
SQL_Table = "bloomberg_dividend"

Email_Header = "<style>p.a {font-family:Calibri;panose-1:2 15 5 2 2 2 4 3 2 4;font-size: 14.5px;}</style><p Class='a'>"
Email_Footer = "</p>"

# Telegram
ID = "486797751"


# # token = "736426328:AAH90fQZfcovGB8iP617yOslnql5dFyu-M0"		# For Mismatch and LP Margin
# # token = "776609726:AAHVrhEffiJ4yWTn1nw0ZBcYttkyY0tuN0s"        # For USDTWF



def Send_Email(To_recipients, cc_recipients, Subject, HTML_Text, Attachment_Name):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()  # Hello to SMTP server
    server.starttls()  # Need to start the TLS connection
    server.login("aaron.riskbgi@gmail.com", "ReportReport")  # Login with credientials

    me = "aaron.riskbgi@gmail.com"
    you = To_recipients
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    # Bcc_recipients = ["aaron.lim@blackwellglobal.com"]

    msg['Subject'] = Subject
    msg['From'] = me
    msg['To'] = ",".join(To_recipients)
    msg['cc'] = ",".join(cc_recipients)
    # msg['Bcc'] = ",".join(Bcc_recipients)  # Have to add this function at a later date...

    for i in range(len(Attachment_Name)):
        Buffer = Attachment_Name[i].split('/')
        filename = Buffer[len(Buffer) - 1]
        attachment = open(Attachment_Name[i], "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        # Only Want to add the part of the name where it is the excel name.
        part.add_header('Content-Disposition',
                        "attachment; filename= " + filename.split("\\")[len(filename.split("\\")) - 1])
        msg.attach(part)

    p = MIMEText(HTML_Text, 'html')
    msg.attach(p)
    server.sendmail(me, To_recipients + cc_recipients, msg.as_string())
    # server.sendmail(me, To_recipients + Bcc_recipients + cc_recipients, msg.as_string())


def Get_time_String():
    now = datetime.now()
    return now.strftime("%Y-%b-%d_%H-%M-%S")

    # return str(now.year) + "-" + str(now.month) + "-" + str(now.day) + "_" + str(now.hour) + "-" + str(
    #    now.minute) + "-" + str(now.second)


def Get_time_String_Simple():
    now = datetime.now()
    return now.strftime("%Y-%b-%d %H:00")
#
#
# def Call_Alert():
#     ctypes.windll.user32.MessageBoxW(0, "Full PnL Picture Missing", "Picture Missing", 1)
#

# Array to HTML Table.
def Array_To_HTML_Table(Table_Header, Table_Data,  Highlight_words = []):
    # HTML_Table_Header = "<table border = \"1\" cellpadding = \"4\" bordercolor = \"Black\" style=\"text-align:center;\"  >"
    HTML_Table_Header = "<table border = \"2\" cellpadding = \"4\" bordercolor = \"Black\" style=\"text-align:center;\"  >"
    HTML_Table_Code = HTML_Table_Header
    Header_Count = len(Table_Header)

    # Add the Table Header.
    HTML_Table_Code = HTML_Table_Code + " <tr bgcolor=\"#BBC7FF\"> "
    # HTML_Table_Code = HTML_Table_Code + " <tr bgcolor=\"#0052cc\">  "
    for i in range(Header_Count):
        # HTML_Table_Code = HTML_Table_Code + " <th><FONT COLOR=white>" + Table_Header[i] +"</FONT></th>"
        HTML_Table_Code = HTML_Table_Code + " <th>" + Table_Header[i] + "</th>"
    HTML_Table_Code = HTML_Table_Code + " </tr> "

    # Add the Table Data.
    for i in range(len(Table_Data)):
        HTML_Table_Code = HTML_Table_Code + " <tr> "
        for j in range(len(Table_Data[i])):
            if any([Table_Data[i][j].find(w) >= 0 for w in Highlight_words]):   # If there are any words to be highlighted.
                HTML_Table_Code = HTML_Table_Code + " <td bgcolor=#ff9999>" + str(Table_Data[i][j]) + "</td>"
            else:
                HTML_Table_Code = HTML_Table_Code + " <td>" + str(Table_Data[i][j]) + "</td>"


        HTML_Table_Code = HTML_Table_Code + " </tr> "
    HTML_Table_Code = HTML_Table_Code + "</table>"
    return HTML_Table_Code



# A list of Dictionary to HTML Table.
# Word List to turn the cell red should it be needed.
# [{},{},{}]
def List_of_Dict_To_Horizontal_HTML_Table(Data_Dict_List, Word_List=[]):

    if len(Data_Dict_List) == 0:    # Nothing here.
        return ""

    Table_Header = list(Data_Dict_List[0].keys())
    Table_Data = [list(d.values()) for d in Data_Dict_List]

    # HTML_Table_Header = "<table border = \"1\" cellpadding = \"4\" bordercolor = \"Black\" style=\"text-align:center;\"  >"
    HTML_Table_Header = "<table border = \"2\" cellpadding = \"4\" bordercolor = \"Black\" style=\"text-align:center;\"  >"
    HTML_Table_Code = HTML_Table_Header

    # Add the Table Header.
    # Header Label.
    HTML_Table_Code +=  " <tr bgcolor=\"#BBC7FF\"> " + " ".join(["<th>{}</th>".format(th) for th in Table_Header])  + "</tr>"


    # Add the Table Data.
    for i in range(len(Table_Data)):
        HTML_Table_Code = HTML_Table_Code + " <tr> "
        for j in range(len(Table_Data[i])):
            if isinstance(Table_Data[i][j], dict):  # Calling recursively
                HTML_Table_Code += " <td>" + Dict_To_Vertical_HTML_Table(Table_Data[i][j]) + "</td>"
            else:
                # Want to turn the cell red if there are any alert words found.
                HTML_Table_Code += "<td bgcolor=\"#ff8080\">" if any([Table_Data[i][j].find(a) >= 0 for a in Word_List]) else "<td>"
                HTML_Table_Code +=  str(Table_Data[i][j]) + "</td>"


        HTML_Table_Code = HTML_Table_Code + " </tr> "



    HTML_Table_Code = HTML_Table_Code + "</table>"
    return HTML_Table_Code



# Dictionary to vertical HTML Table.
# {}
def Dict_To_Vertical_HTML_Table(Data_Dict_List):

    if len(Data_Dict_List) == 0:    # Nothing here.
        return ""

    # HTML_Table_Header = "<table border = \"1\" cellpadding = \"4\" bordercolor = \"Black\" style=\"text-align:center;\"  >"
    HTML_Table_Header = "<table border = \"1\" cellpadding = \"3\" bordercolor = \"Grey\" style=\"text-align:center; border-collapse: collapse;\"  >"
    HTML_Table_Code = HTML_Table_Header

    for k,d in Data_Dict_List.items():
        HTML_Table_Code += " <tr> <th bgcolor=\"#ffcc80\">{k}</th><td>{d}</td></tr>".format(k=k, d=d)

    HTML_Table_Code = HTML_Table_Code + "</table>"
    return HTML_Table_Code



# # Query SQL and return the results in an array.
# # [Results Data, Column Data]
# # Uses pymysql instead
def Query_SQL(SQL_Query):

    connection = pymysql.connect(host=SQL_IP, user=SQL_User, passwd=SQL_Password, db=SQL_Database)
    connection.autocommit = True        # Set it to always commit.
    Cursor = connection.cursor()
    #SQL_Query = "Select * from aaron.bloomberg_dividend WHERE `date` >= NOW() AND WEEKDAY(`date`) BETWEEN 0 AND 4 ORDER BY date "
    #SQL_Query = "Select * from aaron.bloomberg_dividend WHERE `date` >= NOW() AND WEEKDAY(`date`) BETWEEN 0 AND 4 and `date`='2018-10-12'  ORDER BY date"
    Cursor.execute(SQL_Query)
    results = Cursor.fetchall()     # Is in Tuple
    Column_Details = Cursor.description # To get the column details, with length and etc...
    Cursor.close() # Close the Cursor.
    connection.close()

    return [tuple_to_array(results),tuple_to_array(Column_Details)]


# Write a Tuple to be an array
def tuple_to_array(Tuple_t):
    Return_array = []
    for t in Tuple_t:
        Return_Array_Buffer = []
        for tt in t:
            Return_Array_Buffer.append(tt)
        Return_array.append(Return_Array_Buffer)
    return Return_array


# Check if element is a float string. if it is, return true, else, false
def Check_Float(element):
    try:
        float(element)
        return True
    except ValueError:
        #print("Not a float")
        return False


# To run C Programs
def Run_C_Prog(Path):
    p = subprocess.Popen(Path, stdout=subprocess.PIPE)
    (output, err) = p.communicate()  # Want to capture the COUT
    C_Return_Val = ctypes.c_int32(p.returncode).value   # Convert to -ve/+ve.
    return (C_Return_Val, output, err)

# #Post_To_Telegram("708830467:AAHq9GVujNqPhvAKiXhMhqW_Qsl9ObdYiY4", "Test: Hello World.", ["486797751"])
def Post_To_Telegram(Bot_token, text_to_tele, Chat_IDs):
    #URL = "https://api.telegram.org/bot" + Bot_token + "/"
    #https://api.telegram.org/bot708830467:AAHq9GVujNqPhvAKiXhMhqW_Qsl9ObdYiY4/getUpdates
    bot = telegram.Bot(token=Bot_token)
    for c_id in Chat_IDs:
        bot.sendMessage(chat_id=c_id, text=text_to_tele, parse_mode=telegram.ParseMode.MARKDOWN)
#Chat_IDs=[486797751]
#Bot_token = "708830467:AAHq9GVujNqPhvAKiXhMhqW_Qsl9ObdYiY4"