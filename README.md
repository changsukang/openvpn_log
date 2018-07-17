# Introduction
This crawls status from OpenVPN community version, parse and store the information in a PostgreSQL server. It's because the community version provides only volatile status, not detailed logs such as how long a user connected from when to when.

# Environments
This is developed under these environments:
* OpenVPN 2.4.4 
* Python 3.6.5
* PostgreSQL 9.2.24 

# How to use

## OpenVPN
Your openvpn config should include management port like below:
```
management openvpn_server_ip management_port
```
The management port is different from an openvpn service port set like below:
```
port service_port
```

[Management Interface](https://openvpn.net/index.php/open-source/documentation/miscellaneous/79-management-interface.html) - OpenVPN Management Interface Notes

## Python3
Because this uses PostgreSQL to store information, python3 on your system should have "psycopg2." For more detailed information on how to install it, you can check here:

[psycopg2](http://initd.org/psycopg/docs/install.html) - How to install psycopg2

## PostgreSQL
It is beyond scope of this document to explain how to install PostgreSQL. Please make it sure that your system to run these scripts should have 'psql' command because it is used to format a monthly report.

## env.yaml
Please copy env.yaml.example to env.yaml, and edit it. 

```
db:
  host: your.db.net
  dbname: openvpn_log
  user: openvpn
  password: openvpn
```
'db' section is to set up PostgreSQL info. 

```
vpn:
  your_vpn_1:
    host: your.vpn.net
    port: 2194
    email: your@email.net, her@email.net
  your_vpn_2:
    host: 192.168.0.1
    port: 2194
    email: your@email.net, his@email.net
```
'vpn' is to define your openvpns. If you have multiple openvpns, you can define them all here with unique keywords such as 'your_vpn_1' and 'your_vpn_2.' 'host' can have a hostname or an ip address. Please remember 'port' in this section means MANAGEMENT PORT described above. 'email' is a list with a comma to send monthly reports. 

```
admin:
  email: admin@email.net
```
'admin' is to send any error reports.

```
smtp:
  server: your_smtp
  port: 25 # the standard smtp port
  user: your_name
  password: your_password
```
'smtp' is to define a smtp server to use send any emails. If nothing sets, localhost with port 25 and without any authentication is used as default. Unfortunately, SSL/TLS are not supported yet.

## run.sh

## send.sh

## crontab

