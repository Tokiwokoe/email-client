import os
import shutil
import uuid
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from sqlalchemy import update, select
from starlette.responses import RedirectResponse, FileResponse
from account.services import fastapi_users, current_user, get_current_account_info
from fastapi import FastAPI, status, Form, Depends, UploadFile, File, HTTPException
from auth.auth import auth_backend
from auth.schemas import UserRead, UserCreate
from database import User, async_session_maker
from mail.services import imap_read_email, smtp_send_email, add_send_mail_to_database, delete_email_by_number
from models.models import post_account, user
from pages.router import router as router_pages
from cryptography.services import encrypt_message, create_keys, encrypt_file

app = FastAPI()


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix='/auth/jwt',
    tags=['auth'],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix='/auth',
    tags=['auth'],
)

app.include_router(router_pages)


@app.post('/send-email')
async def send_email(receiver: str = Form(...), mail_subject: str = Form(''),
                     mail_text: str = Form(''), cipher: bool = Form(False), signature: bool = Form(False),
                     file: UploadFile = File(None), active_user: User = Depends(current_user)):
    try:
        async_session = async_session_maker()
        post_account_data = await get_current_account_info(active_user)
        login = post_account_data.login
        password = post_account_data.password
        post_server = post_account_data.post_server

        file_path = None

        if cipher:
            try:
                async with async_session.begin():
                    result = await async_session.execute(
                        select(post_account).where(post_account.c.login == str(receiver))
                    )
                    receiver_post_account_data = result.fetchone()
                if receiver_post_account_data:
                    public_key = RSA.import_key(receiver_post_account_data.public_key)
                    des_key = post_account_data.des_key
                    des_iv = post_account_data.des_iv
                    encrypted_des_key = PKCS1_OAEP.new(public_key).encrypt(des_key)
                    encrypted_des_iv = PKCS1_OAEP.new(public_key).encrypt(des_iv)
                    if mail_subject:
                        mail_subject = encrypt_message(
                            input_message=mail_subject,
                            key=des_key,
                            iv=des_iv
                        )
                    mail_text = encrypt_message(
                        input_message=mail_text,
                        key=des_key,
                        iv=des_iv
                    )
                    cipher_header = 'Cipher: True'
            except Exception as err:
                print(err)
                cipher_header = 'Cipher: False'
                encrypted_des_key = ''
                encrypted_des_iv = ''
        else:
            cipher_header = 'Cipher: False'
            encrypted_des_key = ''
            encrypted_des_iv = ''
        if signature:
            pass

        if file:
            original_extension = os.path.splitext(file.filename)[1]
            safe_filename = f'{uuid.uuid4()}{original_extension}'
            temp_file_path = f'uploads/{safe_filename}'
            temp_enc_file_path = f'uploads/encrypted_{safe_filename}'

            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            if cipher:
                encrypted_data = encrypt_file(temp_file_path, temp_enc_file_path, des_key, des_iv)
                encrypted_file_path = f'uploads/encrypted_{safe_filename}'
                with open(encrypted_file_path, "wb") as encrypted_file:
                    encrypted_file.write(encrypted_data)
                file_path = encrypted_file_path
            else:
                file_path = temp_file_path

        #await add_send_mail_to_database(login, receiver, mail_subject, mail_text)
        await smtp_send_email(login, password, receiver, mail_subject, str(mail_text), cipher_header, post_server,
                              encrypted_des_key, encrypted_des_iv, file_path)
    except Exception as err:
        print(err)
    return RedirectResponse(f'/pages/base', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/delete-email/{message_id}/{folder}', response_class=RedirectResponse)
async def delete_email(message_id, folder, active_user: User = Depends(current_user)):
    post_account_data = await get_current_account_info(active_user)
    login = post_account_data.login
    password = post_account_data.password
    post_server = post_account_data.post_server
    try:
        deleted_message = await delete_email_by_number(login, password, message_id, folder, post_server)
    except Exception as err:
        print(err)
    return RedirectResponse(f'/pages/base?folder={folder}', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/add-mail-account/')
async def add_mail_account(post_server: int = Form(...), login: str = Form(...), password: str = Form(...)):
    db = async_session_maker()
    public_key, private_key, des, iv = create_keys()
    try:
        await imap_read_email(login, password, 'INBOX', post_server)
        await db.execute(
            post_account.insert().values(
                post_server=post_server,
                login=login,
                password=password,
                private_key=private_key,
                public_key=public_key,
                des_key=des,
                des_iv=iv,
            )
        )
        await db.commit()
    except Exception as err:
        print(err)

    return RedirectResponse(f'/pages/base', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/users/accounts/{account_id}/switch')
async def switch_current_account(account_id: int, active_user: User = Depends(current_user)):
    async_session = async_session_maker()
    if active_user:
        async with async_session.begin():
            result = await async_session.execute(
                update(user).where(user.c.id == int(active_user.id)).values(current_account_id=account_id)
            )

        user.current_account_id = account_id
    return RedirectResponse(f'/pages/base', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/download/uploads/{filename}')
async def download_file(filename: str):
    file_path = f'uploads/{filename}'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
