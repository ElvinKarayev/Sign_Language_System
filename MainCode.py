import logging
import os
import re
import psycopg2
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Replace with your actual bot token
BOTOKEN = "7383040553:AAE8DlZSc0PKB-UbsY5eZRB6lQmBSpuxnJU"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for conversation flow
(LANGUAGE_SELECTION, ASK_PERMISSION, ROLE_SELECTION, TRANSLATOR_UPLOAD, USER_REQUEST,
 TRANSLATOR_MENU, WRITE_SENTENCE, EDIT_SENTENCES, USER_MENU, USER_VIEW_VIDEOS) = range(10)

# Define directories for downloading videos
TRANSLATOR_DIR = './Video/Translator'
USER_DIR = './Video/User'

# Ensure directories exist
os.makedirs(TRANSLATOR_DIR, exist_ok=True)
os.makedirs(USER_DIR, exist_ok=True)

# PostgreSQL connection setup
def connect_to_db():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        connection = psycopg2.connect(
            dbname="sdp_project",
            user="postgres",
            password="sdp_project",  # Replace with your actual password
            host="localhost",
            port="5432"
        )
        logger.info("Connected to the PostgreSQL database successfully.")
        return connection
    except Exception as error:
        logger.error(f"Error connecting to the database: {error}")
        return None

def check_user_exists(username):
    """Checks if a user exists in the database by username and returns the user's id, language, and role if they exist."""
    if username == "unknown_user":
        return None, None, None  # Cannot find user without a valid username

    connection = connect_to_db()
    if not connection:
        return None, None, None  # Return a tuple

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, country, user_role FROM public.users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return result[0], result[1], result[2]  # Return user_id, language, and role
        else:
            return None, None, None
    except Exception as error:
        logger.error(f"Error checking user in the database: {error}")
        return None, None, None  # Ensure we return a tuple

# Add a new user to the database
def add_new_user(username, language, role):
    """Inserts a new user into the database after getting consent, with role preference."""
    connection = connect_to_db()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO public.users (username, country, consent_status, user_role)
            VALUES (%s, %s, %s, %s) RETURNING user_id
        """, (username, language, True, role))
        db_user_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"New user {username} added to the database with role {role}.")
        return db_user_id  # Return the newly assigned user_id
    except Exception as error:
        logger.error(f"Error adding new user to the database: {error}")
        return None

# Update user's role and language in the database
def update_user_role_and_language(user_id, role, language):
    """Updates the user's role and language in the database."""
    connection = connect_to_db()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE public.users SET user_role = %s, country = %s WHERE user_id = %s
        """, (role, language, user_id))
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"User {user_id} updated with role {role} and language {language}.")
    except Exception as error:
        logger.error(f"Error updating user role and language in the database: {error}")

# Update user's language in the database
def update_user_language(user_id, language):
    """Updates the user's language in the database."""
    connection = connect_to_db()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE public.users SET country = %s WHERE user_id = %s
        """, (language, user_id))
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"User {user_id}'s language updated to {language}.")
    except Exception as error:
        logger.error(f"Error updating user language in the database: {error}")

def get_user_language(user_id):
    """Retrieves user's language (country) from the database."""
    connection = connect_to_db()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT country FROM public.users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return result[0]
        return None
    except Exception as error:
        logger.error(f"Error getting user language from database: {error}")
        return None

