from Crypto.Cipher import PKCS1_OAEP
from starlette.responses import RedirectResponse
from config import PASSWORD
from fastapi import FastAPI, status
from fastapi_users import FastAPIUsers
from auth.auth import auth_backend
from auth.manager import get_user_manager
from auth.schemas import UserRead, UserCreate
from database import User
from mail.services import imap_read_email, smtp_send_email, add_send_mail_to_database, delete_email_by_number
from pages.router import router as router_pages, get_base_template
from cryptography.services import encrypt_message, create_keys, rsa


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


@app.get('/read-email/{imap_login}%{{folder}}')
def read_email(imap_login, folder):
    return imap_read_email(imap_login, imap_password, folder)


@app.post('/send-email/{smtp_login}%{receiver}%{mail_text}')
def send_email(smtp_login: str, receiver: str, mail_text: str, cipher: bool = False, mail_subject: str = ''):
    try:
        if cipher:
            fake_rsa, public_key, private_key, encrypted_des_key, encrypted_des_iv = create_keys()
            if mail_subject:
                mail_subject = encrypt_message(
                    input_message=mail_subject,
                    key=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_key),
                    iv=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_iv)
                )
            mail_text = encrypt_message(
                input_message=mail_text,
                key=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_key),
                iv=PKCS1_OAEP.new(rsa).decrypt(encrypted_des_iv)
            )
            cipher_header = 'Cipher: True'
            rsa_header = f'RSA: {rsa}'
            des_key_header = f'DES_key: {encrypted_des_key}'
            des_iv_header = f'DES_IV: {encrypted_des_iv}'
        else:
            cipher_header = 'Cipher: False'
            rsa_header = 'RSA: False'
            des_key_header = 'DES_key: False'
            des_iv_header = 'DES_IV: False'

        #await add_send_mail_to_database(smtp_login, receiver, mail_subject, mail_text)
        return smtp_send_email(smtp_login, smtp_password, receiver, mail_subject, str(mail_text), cipher_header,
                               rsa_header, des_key_header, des_iv_header)
    except Exception as err:
        print(err)


@app.post('/delete-email/{message_id}', response_class=RedirectResponse)
def delete_email(message_id, folder='Trash'):
    smtp_login = 'nastya.mam4ur@rambler.ru'
    smtp_password = PASSWORD
    try:
        deleted_message = delete_email_by_number(smtp_login, smtp_password, message_id, folder)
    except Exception as err:
        print(err)
    return RedirectResponse(f'/pages/base?folder={folder}', status_code=status.HTTP_303_SEE_OTHER)
