"""仅供操作者手工创建管理员；不会覆盖或提升任何已有账户。"""

import argparse
import asyncio
import getpass
import sys
import warnings

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from database import AsyncSessionLocal, UserDB, engine
from dependencies import password_context
from schemas import RegisterRequest


def read_password(prompt: str, password_stdin: bool) -> str:
    """按 prompt 读取密码；password_stdin 显式允许从受控标准输入逐行读取而不回显。"""
    if password_stdin:
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        return line.removesuffix("\n").removesuffix("\r")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


async def create_admin(request: RegisterRequest) -> int:
    """将已验证 request 保存为管理员，重名返回非零且不修改原账户。"""
    try:
        async with AsyncSessionLocal() as db:
            user = UserDB(
                username=request.username,
                name=request.username,
                role="admin",
                password_hash=password_context.hash(request.password),
            )
            db.add(user)
            try:
                await db.commit()
            except IntegrityError as error:
                await db.rollback()
                if error.orig.args and error.orig.args[0] == 1062:
                    print("用户名已存在，未修改原账户。", file=sys.stderr)
                    return 1
                raise
            print(f"管理员创建成功：id={user.id}，username={user.username}，role=admin")
            return 0
    finally:
        await engine.dispose()


def main() -> int:
    """解析操作者命令行和交互输入，验证后创建管理员；无函数参数。"""
    parser = argparse.ArgumentParser(description="手工创建管理员，不覆盖或提升已有账户")
    parser.add_argument("--username", help="管理员用户名；省略时交互输入")
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="显式从受控标准输入读取密码及确认各一行；不回显，请勿使用含明文密码的命令行",
    )
    args = parser.parse_args()
    try:
        username = args.username if args.username is not None else input("用户名：")
        password = read_password("密码：", args.password_stdin)
        confirmation = read_password("确认密码：", args.password_stdin)
    except (EOFError, KeyboardInterrupt):
        print("输入已取消，未创建账户。", file=sys.stderr)
        return 1
    except getpass.GetPassWarning:
        print("当前终端不支持安全隐藏输入；请使用交互终端或显式受控 --password-stdin。", file=sys.stderr)
        return 1
    if password != confirmation:
        print("两次密码不一致，未创建账户。", file=sys.stderr)
        return 1
    try:
        request = RegisterRequest(username=username, password=password)
    except ValidationError as error:
        for detail in error.errors(include_input=False):
            print(f"{'.'.join(map(str, detail['loc']))}: {detail['msg']}", file=sys.stderr)
        return 1
    return asyncio.run(create_admin(request))


if __name__ == "__main__":
    sys.exit(main())
