from peewee import *

user = 'root'
password = '11111'
db_name = 'test_database'

dbhandle = MySQLDatabase(
    db_name, user=user,
    password=password,
    host='localhost'
)


class Members(Model):
    class Meta:
        database = dbhandle
        order_by = ('chat_id',)

    chat_id = BigIntegerField()
    member_id = BigIntegerField()


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
