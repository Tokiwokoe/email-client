from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, Text


metadata = MetaData()


folder = Table(
    'folder',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, unique=True),
)


post_account = Table(
    'post_account',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('login', String, nullable=False),
    Column('password', String, nullable=False),
    Column('user_id', Integer, ForeignKey('user.id'), nullable=False),
)


user = Table(
    'user',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String, nullable=False),
    Column('password', String, nullable=False),
)

email_letter = Table(
    'email_letter',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('forward_from', ForeignKey('user.id'), nullable=False),
    Column('sender_folder_id', ForeignKey('folder.id'), nullable=False),
    Column('forward_to', ForeignKey('user.id'), nullable=False),
    Column('receiver_folder_id', ForeignKey('folder.id'), nullable=False),
    Column('text', Text, nullable=False),
)
