from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, BigInteger, Table, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from .db_session import SqlAlchemyBase

book_genre = Table(
    "book_genre",
    SqlAlchemyBase.metadata,
    Column("book_id", Integer, ForeignKey("books.book_id")),
    Column("genre_id", Integer, ForeignKey("genres.genre_id"))
)


class User(SqlAlchemyBase):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)  # Telegram ID
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    registration_date = Column(DateTime, default=datetime.utcnow)

    books = relationship("Book", back_populates="uploader")
    bookmarks = relationship("Bookmark", back_populates="user")
    audiobooks = relationship("Audiobook", back_populates="uploader")
    reviews = relationship("Review", back_populates="user")


class Book(SqlAlchemyBase):
    __tablename__ = "books"

    book_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255))
    description = Column(Text)
    # book_url = Column(String(512))
    # cover_url = Column(String(512))
    is_public = Column(Boolean, default=True)
    uploader_id = Column(BigInteger, ForeignKey("users.user_id"))

    uploader = relationship("User", back_populates="books")
    bookmarks = relationship("Bookmark", back_populates="book")
    audiobooks = relationship("Audiobook", back_populates="book")
    # pdfs = relationship("PDFBook", back_populates="book")
    genres = relationship("Genre", secondary=book_genre, back_populates="books")
    reviews = relationship("Review", back_populates="book")
    pages = relationship("Page", back_populates="book")

    @property
    def average_rating(self):
        if not self.reviews:  # Если нет отзывов
            return 0.0  # или None, в зависимости от вашей логики

        total = sum(review.rating for review in self.reviews)
        return round(total / len(self.reviews), 1)  # Округляем до 1 знака после запятой


class Page(SqlAlchemyBase):
    __tablename__ = "pages"

    page_id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.book_id"))
    num = Column(Integer)
    text = Column(String)

    book = relationship("Book", back_populates="pages")


class Genre(SqlAlchemyBase):
    __tablename__ = "genres"

    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # Например: "Фантастика", "Детектив"

    books = relationship("Book", secondary=book_genre, back_populates="genres")


class Audiobook(SqlAlchemyBase):
    __tablename__ = "audiobooks"

    audiobook_id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.book_id"))  # Связь с книгой
    title = Column(String(255))  # Название аудиоверсии (может отличаться от текстовой)
    audio_url = Column(String(512), nullable=False)  # Ссылка на файл
    duration_seconds = Column(Integer)  # Длительность в секундах
    language = Column(String(50), default="ru")  # Язык озвучки
    uploader_id = Column(BigInteger, ForeignKey("users.user_id"))  # Кто загрузил

    book = relationship("Book", back_populates="audiobooks")
    uploader = relationship("User", back_populates="audiobooks")


class Bookmark(SqlAlchemyBase):
    __tablename__ = "bookmarks"

    bookmark_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    book_id = Column(Integer, ForeignKey("books.book_id"))
    page_number = Column(Integer)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")
    book = relationship("Book", back_populates="bookmarks")


class Review(SqlAlchemyBase):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    book_id = Column(Integer, ForeignKey("books.book_id"))
    text = Column(Text)  # Текст отзыва
    rating = Column(Numeric(2, 1))  # Рейтинг от 1.0 до 5.0
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")
