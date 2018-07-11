#!/usr/bin/python3
import sys, os
import argparse
import subprocess
from subprocess import Popen, PIPE
from datetime import date

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText    

import logging
from logging.handlers import RotatingFileHandler

from shared import load_env
from shared import get_first_day
from shared import get_dates_for_sql
from shared import get_table

def get_records(today, vpn, month):
    (start_date, end_date,) = get_dates_for_sql(today, month)
    sql = \
        "select name, extrn_ipport, intrn_ip, conn_since, " + \
        "last_refresh, rx_bytes, tx_bytes " + \
        "from " + get_table(vpn) + " where " + \
        "conn_since >= '" + start_date + "' and " + \
        "conn_since < '" + end_date + "' " + \
        "order by conn_since asc"
    try:
        logger.info(sql)
        records = subprocess.check_output(
            ['psql', db_info['dbname'], 
             '-h', db_info['host'], 
             '-U', db_info['user'], 
             '-c', sql], 
            universal_newlines=True
            )
    except Exception as e:
        logger.error('unable to get full records for ' + vpn)
        logger.error(e)
    return records

def get_summary(today, vpn, month):
    (start_date, end_date,) = get_dates_for_sql(today, month)
    sql = \
        "select name, count(name) as access, " + \
        "to_char(sum(rx_bytes)/1024/1024, '99,999.99\" MB\"') as rx, " + \
        "to_char(sum(tx_bytes)/1024/1024, '99,999.99\" MB\"') as tx " + \
        "from " + get_table(vpn) + " where " + \
        "conn_since >= '" + start_date + "' and " + \
        "conn_since < '" + end_date + "' " + \
        "group by name order by name asc"
    try:
        logger.info(sql)
        summary = subprocess.check_output(
            ['psql', db_info['dbname'], 
             '-h', db_info['host'], 
             '-U', db_info['user'], 
             '-c', sql], 
            universal_newlines=True
            )
    except Exception as e:
        logger.error('unable to get a summary for ' + vpn)
        logger.error(e)
    return summary

def write_report(output, today, vpn, month):
    with open(output, 'w') as f:
        f.write('SUMMARY (order by name)\n')
        f.write(get_summary(today, vpn, month))
        f.write('\n')
        f.write('FULL RECORDS (order by conn_since)\n')
        f.write(get_records(today, vpn, month))
    logger.info('wrote ' + output)

def send_mail(output, vpn, month):
    subject = '[' + vpn + '] OpenVPN Usage Report'
    recipients = vpn_info[vpn]['email']
    body = MIMEText('See attached.', 'plain')
    with open(output, 'r') as f:
        attachment = MIMEText(f.read(), 'plain')
    attachment.add_header('Content-Disposition', 
                          'attachment', 
                          filename=os.path.basename(output))
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['To'] = recipients
    msg.attach(body)
    msg.attach(attachment)
    try:
        p = Popen(['/usr/sbin/sendmail', '-t', '-oi'], 
                  stdin=PIPE, 
                  universal_newlines=True)
        p.communicate(msg.as_string())
        logger.info('sent \"' + subject + '\" to ' + recipients)
    except Exception as e:
        logger.error('unable to send \"' + subject + '\" to ' + recipients)
        logger.error(e)
    
def send_report(vpn, month):
    today = date.today()
    subject_date = get_first_day(today, month)
    output = base_dir + '/reports/' + vpn + '_' + subject_date + '.txt'
    write_report(output, today, vpn, month)
    send_mail(output, vpn, month)

if __name__ == '__main__':
    # load working dir and this script's name without its extension
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    # set logging up
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    log_file = base_dir + '/logs/' + name + '.log'
    handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # load db info and vpn server info
    db_info, vpn_info = load_env(base_dir + '/env.yaml')
    parser = argparse.ArgumentParser(description='send a monthly report')
    parser.add_argument('-s', nargs=1, required=True, 
                        choices=list(vpn_info.keys()), 
                        help='choose a vpn server')
    parser.add_argument('-m', nargs=1, choices=['this', 'prev'],
                        required=False, default='this', 
                        help='set month to issue a report')
    args = parser.parse_args()
    # fetch records from db to send a report
    send_report(vpn=args.s[0], month=args.m[0])
