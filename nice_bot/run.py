import logging
import random
import datetime
import time
import telegram.error
import messages
import stickers_list
import peewee
from db_init import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def create_user(chat_id, user_id, user_full_name, user_nickname):
    dbhandle.connect()
    is_user_in_chat = False
    for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == user_id)):
        is_user_in_chat = True
    if is_user_in_chat:
        dbhandle.close()
        return False

    q = Members.create(chat_id=chat_id, member_id=user_id, coefficient=10, pidor_coefficient=10, full_name=user_full_name, nick_name=user_nickname)

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
    try:
        dbhandle.connect()
        query = Members.delete().where((Members.chat_id == chat_id) & (Members.member_id == user_id))
        deleted_rows = query.execute()
        dbhandle.close()
        if deleted_rows == 0:
            return 'Пользователь не найден'
        else:
            return 'deleted'
    except Exception:
        dbhandle.close()


def get_all_chat_ids():
    dbhandle.connect()
    chat_ids = [i.chat_id for i in Members.select(Members.chat_id).distinct()]
    dbhandle.close()
    return chat_ids


def get_all_members(chat_id):
    try:
        dbhandle.connect()
        members = [i.member_id for i in Members.select(Members.member_id).where(Members.chat_id == chat_id)]
        dbhandle.close()
        return members
    except Exception:
        dbhandle.connect()


def get_random_id(chat_id, pidor_or_nice):
        members = get_all_members(chat_id)
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
        chosen_member = random.choice(members)
        update_coefficient_for_users(chat_id, chosen_member, pidor_or_nice)
        return chosen_member


def get_user_coefficient(chat_id, member_id, pidor_or_nice):
    try:
        dbhandle.connect()
        coefficient = -1
        if pidor_or_nice == 'nice':
            for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == member_id)):
                coefficient = i.coefficient
        if pidor_or_nice == 'pidor':
            for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == member_id)):
                coefficient = i.pidor_coefficient
        dbhandle.close()
        return coefficient
    except Exception:
        dbhandle.close()


def get_random_id_carmic(chat_id, pidor_or_nice):
    users_and_weights = {}
    members = get_all_members(chat_id)
    if pidor_or_nice == 'pidor':
        if is_not_time_expired(chat_id, 'current_nice'):
            immune_id = get_current_user(chat_id, 'current_nice')['id']
            members.remove(immune_id)
        if members == []:
            return 'Nothing'
        for k in members:
            users_and_weights[k] = get_user_coefficient(chat_id, k, 'pidor')
    if pidor_or_nice == 'nice':
        if is_not_time_expired(chat_id, 'current_pidor'):
            immune_id = get_current_user(chat_id, 'current_pidor')['id']
            members.remove(immune_id)
        if members == []:
            return 'Nothing'
        for k in members:
            users_and_weights[k] = get_user_coefficient(chat_id, k, 'nice')
    users = list(users_and_weights.keys())
    weights = list(users_and_weights.values())
    chosen_member = random.choices(users, weights=weights, k=1)[0]
    update_coefficient_for_users(chat_id, chosen_member, pidor_or_nice)
    return chosen_member


def check_coefficient_for_chosen(coefficient):
    if coefficient >= 20:
        new_coefficient_chosen = 20
    if coefficient <= 0:
        new_coefficient_chosen = 0
    else:
        new_coefficient_chosen = coefficient
    return new_coefficient_chosen


def check_coefficient_for_others(coefficient):
    if coefficient > 10:
        new_nice_coefficient = coefficient - 1
    if coefficient < 10:
        new_nice_coefficient = coefficient + 1
    if coefficient == 10:
        new_nice_coefficient = coefficient
    return new_nice_coefficient


