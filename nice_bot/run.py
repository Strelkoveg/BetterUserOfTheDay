import logging
import random
import datetime
import time
import messages
import stickers
import peewee
from os import getenv
from db_init import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def create_user(chat_id, user_id):
    dbhandle.connect()
    is_user_in_chat = False
    for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == user_id)):
        is_user_in_chat = True
    if is_user_in_chat:
        dbhandle.close()
        return False
    Members.create(chat_id=chat_id, member_id=user_id)
    stats_of_user = 0
    pidor_stats_of_user = 0
    for k in Stats.select().where((Stats.chat_id == chat_id) & (Stats.member_id == user_id)):
        stats_of_user = k.count
    for p in PidorStats.select().where((PidorStats.chat_id == chat_id) & (PidorStats.member_id == user_id)):
        pidor_stats_of_user = p.count
    if (stats_of_user == 0) and (pidor_stats_of_user == 0):
        query = PidorStats.delete().where((PidorStats.chat_id == chat_id) & (PidorStats.member_id == user_id))
        query.execute()
        query = Stats.delete().where((Stats.chat_id == chat_id) & (Stats.member_id == user_id))
        query.execute()
        Stats.create(chat_id=chat_id, member_id=user_id, count=0)
        PidorStats.create(chat_id=chat_id, member_id=user_id, count=0)
    is_current_pidor_exists_for_chat = False
    is_current_nice_exists_for_chat = False
    for b in CurrentPidor.select().where(CurrentPidor.chat_id == chat_id):
        is_current_pidor_exists_for_chat = True
    for u in CurrentNice.select().where(CurrentNice.chat_id == chat_id):
        is_current_nice_exists_for_chat = True
    if (is_current_nice_exists_for_chat and is_current_pidor_exists_for_chat) is False:
        CurrentNice.create(chat_id=chat_id, member_id=0, timestamp=0)
        CurrentPidor.create(chat_id=chat_id, member_id=0, timestamp=0)
    dbhandle.close()
    return True


def unreg_in_data(chat_id, user_id):
    dbhandle.connect()
    query = Members.delete().where((Members.chat_id == chat_id) & (Members.member_id == user_id))
    deleted_rows = query.execute()
    dbhandle.close()
    if deleted_rows == 0:
        return 'Пользователь не найден'
    else:
        return 'deleted'


def get_random_id(chat_id, pidor_or_nice):
    dbhandle.connect()
    members = []
    for l in Members.select().where(Members.chat_id == chat_id):
        members.append(l.member_id)
    dbhandle.close()
    if pidor_or_nice == 'pidor':
        if is_not_time_expired(chat_id, 'current_nice'):
            immune_id = get_current_user(chat_id, 'current_nice')['id']
            members.remove(immune_id)
    if pidor_or_nice == 'nice':
        if is_not_time_expired(chat_id, 'current_pidor'):
            immune_id = get_current_user(chat_id, 'current_pidor')['id']
            members.remove(immune_id)
    if members == []:
        return 'Nothing'
    return random.choice(members)


def update_pidor_stats(chat_id, pidor_id, stats_type):
    dbhandle.connect()
    current_stat = 0
    if stats_type == 'stats':
        for l in Stats.select().where((Stats.chat_id == chat_id) & (Stats.member_id == pidor_id)):
            current_stat = l.count
    if stats_type == 'pidor_stats':
        for p in PidorStats.select().where((PidorStats.chat_id == chat_id) & (PidorStats.member_id == pidor_id)):
            current_stat = p.count
    new_stat = current_stat + 1
    if stats_type == 'stats':
        query = Stats.update(count=new_stat).where((Stats.chat_id == chat_id) &
                                                   (Stats.member_id == pidor_id))
        query.execute()
    if stats_type == 'pidor_stats':
        query = PidorStats.update(count=new_stat).where((PidorStats.chat_id == chat_id) &
                                                        (PidorStats.member_id == pidor_id))
        query.execute()
    dbhandle.close()
    return new_stat


