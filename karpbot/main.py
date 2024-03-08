import asyncio
import aioschedule as schedule
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from config_data.config import Config, load_config
import sqlite3
from services.calendar import Work_calendar
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
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
    await state.set_state(FSMFillForm.fill_shedule)


# ввод типа расписания, ДОДЕЛАТЬ КНОПКИ ВЫБОРА

@dp.message(StateFilter(FSMFillForm.fill_shedule))
async def process_shedule_sent(message: Message, state: FSMContext):
    # сохраняем тип расписания
    await state.update_data(shedule=message.text)
    await message.answer(text='Тип записан')
    # Устанавливаем состояние ожидания ввода времени1
    await state.set_state(FSMFillForm.fill_time1)


# выбор времени1
@dp.message(StateFilter(FSMFillForm.fill_time1))
async def process_time1_sent(message: Message, state: FSMContext):
    # Cохраняем возраст в хранилище по ключу "month"
    await state.update_data(time1=message.text)
    
    await message.answer(
        text='Спасибо!\n\nУкажите время',
        )
   
    await state.set_state(FSMFillForm.fill_time2)

@dp.message(StateFilter(FSMFillForm.fill_time2))
async def process_time2_sent(message: Message, state: FSMContext):
    # Cохраняем возраст в хранилище по ключу "month"
    await state.update_data(time2=message.text)
    
    await message.answer(
        text='Спасибо!\n\nУкажите время',
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
        text='added work'
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
async def process_start_extras_command(message: Message, state: FSMContext):
    await message.answer(text='enter extras')
    # Устанавливаем состояние ожидания ввода типа расписания
    await state.set_state(FSMFillForm.fill_extras_date)


# ввод типа расписания, ДОДЕЛАТЬ КНОПКИ ВЫБОРА

@dp.message(StateFilter(FSMFillForm.fill_extras_date))
async def process_extras_date_sent(message: Message, state: FSMContext):
    # сохраняем тип расписания
    await state.update_data(extras_date=message.text)
    await message.answer(text='date saved, enter time')
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



async def job():
    connection = sqlite3.connect('shedules.db')
    cursor = connection.cursor()
    cursor.execute(' SELECT chat_id FROM shedules')
    schedules_info=cursor.fetchall()
    for i in schedules_info:
        cursor.execute(' SELECT * FROM shedules WHERE chat_id = (?)', (i))
        res=cursor.fetchall()
        cursor.execute('SELECT date, time FROM extras WHERE user_id = (?)', (res[0][1]))
        user_id=res[0][1]
        shedule=res[0][2]
        time1=res[0][3]
        time2=res[0][4]
        start_date=res[0][5]
        connection.close()
        present_day = datetime.today()
        tomorrow = present_day + timedelta(1)
        tomorrow_day=tomorrow.strftime('%d.%m.%Y')
        kid=Work_calendar(user_id,shedule,[],time1,time2,start_date)
        answer=kid.do_work(tomorrow_day)
        await bot.send_message(chat_id=i[0], text=answer)
    



    


# Этот хэндлер будет срабатывать на любые сообщения, кроме тех
# для которых есть отдельные хэндлеры, вне состояний
@dp.message(StateFilter(default_state))
async def send_echo(message: Message):
    await message.reply(text='Извините, моя твоя не понимать')

def tick():
    print('Tick! The time is: %s' % datetime.now())


async def shedule():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job, 'interval', seconds=200)
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
