def update_coefficient_for_users(chat_id, chosen_member, nice_or_pidor):
    try:
        members = get_all_members(chat_id)
        members.remove(chosen_member)
        if nice_or_pidor == 'nice':
            if is_not_time_expired(chat_id, 'current_pidor'):
                members.remove(get_current_user(chat_id, 'current_pidor')['id'])
        if nice_or_pidor == 'pidor':
            if is_not_time_expired(chat_id, 'current_nice'):
                members.remove(get_current_user(chat_id, 'current_nice')['id'])
        dbhandle.connect()
        current_coefficient_chosen = 10
        if nice_or_pidor == 'nice':
            for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == chosen_member)):
                current_coefficient_chosen = i.coefficient
            new_coefficient_chosen = check_coefficient_for_chosen(current_coefficient_chosen - 2)
            query = Members.update(coefficient=new_coefficient_chosen).where((Members.chat_id == chat_id) &
                                                                             (Members.member_id == chosen_member))
            query.execute()
        if nice_or_pidor == 'pidor':
            for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == chosen_member)):
                current_coefficient_chosen = i.coefficient
            new_coefficient_chosen = check_coefficient_for_chosen(current_coefficient_chosen - 2)
            query = Members.update(pidor_coefficient=new_coefficient_chosen).where((Members.chat_id == chat_id) &
                                                                                   (Members.member_id == chosen_member))
            query.execute()
        for t in members:
            if nice_or_pidor == 'nice':
                current_nice_coefficient = 10
                for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == t)):
                    current_nice_coefficient = i.coefficient
                new_nice_coefficient = check_coefficient_for_others(current_nice_coefficient)
                query = Members.update(coefficient=new_nice_coefficient).where((Members.chat_id == chat_id) &
                                                                           (Members.member_id == t))
                query.execute()
            if nice_or_pidor == 'pidor':
                current_pidor_coefficient = 10
                for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == t)):
                    current_pidor_coefficient = i.coefficient
                new_pidor_coefficient = check_coefficient_for_others(current_pidor_coefficient)
                query = Members.update(pidor_coefficient=new_pidor_coefficient).where((Members.chat_id == chat_id) &
                                                                           (Members.member_id == t))
                query.execute()
        dbhandle.close()
    except Exception:
        dbhandle.close()


def update_pidor_stats(chat_id, pidor_id, stats_type):
    try:
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
    except Exception:
        dbhandle.close()


def get_pidor_stats(chat_id, stats_type):
    try:
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
    except Exception:
        dbhandle.close()


def get_user_percentage_nice_pidor(chat_id, member_id):
    try:
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
    except Exception:
        dbhandle.close()

def reset_stats_data(chat_id):
    try:
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
    except Exception:
        dbhandle.close()


def update_current(chat_id, current_dict, user_id):
    try:
        dbhandle.connect()
        if current_dict == 'current_nice':
            CurrentNice.update(member_id=user_id, timestamp=time.mktime(datetime.datetime.now().timetuple())).where\
                (CurrentNice.chat_id == chat_id).execute()
        if current_dict == 'current_pidor':
            CurrentPidor.update(member_id=user_id, timestamp=time.mktime(datetime.datetime.now().timetuple())).where\
                (CurrentPidor.chat_id == chat_id).execute()
        dbhandle.close()
    except Exception:
        dbhandle.close()


def is_not_time_expired(chat_id, type_of_current):
    current = get_current_user(chat_id, type_of_current)
    current_timestamp = current['timestamp']
    day_timestamp = time.mktime(datetime.date.today().timetuple())
    return current_timestamp > day_timestamp


def add_chat_to_carmic_dices_in_db(chat_id):
    try:
        if are_carmic_dices_enabled(chat_id) is False:
            dbhandle.connect()
            CarmicDicesEnabled.create(chat_id=chat_id)
            dbhandle.close()
    except Exception:
        dbhandle.close()

def remove_chat_from_carmic_dices_in_db(chat_id):
    try:
        if are_carmic_dices_enabled(chat_id):
            dbhandle.connect()
            CarmicDicesEnabled.delete().where(CarmicDicesEnabled.chat_id == chat_id)
            dbhandle.close()
    except Exception:
        dbhandle.close()

def are_carmic_dices_enabled(chat_id):
    try:
        dbhandle.connect()
        carmic_dices_enabled = False
        for i in CarmicDicesEnabled.select().where(CarmicDicesEnabled.chat_id == chat_id):
            carmic_dices_enabled = True
        dbhandle.close()
        return carmic_dices_enabled
    except Exception:
        dbhandle.close()