def get_pidor_stats(chat_id, stats_type):
    dbhandle.connect()
    stats = {}
    if stats_type == 'stats':
        for p in Stats.select().where(Stats.chat_id == chat_id):
            stats[p.member_id] = p.count
    if stats_type == 'pidor_stats':
        for f in PidorStats.select().where(PidorStats.chat_id == chat_id):
            stats[f.member_id] = f.count
    dbhandle.close()
    if stats == {}:
        return 'Ни один пользователь не зарегистрирован, статистики нет'
    else:
        return stats


def get_all_members(chat_id):
    members = []
    dbhandle.connect()
    for i in Members.select(Members.member_id).where(Members.chat_id == chat_id):
        members.append(i.member_id)
    dbhandle.close()
    return members


def get_user_percentage_nice_pidor(chat_id, member_id):
    nice = 0
    dbhandle.connect()
    for i in Stats.select().where((Stats.chat_id == chat_id) & (Stats.member_id == member_id)):
        nice = i.count
    pidor = 0
    for o in PidorStats.select().where((PidorStats.chat_id == chat_id) & (PidorStats.member_id == member_id)):
        pidor = o.count
    dbhandle.close()
    all_count = pidor + nice
    if pidor == 0 and nice != 0:
        pidor_percent = 0
        nice_percent = 100
    if nice == 0 and pidor != 0:
        pidor_percent = 100
        nice_percent = 0
    if pidor == 0 and nice == 0:
        pidor_percent = 50
        nice_percent = 50
    else:
        pidor_percent = int((pidor / all_count) * 100)
        nice_percent = 100 - pidor_percent
    return {'member_id': member_id, 'nice': nice_percent, 'pidor': pidor_percent}


def reset_stats_data(chat_id):
    dbhandle.connect()
    Stats.update(count=0).where(Stats.chat_id == chat_id).execute()
    PidorStats.update(count=0).where(PidorStats.chat_id == chat_id).execute()
    members_in_game = []
    members_in_stats = []
    members_in_pidorstats = []
    for p in Members.select().where(Members.chat_id == chat_id):
        members_in_game.append(p.member_id)
    for k in Stats.select().where(Stats.chat_id == chat_id):
        members_in_stats.append(k.member_id)
    for f in PidorStats.select().where(PidorStats.chat_id == chat_id):
        members_in_pidorstats.append(f.member_id)
    for s in members_in_stats:
        if (s in members_in_game) is False:
            stats_query = Stats.delete().where((Stats.chat_id == chat_id) & (Stats.member_id == s))
            stats_query.execute()
    for s in members_in_pidorstats:
        if (s in members_in_game) is False:
            p_query = PidorStats.delete().where((PidorStats.chat_id == chat_id) & (PidorStats.member_id == s))
            p_query.execute()
    CurrentNice.update(timestamp=0).where(CurrentNice.chat_id == chat_id).execute()
    CurrentPidor.update(timestamp=0).where(CurrentPidor.chat_id == chat_id).execute()
    dbhandle.close()


def update_current(chat_id, current_dict, user_id):
    dbhandle.connect()
    if current_dict == 'current_nice':
        CurrentNice.update(member_id=user_id, timestamp=time.mktime(datetime.datetime.now().timetuple())).where\
            (CurrentNice.chat_id == chat_id).execute()
    if current_dict == 'current_pidor':
        CurrentPidor.update(member_id=user_id, timestamp=time.mktime(datetime.datetime.now().timetuple())).where\
            (CurrentPidor.chat_id == chat_id).execute()
    dbhandle.close()


def is_not_time_expired(chat_id, type_of_current):
    current = get_current_user(chat_id, type_of_current)
    current_timestamp = current['timestamp']
    day_timestamp = time.mktime(datetime.date.today().timetuple())
    return current_timestamp > day_timestamp


