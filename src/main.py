from config import PASSWORD
from fastapi import FastAPI, Depends
from fastapi_users import FastAPIUsers
from auth.auth import auth_backend
from auth.manager import get_user_manager
from auth.schemas import UserRead, UserCreate
from database import User
from mail.services import imap_read_email, smtp_send_email
from pages.router import router as router_pages


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


@app.post('/send-email/{smtp_login}%{sender}%{receiver}%{mail_subject}%{mail_text}')
def send_email(smtp_login, sender, receiver, mail_subject, mail_text):
    return smtp_send_email(smtp_login, smtp_password, sender, receiver, mail_subject, mail_text)