def get_current_user(chat_id, current_dict):
    try:
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
    except Exception:
        dbhandle.close()


def set_full_name_and_nickname_in_db(chat_id, member_id, fullname, nickname):
    try:
        dbhandle.connect()
        Members.update(full_name=fullname, nick_name=nickname).where((Members.chat_id == chat_id)
                                                                     & (Members.member_id == member_id)).execute()
        dbhandle.close()
    except Exception:
        dbhandle.close()


def get_full_name_from_db(chat_id, member_id):
    try:
        dbhandle.connect()
        full_name = 'No full name found'
        for k in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == member_id)):
            full_name = k.full_name
        dbhandle.close()
        return full_name
    except Exception:
        dbhandle.close()


def get_nickname_from_db(chat_id, member_id):
    try:
        dbhandle.connect()
        nick_name = 'No nickname found'
        for k in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == member_id)):
            nick_name = k.nick_name
        dbhandle.close()
        return nick_name
    except Exception:
        dbhandle.close()


async def reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.from_user.id
    user_info = await context.bot.get_chat_member(chat_id, reg_member)
    user_full_name = user_info.user.full_name
    user_nickname = user_info.user.username
    if user_nickname is None:
        user_nickname = str(reg_member) + 'nonickname'
    success_or_not = create_user(chat_id, reg_member, user_full_name, user_nickname)

    if success_or_not:
        message = f"{user_full_name}, ты в игре"
    else:
        message = f"{user_full_name}, зачем тебе регаться ещё раз?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def unreg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.from_user.id
    if (chat_id == -457200309) and (reg_member == 435466570):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f'Сане выйти нельзя, ничего не поделаешь')
    else:
        user_info = await context.bot.get_chat_member(chat_id, reg_member)
        message = unreg_in_data(chat_id, reg_member)
        if message == 'Пользователь не найден':
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        else:
            try:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'{user_info.user.full_name} c позором бежал, но статистика всё помнит')
            except telegram.error.BadRequest:
                user_full_name = get_full_name_from_db(chat_id, reg_member)
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'{user_full_name} c позором бежал, но статистика всё помнит')


async def pidor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    congratulations = ""
    pidor_count = ""

    if is_not_time_expired(chat_id, 'current_pidor'):
        current_pidor_id = get_current_user(chat_id, 'current_pidor')['id']
        try:
            user_info = await context.bot.get_chat_member(chat_id, current_pidor_id)
            user_full_name = user_info.user.full_name
            user_nickname = user_info.user.username
            set_full_name_and_nickname_in_db(chat_id, current_pidor_id, user_full_name, user_nickname)
            message = f'Пидор дня уже определён, это {user_full_name} (@{user_nickname})'
        except telegram.error.BadRequest:
            user_full_name_from_db = get_full_name_from_db(chat_id, current_pidor_id)
            message = f'Пидор дня уже определён, это {user_full_name_from_db})'
    else:
        func = True
        if are_carmic_dices_enabled(chat_id):
            pidor_id = get_random_id_carmic(chat_id, 'pidor')
        else:
            pidor_id = get_random_id(chat_id, 'pidor')
        if pidor_id == 'Nothing':
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Невозможно выбрать пидора, список '
                                                                                  'кандидатов пуст')
            return
        pidor_count = update_pidor_stats(chat_id, pidor_id, 'pidor_stats')
        try:
            user_info = await context.bot.get_chat_member(chat_id, pidor_id)
            user_full_name = user_info.user.full_name
            user_nickname = user_info.user.username
            set_full_name_and_nickname_in_db(chat_id, pidor_id, user_full_name, user_nickname)
            message = f'Пидор дня - {user_full_name}  (@{user_nickname})'
        except telegram.error.BadRequest:
            user_full_name_from_db = get_full_name_from_db(chat_id, pidor_id)
            user_nickname_from_db = get_nickname_from_db(chat_id, pidor_id)
            message = f'Пидор дня - {user_full_name_from_db} (@{user_nickname_from_db}))'
        update_current(chat_id, 'current_pidor', pidor_id)
        for i in messages.PIDOR_MESSAGES:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=i)
            time.sleep(1)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    sticker = get_stickers_enable(chat_id)
    if sticker == True:
        congratulations = pidor_count_func(pidor_count)
        result_sticker = pidors_stickers()
        if congratulations != "":
            await context.bot.send_message(chat_id=update.effective_chat.id, text=congratulations)
            await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                           sticker=result_sticker)
        else:
            await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                           sticker=result_sticker)
    else:
        congratulations = pidor_count_func(pidor_count)
        # original
        if congratulations != "":
            await context.bot.send_message(chat_id=update.effective_chat.id, text=congratulations)
            await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                           sticker=stickers_list.BILLY_TEAR_OFF_VEST)
        # original