def get_current_user(chat_id, current_dict):
    dbhandle.connect()
    current_user = {'id': 0, 'timestamp': 0}
    if current_dict == 'current_nice':
        for p in CurrentNice.select().where(CurrentNice.chat_id == chat_id):
            current_user['id'] = p.member_id
            current_user['timestamp'] = p.timestamp
    if current_dict == 'current_pidor':
        for m in CurrentPidor.select().where(CurrentPidor.chat_id == chat_id):
            current_user['id'] = m.member_id
            current_user['timestamp'] = m.timestamp
    dbhandle.close()
    return current_user


async def reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.from_user.id
    user_info = await context.bot.get_chat_member(chat_id, reg_member)
    success_or_not = create_user(chat_id, reg_member)
    if success_or_not:
        message = f"{user_info.user.full_name}, ты в игре"
    else:
        message = f"{user_info.user.full_name}, зачем тебе регаться ещё раз?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def unreg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.from_user.id
    user_info = await context.bot.get_chat_member(chat_id, reg_member)
    message = unreg_in_data(chat_id, reg_member)
    if message == 'Пользователь не найден':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f'{user_info.user.full_name} c позором бежал, но статистика всё помнит')


async def pidor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    congratulations = ""
    if is_not_time_expired(chat_id, 'current_pidor'):
        user_info = await context.bot.get_chat_member(chat_id, get_current_user(chat_id, 'current_pidor')['id'])
        message = f'Пидор дня уже определён, это {user_info.user.full_name} (@{user_info.user.username})'
    else:
        pidor_id = get_random_id(chat_id, 'pidor')
        if pidor_id == 'Nothing':
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Невозможно выбрать пидора, список '
                                                                                  'кандидатов пуст')
            return
        pidor_count = update_pidor_stats(chat_id, pidor_id, 'pidor_stats')
        user_info = await context.bot.get_chat_member(chat_id, pidor_id)
        message = f'Пидор дня - {user_info.user.full_name}  (@{user_info.user.username})'
        update_current(chat_id, 'current_pidor', pidor_id)
        for i in messages.PIDOR_MESSAGES:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=i)
            time.sleep(1)
        if pidor_count == 1:
            congratulations = messages.PIDOR_1_TIME
        if pidor_count == 10:
            congratulations = messages.TEN_TIMES
        if pidor_count == 50:
            congratulations = messages.FIFTEEN_TIMES_TIMES
        if pidor_count == 100:
            congratulations = messages.HUNDRED_TIMES
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    if congratulations != "":
        await context.bot.send_message(chat_id=update.effective_chat.id, text=congratulations)
        await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                       sticker=stickers.BILLY_TEAR_OFF_VEST)


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    congratulations = ""
    if is_not_time_expired(chat_id, 'current_nice'):
        user_info = await context.bot.get_chat_member(chat_id, get_current_user(chat_id, 'current_nice')['id'])
        message = f'Красавчик дня уже определён, это {user_info.user.full_name} (@{user_info.user.username})'
    else:
        nice_guy_id = get_random_id(chat_id, 'nice')
        if nice_guy_id == 'Nothing':
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Невозможно выбрать красавчика, '
                                                                                  'список кандидатов пуст')
            return
        pidor_count = update_pidor_stats(chat_id, nice_guy_id, 'stats')
        user_info = await context.bot.get_chat_member(chat_id, nice_guy_id)
        message = f'Красавчик дня - {user_info.user.full_name} (@{user_info.user.username})'
        update_current(chat_id, 'current_nice', nice_guy_id)
        for i in messages.NICE_MESSAGES:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=i)
            time.sleep(1)
        if pidor_count == 1:
            congratulations = messages.NICE_1_TIME
        if pidor_count == 10:
            congratulations = messages.NICE_10_TIMES
        if pidor_count == 50:
            congratulations = messages.NICE_50_TIMES
        if pidor_count == 100:
            congratulations = messages.NICE_100_TIMES
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    if congratulations != "":
        await context.bot.send_message(chat_id=update.effective_chat.id, text=congratulations)
        await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                       sticker=stickers.DRINK_CHAMPAGNE)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    statistics = get_pidor_stats(chat_id, 'stats')
    if statistics == 'Ни один пользователь не зарегистрирован, статистики нет':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=statistics)
    else:
        usernames = []
        counts = []
        for item in statistics.items():
            user_info = await context.bot.get_chat_member(chat_id, item[0])
            usernames.append(f'{user_info.user.full_name} (@{user_info.user.username})')
            counts.append(item[1])
        user_stats = dict(zip(usernames, counts))
        text_list = ['Результаты игры красавчик дня:']
        for j in dict(sorted(user_stats.items(), key=lambda sort_item: sort_item[1], reverse=True)).items():
            text_list.append(f'{j[0]}: {j[1]}')
        text = '\n'.join(text_list)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def pidor_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    statistics = get_pidor_stats(chat_id, 'pidor_stats')
    if statistics == 'Ни один пользователь не зарегистрирован, статистики нет':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=statistics)
    else:
        usernames = []
        counts = []
        for item in statistics.items():
            user_info = await context.bot.get_chat_member(chat_id, item[0])
            usernames.append(f'{user_info.user.full_name} (@{user_info.user.username})')
            counts.append(item[1])
        user_stats = dict(zip(usernames, counts))
        text_list = ['Результаты игры пидор дня:']
        for j in dict(sorted(user_stats.items(), key=lambda sort_item: sort_item[1], reverse=True)).items():
            text_list.append(f'{j[0]}: {j[1]}')
        text = '\n'.join(text_list)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    keyboard = [[
            InlineKeyboardButton("Да", callback_data=f"Yes, {chat_id}"),
            InlineKeyboardButton("Нет", callback_data="No"),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Точно сбросить статистику? Вернуть её будет нельзя, "
                                    "все забудут, кто был красавчиком", reply_markup=reply_markup)


async def confirm_reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data == 'No':
        await query.edit_message_text(text='Правильный выбор 👍')
    else:
        chat_id = int(query.data.split(" ")[1])
        reset_stats_data(chat_id)
        await query.edit_message_text(text='Статистика очищена, начинаем с чистого листа🙈')


async def member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.left_chat_member.id
    user_info = await context.bot.get_chat_member(chat_id, reg_member)
    message = unreg_in_data(chat_id, reg_member)
    if message == 'Пользователь не найден':
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Мы не будем по нему скучать, '
                                                                              'ведь он не был в игре🤡')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f'{user_info.user.full_name} c позором бежал, но статистика всё помнит')


