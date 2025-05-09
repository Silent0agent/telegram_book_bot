from aiogram.fsm.state import StatesGroup, State


class FSMStartMenu(StatesGroup):
    start_menu = State()
    choose_search = State()


class FSMSearchBook(StatesGroup):
    search_by_title_and_author = State()
    search_by_title = State()
    search_by_author = State()
    search_by_description = State()
    search_by_genre = State()
    search_all = State()
    search_user_books = State()

class FSMCreateReview(StatesGroup):
    rating = State()
    text = State()

class FSMAddBook(StatesGroup):
    fill_title = State()
    fill_author = State()
    fill_description = State()
    fill_genres = State()
    fill_is_public = State()
    upload_cover = State()
    upload_text_file = State()
    added = State()
