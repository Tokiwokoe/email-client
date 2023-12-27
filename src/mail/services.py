import ast
import imaplib
import email
import os
from email import encoders
from email.mime.base import MIMEBase

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from PIL import Image
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select
from cryptography.services import decrypt_message, decrypt_file
from database import async_session_maker
from models.models import email_letter, post_account


async def get_post_server_info(post_server_id):
    if post_server_id == 1:
        post_server_data = {
            'SMTP_SERVER': 'smtp.rambler.ru',
            'SMTP_PORT': 465,
            'IMAP_SERVER': 'imap.rambler.ru',
            'IMAP_PORT': 993,
            'INBOX': 'INBOX',
            'SentBox': 'SentBox',
            'Spam': 'Spam',
            'DraftBox': 'DraftBox',
            'Trash': 'Trash'
        }
    elif post_server_id == 2:
        post_server_data = {
            'SMTP_SERVER': 'smtp.yandex.ru',
            'SMTP_PORT': 465,
            'IMAP_SERVER': 'imap.yandex.ru',
            'IMAP_PORT': 993,
            'INBOX': 'INBOX',
            'SentBox': 'Sent',
            'Spam': 'Spam',
            'DraftBox': 'Drafts',
            'Trash': 'Trash'
        }
    else:
        post_server_data = {}

    return post_server_data


async def imap_read_email(imap_login, imap_password, folder, post_server):
    post_server_data = await get_post_server_info(post_server)
    with imaplib.IMAP4_SSL(post_server_data['IMAP_SERVER'], post_server_data['IMAP_PORT']) as server:
        server.login(imap_login, imap_password)

        response, folders = server.list()
        server.select(post_server_data[folder])

        mails = []
        response, messages = server.search(None, 'ALL')
        messages = messages[0].split(b' ')
        message_id = 1
        for message in messages:
            mails.append(await print_email(message, server, message_id, folder))
            message_id += 1

        server.close()
        return mails


async def print_email(message, server, message_id, folder):
    mail = {}
    response, msg = server.fetch(message, '(RFC822)')
    email_message = email.message_from_bytes(msg[0][1])
    cipher_header = email_message.get('X-Cipher-Header', 'Cipher: False')
    encrypted_des_key = email_message.get('encrypted_des_key')
    encrypted_des_iv = email_message.get('encrypted_des_iv')

    is_encrypted = 'Cipher: True' in cipher_header

    mail['Folder'] = folder
    frm = email.header.decode_header(email_message['From'])[0][0]
    mail['From'] = frm if type(frm) is str else frm.decode('utf-8')
    sbj = email.header.decode_header(email_message['To'])[0][0]
    mail['To'] = sbj
    subject = email.header.decode_header(email_message['Subject'])[0][0]
    mail['Subject'] = subject if type(subject) is str else subject.decode('utf-8')
    mail['Message-ID'] = message_id
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))

            if 'attachment' not in content_disposition:
                if content_type == 'text/plain':
                    mail['Text'] = part.get_payload(decode=True).decode('utf-8')
    else:
        content_type = email_message.get_content_type()

        if content_type == 'text/plain':
            mail['Text'] = email_message.get_payload(decode=True).decode('utf-8')
    for part in email_message.walk():
        filename = part.get_filename()
        if filename:
            decoded_filename = email.header.decode_header(filename)[0][0]
            if isinstance(decoded_filename, bytes):
                decoded_filename = decoded_filename.decode('utf-8')
            mail['Attachment'] = decoded_filename
            payload = part.get_payload(decode=True)
            if payload:
                if 'image' in content_type:
                    with io.BytesIO(payload) as img_stream:
                        img = Image.open(img_stream)
                        img.show()
                if '.txt' in decoded_filename:
                    try:
                        file_content = part.get_payload(decode=True).decode('utf-8')
                    except Exception:
                        file_content = part.get_payload(decode=False)
                    mail['Attachment'] = file_content
    if is_encrypted:
        try:
            async_session = async_session_maker()
            async with async_session.begin():
                result = await async_session.execute(
                    select(post_account).where(post_account.c.login == str(mail['To'])))
                post_account_data = result.fetchone()
            if post_account_data:
                private_key = RSA.import_key(post_account_data.private_key)
                async with async_session.begin():
                    result = await async_session.execute(
                        select(post_account).where(post_account.c.login == str(mail['From'])))
                    post_account_data = result.fetchone()
                des_key = PKCS1_OAEP.new(private_key).decrypt(ast.literal_eval(encrypted_des_key))
                des_iv = PKCS1_OAEP.new(private_key).decrypt(ast.literal_eval(encrypted_des_iv))
                mail['Text'] = decrypt_message(
                    input_message=ast.literal_eval(mail['Text']),
                    key=des_key,
                    iv=des_iv
                )
                mail['Subject'] = decrypt_message(
                    input_message=ast.literal_eval(mail['Subject']),
                    key=des_key,
                    iv=des_iv
                )
                try:
                    if 'Attachment' in mail:
                        mail['Attachment'] = decrypt_file(
                            input_file=f'uploads/{filename}',
                            output_file=f'uploads/decrypted_{filename}',
                            key=des_key,
                            iv=des_iv
                        )
                except Exception as err:
                    print(err)
        except ValueError as err:
            print(err)
            mail['Text'] = 'Ключи для дешифрования утеряны'
            mail['Subject'] = 'Ключи для дешифрования утеряны'
    return mail


