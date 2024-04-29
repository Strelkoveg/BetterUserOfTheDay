from peewee import *
from os import getenv

user = getenv('DB_USER')
password = getenv('DB_PASSWORD')
db_name = getenv('DB_NAME')
db_host = getenv('DB_HOST')

dbhandle = MySQLDatabase(
    db_name, user=user,
    password=password,
    host=db_host
)


class Members(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    member_id = BigIntegerField()
    coefficient = IntegerField()
    pidor_coefficient = IntegerField()
    full_name = CharField()
    nick_name = CharField()


class PidorStats(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    member_id = BigIntegerField()
    count = IntegerField()


class Stats(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    member_id = BigIntegerField()
    count = IntegerField()


class CurrentPidor(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    member_id = BigIntegerField()
    timestamp = BigIntegerField()


class CurrentNice(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    member_id = BigIntegerField()
    timestamp = BigIntegerField()


class CarmicDicesEnabled(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()


class PidorStickers(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    enable = BooleanField()


