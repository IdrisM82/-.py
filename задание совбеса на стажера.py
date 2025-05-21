from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

# Настройка базы данных
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/library"  # Замените на ваши данные
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Модели
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year_published = Column(Integer, nullable=True)
    isbn = Column(String, unique=True, nullable=True)
    copies = Column(Integer, default=1)


class Reader(Base):
    __tablename__ = "readers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)


class BorrowedBook(Base):
    __tablename__ = "borrowed_books"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    reader_id = Column(Integer, ForeignKey("readers.id"))
    borrow_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)


# Схемы
class UserCreate(BaseModel):
    email: str
    password: str


class BookCreate(BaseModel):
    title: str
    author: str
    year_published: Optional[int] = None
    isbn: Optional[str] = None
    copies: Optional[int] = 1


class ReaderCreate(BaseModel):
    name: str
    email: str


class BorrowBook(BaseModel):
    book_id: int
    reader_id: int


class BorrowedBookResponse(BaseModel):
    id: int
    book_id: int
    reader_id: int
    borrow_date: datetime
    return_date: Optional[datetime] = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year_published: Optional[int]
    isbn: Optional[str]
    copies: int


class ReaderResponse(BaseModel):
    id: int
    name: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str


# CRUD операции
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(db: Session, email: str, password: str):
    hashed_password = pwd_context.hash(password)
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_book(db: Session, book: BookCreate):
    db_book = Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_books(db: Session):
    return db.query(Book).all()


def get_book(db: Session, book_id: int):
    return db.query(Book).filter(Book.id == book_id).first()


def update_book(db: Session, book_id: int, book: BookCreate):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book:
        for key, value in book.dict().items():
            setattr(db_book, key, value)
        db.commit()
        db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book:
        db.delete(db_book)
        db.commit()
    return db_book


def create_reader(db: Session, reader: ReaderCreate):
    db_reader = Reader(**reader.dict())
    db.add(db_reader)
    db.commit()
    db.refresh(db_reader)
    return db_reader


def get_readers(db: Session):
    return db.query(Reader).all()


def borrow_book(db: Session, book_id: int, reader_id: int):
    book = db.query(Book).filter(Book.id == book_id).first()
    if book and book.copies > 0:
        borrowed_book = BorrowedBook(
            book_id=book_id,
            reader_id=reader_id,
            borrow_date=datetime.now()
        )
        db.add(borrowed_book)
        book.copies -= 1
        db.commit()
        db.refresh(borrowed_book)
        return borrowed_book
    return None


def return_book(db: Session, book_id: int, reader_id: int):
    borrowed_book = db.query(BorrowedBook).filter(
        BorrowedBook.book_id == book_id,
        BorrowedBook.reader_id == reader_id,
        BorrowedBook.return_date == None
    ).first()
    if borrowed_book:
        borrowed_book.return_date = datetime.now()
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            book.copies += 1
        db.commit()
        return borrowed_book
    return None


# Аутентификация
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
SECRET_KEY = "your_secret_key"  # Измените на ваш секретный ключ
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Основное приложение
app = FastAPI()


@app.post("/register", response_model=User


Create)

async def register(user: UserCreate, db: Session = Depends(SessionLocal)):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user.email, user.password)


@app.post("/login", response_model=Token)
async def login(user: UserCreate, db: Session = Depends(SessionLocal)):
    db_user = get_user_by_email(db, user.email)
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/books/", response_model=BookResponse)
async def create_book_endpoint(book: BookCreate, db: Session = Depends(SessionLocal),
                               current_user: User = Depends(get_user_by_email)):
    return create_book(db, book)


@app.get("/books/", response_model=list[BookResponse])
async def read_books_endpoint(db: Session = Depends(SessionLocal)):
    return get_books(db)


@app.get("/books/{book_id}", response_model=BookResponse)
async def read_book_endpoint(book_id: int, db: Session = Depends(SessionLocal)):
    db_book = get_book(db, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book


@app.put("/books/{book_id}", response_model=BookResponse)
async def update_book_endpoint(book_id: int, book: BookCreate, db: Session = Depends(SessionLocal),
                               current_user: User = Depends(get_user_by_email)):
    return update_book(db, book_id, book)


@app.delete("/books/{book_id}", response_model=BookResponse)
async def delete_book_endpoint(book_id: int, db: Session = Depends(SessionLocal),
                               current_user: User = Depends(get_user_by_email)):
    return delete_book(db, book_id)


@app.post("/readers/", response_model=ReaderResponse)
async def create_reader_endpoint(reader: ReaderCreate, db: Session = Depends(SessionLocal),
                                 current_user: User = Depends(get_user_by_email)):
    return create_reader(db, reader)


@app.get("/readers/", response_model=list[ReaderResponse])
async def read_readers_endpoint(db: Session = Depends(SessionLocal)):
    return get_readers(db)


@app.post("/borrow/", response_model=BorrowedBookResponse)
async def borrow_book_endpoint(borrow: BorrowBook, db: Session = Depends(SessionLocal),
                               current_user: User = Depends(get_user_by_email)):
    return borrow_book(db, borrow.book_id, borrow.reader_id)


@app.post("/return/", response_model=BorrowedBookResponse)
async def return_book_endpoint(borrow: BorrowBook, db: Session = Depends(SessionLocal),
                               current_user: User = Depends(get_user_by_email)):
    return return_book(db, borrow.book_id, borrow.reader_id)


# Создание таблиц
Base.metadata.create_all(bind=engine)