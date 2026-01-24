LEXICON: dict[str, str] = {
    # Main commands
    "/start": "📚 <b>Hello, reader!</b>\n\n"
    "This is a library bot where you can read books\n\n"
    "ℹ️ All commands: /help",
    "/help": "🆘 <b>Bot Help</b>\n\n"
    "📖 <b>Main Commands:</b>\n"
    "/start - restart the bot\n"
    "/bookmarks - your bookmarks\n"
    "/continue - continue reading\n"
    "/page N - go to page\n\n"
    "🔍 <b>Search:</b>\n"
    "/search - find a book\n\n"
    "📌 <b>Bookmarks:</b>\n"
    "Click on page number to save\n\n"
    "✨ <b>Enjoy reading!</b>",
    "/bookmarks": "🔖 <b>Your bookmarks:</b>",
    "no_bookmarks": "💬 You don't have bookmarks yet\n\n"
    "To add - click on page number while reading\n\n"
    "/continue - continue reading",
    # Navigation
    "forward": "➡️",
    "backward": "⬅️",
    "pagination_backward": "⏪",
    "pagination_forward": "⏩",
    "cancel": "🔙 Back",
    "cancel_text": "/continue - continue reading",
    "enumeration_1": "1️⃣",
    "enumeration_2": "2️⃣",
    "enumeration_3": "3️⃣",
    "enumeration_4": "4️⃣",
    "enumeration_5": "5️⃣",
    "enumeration_6": "6️⃣",
    "enumeration_7": "7️⃣",
    "enumeration_8": "8️⃣",
    "enumeration_9": "9️⃣",
    # Search and filtering
    "start_search": "🔍 Search books",
    "search_user_books": "📚 My books",
    "user_bookmarks": "🔖 My bookmarks",
    "user_reviews": "💬 My reviews",
    "user_audiobooks": "🎧 My audiobooks",
    "choose_search": "🔎 How to search?",
    "search_by_title_and_author": "📖 By title and author",
    "search_by_title": "📝 By title",
    "search_by_author": "👤 By author",
    "search_by_description": "📋 By description",
    "search_by_genre": "🏷️ By genre",
    "search_all": "📚 All books",
    "no_books_found": "😕 No books found",
    "enter_title_and_author": "📖 Enter title and/or author",
    "enter_title": "📝 Enter book title",
    "enter_author": "👤 Enter book author",
    "enter_description": "📋 Enter book description",
    "choose_genre": "📚 Choose book genre:",
    # Working with books
    "read_book": "📖 Read",
    "view_book_audiobooks": "🎧 Audio versions",
    "view_book_reviews": "💬 Reviews",
    "add_book": "➕ Add book",
    "delete_book": "🗑️ Delete book",
    "book_not_found": "❌ Book not found",
    "page_not_found": "❌ Page not found",
    "no_pages_in_book": "📖 The book has no pages",
    "book_pages_amount": "📖 The book has {total_pages} pages total",
    "command_page_hint": "ℹ️ Use: /page &lt;number&gt;",
    "no_active_book": "📚 No active book",
    "go_to_book_cover": "Go to cover",
    # Bookmarks
    "edit_bookmarks": "✏️ Edit bookmarks",
    "edit_bookmarks_button": "✏️ EDIT",
    "del": "❌ Delete",
    "bookmark_not_found": "🔖 Bookmark not found",
    "bookmark_page_label": "page",
    # Reviews
    "entered_create_mode": "You entered review creation/edit mode. "
    "To exit enter the command\n/cancel_create_review",
    "create_review": "⭐ Leave a review",
    "redact_review": "✏️ Edit",
    "delete_review": "🗑️ Delete",
    "user_review": "💬 My review",
    "fill_review_rating": "⭐ Rate the book (1-5):",
    "fill_review_text": "📝 Write a review:",
    "wrong_rating": "❌ Rating must be from 1 to 5",
    "review_not_found": "💬 Review not found",
    "no_user_reviews": "💬 You have no reviews",
    "no_book_reviews": "💬 No reviews yet. Be the first!",
    "create_review_success": "✅ Review saved!",
    "review_data_damaged": "❌ Review data error",
    # Audiobooks
    "audiobook_generated": "🎧 Audiobook '{book_title}' is ready!",
    "generated_audiobook_title": "Audiobook version of "
    "{book_title} (generated)",
    "go_to_audiobook": "Go to audiobook",
    "listen_audiobook": "🎧 Listen",
    "add_audiobook": "➕ Add audiobook",
    "delete_audiobook": "🗑️ Delete",
    "audiobook_not_found": "❌ Audiobook not found",
    "no_user_audiobooks": "🎧 You have no audiobooks",
    "no_book_audiobooks": "🎧 No audiobooks for this book",
    "fill_audiobook_title": "🔊 Audiobook title:",
    "upload_audio": "🎵 Send audio file",
    "wait_for_listen_audio": "⏳ Loading audiobook...",
    "add_audiobook_success": "✅ Audiobook added!",
    # Forms and validation
    "fill_title": "📖 Book title:",
    "fill_author": "👤 Author:",
    "fill_description": "📋 Description:",
    "upload_cover": "🖼️ Book cover:",
    "fill_is_public": "👥 Book visibility:",
    "fill_is_public_true": "📢 Public",
    "fill_is_public_false": "🔒 Private (only me)",
    "fill_genres": "🏷️ Choose genres:",
    "upload_text_file": "📄 Book text file:",
    "confirm_genres": "✅ Confirm",
    "chosen": "✔️",
    # Information about uploaded items
    "book_uploaded_by_label": "Uploaded by",
    "book_title_label": "Title",
    "book_author_label": "Author",
    "audiobook_label": "Audiobook",
    "book_rating_label": "Rating",
    "book_title_with_author_label": "Book",
    "book_description_label": "Description",
    "audiobook_title_label": "Audiobook",
    "review_rating_label": "Rating",
    "review_text_label": "Review",
    "book_genres_label": "Genres",
    "no_book_genres_label": "No genres",
    "no_book_reviews_label": "No reviews",
    # Errors
    "echo": "I don't understand your request",
    "add_book_error": "❌ Error adding book",
    "add_audiobook_error": "❌ Error adding audiobook",
    "add_review_error": "❌ Error adding review",
    "add_audiobook_title_error": "❌ Error processing title",
    "add_review_rating_error": "❌ Error processing rating",
    "book_delete_error": "❌ Error deleting book",
    "cancel_add_audiobook_error": "❌ Error canceling audiobook creation",
    "cancel_add_review_error": "❌ Error canceling review creation",
    "page_not_found_error": "❌ Page {page_num} not found",
    "author_too_long_error": "❌ Author name too long. "
    "Maximum {max_length} characters",
    "title_too_long_error": "❌ Book title too long. "
    "Maximum {max_length} characters",
    "description_too_long_error": "❌ Description too long. "
    "Maximum {max_length} characters",
    "search_error": "❌ Search error",
    "search_stop": "❌ Search stopped. Start over.",
    "search_message_type_error": "❌ Please use only text messages for search.",
    "unknown_error": "❌ Unknown error",
    "old_message_alert": "⚠️ Outdated message",
    "wrong_command_format": "⚠️ Wrong command format",
    "cancel_add_book_first_warning": "⚠️ Finish adding book or "
    "cancel with command\n/cancel_add_book",
    "cancel_add_review_first_warning": "⚠️ Finish review creation or "
    "cancel with command\n/cancel_create_review",
    "open_the_book_first": "❌ Open the book first",
    "upload_text_file_error": "❌ Need .txt file",
    "upload_cover_error": "❌ Need image",
    "file_unavailable": "❌ File unavailable",
    "empty_title_warning": "❌ Enter title",
    "empty_author_warning": "❌ Enter author",
    "empty_description_warning": "❌ Enter description",
    "empty_review_warning": "❌ Enter review text",
    "ask_for_text_message": "ℹ️ Send text",
    "ask_for_audio_message": "ℹ️ Send audio",
    "ask_for_review_rating": "ℹ️ Enter rating 1-5",
    "gtts_text_too_long": "ℹ️ Your book text is too large for "
    "audio generation. You can add your own audio version via book menu",
    "gtts_start_generating": "ℹ️ Started generating audiobook {book_title}, "
    "it will run in background process, so you can use the bot",
    "gtts_api_failure": "⚠️ Speech synthesis service is overloaded. "
    "Try again later or upload audio file manually.",
    # Statuses
    "entered_add_book_mode": "📖 Add book mode\n/cancel_add_book - cancel",
    "entered_add_audiobook_mode": "🎧 Add audiobook mode\n"
    "/cancel_add_audiobook - cancel",
    "canceled_add_book": "❌ Book addition canceled",
    "canceled_add_audiobook": "❌ Audiobook addition canceled",
    "canceled_create_review": "❌ Review creation canceled",
    "add_book_success": "✅ Book added!",
    "book_delete_success": "✅ Book deleted!",
    "review_delete_success": "✅ Review deleted!",
    "audiobook_delete_success": "✅ Audiobook deleted!",
    # Ratings
    "rating_1": "⭐ (1/5)",
    "rating_2": "⭐⭐ (2/5)",
    "rating_3": "⭐⭐⭐ (3/5)",
    "rating_4": "⭐⭐⭐⭐ (4/5)",
    "rating_5": "⭐⭐⭐⭐⭐ (5/5)",
}

LEXICON_COMMANDS: dict[str, str] = {
    "/start": "Start bot",
    "/help": "Bot help",
    "/bookmarks": "My bookmarks",
    "/continue": "Continue reading your active book",
    "/search": "Search book",
}

DEFAULT_GENRES: list[str] = [
    # Fiction
    "Science Fiction",
    "Fantasy",
    "Detective",
    "Thriller",
    "Horror",
    "Novel",
    "Adventure",
    "Historical Fiction",
    "Romance",
    "Mystery",
    # Classics and drama
    "Classic Literature",
    "Drama",
    "Poetry",
    "Fairy Tales",
    "Fables",
    # Scientific and non-fiction
    "Science Fiction",
    "Popular Science",
    "Biography",
    "Memoir",
    "History",
    # Other popular
    "Psychology",
    "Self-development",
    "Business",
    "Philosophy",
    "Humor",
    # Subgenres of sci-fi/fantasy
    "Cyberpunk",
    "Post-apocalyptic",
    "Urban Fantasy",
    "Space Opera",
    "Alternative History",
    # For children and teens
    "Children's Literature",
    "Teen Literature",
    "Young Adult",
    # Specific
    "Non-fiction",
    "Travel",
    "Cooking",
    "Art",
    "Sports",
]