def get_stickers_enable(chat_id):
        dbhandle.connect()
        result = ''
        for pt in PidorStickers.select().where(PidorStickers.chat_id == chat_id):
            result = pt.enable
        if result == True:
            return True
        else:
            return False
        dbhandle.close()


async def stickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    keyboard = [[
        InlineKeyboardButton("Да", callback_data=f"stickers Yes {chat_id}"),
        InlineKeyboardButton("Нет", callback_data=f"stickers No {chat_id}"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Хочешь включить или отключить рандомные стикеры?", reply_markup=reply_markup)

def pidor_count_func(pidor_count):
    if pidor_count == 1:
        congratulations = messages.PIDOR_1_TIME
    if pidor_count == 10:
        congratulations = messages.TEN_TIMES
    if pidor_count == 50:
        congratulations = messages.FIFTEEN_TIMES
    if pidor_count == 100:
        congratulations = messages.HUNDRED_TIMES
    else:
        congratulations = ""
    return congratulations

def handsome_count_func(pidor_count):
    if pidor_count == 1:
        congratulations = messages.NICE_1_TIME
    if pidor_count == 10:
        congratulations = messages.NICE_10_TIMES
    if pidor_count == 50:
        congratulations = messages.NICE_50_TIMES
    if pidor_count == 100:
        congratulations = messages.NICE_100_TIMES
    else:
        congratulations = ""
    return congratulations


def pidors_stickers():
    return random.choice(stickers_list.CUSTOM_STICKERS_PIDOR)

def handsome_stickers():
    handsome = random.choice(stickers_list.CUSTOM_STICKERS_HANDSOME)
    return handsome


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    congratulations = ""
    if is_not_time_expired(chat_id, 'current_nice'):
        current_nice_id = get_current_user(chat_id, 'current_nice')['id']
        try:
            user_info = await context.bot.get_chat_member(chat_id, current_nice_id)
            user_full_name = user_info.user.full_name
            user_nickname = user_info.user.username
            set_full_name_and_nickname_in_db(chat_id, current_nice_id, user_full_name, user_nickname)
            message = f'Красавчик дня уже определён, это {user_full_name} (@{user_nickname})'
        except telegram.error.BadRequest:
            user_full_name_from_db = get_full_name_from_db(chat_id, current_nice_id)
            message = f'Красавчик дня уже определён, это {user_full_name_from_db})'
    else:
        if are_carmic_dices_enabled(chat_id):
            nice_guy_id = get_random_id_carmic(chat_id, 'nice')
        else:
            nice_guy_id = get_random_id(chat_id, 'nice')
        if nice_guy_id == 'Nothing':
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Невозможно выбрать красавчика, '
                                                                                  'список кандидатов пуст')
            return
        pidor_count = update_pidor_stats(chat_id, nice_guy_id, 'stats')
        try:
            user_info = await context.bot.get_chat_member(chat_id, nice_guy_id)
            user_full_name = user_info.user.full_name
            user_nickname = user_info.user.username
            set_full_name_and_nickname_in_db(chat_id, nice_guy_id, user_full_name, user_nickname)
            message = f'Красавчик дня - {user_full_name}  (@{user_nickname})'
        except telegram.error.BadRequest:
            user_full_name_from_db = get_full_name_from_db(chat_id, nice_guy_id)
            user_nickname_from_db = get_nickname_from_db(chat_id, nice_guy_id)
            message = f'Красавчик дня - {user_full_name_from_db} (@{user_nickname_from_db}))'
        update_current(chat_id, 'current_nice', nice_guy_id)
        for i in messages.NICE_MESSAGES:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=i)
            time.sleep(1)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        sticker = get_stickers_enable(chat_id)
        if sticker == True:
            congratulations = handsome_count_func(pidor_count)
            result_sticker = handsome_stickers()
            if congratulations != "":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=congratulations)
                await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                               sticker=result_sticker)
            else:
                await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                               sticker=result_sticker)
        else:
            congratulations = pidor_count_func(pidor_count)
            # original
            if congratulations != "":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=congratulations)
                await context.bot.send_sticker(chat_id=update.effective_chat.id,
                                               sticker=stickers_list.DRINK_CHAMPAGNE)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    statistics = get_pidor_stats(chat_id, 'stats')
    if statistics == 'Ни один пользователь не зарегистрирован, статистики нет':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=statistics)
    else:
        usernames = []
        counts = []
        for item in statistics.items():
            try:
                user_info = await context.bot.get_chat_member(chat_id, item[0])
                user_full_name = user_info.user.full_name
                user_nickname = user_info.user.username
                set_full_name_and_nickname_in_db(chat_id, item[0], user_full_name, user_nickname)
                usernames.append(f'{user_full_name} (@{user_nickname})')
            except telegram.error.BadRequest:
                user_full_name_from_db = get_full_name_from_db(chat_id, item[0])
                user_nickname_from_db = get_nickname_from_db(chat_id, item[0])
                usernames.append(f'{user_full_name_from_db} (@{user_nickname_from_db})')
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
            try:
                user_info = await context.bot.get_chat_member(chat_id, item[0])
                user_full_name = user_info.user.full_name
                user_nickname = user_info.user.username
                set_full_name_and_nickname_in_db(chat_id, item[0], user_full_name, user_nickname)
                usernames.append(f'{user_info.user.full_name} (@{user_info.user.username})')
            except telegram.error.BadRequest:
                user_full_name_from_db = get_full_name_from_db(chat_id, item[0])
                user_nickname_from_db = get_nickname_from_db(chat_id, item[0])
                usernames.append(f'{user_full_name_from_db} (@{user_nickname_from_db})')
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
            InlineKeyboardButton("Да", callback_data=f"resetstats Yes {chat_id}"),
            InlineKeyboardButton("Нет", callback_data=f"resetstats No {chat_id}"),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Точно сбросить статистику? Вернуть её будет нельзя, "
                                    "все забудут, кто был красавчиком", reply_markup=reply_markup)


