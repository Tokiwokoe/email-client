from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, Text, Boolean, LargeBinary

metadata = MetaData()


folder = Table(
    'folder',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, unique=True),
)


post_server = Table(
    'post_server',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, unique=True),
)


post_account = Table(
    'post_account',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('post_server', ForeignKey('post_server.id'), nullable=False),
    Column('login', String, nullable=False, unique=True),
    Column('password', String, nullable=False),
    Column('private_key', LargeBinary, nullable=False),
    Column('public_key', LargeBinary, nullable=False),
    Column('encrypted_des_key', LargeBinary, nullable=False),
    Column('encrypted_des_iv', LargeBinary, nullable=False),
)


user = Table(
    'user',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String, nullable=False),
    Column('email', String, nullable=False),
    Column('hashed_password', String, nullable=False),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('is_superuser', Boolean, default=False, nullable=False),
    Column('is_verified', Boolean, default=False, nullable=False),
    Column('current_account_id', ForeignKey('post_account.id'), nullable=True),
)


users_account = Table(
    'users_account',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user', ForeignKey('user.id'), nullable=False),
    Column('post_account', ForeignKey('post_account.id'), nullable=False),
)


email_letter = Table(
    'email_letter',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('forward_from', String, nullable=False),
    Column('sender_folder', ForeignKey('folder.id'), nullable=False),
    Column('forward_to', String, nullable=False),
    Column('receiver_folder_id', ForeignKey('folder.id'), nullable=False),
    Column('mail_subject', String),
    Column('text', Text),
    Column('cipher', Boolean),
)


connection = Table(
    'connection',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('connection_sender', ForeignKey('post_account.login'), nullable=False),
    Column('connection_receiver', ForeignKey('post_account.login'), nullable=False),
)