def save_video_info(user_id, file_path, language, sentence=None, reference_id=None, sentence_id=None):
    """Saves video information and associated sentence to the database."""
    connection = connect_to_db()
    full_file_path = os.path.abspath(file_path)
    full_file_path = full_file_path.replace('\\', '/')
    if not connection:
        return
    try:
        # First, if there's a sentence and no sentence_id provided, save it to sentences table
        if sentence and not sentence_id:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO public.sentences (sentence_language, sentence_content, user_id)
                VALUES (%s, %s, %s) RETURNING sentence_id
            """, (language, sentence, user_id))
            sentence_id = cursor.fetchone()[0]
            connection.commit()
            cursor.close()
        # Then save video information
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO public.videos 
            (user_id, file_path, text_id, language, video_reference_id, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (user_id, full_file_path, sentence_id, language, reference_id))
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"Video and sentence information saved for user {user_id}")
    except Exception as error:
        logger.error(f"Error saving video information to database: {error}")

def get_random_translator_video(user_language, context=None):
    connection = connect_to_db()
    if not connection:
        logger.error("Failed to connect to database")
        return None, None

    try:
        cursor = connection.cursor()
        user_id = context.user_data.get('user_id') if context else None

        logger.info(f"Searching for videos in language: {user_language} for user: {user_id}")

        cursor.execute("""
            SELECT v.video_id, v.file_path, s.sentence_content
            FROM videos v
            LEFT JOIN sentences s ON v.text_id = s.sentence_id
            JOIN users u ON v.user_id = u.user_id
            WHERE v.language = %s
              AND u.user_role = 'Translator'
              AND v.video_id NOT IN (
                  SELECT CAST(uv.video_reference_id AS integer)
                  FROM videos uv
                  WHERE uv.user_id = %s
                    AND uv.video_reference_id IS NOT NULL
              )
        """, (user_language, user_id))

        all_results = cursor.fetchall()
        logger.info(f"Found {len(all_results)} unwatched videos in {user_language}")

        if all_results:
            import random
            chosen_result = random.choice(all_results)
            video_id = chosen_result[0]
            file_path = chosen_result[1]
            sentence = chosen_result[2]

            logger.info(f"Selected video ID: {video_id}, path: {file_path}")

            if context:
                context.user_data['current_translator_video_id'] = video_id

            cursor.close()
            connection.close()
            return file_path, sentence

        cursor.close()
        connection.close()
        logger.warning(f"No unwatched videos found for language: {user_language}")
        return None, None

    except Exception as error:
        logger.error(f"Error fetching random translator video: {error}")
        if connection:
            connection.close()
        return None, None


def get_video_text_id(video_id):
    """Retrieve the text_id associated with a video."""
    connection = connect_to_db()
    if not connection:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT text_id FROM public.videos WHERE video_id = %s
        """, (video_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        if result:
            return result[0]
        else:
            return None
    except Exception as error:
        logger.error(f"Error retrieving text_id for video_id {video_id}: {error}")
        return None

def add_translator_menu_translations():
    menu_translations = {
        'view_sentences': {
            'English': "View Sentences",
            'German': "Sätze anzeigen",
            'Azerbaijani': "Cümlələrə baxın"
        },
        'write_sentence': {
            'English': "Write a Sentence",
            'German': "Einen Satz schreiben",
            'Azerbaijani': "Cümlə yazın"
        },
        'edit_sentences': {
            'English': "Edit Sentences",
            'German': "Sätze bearbeiten",
            'Azerbaijani': "Cümlələri redaktə edin"
        },
        'change_language': {
            'English': "Change Language",
            'German': "Sprache ändern",
            'Azerbaijani': "Dili dəyişdirin"
        },
        'sentence_exists': {
            'English': "This sentence already exists in the database.",
            'German': "Dieser Satz existiert bereits in der Datenbank.",
            'Azerbaijani': "Bu cümlə artıq verilənlər bazasında mövcuddur."
        },
        'menu': {
            'English': "Translator Menu - Please select an option:",
            'German': "Übersetzer-Menü - Bitte wählen Sie eine Option:",
            'Azerbaijani': "Tərcüməçi Menyusu - Zəhmət olmasa bir seçim edin:"
        },
        'available_sentences': {
            'English': "Available sentences:",
            'German': "Verfügbare Sätze:",
            'Azerbaijani': "Mövcud cümlələr:"
        },
        'no_sentences_found': {
            'English': "No sentences found for your language.",
            'German': "Für Ihre Sprache wurden keine Sätze gefunden.",
            'Azerbaijani': "Diliniz üçün cümlə tapılmadı."
        },
        'please_write_sentence': {
            'English': "Please write your sentence:",
            'German': "Bitte schreiben Sie Ihren Satz:",
            'Azerbaijani': "Zəhmət olmasa cümlənizi yazın:"
        },
        'go_back': {
            'English': "Go back",
            'German': "Zurück",
            'Azerbaijani': "Geri dön"
        },
        'delete_sentence': {
            'English': "Delete Sentence",
            'German': "Satz löschen",
            'Azerbaijani': "Cümləni sil"
        },
        'delete_sentence_prompt': {
            'English': "To delete this sentence, press the button below:",
            'German': "Um diesen Satz zu löschen, drücken Sie die Schaltfläche unten:",
            'Azerbaijani': "Bu cümləni silmək üçün aşağıdakı düyməni basın:"
        },
        'edit_menu_prompt': {
            'English': "You can go back to the menu by pressing the button below.",
            'German': "Sie können zum Menü zurückkehren, indem Sie die Schaltfläche unten drücken.",
            'Azerbaijani': "Aşağıdakı düyməni basaraq menyuya qayıda bilərsiniz."
        },
        'sentence_deleted': {
            'English': "The sentence has been deleted.",
            'German': "Der Satz wurde gelöscht.",
            'Azerbaijani': "Cümlə silindi."
        },
        'previous': {
            'English': "Previous",
            'German': "Zurück",
            'Azerbaijani': "Əvvəlki"
        },
        'next': {
            'English': "Next",
            'German': "Weiter",
            'Azerbaijani': "Növbəti"
        }
    }
    return menu_translations

def add_user_menu_translations():
    menu_translations = {
        'user_menu': {
            'English': "User Menu - Please select an option:",
            'German': "Benutzermenü - Bitte wählen Sie eine Option:",
            'Azerbaijani': "İstifadəçi Menyusu - Zəhmət olmasa bir seçim edin:"
        },
        'view_videos': {
            'English': "View Your Videos",
            'German': "Ihre Videos ansehen",
            'Azerbaijani': "Videolarınıza baxın"
        },
        'request_video': {
            'English': "Request Video",
            'German': "Video anfordern",
            'Azerbaijani': "Video tələb edin"
        }
    }
    return menu_translations

def check_sentence_exists(sentence: str) -> bool:
    """Check if a sentence already exists in the database."""
    connection = connect_to_db()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.sentences 
            WHERE LOWER(sentence_content) = LOWER(%s)
        """, (sentence,))
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        return count > 0
    except Exception as error:
        logger.error(f"Error checking sentence existence: {error}")
        return False

def get_all_sentences(language: str) -> list:
    """Retrieve all sentences for a specific language from the database."""
    connection = connect_to_db()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT sentence_content 
            FROM public.sentences 
            WHERE sentence_language = %s
            ORDER BY sentence_id DESC
        """, (language,))
        sentences = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        return sentences
    except Exception as error:
        logger.error(f"Error retrieving sentences: {error}")
        return []