async def percent_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    members = get_all_members(chat_id)
    stats_list = []
    for j in members:
        stats_list.append(get_user_percentage_nice_pidor(chat_id, j))
    sorted_stats_list = sorted(stats_list, key=lambda d: d['nice'])
    text_list = []
    for i in sorted_stats_list:
        user_info = await context.bot.get_chat_member(chat_id, i['member_id'])
        text_list.append(f"{user_info.user.full_name} (@{user_info.user.username}) на {i['nice']}% красавчик и на "
                         f"{i['pidor']}% пидор")
    text = '\n'.join(text_list)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


if __name__ == '__main__':
    try:
        dbhandle.connect()
        Members.create_table()
        PidorStats.create_table()
        Stats.create_table()
        CurrentPidor.create_table()
        CurrentNice.create_table()
        dbhandle.close()
    except peewee.InternalError as px:
        print(str(px))
    application = ApplicationBuilder().token(getenv('BOT_TOKEN')).build()
    reg_handler = CommandHandler('reg', reg)
    unreg_handler = CommandHandler('unreg', unreg)
    pidor_handler = CommandHandler('pidor', pidor)
    run_handler = CommandHandler('run', run)
    stats_handler = CommandHandler('stats', stats)
    pidor_stats_handler = CommandHandler('pidorstats', pidor_stats)
    reset_stats_handler = CommandHandler('resetstats', reset_stats)
    percent_stats_handler = CommandHandler('percentstats', percent_stats)
    application.add_handlers([reg_handler, unreg_handler, pidor_handler, run_handler, stats_handler,
                              pidor_stats_handler, reset_stats_handler, percent_stats_handler,
                              CallbackQueryHandler(confirm_reset_stats)])
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, member_left))
    application.run_polling()
