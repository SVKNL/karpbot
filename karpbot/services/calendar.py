from datetime import timedelta, datetime, date
import requests

class Work_calendar:
    year = datetime.today().strftime('%Y-%m-%d %H:%M:%S')[0:4]
    link = f'https://production-calendar.ru/get/ru/{year}/json'
    # list of dicts for each day of current year
    # date as 'd.m.y'
    prod_cal = requests.get(link).json()['days']
    shedules = ['common', 'double_day', 'double_day_night', 'double_night', 'triple', 'common_even']
    
    def __init__(self, user_id: int, shedule: str, extras: list, time1, time2, start_date):
        self.user_id = user_id
        self.shedule = shedule
        self.extras = extras
        self.time1 = time1
        self.time2 = time2
        self.start_date = start_date

    def do_work(self, my_date: str):
        # in case shedule = common
        if self.shedule == 'common_even':
            for i in self.prod_cal:
                if i['date'] == my_date:
                    code = i['type_id']
            if code == 2 or code == 3 or code == 6:
                holiday = True
            else:
                holiday = False
            for i in self.extras:
                if i['date'] == my_date:
                    holiday = False
            if holiday == True:
                return 'free'
            else:
                if int(my_date[0:2]) % 2 == 0:
                    return self.time1
                else:
                    return self.time2
        else:
            return 'lol'            

    

    
    
present_day = datetime.today().strftime('%d.%m.%Y')    




present_day = datetime.today()
tomorrow = present_day + timedelta(1)
tomorrow.strftime('%Y-%m-%d %H:%M:%S')[8:10]


