import asyncio
import aioschedule as schedule
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, Message, PhotoSize
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, DialogCalendar, DialogCalendarCallback, \
    get_user_locale
from config_data.config import Config, load_config
import sqlite3
from services.calendar import Work_calendar
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from apscheduler.triggers.combining import AndTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram.utils.markdown import hbold
from aiogram.filters.callback_data import CallbackData
config: Config = load_config()
BOT_TOKEN: str = config.tg_bot.token

# Создаем объекты бота и диспетчера
bot = Bot(BOT_TOKEN)
dp = Dispatcher()








# Создаем "базу данных" пользователей
user_dict: dict[int, dict[str, str | int | bool]] = {}

chat_id_dict = {}

# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодейтсвия с пользователем
    fill_shedule = State()        # пулл состояний для созданния расписания
    fill_time1 = State()         
    fill_time2 = State()      
    fill_start_date = State()   
    fill_extras_date = State()      # пулл состояний для добавления раб дней вне расписания
    fill_extras_time = State()
    fill_announcements = State()   # Состояние для получения уведомлений


# Этот хэндлер будет срабатывать на команду /start вне состояний
# и предлагать перейти к заполнению анкеты, отправив команду /fillform
@dp.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message):
    await message.answer(
        text='Это бот-календарь для барсука\n\n'
             'Чтобы внести дежурства введи /fillform'
    )
    


# Этот хэндлер будет срабатывать на команду "/cancel" в состоянии
# по умолчанию и сообщать, что эта команда работает внутри машины состояний
@dp.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    await message.answer(
        text='Режим оповещений и так выключен'
            
    )


# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Режим календаря был отключен'
             
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()


