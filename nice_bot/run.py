import logging
import time
import telegram.error
import messages
import stickers
import peewee
import os
from db_init import dbhandle, Members, PidorStats, Stats, CurrentPidor, CurrentNice, CarmicDicesEnabled
from db_functions import (create_user, unreg_in_data, is_not_time_expired, are_carmic_dices_enabled, update_pidor_stats,
                          get_current_user, get_user_percentage_nice_pidor, get_pidor_stats, get_all_members,
                          get_random_id, get_random_id_carmic, get_full_name_from_db, get_nickname_from_db,
                          get_all_chat_ids, add_chat_to_carmic_dices_in_db, remove_chat_from_carmic_dices_in_db,
                          reset_stats_data, set_full_name_and_nickname_in_db, update_current,
                          get_chat_members_nice_coefficients, get_chat_members_pidor_coefficients)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reg_member = update.message.from_user.id
    user_info = await context.bot.get_chat_member(chat_id, reg_member)
    user_full_name = user_info.user.full_name
    user_nickname = user_info.user.username
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
            message = f'Пидор дня уже определён, это {user_full_name_from_db}'
    else:
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
            message = f'Пидор дня - {user_full_name_from_db} (@{user_nickname_from_db})'
        update_current(chat_id, 'current_pidor', pidor_id)
        for i in messages.PIDOR_MESSAGES:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=i)
            time.sleep(1)
        if pidor_count == 1:
            congratulations = messages.PIDOR_1_TIME
        if pidor_count == 10:
            congratulations = messages.TEN_TIMES
        if pidor_count == 50:
            congratulations = messages.FIFTEEN_TIMES
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
        current_nice_id = get_current_user(chat_id, 'current_nice')['id']
        try:
            user_info = await context.bot.get_chat_member(chat_id, current_nice_id)
            user_full_name = user_info.user.full_name
            user_nickname = user_info.user.username
            set_full_name_and_nickname_in_db(chat_id, current_nice_id, user_full_name, user_nickname)
            message = f'Красавчик дня уже определён, это {user_full_name} (@{user_nickname})'
        except telegram.error.BadRequest:
            user_full_name_from_db = get_full_name_from_db(chat_id, current_nice_id)
            message = f'Красавчик дня уже определён, это {user_full_name_from_db}'
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
            message = f'Красавчик дня - {user_full_name_from_db} (@{user_nickname_from_db})'
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


async def show_coefficients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    coefficients = get_chat_members_nice_coefficients(chat_id)
    text_list = ["Вероятности стать красавчиком:"]
    for k, v in coefficients.items():
        text_list.append(f"{k} - {v}")
    text = '\n'.join(text_list)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def show_pidor_coefficients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    coefficients = get_chat_members_pidor_coefficients(chat_id)
    text_list = ["Вероятности стать пидором:"]
    for k, v in coefficients.items():
        text_list.append(f"{k} - {v}")
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

async def send_message_to_another_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != 326053639:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Это команду может выполнить только автор бота')
    else:
        chat_ids = get_all_chat_ids()
        for i in chat_ids:
            try:
                await context.bot.send_message(chat_id=i, text=messages.WARM_UP_MESSAGE)
            except telegram.error.Forbidden:
                print(f'bot is blocked in chat {i}')
                pass
            except telegram.error.BadRequest:
                print(f'chat {i} not found')
                pass

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=messages.DONATION)



if __name__ == '__main__':
    try:
        dbhandle.connect()
        Members.create_table()
        PidorStats.create_table()
        Stats.create_table()
        CurrentPidor.create_table()
        CurrentNice.create_table()
        CarmicDicesEnabled.create_table()
        dbhandle.close()
    except peewee.InternalError as px:
        print(str(px))
    application = ApplicationBuilder().token(os.getenv('BOT_TOKEN')).build()
    reg_handler = CommandHandler('reg', reg)
    unreg_handler = CommandHandler('unreg', unreg)
    pidor_handler = CommandHandler('pidor', pidor)
    run_handler = CommandHandler('run', run)
    stats_handler = CommandHandler('stats', stats)
    pidor_stats_handler = CommandHandler('pidorstats', pidor_stats)
    reset_stats_handler = CommandHandler('resetstats', reset_stats)
    percent_stats_handler = CommandHandler('percentstats', percent_stats)
    nice_coefficients_handler = CommandHandler('nicecoefficients', show_coefficients)
    pidor_coefficients_handler = CommandHandler('pidorcoefficients', show_pidor_coefficients)
    donate_handler = CommandHandler('contacts', donate)
    message_to_another_chat_handler = CommandHandler('another', send_message_to_another_chat)
    switch_on_carmic_dices_in_chat_handler = CommandHandler('carmicdices', switch_on_carmic_dices_in_chat)
    application.add_handlers([reg_handler, unreg_handler, pidor_handler, run_handler, stats_handler,
                              pidor_stats_handler, reset_stats_handler, percent_stats_handler,
                              nice_coefficients_handler, pidor_coefficients_handler,
                              switch_on_carmic_dices_in_chat_handler, donate_handler, message_to_another_chat_handler,
                              CallbackQueryHandler(confirm_dialogs)])
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, member_left))
    application.run_polling()
