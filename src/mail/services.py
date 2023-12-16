import ast
import imaplib
import email
from Crypto.Cipher import PKCS1_OAEP
from PIL import Image
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.services import decrypt_message, rsa
from database import async_session_maker
from models.models import email_letter


SMTP_SERVER = 'smtp.rambler.ru'
SMTP_PORT = 465
IMAP_SERVER = 'imap.rambler.ru'
IMAP_PORT = 993


def imap_read_email(imap_login, imap_password):
    with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT) as server:
        server.login(imap_login, imap_password)

        response, folders = server.list()

        print(folders)

        server.select('INBOX')
        mails = []
        response, messages = server.search(None, 'ALL')
        messages = messages[0].split(b' ')
        for message in messages:
            mails.append(print_email(message, server))

        server.close()
        return mails


def print_email(message, server):
    mail = {}
    response, msg = server.fetch(message, '(RFC822)')
    email_message = email.message_from_bytes(msg[0][1])

    cipher_header = email_message.get('X-Cipher-Header', 'Cipher: False')
    rsa_header = email_message.get('X-RSA-Header', 'RSA: False')
    des_key_header = email_message.get('X-DES-key-Header', 'DES_key: False')
    des_iv_header = email_message.get('X-DES-IV-Header', 'DES_IV: False')

    is_encrypted = 'Cipher: True' in cipher_header

    frm = email.header.decode_header(email_message['From'])[0][0]
    mail['From'] = frm if type(frm) is str else frm.decode("utf-8")
    sbj = email.header.decode_header(email_message['To'])[0][0]
    mail['To'] = sbj
    subject = email.header.decode_header(email_message['Subject'])[0][0]
    mail['Subject'] = subject if type(subject) is str else subject.decode("utf-8")
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" not in content_disposition:
                if content_type == "text/plain":
                    mail['Text'] = part.get_payload(decode=True).decode('utf-8')
    else:
        content_type = email_message.get_content_type()

        if content_type == "text/plain":
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
                if "image" in content_type:
                    with io.BytesIO(payload) as img_stream:
                        img = Image.open(img_stream)
                        img.show()
                if ".txt" in decoded_filename:
                    file_content = part.get_payload(decode=True).decode('utf-8')
                    mail['Attachment'] = file_content
    if is_encrypted:
        des_key = ast.literal_eval(des_key_header.replace('DES_key: ', ''))
        des_iv = ast.literal_eval(des_iv_header.replace('DES_IV: ', ''))
        mail['Text'] = decrypt_message(
            input_message=ast.literal_eval(mail['Text']),
            key=PKCS1_OAEP.new(rsa).decrypt(des_key),
            iv=PKCS1_OAEP.new(rsa).decrypt(des_iv)
        )
    return mail


def smtp_send_email(smtp_login, smtp_password, receiver, mail_subject, mail_text, cipher_header, rsa_header, des_key_header, des_iv_header):
    msg = MIMEMultipart()
    msg['From'] = smtp_login
    msg['To'] = receiver
    if not mail_subject:
        mail_subject = 'Без_темы'
    msg['Subject'] = mail_subject
    text = mail_text
    msg.attach(MIMEText(text))
    msg.add_header('X-Cipher-Header', cipher_header)
    msg.add_header('X-RSA-Header', rsa_header)
    msg.add_header('X-DES-key-Header', des_key_header)
    msg.add_header('X-DES-IV-Header', des_iv_header)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        try:
            server.login(smtp_login, smtp_password)
            server.sendmail(smtp_login, [receiver], msg.as_string())
            return 'Успешно отправлено'
        except Exception:
            return 'При отправке произошла ошибка!'


async def add_send_mail_to_database(smtp_login, receiver, mail_subject, mail_text, cipher):
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
