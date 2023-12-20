from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from config import PASSWORD
from mail.services import imap_read_email
import imaplib

router = APIRouter(
    prefix='/pages',
    tags=['Pages']
)

templates = Jinja2Templates(directory='templates')


@router.get('/base')
async def get_base_template(request: Request):
    folder = request.query_params.get('folder')
    if folder:
        try:
            emails = await imap_read_email('nastya.mam4ur@rambler.ru', PASSWORD, folder)
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
    return templates.TemplateResponse("add_mail_account.html", {"request": request})
