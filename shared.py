#!/usr/bin/python3

def load_env(env_file):
    import yaml
    with open(env_file, 'r') as f:
        env = yaml.load(f)
        db_info = env.get('db', None)
        vpn_info = env.get('vpn', None)
    return db_info, vpn_info

def get_first_day(today, month="this"):
    from datetime import date
    first = today.replace(day=1)
    if month == "prev":
        try:
            first = first.replace(month=first.month-1)
        except ValueError:
            if first.month == 1:
                first = first.replace(month=12)
                first = first.replace(year=first.year-1)
    elif month == "next":
        try:
            first = first.replace(month=first.month+1)
        except ValueError:
            if first.month == 12:
                first = first.replace(month=1)
                first = first.replace(year=first.year+1)
    return date.strftime(first, "%Y-%m-%d")

def get_dates_for_sql(today, debug=False):
    if not debug:
        start_date = get_first_day(today, "prev")
        end_date = get_first_day(today, "this")
    else:
        start_date = get_first_day(today, "this")
        end_date = get_first_day(today, "next")
    return (start_date, end_date,)

def get_table(vpn):
    return vpn + '_log'