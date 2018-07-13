#!/usr/bin/python3
import sys, os
import argparse
import psycopg2
import socket

import logging
from logging.handlers import RotatingFileHandler

from shared import get_table
from shared import load_env
from shared import send_error

socket_buffer = 512
socket_timeout = 10.0

def insert_record(cur, table, name, info):
    sql = \
        "insert into " + table + " (" + \
        "name, " + \
        "extrn_ipport, " + \
        "intrn_ip, " + \
        "conn_since, " + \
        "last_refresh, " + \
        "rx_bytes, " + \
        "tx_bytes " + \
        ") values ('" + \
        name + "', '" + \
        info['extrn_ipport'] + "', '" + \
        info['intrn_ip'] + "', '" + \
        info['conn_since'] + "', '" + \
        info['last_refresh'] + "', " + \
        info['rx_bytes'] + ", " + \
        info['tx_bytes'] + " )"
    logger.info(sql)
    cur.execute(sql)

def update_record(cur, table, name, info):
    sql = \
        "update " + table + " " + \
        "set " + \
        "last_refresh = '" + info['last_refresh'] + "', " + \
        "rx_bytes = " + info['rx_bytes'] + ", " + \
        "tx_bytes = " + info['rx_bytes'] + " " + \
        "where " + \
        "name = '" + name + "' and " + \
        "extrn_ipport = '" + info['extrn_ipport'] + "' and " + \
        "conn_since = '" + info['conn_since'] + "'"
    logger.info(sql)
    cur.execute(sql)

def is_record(cur, table, name, info):
    sql = \
        "select count(*) from " + table + " where " + \
        "name = '" + name + "' and " + \
        "extrn_ipport = '" + info['extrn_ipport'] + "' and " + \
        "conn_since = '" + info['conn_since'] + "'"
    logger.info(sql)
    cur.execute(sql)
    return True if cur.fetchone()[0] > 0 else False

def store_to_db(refined, table):
    try:
        with psycopg2.connect(
            "host=" + db_info['host'] + " " +
            "dbname=" + db_info['dbname'] + " " +
            "user=" + db_info['user'] + " " +
            "password=" + db_info['password']
            ) as conn:
            cur = conn.cursor()
            for name, info in refined.items():
                if name == 'UNDEF': 
                    logger.warning('unauthorized access: ' + name + ' ' + str(info))
                    continue
                if not info.get('intrn_ip'):
                    logger.warning('no internal IP: ' + name + ' ' + str(info))
                    continue
                if is_record(cur, table, name, info):
                    update_record(cur, table, name, info)
                else: 
                    insert_record(cur, table, name, info)
            cur.close()
            conn.commit()
    except Exception as e:
        logger.error('unable to store data:\n' + str(refined))
        logger.error(e)
        raise Exception(e)
    return

def get_conn_since(line, refined):
    info = line.split(',')
    if len(info) == 5:
        name = info[0]
        user = refined.get(name, {})
        user['extrn_ipport'] = info[1]
        user['rx_bytes'] = info[2]
        user['tx_bytes'] = info[3]
        user['conn_since'] = info[4]
    else: # to support Common Name (CN) complying to the RFC 2253
        name = info[0] + ',' + info[1]
        user = refined.get(name, {})
        user['extrn_ipport'] = info[2]
        user['rx_bytes'] = info[3]
        user['tx_bytes'] = info[4]
        user['conn_since'] = info[5]
    return name, user

def get_last_ref(line, refined):
    info = line.split(',')
    if len(info) == 4:
        name = info[1]
        user = refined[name]
        user['intrn_ip'] = info[0]
        user['last_refresh'] = info[3]
    else: # to support Common Name (CN) complying to the RFC 2253
        name = info[1] + ',' + info[2]
        user = refined[name]
        user['intrn_ip'] = info[0]
        user['last_refresh'] = info[4]
    return name, user

def refine(status):
    try:
        refined = {}
        is_connected_since = False
        is_last_ref = False
        for line in status.splitlines():
            if 'Connected Since' in line: 
                is_connected_since = True
            elif 'ROUTING TABLE' in line: 
                is_connected_since = False
            elif 'Last Ref' in line: 
                is_last_ref = True
            elif 'GLOBAL STATS' in line: 
                is_last_ref = False
            else:
                if is_connected_since:
                    name, user = get_conn_since(line, refined)
                    refined[name] = user
                if is_last_ref: 
                    name, user = get_last_ref(line, refined)
                    refined[name] = user
    except Exception as e:
        logger.error('unable to process data:\n' + status)
        logger.error(e)
        raise Exception(e)
    return refined

def recv_all(s):
    '''To get long status via a socket'''
    status = b''
    while True:
        received = s.recv(socket_buffer)
        status += received
        if received == b'':
            logger.debug('no data received via socket')
        if b'\r\nEND\r\n' in received:
            break
    return status
        
def crawl_status(vpn):
    status = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(socket_timeout)
            s.connect((vpn_info[vpn]['host'], vpn_info[vpn]['port']))
            status = s.recv(socket_buffer).decode('utf-8') # introduction message
            s.sendall(b'status\n')
            status = recv_all(s).decode('utf-8')
    except Exception as e:
        logger.error('unable to get status from ' + vpn)
        logger.error(e)
        raise Exception(e)
    return status

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
    db_info, vpn_info, admin_info = load_env(base_dir + '/env.yaml')

    # pase arguments to select which vpn to access
    parser = argparse.ArgumentParser(description='parse logs to store')
    parser.add_argument('-s', nargs=1, required=True, 
                        choices=list(vpn_info.keys()),
                        help='choose a vpn server')
    args = parser.parse_args()
    vpn = args.s[0]

    # crawl, parse and store
    try:
        status = crawl_status(vpn)
        refined = refine(status)
        table = get_table(vpn)
        store_to_db(refined, table)
    except Exception as e:
        subject = '[' + vpn.upper() + '] Error on ' + name
        send_error(subject, admin_info['email'], e, log_file)
