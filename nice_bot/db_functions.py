import random
import time
import datetime

from peewee import fn

from db_init import dbhandle, Members, Stats, PidorStats, CurrentPidor, CurrentNice, CarmicDicesEnabled


def create_user(chat_id, user_id, user_full_name, user_nickname):

    user_nickname = "NULL" if user_nickname == None else user_nickname

    dbhandle.connect()
    is_user_in_chat = False
    for i in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == user_id)):
        is_user_in_chat = True
    if is_user_in_chat:
        dbhandle.close()
        return False
    Members.create(chat_id=chat_id, member_id=user_id, coefficient=10, pidor_coefficient=10, full_name=user_full_name,
                   nick_name=user_nickname)
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


def get_all_chat_ids():
    dbhandle.connect()
    chat_ids = [i.chat_id for i in Members.select(Members.chat_id).distinct()]
    dbhandle.close()
    return chat_ids


def get_all_members(chat_id):
    dbhandle.connect()
    members = [i.member_id for i in Members.select(Members.member_id).where(Members.chat_id == chat_id)]
    dbhandle.close()
    return members


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


def add_chat_to_carmic_dices_in_db(chat_id):
    if are_carmic_dices_enabled(chat_id) is False:
        dbhandle.connect()
        CarmicDicesEnabled.create(chat_id=chat_id)
        dbhandle.close()


def remove_chat_from_carmic_dices_in_db(chat_id):
    if are_carmic_dices_enabled(chat_id):
        dbhandle.connect()
        CarmicDicesEnabled.delete().where(CarmicDicesEnabled.chat_id == chat_id)
        dbhandle.close()


def are_carmic_dices_enabled(chat_id):
    dbhandle.connect()
    carmic_dices_enabled = False
    for i in CarmicDicesEnabled.select().where(CarmicDicesEnabled.chat_id == chat_id):
        carmic_dices_enabled = True
    dbhandle.close()
    return carmic_dices_enabled


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


def set_full_name_and_nickname_in_db(chat_id, member_id, fullname, nickname):

    nickname = "NULL" if nickname == None else nickname

    dbhandle.connect()
    Members.update(full_name=fullname, nick_name=nickname).where((Members.chat_id == chat_id)
                                                                 & (Members.member_id == member_id)).execute()
    dbhandle.close()


def get_full_name_from_db(chat_id, member_id):
    dbhandle.connect()
    full_name = 'No full name found'
    for k in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == member_id)):
        full_name = k.full_name
    dbhandle.close()
    return full_name


def get_nickname_from_db(chat_id, member_id):
    dbhandle.connect()
    nick_name = 'No nickname found'
    for k in Members.select().where((Members.chat_id == chat_id) & (Members.member_id == member_id)):
        nick_name = k.nick_name
    dbhandle.close()
    return nick_name

def get_chat_members_nice_coefficients(chat_id):
    dbhandle.connect()
    coefficients = {}
    coef_sum = Members.select(fn.SUM(Members.coefficient)).where(Members.chat_id == chat_id).scalar()
    for k in Members.select(Members.full_name, Members.coefficient).where(Members.chat_id == chat_id):
        coefficients[k.full_name] = round(k.coefficient / coef_sum * 100, 2)
    dbhandle.close()
    return coefficients

def get_chat_members_pidor_coefficients(chat_id):
    dbhandle.connect()
    coefficients = {}
    coef_sum = Members.select(fn.SUM(Members.pidor_coefficient)).where(Members.chat_id == chat_id).scalar()
    for k in Members.select(Members.full_name, Members.pidor_coefficient).where(Members.chat_id == chat_id):
        coefficients[k.full_name] = round(k.pidor_coefficient / coef_sum * 100, 2)
    dbhandle.close()
    return coefficients