async def smtp_send_email(smtp_login, smtp_password, receiver, mail_subject, mail_text, cipher_header, post_server,
                          encrypted_des_key, encrypted_des_iv, file_path):
    post_server_data = await get_post_server_info(post_server)
    msg = MIMEMultipart()
    msg['From'] = smtp_login
    msg['To'] = receiver
    if not mail_subject:
        mail_subject = 'Без_темы'
    msg['Subject'] = str(mail_subject)
    text = mail_text
    msg.attach(MIMEText(text))
    msg.add_header('X-Cipher-Header', cipher_header)
    msg.add_header('encrypted_des_key', str(encrypted_des_key))
    msg.add_header('encrypted_des_iv', str(encrypted_des_iv))

    if file_path:
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(file_path)}",
        )
        msg.attach(part)

    with smtplib.SMTP_SSL(post_server_data['SMTP_SERVER'], post_server_data['SMTP_PORT']) as server:
        try:
            server.login(smtp_login, smtp_password)
            server.sendmail(smtp_login, [receiver], msg.as_string())
            print('Успешно отправлено')
            return 'Успешно отправлено'
        except Exception as err:
            print(err)
            return 'При отправке произошла ошибка!'


async def delete_email_by_number(imap_login, imap_password, email_number, folder, post_server):
    try:
        post_server_data = await get_post_server_info(post_server)
        with imaplib.IMAP4_SSL(post_server_data['IMAP_SERVER'], post_server_data['IMAP_PORT']) as server:
            server.login(imap_login, imap_password)
            server.select(post_server_data[folder])
            if folder != 'Trash':
                server.copy(email_number, 'Trash')
            server.store(email_number, '+FLAGS', '(\Deleted)')
            server.expunge()
            return f'Письмо с номером {email_number} успешно удалено.'
    except Exception as err:
        return f'Произошла ошибка при удалении письма: {str(err)}'


async def add_send_mail_to_database(smtp_login, receiver, mail_subject, mail_text):
    db = async_session_maker()
    if not mail_subject:
        mail_subject = 'Без_темы'
    await db.execute(
        email_letter.insert().values(
            forward_from=smtp_login,
            sender_folder_id=1,  # Отправленное
            forward_to=receiver,
            receiver_folder_id=1,  # Входящие
            mail_subject=mail_subject,
            text=mail_text,
        )
    )
    await db.commit()


async def open_email(imap_login, imap_password, post_server, folder, email_id):
    post_server_data = await get_post_server_info(post_server)
    with imaplib.IMAP4_SSL(post_server_data['IMAP_SERVER'], post_server_data['IMAP_PORT']) as server:
        server.login(imap_login, imap_password)
        server.select(post_server_data[folder])

        mails = []
        response, messages = server.search(None, email_id)
        messages = messages[0].split(b' ')
        message_id = 1
        for message in messages:
            mails.append(await print_email(message, server, email_id, folder))
            message_id += 1

        server.close()
        return mails
