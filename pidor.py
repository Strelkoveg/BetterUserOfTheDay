import logging
import random
import json
import datetime
import time
import messages
import stickers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def create_user(chat_id, user_id):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
        try:
            members = data[str(chat_id)]['members']
            if user_id in members:
                return False
            members.append(user_id)
            data[str(chat_id)]['members'] = members
            try:
                if (data[str(chat_id)]['stats'][f'{user_id}'] != 0) or \
                        (data[str(chat_id)]['pidor_stats'][f'{user_id}'] != 0):
                    pass
                else:
                    data[str(chat_id)]['stats'][f'{user_id}'] = 0
                    data[str(chat_id)]['pidor_stats'][f'{user_id}'] = 0
            except KeyError:
                data[str(chat_id)]['stats'][f'{user_id}'] = 0
                data[str(chat_id)]['pidor_stats'][f'{user_id}'] = 0
        except KeyError:
            data[str(chat_id)] = {'members': [user_id], 'pidor_stats': {f'{user_id}': 0}, 'stats': {f'{user_id}': 0},
                                  'current_pidor': {
                                      'id': 0,
                                      'timestamp': 1679601600
                                  },
                                  'current_nice': {
                                      'id': 0,
                                      'timestamp': 1679601600
                                  }}
    with open('data.json', 'w') as new_file:
        new_file.write(json.dumps(data))
    return True


def unreg_in_data(chat_id, user_id):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
    try:
        data[str(chat_id)]['members'].remove(user_id)
    except KeyError:
        return 'Пользователь не найден'
    except ValueError:
        return 'Пользователь не найден'
    with open('data.json', 'w') as new_file:
        new_file.write(json.dumps(data))
        return 'deleted'


def get_random_id(chat_id, pidor_or_nice):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
    members = data[str(chat_id)]['members']
    if pidor_or_nice == 'pidor':
        if is_not_time_expired(chat_id, 'current_nice'):
            immune_id = get_current_user(chat_id, 'current_nice')['id']
            members.remove(immune_id)
    if pidor_or_nice == 'nice':
        if is_not_time_expired(chat_id, 'current_pidor'):
            immune_id = get_current_user(chat_id, 'current_pidor')['id']
            members.remove(immune_id)
    return random.choice(members)


def update_pidor_stats(chat_id, pidor_id, stats_type):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
        data[str(chat_id)][stats_type][str(pidor_id)] += 1
    with open('data.json', 'w') as new_file:
        new_file.write(json.dumps(data))
    return data[str(chat_id)][stats_type][str(pidor_id)]


def get_pidor_stats(chat_id, stats_type):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
        try:
            stats = data[str(chat_id)][stats_type]
        except KeyError:
            return 'Ни один пользователь не зарегистрирован, статистики нет'
    return stats


def reset_stats_data(chat_id):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
    statistics = data[str(chat_id)]['stats'].keys()
    for i in statistics:
        data[str(chat_id)]['stats'][i] = 0
    del_stat = 0
    for k in statistics:
        if (int(k) in data[str(chat_id)]['members']) is False:
            del_stat = k
            break
    if del_stat != 0:
        del data[str(chat_id)]['stats'][del_stat]
    pidor_statistics = data[str(chat_id)]['pidor_stats'].keys()
    for l in pidor_statistics:
        data[str(chat_id)]['pidor_stats'][l] = 0
    del_pidor_stat = 0
    for p in pidor_statistics:
        if (int(p) in data[str(chat_id)]['members']) is False:
            del_pidor_stat = p
            break
    if del_pidor_stat != 0:
        del data[str(chat_id)]['pidor_stats'][del_pidor_stat]
    data[str(chat_id)]['current_pidor']['timestamp'] = 0
    data[str(chat_id)]['current_nice']['timestamp'] = 0
    with open('data.json', 'w') as new_file:
        new_file.write(json.dumps(data))


def update_current(chat_id, current_dict, user_id):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
    with open('data.json', 'w') as new_file:
        data[str(chat_id)][current_dict]['timestamp'] = time.mktime(datetime.datetime.now().timetuple())
        data[str(chat_id)][current_dict]['id'] = user_id
        new_file.write(json.dumps(data))


def is_not_time_expired(chat_id, type_of_current):
    current = get_current_user(chat_id, type_of_current)
    current_timestamp = current['timestamp']
    day_timestamp = time.mktime(datetime.date.today().timetuple())
    return current_timestamp > day_timestamp


def get_current_user(chat_id, current_dict):
    with open('data.json', 'r') as file:
        data = json.loads(file.read())
        current = data[str(chat_id)][current_dict]
    return current


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
        message = f'Пидор дня уже определён, это {user_info.user.full_name}'
    else:
        pidor_id = get_random_id(chat_id, 'pidor')
        pidor_count = update_pidor_stats(chat_id, pidor_id, 'pidor_stats')
        user_info = await context.bot.get_chat_member(chat_id, pidor_id)
        message = f'Пидор дня - {user_info.user.full_name}'
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
        message = f'Красавчик дня уже определён, это {user_info.user.full_name}'
    else:
        nice_guy_id = get_random_id(chat_id, 'nice')
        pidor_count = update_pidor_stats(chat_id, nice_guy_id, 'stats')
        user_info = await context.bot.get_chat_member(chat_id, nice_guy_id)
        message = f'Красавчик дня - {user_info.user.full_name}'
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
            usernames.append(user_info.user.full_name)
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
            usernames.append(user_info.user.full_name)
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
        chat_id = query.data.split(" ")[1]
        reset_stats_data(chat_id)
        await query.edit_message_text(text='Статистика очищена, начинаем с чистого листа🙈')


if __name__ == '__main__':
    application = ApplicationBuilder().token('TOKEN').build()
    reg_handler = CommandHandler('reg', reg)
    unreg_handler = CommandHandler('unreg', unreg)
    pidor_handler = CommandHandler('pidor', pidor)
    run_handler = CommandHandler('run', run)
    stats_handler = CommandHandler('stats', stats)
    pidor_stats_handler = CommandHandler('pidorstats', pidor_stats)
    reset_stats_handler = CommandHandler('resetstats', reset_stats)
    application.add_handlers([reg_handler, unreg_handler, pidor_handler, run_handler, stats_handler,
                              pidor_stats_handler, reset_stats_handler,
                              CallbackQueryHandler(confirm_reset_stats)])
    application.run_polling()
