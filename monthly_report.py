#!/usr/bin/python3
import sys, os
import argparse

import subprocess
from subprocess import Popen, PIPE

import logging
from logging.handlers import RotatingFileHandler

from datetime import date

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from shared import load_env
from shared import get_first_day
from shared import get_dates_for_sql
from shared import get_table
from shared import get_user_at_host
from shared import send_error

def get_records(today, vpn, month):
    start_date, end_date = get_dates_for_sql(today, month)
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
        raise Exception(e)
    return records

def get_summary(today, vpn, month):
    start_date, end_date = get_dates_for_sql(today, month)
    summary = ''
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
        raise Exception(e)
    return summary

def write_report(output, today, vpn, month):
    with open(output, 'w') as f:
        f.write('SUMMARY (order by name)\n')
        f.write(get_summary(today, vpn, month))
        f.write('\n')
        if is_full:
            f.write('FULL RECORDS (order by conn_since)\n')
            f.write(get_records(today, vpn, month))
        else:
            f.write('Notice: Use \'-f\' option to see full records.\n')
    logger.info('wrote ' + output)
    return

def send_mail(output, vpn, month):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = '[' + vpn.upper() + '] OpenVPN Usage Report'
        import platform
        msg['From'] = get_user_at_host()
        msg['To'] = vpn_info[vpn]['email']
        msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'
        body = MIMEText('See attached.')
        with open(output, 'r') as f:
            attachment = MIMEText(f.read())
        attachment.add_header('Content-Disposition', 
                              'attachment', 
                              filename=os.path.basename(output))
        msg.attach(body)
        msg.attach(attachment)
        with smtplib.SMTP(smtp_info['server']) as s:
            s.send_message(msg)
        logger.info('sent \"' + msg['Subject'] + '\" to ' + msg['To'])
    except Exception as e:
        logger.error('unable to send \"' + msg['Subject'] + '\" to ' + msg['To'])
        logger.error(e)
        raise Exception(e)
    return
    
def send_report(vpn, month):
    today = date.today()
    subject_date = get_first_day(today, month)
    output = base_dir + '/reports/' + vpn + '_' + subject_date + '.txt'
    write_report(output, today, vpn, month)
    send_mail(output, vpn, month)
    return

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
    
    # load env
    db_info, vpn_info, admin_info, smtp_info = load_env(base_dir + '/env.yaml')

    # parse arguments
    parser = argparse.ArgumentParser(description='send a monthly report')
    parser.add_argument('-s', nargs=1, required=True, 
                        choices=list(vpn_info.keys()), 
                        help='choose a vpn server')
    parser.add_argument('-m', nargs=1, choices=['this', 'prev'],
                        required=False, default='this', 
                        help='set month to issue a report')
    parser.add_argument('-f', action='store_true',
                        required=False, help='with full records')
    args = parser.parse_args()
    vpn = args.s[0]
    month = args.m[0]
    is_full = args.f

    # fetch records from db to send a report
    try:
        send_report(vpn, month)
    except Exception as e:
        subject = '[' + vpn.upper() + '] Error on ' + name
        send_error(smtp_info, subject, admin_info['email'], e, log_file)