async def confirm_dialogs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query.data
    if query.startswith('resetstats') and (query.split(" ")[1] == 'No'):
        await update.callback_query.edit_message_text(text='Правильный выбор 👍')
    elif query.startswith('resetstats') and (query.split(" ")[1] == 'Yes'):
        chat_id = int(query.split(" ")[2])
        reset_stats_data(chat_id)
        await update.callback_query.edit_message_text(text='Статистика очищена, начинаем с чистого листа🙈')
    elif query.startswith('carma') and (query.split(" ")[1] == 'No'):
        chat_id = query.split(" ")[2]
        remove_chat_from_carmic_dices_in_db(chat_id)
        await update.callback_query.edit_message_text(text='Кармические кубики отключены')
    elif query.startswith('carma') and (query.split(" ")[1] == 'Yes'):
        chat_id = query.split(" ")[2]
        add_chat_to_carmic_dices_in_db(chat_id)
        await update.callback_query.edit_message_text(text='Кармические кубики включены')
    elif query.startswith('stickers') and (query.split(" ")[1] == 'Yes'):
        chat_id = query.split(" ")[2]
        status_stick = enable_stickers(chat_id)
        await update.callback_query.edit_message_text(text=status_stick)
    elif query.startswith('stickers') and (query.split(" ")[1] == 'No'):
        await update.callback_query.edit_message_text(text='Правильный выбор 👍')