# перевод в режим добавления нового расписания
@dp.message(Command(commands='fillshedule'), StateFilter(default_state))
async def process_start_shedule_command(message: Message, state: FSMContext):
    await message.answer(text='enter shedule')
    # Устанавливаем состояние ожидания ввода типа расписания
    # Создаем объекты инлайн-кнопок
    common_button = InlineKeyboardButton(
        text='5/2 с началом в одно время',
        callback_data='common'
    )
    common_even_button = InlineKeyboardButton(
        text='5/2 с разными сменами',
        callback_data='common_even'
    )
    
    # Добавляем кнопки в клавиатуру (две в одном ряду и одну в другом)
    keyboard: list[list[InlineKeyboardButton]] = [
        [common_button, common_even_button],
        
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    # Отправляем пользователю сообщение с клавиатурой
    await message.answer(
        text='Выберитие ваш график',
        reply_markup=markup
    )
    await state.set_state(FSMFillForm.fill_shedule)


# ввод типа расписания, ДОДЕЛАТЬ КНОПКИ ВЫБОРА

@dp.callback_query(StateFilter(FSMFillForm.fill_shedule))
async def process_shedule_sent(callback: CallbackQuery, state: FSMContext):
    # сохраняем тип расписания
    await state.update_data(shedule=callback.data)
    await callback.message.answer(text='Тип записан, введите первое время начала')
    # Устанавливаем состояние ожидания ввода времени1
    await state.set_state(FSMFillForm.fill_time1)


# выбор времени1
@dp.message(StateFilter(FSMFillForm.fill_time1))
async def process_time1_sent(message: Message, state: FSMContext):
    # Cохраняем возраст в хранилище по ключу "month"
    await state.update_data(time1=message.text)
    
    await message.answer(
        text='Спасибо!\n\nУкажите второе время начала',
        )
   
    await state.set_state(FSMFillForm.fill_time2)

@dp.message(StateFilter(FSMFillForm.fill_time2))
async def process_time2_sent(message: Message, state: FSMContext):
    # Cохраняем возраст в хранилище по ключу "month"
    await state.update_data(time2=message.text)
    
    await message.answer(
        text='Спасибо!\n\nУкажите с какого дня построить расписание',
        )
   
    await state.set_state(FSMFillForm.fill_start_date)

# Этот хэндлер будет срабатывать на нажатие кнопки при
# выборе пола и переводить в состояние отправки фото
@dp.message(StateFilter(FSMFillForm.fill_start_date))
async def process_start_date_press(message: Message, state: FSMContext):
    # Cохраняем пол (callback.data нажатой кнопки) в хранилище,
    # по ключу "gender"
    await state.update_data(start_date=message.text)
    await message.answer(
        text='расписание добавлено, уведомления на следующий день включены'
    )
  
    user_dict[message.from_user.id] = await state.get_data()
    connection = sqlite3.connect('shedules.db')
    cursor = connection.cursor()
   
    cursor.execute(''' CREATE TABLE IF NOT EXISTS shedules(
        id INTEGER PRIMARY KEY,
        user_id ,
        shedule ,
        time1 ,
        time2 ,
        start_date,
        chat_id )''')
    cursor.execute('''INSERT INTO shedules (user_id, shedule, time1, time2, start_date, chat_id) VALUES (?,?,?,?,?,?)''',
       ( message.from_user.id,
     user_dict[message.from_user.id]['shedule'], user_dict[message.from_user.id]['time1'],
     user_dict[message.from_user.id]['time2'], user_dict[message.from_user.id]['start_date'], message.chat.id))
    cursor.execute(' SELECT * FROM shedules ')
    users=cursor.fetchall()
    for user in users:
        print(user)
    connection.commit()
    connection.close()
   
# перевод в режим добавления нового расписания
@dp.message(Command(commands='fillextras'), StateFilter(default_state))
async def process_start_extras_command(message: Message, state: FSMContext,):
    
   
    await message.answer(
        "Please select a date: ",
        reply_markup=await SimpleCalendar().start_calendar()
    )
    await state.set_state(FSMFillForm.fill_extras_date)
    


# ввод типа расписания, ДОДЕЛАТЬ КНОПКИ ВЫБОРА

@dp.callback_query(StateFilter(FSMFillForm.fill_extras_date))
async def process_extras_date_sent(callback: CallbackQuery, state: FSMContext):
    # сохраняем тип расписания
    raw_list = callback.data.split(':')
    if len(raw_list[3]) == 1:
        raw_list[3] = '0'+raw_list[3]
    if len(raw_list[4]) == 1:
        raw_list[3] = '0'+raw_list[3]
    formatted_date = raw_list[4] + '.' + raw_list[3] + '.' + raw_list[2]    
    await state.update_data(extras_date=formatted_date)
    await callback.message.delete()
    await callback.message.answer(
        text='Спасибо! А теперь enter time '
             
    )
    # Устанавливаем состояние ожидания ввода времени1
    await state.set_state(FSMFillForm.fill_extras_time)


# выбор времени1
@dp.message(StateFilter(FSMFillForm.fill_extras_time))
async def process_extras_time_sent(message: Message, state: FSMContext):
    # Cохраняем возраст в хранилище по ключу "month"
    await state.update_data(extras_time=message.text)
    
    await message.answer(
        text='time saved',
        )
   
    user_dict[message.from_user.id] = await state.get_data()
    connection = sqlite3.connect('shedules.db')
    cursor = connection.cursor()
    cursor.execute(''' CREATE TABLE IF NOT EXISTS extras(
        id INTEGER PRIMARY KEY,
        user_id ,
        date ,
        time ,
        chat_id  )''')
    cursor.execute('''INSERT INTO extras (user_id, date, time, chat_id) VALUES (?,?,?,?)''', (
        message.from_user.id,
        user_dict[message.from_user.id]['extras_date'], user_dict[message.from_user.id]['extras_time'],
        message.chat.id))
    cursor.execute(' SELECT * FROM extras ')
    users = cursor.fetchall()
    for user in users:
        print(user)
    connection.commit()
    connection.close()


async def job_responce(i):
    
        connection = sqlite3.connect('shedules.db')
        cursor = connection.cursor()
        cursor.execute(' SELECT * FROM shedules WHERE chat_id = (?)', (i))
        res=cursor.fetchall()
        #y=res[0][1]
        #x=(res,)
        #print(x)
        cursor.execute('SELECT date, time FROM extras WHERE chat_id = (?)', ((res[0][1],)))
        extras_list=cursor.fetchall()
        extras={}
        for j in extras_list:
            extras[j[0]]=j[1]
        print(extras)
        user_id=res[0][1]
        shedule=res[0][2]
        time1=res[0][3]
        time2=res[0][4]
        start_date=res[0][5]
        connection.close()
        present_day = datetime.today()
        tomorrow = present_day + timedelta(1)
        tomorrow_day=tomorrow.strftime('%d.%m.%Y')
        kid=Work_calendar(user_id,shedule,extras,time1,time2,start_date)
        answer=kid.do_work(tomorrow_day)
        await bot.send_message(chat_id=i[0], text=answer)


async def job():
    connection = sqlite3.connect('shedules.db')
    cursor = connection.cursor()
    cursor.execute(' SELECT chat_id FROM shedules')
    schedules_info = cursor.fetchall()
    print(schedules_info)
    tasks = [job_responce(i) for i in schedules_info]
    await asyncio.gather(*tasks)
    
    



    


# Этот хэндлер будет срабатывать на любые сообщения, кроме тех
# для которых есть отдельные хэндлеры, вне состояний
@dp.message(StateFilter(default_state))
async def send_echo(message: Message):
    await message.reply(text='Извините, моя твоя не понимать')

def tick():
    print('Tick! The time is: %s' % datetime.now())


async def shedule():
    scheduler = AsyncIOScheduler()
    # moscow -3
    #trigger = CronTrigger(hour=19)
    scheduler.add_job(job, 'interval', seconds=5)
    scheduler.start()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    while True:
        
        await asyncio.sleep(1000)




    
    
    
    
        

if __name__ == '__main__':
    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    loop = asyncio.get_event_loop()
    try:
        
        loop.create_task(dp.start_polling(bot))
        loop.create_task(shedule())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:    
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
    
    loop.stop()
    loop.close()           
