def get_sentences_and_videos(user_id, language):
    """Fetch sentences and associated videos for a given user_id and language."""
    if not user_id:
        return []
    connection = connect_to_db()
    if not connection:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT s.sentence_id, s.sentence_content, v.file_path
            FROM public.sentences s
            LEFT JOIN public.videos v ON s.sentence_id = v.text_id
            WHERE s.user_id = %s AND s.sentence_language = %s
            ORDER BY s.sentence_id DESC
        """, (user_id, language))
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        # Return list of tuples: (sentence_id, sentence_content, video_file_path)
        return results
    except Exception as error:
        logger.error(f"Error fetching sentences and videos: {error}")
        return []

def delete_sentence_and_video(sentence_id, user_id):
    """Delete a sentence and its associated video from the database and file system."""
    if not user_id:
        return
    connection = connect_to_db()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        # Get the video file path before any deletion
        cursor.execute("""
            SELECT v.file_path FROM public.videos v
            WHERE v.text_id = %s AND v.user_id = %s
        """, (sentence_id, user_id))
        result = cursor.fetchone()
        video_file_path = result[0] if result else None

        # Delete the sentence first (if using CASCADE, this will delete the video record)
        cursor.execute("""
            DELETE FROM public.sentences
            WHERE sentence_id = %s AND user_id = %s
        """, (sentence_id, user_id))

        connection.commit()  # Commit the database deletion

        # Delete the video file from the file system
        if video_file_path and os.path.exists(video_file_path):
            os.remove(video_file_path)
            logger.info(f"Deleted video file {video_file_path}")

        cursor.close()
        connection.close()
        logger.info(f"Deleted sentence {sentence_id} and associated video for user {user_id}")
    except Exception as error:
        logger.error(f"Error deleting sentence and video: {error}")

def get_user_videos_and_translator_videos(user_id):
    """Fetch user's videos and corresponding translator videos."""
    if not user_id:
        return []
    connection = connect_to_db()
    if not connection:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT uv.video_id as user_video_id,
                   uv.file_path as user_video_path,
                   tv.file_path as translator_video_path
            FROM public.videos uv
            LEFT JOIN public.videos tv ON uv.video_reference_id = tv.video_id
            WHERE uv.user_id = %s
            ORDER BY uv.uploaded_at DESC
        """, (user_id,))
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        # Return a list of dictionaries
        videos = []
        for row in results:
            videos.append({
                'user_video_id': row[0],
                'user_video_path': row[1],
                'translator_video_path': row[2]
                # No need for 'sentence'
            })
        return videos
    except Exception as error:
        logger.error(f"Error fetching user's videos: {error}")
        return []

def delete_user_video(video_id, user_id):
    """Delete a user's video from the database and file system."""
    if not user_id:
        return
    connection = connect_to_db()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        # Get the video file path before deletion
        cursor.execute("""
            SELECT file_path FROM public.videos
            WHERE video_id = %s AND user_id = %s
        """, (video_id, user_id))
        result = cursor.fetchone()
        if result:
            video_file_path = result[0]
            # Delete the video record
            cursor.execute("""
                DELETE FROM public.videos
                WHERE video_id = %s AND user_id = %s
            """, (video_id, user_id))
            connection.commit()
            # Delete the video file from the file system
            if video_file_path and os.path.exists(video_file_path):
                os.remove(video_file_path)
                logger.info(f"Deleted user video file {video_file_path}")
            cursor.close()
            connection.close()
            logger.info(f"Deleted user video {video_id} for user {user_id}")
        else:
            logger.error(f"Video with id {video_id} not found for user {user_id}")
            cursor.close()
            connection.close()
    except Exception as error:
        logger.error(f"Error deleting user video: {error}")

# Define translations
translations = {
    'English': {
        'consent_message': "Dear Contributor, Thank you very much for the assistance you have provided us! The videos you have sent are being used to promote, disseminate, and teach sign language. If you consent to the use of these videos for research purposes…",
        'confirm_button': "Confirm",
        'cancel_button': "Cancel",
        'choose_role': "Are you a Translator or a User?",
        'translator_button': "Translator",
        'user_button': "User",
        'translator_prompt': "Please write the sentence you want to translate.",
        'video_prompt': "Now, please upload the video for the translation.",
        'user_prompt': "Please upload your video for translation.",
        'valid_video_error': "Please upload a valid video.",
        'thank_you_video': "Video received. Thank you!",
        'thank_you_response': "Your response video has been received. Thank you!",
        'cancel_message': "Operation canceled. To start again, press the /start button.",
        'no_videos_available': "Sorry, no translator videos are available at the moment.",
        'translated_sentence': "Translated sentence: {}",
        'continue_exchange': "Thank you for your video! Here's another translation for you:",
        'no_more_videos': "There are no more translator videos available at the moment.",
        'restart_message': "Please press the /start button to begin.",
        'language_updated': "Your language has been updated.",
        'bot_restarted': "It seems the bot was restarted or you're not in an active conversation.",
        'start_button': "/start"
    },
    'German': {
        'consent_message': "Sehr geehrter Mitwirkender, Vielen Dank für die Unterstützung, die Sie uns gegeben haben! Die von Ihnen gesendeten Videos werden genutzt, um die Gebärdensprache zu fördern, zu verbreiten und zu lehren. Wenn Sie der Nutzung dieser Videos zu Forschungszwecken zustimmen…",
        'confirm_button': "Bestätigen",
        'cancel_button': "Abbrechen",
        'choose_role': "Sind Sie ein Übersetzer oder ein Benutzer?",
        'translator_button': "Übersetzer",
        'user_button': "Benutzer",
        'translator_prompt': "Bitte schreiben Sie den Satz, den Sie übersetzen möchten.",
        'video_prompt': "Laden Sie nun bitte das Video für die Übersetzung hoch.",
        'user_prompt': "Bitte laden Sie Ihr Video zur Übersetzung hoch.",
        'valid_video_error': "Bitte laden Sie ein gültiges Video hoch.",
        'thank_you_video': "Video empfangen. Vielen Dank!",
        'thank_you_response': "Ihr Antwortvideo wurde empfangen. Vielen Dank!",
        'cancel_message': "Vorgang abgebrochen. Um neu zu starten, drücken Sie die /start-Taste.",
        'no_videos_available': "Entschuldigung, derzeit sind keine Übersetzervideos verfügbar.",
        'translated_sentence': "Übersetzter Satz: {}",
        'continue_exchange': "Danke für Ihr Video! Hier ist eine weitere Übersetzung:",
        'no_more_videos': "Derzeit sind keine weiteren Übersetzervideos verfügbar.",
        'restart_message': "Bitte drücken Sie die /start-Taste, um zu beginnen.",
        'language_updated': "Ihre Sprache wurde aktualisiert.",
        'bot_restarted': "Es scheint, dass der Bot neu gestartet wurde oder Sie sich nicht in einer aktiven Unterhaltung befinden.",
        'start_button': "/start"
    },
    'Azerbaijani': {
        'consent_message': "Hörmətli şəxs, bizə göstərdiyiniz kömək üçün çox sağolun! Göndərdiyiniz videolar işarə dilinin yayılması, təşviqi və öyrənilməsi məqsədilə istifadə olunur. Əgər göndərdiyiniz videoların elmi-tədqiqat məqsədilə istifadə edilməsini təstiq edirsinizsə...",
        'confirm_button': "Təsdiq edin",
        'cancel_button': "Ləğv edin",
        'choose_role': "Tərcüməçi, yoxsa istifadəçisiniz?",
        'translator_button': "Tərcüməçi",
        'user_button': "İstifadəçi",
        'translator_prompt': "Tərcümə etmək istədiyiniz cümləni yazın.",
        'video_prompt': "İndi tərcümə üçün videonuzu yükləyin.",
        'user_prompt': "Tərcümə üçün videonuzu yükləyin.",
        'valid_video_error': "Etibarlı bir video yükləyin.",
        'thank_you_video': "Video qəbul edildi. Çox sağ olun!",
        'thank_you_response': "Cavab videonuz qəbul edildi. Çox sağ olun!",
        'cancel_message': "Əməliyyat ləğv edildi. Yenidən başlamaq üçün /start düyməsini basın.",
        'no_videos_available': "Üzr istəyirik, hal-hazırda tərcüməçi videoları mövcud deyil.",
        'translated_sentence': "Tərcümə edilmiş cümlə: {}",
        'continue_exchange': "Videonuz üçün təşəkkür edirik! Növbəti tərcümə budur:",
        'no_more_videos': "Hal-hazırda başqa tərcüməçi videoları mövcud deyil.",
        'restart_message': "Başlamaq üçün /start düyməsini basın.",
        'language_updated': "Diliniz yeniləndi.",
        'bot_restarted': "Görünür, bot yenidən başladılıb və ya aktiv söhbətdə deyilsiniz.",
        'start_button': "/start"
    }
}

