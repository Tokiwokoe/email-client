from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from sqlalchemy import select, update
from sqlalchemy.sql import crud
from starlette.responses import RedirectResponse
from config import PASSWORD
from fastapi import FastAPI, status, Form, Depends, HTTPException
from fastapi_users import FastAPIUsers
from auth.auth import auth_backend
from auth.manager import get_user_manager
from auth.schemas import UserRead, UserCreate
from database import User, async_session_maker
from mail.services import imap_read_email, smtp_send_email, add_send_mail_to_database, delete_email_by_number
from models.models import post_account, user
from pages.router import router as router_pages
from cryptography.services import encrypt_message, create_keys


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
async def read_email(imap_login, folder):
    return await imap_read_email(imap_login, imap_password, folder)


@app.post('/send-email')
async def send_email(smtp_login: str = Form(...), receiver: str = Form(...), mail_subject: str = Form(''),
                     mail_text: str = Form(''), cipher: bool = Form(False)):
    try:
        if cipher:
            try:
                async_session = async_session_maker()
                async with async_session.begin():
                    result = await async_session.execute(
                        select(post_account).where(post_account.c.login == 'nastya.mam4ur@rambler.ru'))
                    post_account_data = result.fetchone()

                if post_account_data:
                    private_key = RSA.import_key(post_account_data.private_key)
                    public_key = RSA.import_key(post_account_data.public_key)
                    encrypted_des_key = post_account_data.encrypted_des_key
                    encrypted_des_iv = post_account_data.encrypted_des_iv

                    if mail_subject:
                        mail_subject = encrypt_message(
                            input_message=mail_subject,
                            key=PKCS1_OAEP.new(private_key).decrypt(encrypted_des_key),
                            iv=PKCS1_OAEP.new(private_key).decrypt(encrypted_des_iv)
                        )
                    mail_text = encrypt_message(
                        input_message=mail_text,
                        key=PKCS1_OAEP.new(private_key).decrypt(encrypted_des_key),
                        iv=PKCS1_OAEP.new(private_key).decrypt(encrypted_des_iv)
                    )
                    cipher_header = 'Cipher: True'
            except Exception as err:
                print(err)
                cipher_header = 'Cipher: False'
        else:
            cipher_header = 'Cipher: False'

        #await add_send_mail_to_database(smtp_login, receiver, mail_subject, mail_text)
        await smtp_send_email(smtp_login, smtp_password, receiver, mail_subject, str(mail_text), cipher_header)
    except Exception as err:
        print(err)
    return RedirectResponse(f'/pages/base', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/delete-email/{message_id}/{folder}', response_class=RedirectResponse)
def delete_email(message_id, folder):
    smtp_login = 'nastya.mam4ur@rambler.ru'
    smtp_password = PASSWORD
    try:
        deleted_message = delete_email_by_number(smtp_login, smtp_password, message_id, folder)
    except Exception as err:
        print(err)
    return RedirectResponse(f'/pages/base?folder={folder}', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/add-mail-account/')
async def add_mail_account(post_server: int = Form(...), login: str = Form(...), password: str = Form(...)):
    db = async_session_maker()
    public_key, private_key, encrypted_des_key, encrypted_des_iv = create_keys()
    try:
        await imap_read_email(login, password, 'INBOX')
        await db.execute(
            post_account.insert().values(
                post_server=post_server,
                login=login,
                password=password,
                private_key=private_key,
                public_key=public_key,
                encrypted_des_key=encrypted_des_key,
                encrypted_des_iv=encrypted_des_iv,
            )
        )
        await db.commit()
    except Exception as err:
        print(err)

    return RedirectResponse(f'/pages/base', status_code=status.HTTP_303_SEE_OTHER)


@app.put('/users/accounts/{account_id}/switch')
async def switch_current_account(account_id: int, active_user: User = Depends(current_user)):
    async_session = async_session_maker()
    if user:
        async with async_session.begin():
            result = await async_session.execute(
                update(user).where(user.c.id == int(active_user.id)).values(current_account_id=account_id)
            )

        user.current_account_id = account_id
    return RedirectResponse(f'/pages/base', status_code=status.HTTP_303_SEE_OTHER)
