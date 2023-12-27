from fastapi_users import FastAPIUsers
from sqlalchemy import select
from auth.manager import get_user_manager
from auth.auth import auth_backend
from database import User, async_session_maker
from models.models import post_account, user, users_account


fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user()


async def get_current_account_info(active_user):
    if active_user:
        async_session = async_session_maker()
        async with async_session.begin():
            result = await async_session.execute(
                select(user).where(user.c.id == int(active_user.id)))
            user_data = result.fetchone()
            if user_data:
                result = await async_session.execute(
                    select(post_account).where(post_account.c.id == int(user_data.current_account_id)))
                post_account_data = result.fetchone()

        return post_account_data


async def get_users_accounts_info(active_user):
    if active_user:
        async_session = async_session_maker()
        async with async_session.begin():
            result = await async_session.execute(
                select(users_account).where(users_account.c.user == int(active_user.id)))
            user_data = result.fetchall()
            if user_data:
                post_account_data = []
                for data in user_data:
                    account = {}
                    result = await async_session.execute(
                        select(post_account.c.id).where(post_account.c.id == int(data.post_account)))
                    account['ID'] = result.fetchone()[0]
                    result = await async_session.execute(
                        select(post_account.c.login).where(post_account.c.id == int(data.post_account)))
                    account['Login'] = result.fetchone()[0]
                    post_account_data.append(account)

        return post_account_data