# Function to get translation based on selected language
def get_translation(context, key):
    language = context.user_data.get('language', 'English')
    return translations[language][key]

# Helper Functions
def get_user_id_from_context(context, update):
    """Retrieve the user_id from context.user_data or from the database using the username."""
    user_id = context.user_data.get('user_id')
    if user_id:
        return user_id
    else:
        # Get username from context or update
        username = context.user_data.get('username')
        if not username:
            user = update.effective_user
            username = user.username or "unknown_user"
            context.user_data['username'] = username
        if username and username != "unknown_user":
            db_user_id, _, _ = check_user_exists(username)
            if db_user_id:
                context.user_data['user_id'] = db_user_id
                return db_user_id
    return None

async def send_message(update: Update, text: str, reply_markup=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bot by checking if user exists and using their language, or asking for language selection if new."""
    user = update.effective_user
    username = user.username or "unknown_user"

    # Store username
    context.user_data['username'] = username

    # Check if the user already exists in the database and retrieve their language and role
    db_user_id, user_language, user_role = check_user_exists(username)

    if db_user_id is not None and user_language is not None and user_role is not None:
        # User exists, store db_user_id
        context.user_data['user_id'] = db_user_id
        context.user_data['language'] = user_language
        context.user_data['role'] = user_role

        # Proceed depending on the role
        if user_role == 'Translator':
            return await show_translator_menu(update, context)
        else:
            return await show_user_menu(update, context)

    elif db_user_id is None and user_language is None and user_role is None:
        # User does not exist, ask for language selection
        return await prompt_language_selection(update, context)
    else:
        # Database connection failed or another error occurred
        await update.message.reply_text("Sorry, we're experiencing technical difficulties. Please try again later.")
        return ConversationHandler.END

# Prompt language selection
async def prompt_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["🇬🇧 English", "🇩🇪 German", "🇦🇿 Azerbaijani"]]
    await update.message.reply_text(
        "Please select your language:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return LANGUAGE_SELECTION

# Handle language selection
async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_language = update.message.text

    # Store selected language in user_data
    if "🇬🇧" in selected_language:
        context.user_data['language'] = 'English'
    elif "🇩🇪" in selected_language:
        context.user_data['language'] = 'German'
    elif "🇦🇿" in selected_language:
        context.user_data['language'] = 'Azerbaijani'
    else:
        # Handle invalid selection
        await update.message.reply_text("Please select a valid language option.")
        return LANGUAGE_SELECTION  # Stay in the same state

    user_id = get_user_id_from_context(context, update)
    if not user_id and not context.user_data.get('username'):
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    if context.user_data.get('change_language'):
        # User is changing language
        update_user_language(user_id, context.user_data['language'])
        await update.message.reply_text(get_translation(context, 'language_updated'))
        # Clear the flag
        context.user_data.pop('change_language', None)
        # Return to the translator menu
        return await show_translator_menu(update, context)
    else:
        # New user flow, proceed to ask for consent
        reply_keyboard = [[get_translation(context, 'confirm_button'), get_translation(context, 'cancel_button')]]
        await update.message.reply_text(
            get_translation(context, 'consent_message'),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return ASK_PERMISSION

# Handle the confirmation (permission)
async def ask_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text

    if user_response == get_translation(context, 'confirm_button'):

        # Proceed to role selection
        reply_keyboard = [[get_translation(context, 'translator_button'), get_translation(context, 'user_button')], [get_translation(context, 'cancel_button')]]
        await update.message.reply_text(
            get_translation(context, 'choose_role'),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return ROLE_SELECTION
    elif user_response == get_translation(context, 'cancel_button'):
        return await cancel(update, context)
    else:
        await update.message.reply_text(get_translation(context, 'cancel_message'))
        return ConversationHandler.END

# Handle role selection
async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_role_text = update.message.text

    # Check if cancel is pressed
    if user_role_text == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    # Validate user input
    if user_role_text not in [get_translation(context, 'translator_button'), get_translation(context, 'user_button')]:
        await update.message.reply_text(
            get_translation(context, 'choose_role')
        )
        return ROLE_SELECTION

    # Map user_role_text to role_value
    role_value = 'Translator' if user_role_text == get_translation(context, 'translator_button') else 'User'
    context.user_data['role'] = role_value  # Store role in user_data

    username = context.user_data.get('username')
    language = context.user_data.get('language', 'English')

    # Check if user exists
    db_user_id, existing_language, existing_role = check_user_exists(username)
    if db_user_id is not None:
        # User exists, update their role and language
        update_user_role_and_language(db_user_id, role_value, language)
        context.user_data['user_id'] = db_user_id  # Store db_user_id
    else:
        # User does not exist, add new user and store db_user_id
        db_user_id = add_new_user(username, language, role_value)
        if db_user_id is not None:
            context.user_data['user_id'] = db_user_id  # Store db_user_id
        else:
            await update.message.reply_text("Sorry, we're experiencing technical difficulties. Please try again later.")
            return ConversationHandler.END

    # Continue with the flow depending on the role
    if role_value == 'Translator':
        return await show_translator_menu(update, context)
    else:
        return await show_user_menu(update, context)

# Handle user flow
async def handle_user_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_language = context.user_data.get('language', 'English')
    logger.info(f"Handling user flow for language: {user_language}")

    video_path, sentence = get_random_translator_video(user_language, context)

    if video_path:
        logger.info(f"Retrieved video path: {video_path}")
        if os.path.exists(video_path):
            try:
                with open(video_path, 'rb') as video_file:
                    await update.message.reply_video(video_file)
                    if sentence:
                        await update.message.reply_text(
                            get_translation(context, 'translated_sentence').format(sentence)
                        )

                reply_keyboard = [[get_translation(context, 'cancel_button')]]
                await update.message.reply_text(
                    get_translation(context, 'user_prompt'),
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                )
                return USER_REQUEST
            except Exception as e:
                logger.error(f"Error sending video: {e}")
                await update.message.reply_text(
                    "Sorry, there was an error processing the video. Please try again."
                )
                return ConversationHandler.END
        else:
            logger.error(f"Video file not found at path: {video_path}")
            await update.message.reply_text(
                "Sorry, there was an error accessing the video file. Please try again."
            )
            return ConversationHandler.END
    else:
        logger.warning(f"No videos available for language: {user_language}")
        await update.message.reply_text(
            f"Sorry, no videos are currently available in {user_language}. Please try again later."
        )
        return ConversationHandler.END

async def handle_view_user_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'View Your Videos' option for the user with paging."""
    user_id = get_user_id_from_context(context, update)
    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    # Fetch user's videos and corresponding translator videos
    user_videos = get_user_videos_and_translator_videos(user_id)

    if not user_videos:
        await send_message(update, "You have not uploaded any videos yet.")
        return await show_user_menu(update, context)

    # Store user_videos and current index in user_data
    context.user_data['user_videos'] = user_videos
    context.user_data['current_index'] = 0

    # Reset 'message_ids' to ensure a new message is sent
    context.user_data.pop('message_ids', None)

    # Send the 'Go back' message and keyboard
    reply_keyboard = ReplyKeyboardMarkup([[get_translation(context, 'start_button')]], one_time_keyboard=False)

    await send_message(
        update,
        "You can go back to the menu by selecting an option below.",
        reply_markup=reply_keyboard
    )

    # Call function to display the current user video group
    await display_current_user_video_group(update, context)

    return USER_VIEW_VIDEOS

async def display_current_user_video_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_videos = context.user_data.get('user_videos', [])
    current_index = context.user_data.get('current_index', 0)

    if len(user_videos) == 0:
        # No videos left, return to menu
        await send_message(update, "You have not uploaded any videos yet.")
        return await show_user_menu(update, context)

    if current_index >= len(user_videos):
        current_index = len(user_videos) - 1
        context.user_data['current_index'] = current_index
    elif current_index < 0:
        current_index = 0
        context.user_data['current_index'] = current_index

    video_pair = user_videos[current_index]
    user_video_id = video_pair['user_video_id']
    user_video_path = video_pair['user_video_path']
    translator_video_path = video_pair['translator_video_path']

    # Prepare buttons
    buttons = []

    # Add 'Delete' button
    delete_button = InlineKeyboardButton(
        text="Delete",
        callback_data=f"delete_user_video_{user_video_id}"
    )
    buttons.append([delete_button])

    # Add 'Previous' and 'Next' buttons in one horizontal line
    nav_buttons = []
    if current_index > 0:
        prev_button = InlineKeyboardButton(
            text="Previous",
            callback_data="previous_user_video"
        )
        nav_buttons.append(prev_button)
    if current_index < len(user_videos) - 1:
        next_button = InlineKeyboardButton(
            text="Next",
            callback_data="next_user_video"
        )
        nav_buttons.append(next_button)
    if nav_buttons:
        buttons.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(buttons)

    chat_id = update.effective_chat.id
    message_ids = context.user_data.get('message_ids', {})

    # Send or edit translator video
    if 'translator' in message_ids:
        # Edit existing message
        message_id = message_ids['translator']
        if translator_video_path and os.path.exists(translator_video_path):
            with open(translator_video_path, 'rb') as video_file:
                media = InputMediaVideo(media=video_file, caption="Translator Video")
                try:
                    await context.bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media
                    )
                except Exception as e:
                    logger.error(f"Error editing translator video message: {e}")
        else:
            # If video not available, edit message text
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="Translator Video not available"
                )
            except Exception as e:
                logger.error(f"Error editing translator video message text: {e}")
    else:
        # Send new message
        if translator_video_path and os.path.exists(translator_video_path):
            with open(translator_video_path, 'rb') as video_file:
                sent_message = await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption="Translator Video"
                )
                message_ids['translator'] = sent_message.message_id
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text="Translator Video not available"
            )
            message_ids['translator'] = sent_message.message_id

    # Send or edit user's video with buttons
    if 'user' in message_ids:
        # Edit existing message
        message_id = message_ids['user']
        if user_video_path and os.path.exists(user_video_path):
            with open(user_video_path, 'rb') as video_file:
                media = InputMediaVideo(media=video_file, caption="Your Video")
                try:
                    await context.bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Error editing user video message: {e}")
        else:
            # If video not available, edit message text
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="Your Video not available",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error editing user video message text: {e}")
    else:
        # Send new message
        if user_video_path and os.path.exists(user_video_path):
            with open(user_video_path, 'rb') as video_file:
                sent_message = await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption="Your Video",
                    reply_markup=keyboard
                )
                message_ids['user'] = sent_message.message_id
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text="Your Video not available",
                reply_markup=keyboard
            )
            message_ids['user'] = sent_message.message_id

    context.user_data['message_ids'] = message_ids

