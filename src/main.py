from Crypto.Cipher import PKCS1_OAEP
from config import PASSWORD
from fastapi import FastAPI
from fastapi_users import FastAPIUsers
from auth.auth import auth_backend
from auth.manager import get_user_manager
from auth.schemas import UserRead, UserCreate
from database import User
from mail.services import imap_read_email, smtp_send_email, add_send_mail_to_database
from pages.router import router as router_pages
from cryptography.services import create_keys, encrypt_message, decrypt_message


imap_password = PASSWORD
smtp_password = PASSWORD


app = FastAPI()

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix='/auth/jwt',
    tags=['auth'],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(router_pages)

current_user = fastapi_users.current_user()


@app.get('/read-email/{imap_login}')
def read_email(imap_login):
    return imap_read_email(imap_login, imap_password)


@app.post('/send-email/{smtp_login}%{sender}%{receiver}%{mail_subject}%{mail_text}%{cipher}')
def send_email(smtp_login, receiver, mail_subject, mail_text, cipher: bool):
    try:
        if cipher is True:
            rsa, public_key, private_key, encrypted_des_key, encrypted_des_iv = create_keys()
            enc = encrypt_message(input_message=mail_text,
                                  key=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_key),
                                  iv=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_iv))
            mail_text = str(decrypt_message(input_message=enc,
                                            key=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_key),
                                            iv=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_iv)))
        #await add_send_mail_to_database(smtp_login, receiver, mail_subject, mail_text, cipher)
        return smtp_send_email(smtp_login, smtp_password, receiver, mail_subject, mail_text)
    except Exception as err:
        print(err)
