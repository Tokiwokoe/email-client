from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from account.services import get_current_account_info, current_user, get_users_accounts_info
from database import User
from mail.services import imap_read_email
import imaplib


router = APIRouter(
    prefix='/pages',
    tags=['Pages']
)

templates = Jinja2Templates(directory='templates')


@router.get('/base')
async def get_base_template(request: Request, active_user: User = Depends(current_user)):
    folder = request.query_params.get('folder')
    if folder:
        try:
            post_account_data = await get_current_account_info(active_user)
            login = post_account_data.login
            password = post_account_data.password
            post_server = post_account_data.post_server
            emails = await imap_read_email(login, password, folder, post_server)
        except imaplib.IMAP4.error:
            emails = []
    else:
        emails = []
    return templates.TemplateResponse('main_page.html', {'request': request, 'emails': emails})


@router.get('/write-email')
def get_base_template(request: Request):
    return templates.TemplateResponse('write_letter.html', {'request': request})


@router.get('/add-mail-account/')
async def add_mail_account_form(request: Request):
    return templates.TemplateResponse('add_mail_account.html', {'request': request})


@router.get('/change-mail-account/')
async def change_post_account(request: Request, active_user: User = Depends(current_user)):
    try:
        post_accounts = await get_users_accounts_info(active_user)
    except Exception:
        post_accounts = []
    return templates.TemplateResponse('change_post_account.html', {'request': request, 'accounts': post_accounts})
