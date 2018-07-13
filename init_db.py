#!/usr/bin/python3
import sys, os
import logging
from logging.handlers import RotatingFileHandler

import psycopg2

from shared import load_env
from shared import get_table

def create_index(cur, table):
    sql = 'create index on ' + table + ' (name)'
    logger.info(sql)
    cur.execute(sql)
    sql = 'create index on ' + table + ' (conn_since)'
    logger.info(sql)
    cur.execute(sql)

def create_table(cur, table):
    # IPv6 addresses can have 39 characters at most.
    # A port number can have 5 digits: '65535'
    # IPv6 with port is formatted like this: '[IPv6]:port'
    # Therefore, 1+39+1+1+5=47 at most
    sql = \
        'create table if not exists ' + table + ' (' + \
        'name varchar(256) not null, ' + \
        'extrn_ipport varchar(47) not null, ' + \
        'intrn_ip varchar(39) not null, ' + \
        'conn_since timestamp with time zone not null, ' + \
        'last_refresh timestamp with time zone not null, ' + \
        'rx_bytes bigint not null, ' + \
        'tx_bytes bigint not null, ' + \
        'primary key(name, extrn_ipport, conn_since))'
    logger.info(sql)
    cur.execute(sql)

def init_db():
    conn = psycopg2.connect(
        'host=' + db_info['host'] + ' ' +
        'dbname=' + db_info['dbname'] + ' ' +
        'user=' + db_info['user'] + ' ' +
        'password=' + db_info['password']
        )
    cur = conn.cursor()
    for server in list(vpn_info.keys()):
        create_table(cur, get_table(server))
        create_index(cur, get_table(server))
    cur.close()
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # load working dir and this script's name without its extension
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    # set logging up
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    log_file = base_dir + '/logs/' + name + '.log'
    # no rollover
    handler = RotatingFileHandler(log_file, maxBytes=0, backupCount=0) 
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # load db info and vpn server info
    db_info, vpn_info = load_env(base_dir + '/env.yaml')
    # generate tables unless exist
    init_db()