async def handle_next_user_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Increment the current index
    context.user_data['current_index'] += 1

    # Display the next user video group
    await display_current_user_video_group(update, context)

    return USER_VIEW_VIDEOS

async def handle_previous_user_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Decrement the current index
    context.user_data['current_index'] -= 1

    # Display the previous user video group
    await display_current_user_video_group(update, context)

    return USER_VIEW_VIDEOS

async def handle_delete_user_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the deletion of a user's video when 'Delete' button is pressed."""
    query = update.callback_query
    await query.answer()
    data = query.data
    match = re.match(r"delete_user_video_(\d+)", data)
    if match:
        user_video_id = int(match.group(1))
        user_id = get_user_id_from_context(context, update)

        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        # Delete the user's video
        delete_user_video(user_video_id, user_id)

        # Remove the video from the list and adjust current_index
        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)
        for i, video_pair in enumerate(user_videos):
            if video_pair['user_video_id'] == user_video_id:
                del user_videos[i]
                if current_index >= len(user_videos):
                    current_index = len(user_videos) - 1
                context.user_data['current_index'] = current_index
                break

        context.user_data['user_videos'] = user_videos

        # Delete the messages to create the visual effect
        chat_id = update.effective_chat.id
        message_ids = context.user_data.get('message_ids', {})
        for message_id in message_ids.values():
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(f"Error deleting message {message_id}: {e}")

        context.user_data.pop('message_ids', None)

        # If no videos left, inform the user and return to menu
        if not user_videos:
            await query.message.reply_text(
                "You have not uploaded any videos yet.",
                reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'start_button')]], one_time_keyboard=True)
            )
            return await show_user_menu(update, context)

        # Display the current user video group
        await display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS
    else:
        logger.error(f"Invalid callback data: {data}")
        return USER_VIEW_VIDEOS

