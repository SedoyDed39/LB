from peewee import Model, SqliteDatabase, CharField

DATABASE_PATH = 'db.db'
USERS_DATABASE_PATH = 'users.db'

db = SqliteDatabase(DATABASE_PATH)
users_db = SqliteDatabase(USERS_DATABASE_PATH)

class Channel(Model):
    name = CharField()
    channel_id = CharField(unique=True)
    link = CharField()

    class Meta:
        database = db

class User(Model):
    user_id = CharField(unique=True)

    class Meta:
        database = users_db

def create_tables():
    db.connect()
    db.create_tables([Channel])

def create_users_table():
    users_db.connect()
    users_db.create_tables([User])

def create_databases():
    if not db.is_closed():
        db.close()
    if not users_db.is_closed():
        users_db.close()
    db.init(DATABASE_PATH)
    users_db.init(USERS_DATABASE_PATH)
    create_tables()
    create_users_table()

create_databases()