def enable_stickers(chat_id):
    try:
        dbhandle.connect()
        result = ''
        for pt in PidorStickers.select().where(PidorStickers.chat_id == chat_id):
            result = pt.enable
        if result == True:
            query = PidorStickers.delete().where(PidorStickers.chat_id == chat_id)
            query.execute()
            dbhandle.close()
            status_stickers = 'Отключены кастомные метрики'
        else:
            PidorStickers.create(chat_id=chat_id, enable=True)
            dbhandle.close()
            status_stickers = 'Включены кастомные стикеры'
        return status_stickers
    except Exception:
        dbhandle.close()
        status_stickers = 'Что-то пошло не так..'
        return status_stickers

async def member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.left_chat_member.id
    try:
        user_info = await context.bot.get_chat_member(chat_id, reg_member)
        full_name = user_info.user.full_name
        nickname = user_info.user.username
        set_full_name_and_nickname_in_db(chat_id, reg_member, full_name, nickname)
    except telegram.error.BadRequest:
        full_name = get_full_name_from_db(chat_id, reg_member)
        full_name = str(reg_member)
    message = unreg_in_data(chat_id, reg_member)
    if message == 'Пользователь не найден':
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Мы не будем по нему скучать, '
                                                                              'ведь он не был в игре🤡')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f'{full_name} c позором бежал, но статистика всё помнит')


async def percent_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    members = get_all_members(chat_id)
    stats_list = []
    for j in members:
        stats_list.append(get_user_percentage_nice_pidor(chat_id, j))
    sorted_stats_list = sorted(stats_list, key=lambda d: d['nice'])
    text_list = []
    for i in sorted_stats_list:
        try:
            user_info = await context.bot.get_chat_member(chat_id, i['member_id'])
            user_full_name = user_info.user.full_name
            user_nickname = user_info.user.username
            set_full_name_and_nickname_in_db(chat_id, i['member_id'], user_full_name, user_nickname)
            text_list.append(f"{user_full_name} (@{user_nickname}) на {i['nice']}% красавчик и на "
                             f"{i['pidor']}% пидор")
        except telegram.error.BadRequest:
            user_full_name_from_db = get_full_name_from_db(chat_id, i['member_id'])
            user_nickname_from_db = get_nickname_from_db(chat_id, i['member_id'])
            text_list.append(f"{user_full_name_from_db} (@{user_nickname_from_db}) на {i['nice']}% красавчик и на "
                             f"{i['pidor']}% пидор")
    text = '\n'.join(text_list)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def switch_on_carmic_dices_in_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    keyboard = [[
            InlineKeyboardButton("Да", callback_data=f"carma Yes {chat_id}"),
            InlineKeyboardButton("Нет", callback_data=f"carma No {chat_id}"),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Включить кармические кубики? Если они включены, у пидоров больше шансов стать "
                                    "красавчиками, а у красавчиков - стать пидорами", reply_markup=reply_markup)


if __name__ == '__main__':
    try:
        dbhandle.connect()
        Members.create_table()
        PidorStats.create_table()
        Stats.create_table()
        CurrentPidor.create_table()
        CurrentNice.create_table()
        CarmicDicesEnabled.create_table()
        PidorStickers.create_table()
        dbhandle.close()
    except peewee.InternalError as px:
        dbhandle.close()
    application = ApplicationBuilder().token(getenv('BOT_TOKEN')).build()
    reg_handler = CommandHandler('reg', reg)
    unreg_handler = CommandHandler('unreg', unreg)
    pidor_handler = CommandHandler('pidor', pidor)
    run_handler = CommandHandler('run', run)
    stats_handler = CommandHandler('stats', stats)
    pidor_stats_handler = CommandHandler('pidorstats', pidor_stats)
    reset_stats_handler = CommandHandler('resetstats', reset_stats)
    percent_stats_handler = CommandHandler('percentstats', percent_stats)
    stickers_handler = CommandHandler('stickers', stickers)

    switch_on_carmic_dices_in_chat_handler = CommandHandler('carmicdices', switch_on_carmic_dices_in_chat)
    application.add_handlers([reg_handler, unreg_handler, pidor_handler, run_handler, stats_handler,
                              pidor_stats_handler, reset_stats_handler, percent_stats_handler, stickers_handler,
                              switch_on_carmic_dices_in_chat_handler, CallbackQueryHandler(confirm_dialogs)])
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, member_left))
    application.run_polling()