# Display the translator menu options
async def show_translator_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the translator menu options."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')

    reply_keyboard = [
        [menu_translations['view_sentences'][language], menu_translations['write_sentence'][language]],
        [menu_translations['edit_sentences'][language], menu_translations['change_language'][language]],
        [get_translation(context, 'cancel_button')]
    ]

    await send_message(
        update,
        menu_translations['menu'][language],
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return TRANSLATOR_MENU

async def show_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the user menu options."""
    menu_translations = add_user_menu_translations()
    language = context.user_data.get('language', 'English')

    reply_keyboard = [
        [menu_translations['request_video'][language]],
        [menu_translations['view_videos'][language]],
        [get_translation(context, 'cancel_button')]
    ]

    await send_message(
        update,
        menu_translations['user_menu'][language],
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return USER_MENU

# Handle translator menu selections
async def handle_translator_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle translator menu selections."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')
    user_choice = update.message.text

    if user_choice == menu_translations['view_sentences'][language]:
        sentences = get_all_sentences(language)
        if sentences:
            # Use the translated header
            message = f"{menu_translations['available_sentences'][language]}\n\n" + "\n".join(f"- {sentence}" for sentence in sentences)
        else:
            # Use the translated message for no sentences found
            message = menu_translations['no_sentences_found'][language]
        await update.message.reply_text(message)
        return await show_translator_menu(update, context)

    elif user_choice == menu_translations['write_sentence'][language]:
        # Use the translated prompt
        await update.message.reply_text(menu_translations['please_write_sentence'][language])
        return WRITE_SENTENCE

    elif user_choice == menu_translations['edit_sentences'][language]:
        # Proceed to edit sentences
        return await handle_edit_sentences(update, context)

    elif user_choice == menu_translations['change_language'][language]:
        context.user_data['change_language'] = True  # Set flag to indicate language change
        reply_keyboard = [["🇬🇧 English", "🇩🇪 German", "🇦🇿 Azerbaijani"]]
        await update.message.reply_text(
            "Please select your new language:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return LANGUAGE_SELECTION

    elif user_choice == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    return TRANSLATOR_MENU

async def handle_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user menu selections."""
    menu_translations = add_user_menu_translations()
    language = context.user_data.get('language', 'English')
    user_choice = update.message.text

    if user_choice == menu_translations['request_video'][language]:
        return await handle_user_flow(update, context)
    elif user_choice == menu_translations['view_videos'][language]:
        # Proceed to display user's uploaded videos
        return await handle_view_user_videos(update, context)
    elif user_choice == get_translation(context, 'cancel_button'):
        return await cancel(update, context)
    else:
        return await show_user_menu(update, context)

async def user_videos_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle navigation within the 'View Your Videos' menu."""
    user_input = update.message.text if update.message else None
    if user_input == get_translation(context, 'start_button'):
        # Go back to user menu
        return await show_user_menu(update, context)
    else:
        # Unrecognized input, prompt again
        await send_message(update, "Please select an option.")
        return USER_VIEW_VIDEOS

# Handle editing sentences
async def handle_edit_sentences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Edit Sentences' option for the translator with paging."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')
    user_id = get_user_id_from_context(context, update)

    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    # Fetch sentences and associated videos for this translator and language
    sentences_videos = get_sentences_and_videos(user_id, language)

    if not sentences_videos:
        await send_message(update, menu_translations['no_sentences_found'][language])
        return await show_translator_menu(update, context)

    # Store sentences_videos and current index in user_data
    context.user_data['sentences_videos'] = sentences_videos
    context.user_data['current_index'] = 0

    # Reset 'message_id' to ensure a new message is sent
    context.user_data.pop('message_id', None)

    # Send the 'Go back' message and keyboard
    translator_menu_keyboard = [[menu_translations['go_back'][language]]]
    reply_keyboard = ReplyKeyboardMarkup(translator_menu_keyboard, one_time_keyboard=False)

    await send_message(
        update,
        menu_translations['edit_menu_prompt'][language],
        reply_markup=reply_keyboard
    )

    # Call function to display the current sentence-video pair
    await display_current_sentence_video(update, context)

    return EDIT_SENTENCES

async def display_current_sentence_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')

    sentences_videos = context.user_data.get('sentences_videos', [])
    current_index = context.user_data.get('current_index', 0)

    if len(sentences_videos) == 0:
        # No sentences left, return to menu
        await send_message(update, menu_translations['no_sentences_found'][language])
        return await show_translator_menu(update, context)

    if current_index >= len(sentences_videos):
        current_index = len(sentences_videos) - 1
        context.user_data['current_index'] = current_index
    elif current_index < 0:
        current_index = 0
        context.user_data['current_index'] = current_index

    sentence_id, sentence_content, video_file_path = sentences_videos[current_index]

    # Prepare buttons
    buttons = []

    # Add 'Delete' button
    delete_button = InlineKeyboardButton(
        text=menu_translations['delete_sentence'][language],
        callback_data=f"delete_{sentence_id}"
    )
    buttons.append([delete_button])

    # Add 'Previous' and 'Next' buttons in one horizontal line
    nav_buttons = []
    if current_index > 0:
        prev_button = InlineKeyboardButton(
            text=menu_translations.get('previous', {}).get(language, "Previous"),
            callback_data="previous_sentence"
        )
        nav_buttons.append(prev_button)
    if current_index < len(sentences_videos) - 1:
        next_button = InlineKeyboardButton(
            text=menu_translations.get('next', {}).get(language, "Next"),
            callback_data="next_sentence"
        )
        nav_buttons.append(next_button)
    if nav_buttons:
        buttons.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(buttons)

    # Send or edit the video with caption and buttons
    if 'message_id' in context.user_data:
        # Edit existing message
        message_id = context.user_data['message_id']
        chat_id = update.effective_chat.id

        if video_file_path and os.path.exists(video_file_path):
            with open(video_file_path, 'rb') as video_file:
                media = InputMediaVideo(media=video_file, caption=f"• {sentence_content}")
                try:
                    await context.bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Error editing message media: {e}")
        else:
            await send_message(update, "Video file not found.")
            return
    else:
        # Send new message
        if video_file_path and os.path.exists(video_file_path):
            sent_message = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(video_file_path, 'rb'),
                caption=f"• {sentence_content}",
                reply_markup=keyboard
            )
            message_id = sent_message.message_id
            context.user_data['message_id'] = message_id
        else:
            await send_message(update, "Video file not found.")
            return

# Handle deletion of sentences
async def handle_delete_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    match = re.match(r"delete_(\d+)", data)
    if match:
        sentence_id = int(match.group(1))
        user_id = get_user_id_from_context(context, update)

        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        # Delete the sentence and associated video
        delete_sentence_and_video(sentence_id, user_id)

        # Remove the sentence from the list and adjust current_index
        sentences_videos = context.user_data.get('sentences_videos', [])
        current_index = context.user_data.get('current_index', 0)
        for i, (s_id, _, _) in enumerate(sentences_videos):
            if s_id == sentence_id:
                del sentences_videos[i]
                if current_index >= len(sentences_videos):
                    current_index = len(sentences_videos) - 1
                context.user_data['current_index'] = current_index
                break

        context.user_data['sentences_videos'] = sentences_videos

        # Delete the message to cause the visual effect
        chat_id = update.effective_chat.id
        message_id = context.user_data.get('message_id')
        if message_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(f"Error deleting message {message_id}: {e}")
            del context.user_data['message_id']

        # If no sentences left, inform the user and return to menu
        if not sentences_videos:
            language = context.user_data.get('language', 'English')
            await query.message.reply_text(
                add_translator_menu_translations()['no_sentences_found'][language],
                reply_markup=ReplyKeyboardMarkup([[add_translator_menu_translations()['go_back'][language]]], one_time_keyboard=False)
            )
            return await show_translator_menu(update, context)

        # Display the current sentence-video pair
        await display_current_sentence_video(update, context)
        return EDIT_SENTENCES
    else:
        logger.error(f"Invalid callback data: {data}")
        return EDIT_SENTENCES

async def handle_next_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Increment the current index
    context.user_data['current_index'] += 1

    # Display the next sentence-video pair
    await display_current_sentence_video(update, context)

    return EDIT_SENTENCES

async def handle_previous_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Decrement the current index
    context.user_data['current_index'] -= 1

    # Display the previous sentence-video pair
    await display_current_sentence_video(update, context)

    return EDIT_SENTENCES

# Handle navigation in 'Edit Sentences' menu
async def edit_sentences_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle navigation within the 'Edit Sentences' menu."""
    user_input = update.message.text if update.message else None
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')

    if user_input == menu_translations['go_back'][language]:
        # Go back to translator menu
        return await show_translator_menu(update, context)
    else:
        # Unrecognized input, prompt again
        await send_message(update, menu_translations['edit_menu_prompt'][language])
        return EDIT_SENTENCES

# Handle new sentence input from translator
async def handle_write_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new sentence input from translator."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')
    new_sentence = update.message.text

    # Check if cancel is pressed
    if new_sentence == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    # Proceed with handling the sentence if it's not a cancellation
    if check_sentence_exists(new_sentence):
        await update.message.reply_text(menu_translations['sentence_exists'][language])
        return await show_translator_menu(update, context)
    else:
        context.user_data['sentence'] = new_sentence
        await update.message.reply_text(get_translation(context, 'video_prompt'))
        return TRANSLATOR_UPLOAD

# Function to generate the next available filename based on the username
def get_next_available_filename(directory, username, role):
    """Find the next available video filename for the user to avoid conflicts."""
    prefix = f"{role.lower()}_video_{username}_"
    existing_files = [f for f in os.listdir(directory) if f.startswith(prefix)]

    # Extract the highest number from existing files
    max_number = 0
    for file in existing_files:
        match = re.search(rf"{prefix}(\d+)\.mp4", file)
        if match:
            file_number = int(match.group(1))
            max_number = max(max_number, file_number)

    # Increment the number
    next_number = max_number + 1
    return os.path.join(directory, f"{prefix}{next_number}.mp4")

# Function to download the video file
async def download_video(video, file_path, context):
    """Download video from Telegram to local file system."""
    new_file = await context.bot.get_file(video.file_id)
    await new_file.download_to_drive(file_path)

# Handle video upload for translators
async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    if user_input == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    if update.message.video:
        user_id = get_user_id_from_context(context, update)
        username = context.user_data.get('username')

        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        file_path = get_next_available_filename(TRANSLATOR_DIR, username, "translator")

        # Get user's language from context
        user_language = context.user_data.get('language', 'unknown')

        # Get the sentence from context
        sentence = context.user_data.get('sentence')

        # Download the video
        await download_video(update.message.video, file_path, context)

        # Save video information with language and sentence
        save_video_info(user_id, file_path, user_language, sentence)

        # Thank the translator and redirect to the menu
        await update.message.reply_text(get_translation(context, 'thank_you_video'))

        # Redirect to translator menu
        return await show_translator_menu(update, context)
    else:
        await update.message.reply_text(get_translation(context, 'valid_video_error'))
        return TRANSLATOR_UPLOAD

# Handle user video request and upload
async def user_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text and update.message.text == '/start':
        return await start(update, context)

    if update.message.video:
        user_id = get_user_id_from_context(context, update)
        username = context.user_data.get('username')
        user_language = context.user_data.get('language', 'English')
        # Get the translator video ID that the user is responding to
        translator_video_id = context.user_data.get('current_translator_video_id')

        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        # Retrieve the text_id of the translator's video
        translator_text_id = get_video_text_id(translator_video_id)

        file_path = get_next_available_filename(USER_DIR, username, "user")
        await download_video(update.message.video, file_path, context)

        # Save the response video with reference to the translator video and sentence_id
        save_video_info(
            user_id=user_id,
            file_path=file_path,
            language=user_language,
            sentence=None,
            reference_id=translator_video_id,
            sentence_id=translator_text_id
        )

        await update.message.reply_text(get_translation(context, 'thank_you_response'))

        # Get next video
        video_path, sentence = get_random_translator_video(user_language, context)
        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(video_file)
                if sentence:
                    await update.message.reply_text(
                        get_translation(context, 'translated_sentence').format(sentence)
                    )
            return USER_REQUEST
        else:
            await update.message.reply_text(
                get_translation(context, 'no_more_videos'),
                reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'start_button')]], one_time_keyboard=True)
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(get_translation(context, 'valid_video_error'))
        return USER_REQUEST

# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of the conversation."""
    await update.message.reply_text(
        get_translation(context, 'cancel_message'),
        reply_markup=ReplyKeyboardRemove()
    )

    # Provide the "Start" button after cancellation
    await update.message.reply_text(
        get_translation(context, 'restart_message'),
        reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'start_button')]], one_time_keyboard=True)
    )
    return ConversationHandler.END

# Fallback handler for messages outside of conversation
async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages when no conversation is active."""
    # Get the user's username
    user = update.effective_user
    username = user.username or "unknown_user"
    context.user_data['username'] = username

    # Attempt to get the user's language and user_id from the database
    db_user_id, user_language, user_role = check_user_exists(username)
    if db_user_id is not None:
        context.user_data['user_id'] = db_user_id
        context.user_data['language'] = user_language
        context.user_data['role'] = user_role
    else:
        context.user_data['language'] = 'English'

    # Remove any custom keyboards
    await send_message(
        update,
        get_translation(context, 'bot_restarted'),
        reply_markup=ReplyKeyboardRemove()
    )
    # Provide the "Start" button
    await send_message(
        update,
        get_translation(context, 'restart_message'),
        reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'start_button')]], one_time_keyboard=True)
    )

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOTOKEN).build()

    # Set up conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_selection)],
            ASK_PERMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_permission)],
            ROLE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, role_selection)],
            TRANSLATOR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translator_menu)],
            WRITE_SENTENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_write_sentence)],
            TRANSLATOR_UPLOAD: [
                MessageHandler(filters.VIDEO | (filters.TEXT & ~filters.COMMAND), handle_video_upload),
                CommandHandler("start", start)
            ],
            USER_REQUEST: [
                MessageHandler(filters.VIDEO | (filters.TEXT & ~filters.COMMAND), user_video_request),
                CommandHandler("start", start)
            ],
            USER_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_menu)],
            USER_VIEW_VIDEOS: [
                CallbackQueryHandler(handle_delete_user_video, pattern=r"^delete_user_video_\d+$"),
                CallbackQueryHandler(handle_next_user_video, pattern="^next_user_video$"),
                CallbackQueryHandler(handle_previous_user_video, pattern="^previous_user_video$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, user_videos_navigation)
            ],
            EDIT_SENTENCES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_sentences_navigation),
                CallbackQueryHandler(handle_delete_sentence, pattern=r"^delete_\d+$"),
                CallbackQueryHandler(handle_next_sentence, pattern="^next_sentence$"),
                CallbackQueryHandler(handle_previous_sentence, pattern="^previous_sentence$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Add fallback handler for messages outside of conversation
    application.add_handler(MessageHandler(filters.ALL, fallback_handler))

    # Test the database connection during bot initialization
    if connect_to_db():
        logger.info("Database connection tested successfully.")
    else:
        logger.error("Failed to connect to the database. Please check your database settings.")

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
