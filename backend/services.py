# 服务层业务逻辑
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import BookDB
from schemas import BookCreate
from exceptions import BusinessException

class BookService:
    @staticmethod # 静态方法，不需要实例化
    async def create_book(db: AsyncSession, book_in: BookCreate) -> BookDB:
        db_book = BookDB(name = book_in.name, price = book_in.price)
        db.add(db_book)
        await db.commit()
        await db.refresh(db_book) # 刷新db_book对象，获取最新数据
        return db_book

    @staticmethod
    async def get_book_by_id(db: AsyncSession, book_id: int) -> BookDB:
        res = await db.execute(select(BookDB).where(BookDB.id == book_id))
        book = res.scalar_one_or_none() # 如果查询结果为空，返回None
        if not book:
            raise BusinessException(code = 404, msg = "Book not found")
        return book
    
    @staticmethod
    async def list_book(db: AsyncSession, page: int, page_size: int):
        """
        按页查询，page从1开始
        """
        offset = (page - 1) * page_size # 计算偏移量
        count_res = await db.execute(select(BookDB)) # 查询总数
        total = len(count_res.scalars().all())
        stmt = select(BookDB).offset(offset).limit(page_size) # 分页查询
        res = await db.execute(stmt)
        items = res.scalars().all()
        return items, total

    @staticmethod
    async def delete_book(db: AsyncSession, book_id: int):
        book = await BookService.get_book_by_id(db, book_id)
        await db.execute(delete(BookDB).where(BookDB.id == book_id))
        await db.commit()





        