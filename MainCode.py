import random
import asyncio
import json
import logging
import os
import re
import psycopg2
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.ext import CallbackContext
from apscheduler.jobstores.base import JobLookupError
# Replace with your actual bot token
BOTOKEN = "7383040553:AAE8DlZSc0PKB-UbsY5eZRB6lQmBSpuxnJU"
RESTART_JOB_KEY = 'restart_job'
latest_otp = None
async def generate_random_otp(context: ContextTypes.DEFAULT_TYPE):
    global latest_otp
    latest_otp = random.randint(100000, 999999)
async def send_bot_restarted(context: CallbackContext):
    # This will be called after 20 seconds if not cancelled
    # It sends a "bot restarted" message to the user
    job = context.job
    chat_id = job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Bot restarted. Please press the start button to begin again.",
        reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True, one_time_keyboard=True)
    )

def schedule_restarted_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if RESTART_JOB_KEY in context.user_data:
        old_job = context.user_data[RESTART_JOB_KEY]
        try:
            old_job.schedule_removal()
        except JobLookupError:
            pass  # It's fine if the job doesn't exist anymore
        del context.user_data[RESTART_JOB_KEY]

    job = context.application.job_queue.run_once(
        send_bot_restarted,
        when=2,
        chat_id=update.effective_chat.id,
        name=str(update.effective_chat.id)
    )
    context.user_data[RESTART_JOB_KEY] = job

def cancel_restarted_message(context: ContextTypes.DEFAULT_TYPE):
    old_job = context.user_data.pop(RESTART_JOB_KEY, None)  # pop returns None if key not present
    if old_job is not None:
        try:
            old_job.schedule_removal()
        except JobLookupError:
            pass
        
def with_fallback_timeout(handler_func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Schedule the fallback
        schedule_restarted_message(update, context)
        
        # Execute the original handler
        result = await handler_func(update, context)
        
        # Don't cancel here by default. Let handlers that respond call cancel themselves.
        return result
    return wrapper

@with_fallback_timeout
async def global_fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This handler doesn't respond. It only schedules the fallback.
    # If no other handler responds within 20s, user gets the "bot restarted" message.
    pass

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for conversation flow
(LANGUAGE_SELECTION, USERNAME_INPUT, ASK_PERMISSION, ROLE_SELECTION, TRANSLATOR_UPLOAD, USER_REQUEST,
 TRANSLATOR_MENU, WRITE_SENTENCE, EDIT_SENTENCES, USER_MENU, USER_VIEW_VIDEOS, VOTING) = range(12)



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

def check_user_exists(telegram_id, telegram_username=None):
    """Checks if a user exists in the database by telegram_id or username and returns the user's id, username, language, and role if they exist."""
    connection = connect_to_db()
    if not connection:
        return None, None, None, None  # Return a tuple

    try:
        cursor = connection.cursor()
        # First, try to find the user by telegram_id
        if telegram_id:
            cursor.execute("SELECT user_id, username, country, user_role FROM public.users WHERE telegram_id = %s", (telegram_id,))
            result = cursor.fetchone()
            if result:
                cursor.close()
                connection.close()
                return result[0], result[1], result[2], result[3]  # Return user_id, username, language, and role
        cursor.close()
        connection.close()
        return None, None, None, None
    except Exception as error:
        logger.error(f"Error checking user in the database: {error}")
        return None, None, None, None  # Ensure we return a tuple



# Add a new user to the database
def add_new_user(username, language, role, telegram_id):
    """Inserts a new user into the database after getting consent, with role preference."""
    connection = connect_to_db()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO public.users (username, country, consent_status, user_role, telegram_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING user_id
        """, (username, language, True, role, telegram_id))
        db_user_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"New user {username} added to the database with role {role} and telegram_id {telegram_id}.")
        return db_user_id  # Return the newly assigned user_id
    except psycopg2.IntegrityError as error:
        connection.rollback()
        cursor.close()
        connection.close()
        logger.error(f"IntegrityError: {error}")
        # Fetch the existing user
        existing_user_id, _, _, _ = check_user_exists(telegram_id)
        if existing_user_id:
            # Update telegram_id if missing
            if telegram_id and not get_user_telegram_id(existing_user_id):
                update_user_telegram_id(existing_user_id, telegram_id)
            return existing_user_id
        else:
            logger.error(f"User with username {username} already exists but could not retrieve existing user.")
            return None
    except Exception as error:
        connection.rollback()
        cursor.close()
        connection.close()
        logger.error(f"Error adding new user to the database: {error}")
        return None

def get_user_telegram_id(user_id):
    """Retrieve the telegram_id of a user."""
    connection = connect_to_db()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT telegram_id FROM public.users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result[0] if result else None
    except Exception as error:
        logger.error(f"Error retrieving telegram_id for user_id {user_id}: {error}")
        return None


def update_user_telegram_id(user_id, telegram_id):
    """Updates the user's telegram_id in the database."""
    connection = connect_to_db()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE public.users SET telegram_id = %s WHERE user_id = %s
        """, (telegram_id, user_id))
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"User {user_id}'s telegram_id updated to {telegram_id}.")
    except Exception as error:
        logger.error(f"Error updating telegram_id in the database: {error}")



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

def get_random_translator_video(user_language, context=None, exclude_ids=None):
    connection = connect_to_db()
    if not connection:
        logger.error("Failed to connect to database")
        return None, None

    try:
        cursor = connection.cursor()
        user_id = context.user_data.get('user_id') if context else None

        # Exclude skipped and responded videos
        exclude_clause = "AND v.video_id NOT IN %s" if exclude_ids else ""
        query = f"""
            SELECT v.video_id, v.file_path, s.sentence_content
            FROM videos v
            LEFT JOIN sentences s ON v.text_id = s.sentence_id
            WHERE v.language = %s
              AND v.user_id != %s
              AND v.video_reference_id IS NULL
              AND v.video_id NOT IN (
                  SELECT video_reference_id FROM videos WHERE user_id = %s
              )
              {exclude_clause}
        """
        params = [user_language, user_id, user_id]
        if exclude_ids:
            params.append(tuple(exclude_ids))

        logger.info(f"Executing query: {query} with params {params}")
        cursor.execute(query, params)

        all_results = cursor.fetchall()
        logger.info(f"Found {len(all_results)} videos")

        if all_results:
            import random
            chosen_result = random.choice(all_results)
            video_id, file_path, sentence = chosen_result
            logger.info(f"Selected video ID: {video_id}")

            if context:
                context.user_data['current_translator_video_id'] = video_id

            cursor.close()
            connection.close()
            return file_path, sentence

        cursor.close()
        connection.close()
        logger.warning("No videos found matching the criteria")
        return None, None

    except Exception as error:
        logger.error(f"Error fetching videos: {error}")
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
    """Fetch sentences and associated translator videos for a given user_id and language."""
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
            LEFT JOIN public.videos v ON s.sentence_id = v.text_id AND v.video_reference_id IS NULL
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

def get_random_video_for_voting(user_id, language):
    """Fetch a random video (user or translator video) not uploaded by the current user, and not yet voted on by the current user."""
    connection = connect_to_db()
    if not connection:
        logger.error("Failed to connect to database")
        return None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT v.video_id, v.file_path, s.sentence_content
            FROM videos v
            LEFT JOIN sentences s ON v.text_id = s.sentence_id
            WHERE v.language = %s
              AND v.user_id != %s
              AND v.video_id NOT IN (
                  SELECT video_id FROM votes WHERE user_id = %s
              )
        """, (language, user_id, user_id))

        all_results = cursor.fetchall()
        logger.info(f"Found {len(all_results)} videos to vote on in {language}")

        if all_results:
            import random
            chosen_result = random.choice(all_results)
            video_id = chosen_result[0]
            file_path = chosen_result[1]
            sentence_content = chosen_result[2]

            cursor.close()
            connection.close()
            return video_id, file_path, sentence_content
        else:
            cursor.close()
            connection.close()
            logger.info("No more videos available for voting.")
            return None
    except Exception as error:
        logger.error(f"Error fetching random video for voting: {error}")
        if connection:
            connection.close()
        return None



def increment_video_score(video_id, score_type):
    """Increment the positive_scores or negative_scores column for a video."""
    if score_type not in ['positive_scores', 'negative_scores']:
        logger.error(f"Invalid score type: {score_type}")
        return

    connection = connect_to_db()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute(f"""
            UPDATE videos
            SET {score_type} = COALESCE({score_type}, 0) + 1
            WHERE video_id = %s
        """, (video_id,))
        connection.commit()
        cursor.close()
        connection.close()
    except Exception as error:
        logger.error(f"Error updating {score_type} for video {video_id}: {error}")

def record_vote(user_id, video_id, vote_type):
    """Record a vote in the votes table."""
    if vote_type not in ['up', 'down']:
        logger.error(f"Invalid vote type: {vote_type}")
        return

    connection = connect_to_db()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO votes (user_id, video_id, vote_type, vote_timestamp)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (user_id, video_id, vote_type))
        connection.commit()
        cursor.close()
        connection.close()
    except Exception as error:
        logger.error(f"Error recording vote: {error}")

loaded_translations = {}

# Function to get translation based on selected language
def get_translation(context, key):
    language = context.user_data.get('language', 'English')
    # Map language names to language codes
    language_codes = {
        'English': 'en',
        'Azerbaijani': 'az',
        'German': 'de'
    }
    lang_code = language_codes.get(language, 'en')

    # Load translations if not already loaded
    if lang_code not in loaded_translations:
        translation_file = os.path.join('translations', f'{lang_code}.json')
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                loaded_translations[lang_code] = json.load(f)
        except Exception as e:
            logger.error(f"Error loading translation file {translation_file}: {e}")
            loaded_translations[lang_code] = {}

    # Get the translation for the key
    return loaded_translations[lang_code].get(key, key)

# Helper Functions
def get_user_id_from_context(context, update):
    """Retrieve the user_id from context.user_data or from the database using the telegram_id."""
    user_id = context.user_data.get('user_id')
    if user_id:
        return user_id
    else:
        telegram_id = context.user_data.get('telegram_id')
        if not telegram_id:
            # This should not happen, but in case it does, restart the conversation
            return None
        db_user_id, _, _, _ = check_user_exists(telegram_id)
        if db_user_id:
            context.user_data['user_id'] = db_user_id
            return db_user_id
    return None


def create_pagination_keyboard(current_page, total_pages):
    """Create an inline keyboard for pagination."""
    keyboard = []
    row = []
    
    # Add previous page button if not on first page
    if current_page > 1:
        row.append(InlineKeyboardButton("⬅️", callback_data=f"page_{current_page-1}"))
    
    # Add current page indicator
    row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current"))
    
    # Add next page button if not on last page
    if current_page < total_pages:
        row.append(InlineKeyboardButton("➡️", callback_data=f"page_{current_page+1}"))
    
    keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


@with_fallback_timeout
async def display_sentences_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a page of sentences with pagination."""
    cancel_restarted_message(context)
    
    # Get page from context or default to 1
    page = context.user_data.get('current_page', 1)
    
    language = context.user_data.get('language', 'English')
    sentences = get_all_sentences(language)
    
    # Calculate pagination
    items_per_page = 10
    total_pages = (len(sentences) + items_per_page - 1) // items_per_page
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    # Get sentences for current page
    current_sentences = sentences[start_idx:end_idx]
    
    if not current_sentences:
        message = get_translation(context, 'no_sentences_found')
    else:
        # Create numbered list of sentences
        message = f"{get_translation(context, 'available_sentences')}\n\n"
        for idx, sentence in enumerate(current_sentences, start=start_idx + 1):
            message += f"{idx}. {sentence}\n"
    
    # Create pagination keyboard
    keyboard = create_pagination_keyboard(page, total_pages)
    
    # Add Go Back button in reply keyboard
    reply_keyboard = ReplyKeyboardMarkup(
        [[get_translation(context, 'go_back')]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    # Update or send message
    if update.callback_query:
        # Just update the text and pagination keyboard, don't send prompt again
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=keyboard
        )
    else:
        # Only for first time viewing sentences
        await update.message.reply_text(
            text=message,
            reply_markup=keyboard
        )
        await update.message.reply_text(
            get_translation(context, 'edit_menu_prompt'),
            reply_markup=reply_keyboard
        )


@with_fallback_timeout
async def handle_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pagination callback queries."""
    query = update.callback_query
    await query.answer()
    
    cancel_restarted_message(context)
    
    if query.data.startswith("page_"):
        try:
            # Store the new page in context
            page = int(query.data.split("_")[1])
            context.user_data['current_page'] = page
            await display_sentences_page(update, context)
        except Exception as e:
            logger.error(f"Error handling pagination: {e}")
            await send_message(update, get_translation(context, 'technical_difficulty'))
    
    return TRANSLATOR_MENU



async def send_message(update: Update, text: str, reply_markup=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault(RESTART_JOB_KEY, None)
    cancel_restarted_message(context)
    context.user_data.clear()
    """Start the bot by checking if the user exists and proceed accordingly."""
    user = update.effective_user
    telegram_id = user.id
    telegram_username = user.username

    context.user_data['telegram_id'] = telegram_id
    context.user_data['telegram_username'] = telegram_username
    # Check if user exists in the database using telegram_id or username
    db_user_id, username, user_language_db, user_role = check_user_exists(telegram_id, telegram_username)
    
    if db_user_id is not None:
        # User exists, update telegram_id if missing
        if telegram_id and not get_user_telegram_id(db_user_id):
            update_user_telegram_id(db_user_id, telegram_id)

        # Store user data
        context.user_data['user_id'] = db_user_id
        context.user_data['username'] = username
        context.user_data['role'] = user_role
        context.user_data['language'] = user_language_db

        # Proceed to the appropriate menu
        if user_role == 'Translator':
            return await show_translator_menu(update, context)
        else:
            return await show_user_menu(update, context)
    else:
        # New user, proceed to language selection
        reply_keyboard = [["🇬🇧 English", "🇩🇪 German", "🇦🇿 Azerbaijani"]]
        await update.message.reply_text(
            "Please select your language:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return LANGUAGE_SELECTION




async def handle_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    entered_username = update.message.text.strip()
    cancel_restarted_message(context)
    telegram_id = context.user_data['telegram_id']

    # Include that English letters should be used
    if not re.match("^[A-Za-z0-9_]{5,32}$", entered_username):
        await update.message.reply_text(
            get_translation(context, 'invalid_username'),
            reply_markup=ReplyKeyboardRemove()
        )
        return USERNAME_INPUT

    # Check if the username is already taken
    connection = connect_to_db()
    if not connection:
        await update.message.reply_text(get_translation(context, 'technical_difficulty'))
        return ConversationHandler.END

    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM public.users WHERE username = %s", (entered_username,))
    existing_user = cursor.fetchone()
    cursor.close()
    connection.close()

    if existing_user:
        await update.message.reply_text(
            get_translation(context, 'username_taken'),
            reply_markup=ReplyKeyboardRemove()
        )
        return USERNAME_INPUT

    # Username is valid and unique, store it
    context.user_data['username'] = entered_username

    # Proceed to ask for consent
    reply_keyboard = [[get_translation(context, 'confirm_button'), get_translation(context, 'cancel_button')]]
    await update.message.reply_text(
        get_translation(context, 'consent_message'),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_PERMISSION




# Prompt language selection
async def prompt_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    reply_keyboard = [["🇬🇧 English", "🇩🇪 German", "🇦🇿 Azerbaijani"]]
    await update.message.reply_text(
        "Please select your language:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return LANGUAGE_SELECTION


# Handle language selection
async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    selected_language = update.message.text

    # Map emojis to language names
    if "🇬🇧" in selected_language:
        context.user_data['language'] = 'English'
    elif "🇩🇪" in selected_language:
        context.user_data['language'] = 'German'
    elif "🇦🇿" in selected_language:
        context.user_data['language'] = 'Azerbaijani'
    else:
        # Handle invalid selection
        await update.message.reply_text("Please select a valid language option.")
        return LANGUAGE_SELECTION

    # Now, we can use the get_translation function
    user_language = context.user_data['language']
    telegram_username = context.user_data.get('telegram_username')
    telegram_id = context.user_data['telegram_id']

    if telegram_username:
        context.user_data['username'] = telegram_username
    else:
         context.user_data['username'] = "unknown"
        # Proceed to ask for consent
    reply_keyboard = [[get_translation(context, 'confirm_button'), get_translation(context, 'cancel_button')]]
    await update.message.reply_text(
        get_translation(context, 'consent_message'),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_PERMISSION





# Handle the confirmation (permission)
async def ask_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    user_response = update.message.text

    if user_response == get_translation(context, 'confirm_button'):
        # Proceed to role selection
        reply_keyboard = [[get_translation(context, 'translator_button'), get_translation(context, 'user_button')], [get_translation(context, 'cancel_button')]]
        await update.message.reply_text(
            get_translation(context, 'choose_role'),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return ROLE_SELECTION
    elif user_response == get_translation(context, 'cancel_button'):
        return await cancel(update, context)
    else:
        # Handle invalid input
        await update.message.reply_text(get_translation(context, 'invalid_option'))
        return ASK_PERMISSION



# Handle role selection
async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    user_role_text = update.message.text
    global latest_otp
    if 'awaiting_otp' in context.user_data:
        entered_otp = user_role_text

        if entered_otp == str(latest_otp):
            # OTP is correct, proceed with translator registration
            context.user_data['role'] = 'Translator'
            await update.message.reply_text(get_translation(context, 'otp_verified'))

            username = context.user_data.get('username')
            language = context.user_data.get('language', 'English')
            telegram_id = context.user_data['telegram_id']

            db_user_id = add_new_user(username, language, "Translator", telegram_id)
            if db_user_id is not None:
                context.user_data['user_id'] = db_user_id
                return await show_translator_menu(update, context)
            else:
                await update.message.reply_text(get_translation(context, 'technical_difficulty'))
                return ConversationHandler.END
        else:
            # Incorrect OTP, ask to choose role again
            await update.message.reply_text(get_translation(context, 'otp_failed'))
            del context.user_data['awaiting_otp']  # Reset OTP request
            reply_keyboard = [[get_translation(context, 'translator_button'), get_translation(context, 'user_button')], [get_translation(context, 'cancel_button')]]
            await update.message.reply_text(
                get_translation(context, 'choose_role'),
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return ROLE_SELECTION
    # Check if cancel is pressed
    if user_role_text == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    # Validate user input
    if user_role_text not in [get_translation(context, 'translator_button'), get_translation(context, 'user_button')]:
        await update.message.reply_text(
            get_translation(context, 'choose_role')
        )
        return ROLE_SELECTION
    if user_role_text == get_translation(context, 'translator_button'):
        await update.message.reply_text(
            get_translation(context, 'otp_code_prompt')  # "Please enter the OTP code to become a Translator"
        )
        context.user_data['awaiting_otp'] = True  # Set OTP verification status
        return ROLE_SELECTION
    # Map user_role_text to role_value
    role_value = 'Translator' if user_role_text == get_translation(context, 'translator_button') else 'User'
    context.user_data['role'] = role_value  # Store role in user_data
    

    username = context.user_data.get('username')
    language = context.user_data.get('language', 'English')
    telegram_id = context.user_data['telegram_id']

    # Add new user and store db_user_id
    db_user_id = add_new_user(username, language, role_value, telegram_id)
    if db_user_id is not None:
        context.user_data['user_id'] = db_user_id  # Store db_user_id
    else:
        await update.message.reply_text(get_translation(context, 'technical_difficulty'))
        return ConversationHandler.END

    # Continue with the flow depending on the role
    if role_value == 'Translator':
        return await show_translator_menu(update, context)
    else:
        return await show_user_menu(update, context)


# Handle user flow
async def handle_user_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    user_language = context.user_data.get('language', 'English')
    skipped_videos = context.user_data.get('skipped_videos', set())

    logger.info(f"Handling user flow for language: {user_language}, skipped videos: {skipped_videos}")

    # Fetch video, excluding skipped videos
    video_path, sentence = get_random_translator_video(user_language, context, exclude_ids=skipped_videos)

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

                # Add Skip and Cancel buttons
                reply_keyboard = [[
                    get_translation(context, 'cancel_button'),
                    get_translation(context, 'skip_button')
                ]]
                await update.message.reply_text(
                    get_translation(context, 'user_prompt'),
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
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
        await update.message.reply_text(get_translation(context, 'no_more_videos'))
        return await show_user_menu(update, context)

async def handle_view_user_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Handle the 'View Your Videos' option for the user with paging."""
    user_id = get_user_id_from_context(context, update)
    
    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    # Fetch user's videos and corresponding translator videos
    user_videos = get_user_videos_and_translator_videos(user_id)

    if not user_videos:
        await send_message(update, get_translation(context, 'no_uploaded_videos'))
        return await show_user_menu(update, context)

    # Store user_videos and current index in user_data
    context.user_data['user_videos'] = user_videos
    context.user_data['current_index'] = 0

    # Reset 'message_ids' to ensure a new message is sent
    context.user_data.pop('message_ids', None)

    # Send the 'Go back' message and keyboard
    reply_keyboard = ReplyKeyboardMarkup([[get_translation(context, 'go_back')]], resize_keyboard=True, one_time_keyboard=False)

    await send_message(
        update,
        get_translation(context, 'edit_menu_prompt'),
        reply_markup=reply_keyboard
    )


    # Call function to display the current user video group
    await display_current_user_video_group(update, context)

    return USER_VIEW_VIDEOS

async def display_current_user_video_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cancel_restarted_message(context)
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
        text=get_translation(context, 'delete'),
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
                media = InputMediaVideo(media=video_file, caption=get_translation(context, 'translator_video'))
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
                    text=get_translation(context, 'translator_video_not_available')
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
                    caption=get_translation(context, 'translator_video')
                )
                message_ids['translator'] = sent_message.message_id
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=get_translation(context, 'translator_video_not_available')
            )
            message_ids['translator'] = sent_message.message_id

    # Send or edit user's video with buttons
    if 'user' in message_ids:
        # Edit existing message
        message_id = message_ids['user']
        if user_video_path and os.path.exists(user_video_path):
            with open(user_video_path, 'rb') as video_file:
                media = InputMediaVideo(media=video_file, caption=get_translation(context, 'your_video'))
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
                    text=get_translation(context, 'your_video_not_available'),
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
                    caption=get_translation(context, 'your_video'),
                    reply_markup=keyboard
                )
                message_ids['user'] = sent_message.message_id
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=get_translation(context, 'your_video_not_available'),
                reply_markup=keyboard
            )
            message_ids['user'] = sent_message.message_id

    context.user_data['message_ids'] = message_ids

async def handle_next_user_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    # Increment the current index
    context.user_data['current_index'] += 1

    # Display the next user video group
    await display_current_user_video_group(update, context)

    return USER_VIEW_VIDEOS

async def handle_previous_user_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    # Decrement the current index
    context.user_data['current_index'] -= 1

    # Display the previous user video group
    await display_current_user_video_group(update, context)

    return USER_VIEW_VIDEOS

async def handle_delete_user_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
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
    cancel_restarted_message(context)
    """Display the translator menu options."""
    reply_keyboard = [
        [get_translation(context, 'view_sentences'), get_translation(context, 'write_sentence')],
        [get_translation(context, 'edit_sentences'), get_translation(context, 'vote')],
        [get_translation(context, 'generate_otp')],
        [get_translation(context, 'cancel_button')]
    ]

    await send_message(
        update,
        get_translation(context, 'menu'),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return TRANSLATOR_MENU

async def show_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Display the user menu options."""
    # Clear skipped videos when returning to the user menu
    if 'skipped_videos' in context.user_data:
        context.user_data.pop('skipped_videos')
        logger.info("Cleared skipped_videos when returning to the user menu.")
    
    reply_keyboard = [
        [get_translation(context, 'request_video'), get_translation(context, 'view_videos')],
        [get_translation(context, 'cancel_button')]
    ]

    await send_message(
        update,
        get_translation(context, 'user_menu'),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return USER_MENU

# Handle translator menu selections
async def handle_translator_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Handle translator menu selections."""
    user_choice = update.message.text

    if user_choice == get_translation(context, 'view_sentences'):
        # Set initial page in context
        context.user_data['current_page'] = 1
        await display_sentences_page(update, context)
        return TRANSLATOR_MENU

    elif user_choice == get_translation(context, 'go_back'):
    # Return to translator menu
        return await show_translator_menu(update, context)

    elif user_choice == get_translation(context, 'write_sentence'):
        
        await update.message.reply_text(
            get_translation(context, 'please_write_sentence'),
            reply_markup = ReplyKeyboardMarkup([[get_translation(context, 'cancel_button')]], resize_keyboard=True, one_time_keyboard=True)
        )
        
        return WRITE_SENTENCE

    elif user_choice == get_translation(context, 'edit_sentences'):
        return await handle_edit_sentences(update, context)

    elif user_choice == get_translation(context, 'vote'):
        return await start_voting(update, context)

    #elif user_choice == get_translation(context, 'change_language'):
    #    context.user_data['change_language'] = True
    #    reply_keyboard = [["🇬🇧 English", "🇩🇪 German", "🇦🇿 Azerbaijani"]]
    #    await update.message.reply_text(
    #        get_translation(context, 'select_new_language'),
    #        reply_markup=ReplyKeyboardMarkup(reply_keyboard,resize_keyboard=True, one_time_keyboard=True)
    #    )
    #    return LANGUAGE_SELECTION
    elif user_choice == get_translation(context, 'generate_otp'):
        return await handle_view_otp(update, context)

    elif user_choice == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    else:
        # Unrecognized input, prompt again
        await update.message.reply_text(get_translation(context, 'invalid_option'))
        return TRANSLATOR_MENU
async def handle_view_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Retrieve and display the latest OTP."""

    global latest_otp

    otp_message = f"{latest_otp}"

    await send_message(
        update,
        otp_message,
        reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'go_back')]], resize_keyboard=True, one_time_keyboard=True)
    )

    return TRANSLATOR_MENU

async def start_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the voting loop for the translator."""
    cancel_restarted_message(context)
    try:
        user_id = get_user_id_from_context(context, update)
        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        # Create the reply keyboard with the "Go Back" button
        reply_keyboard = ReplyKeyboardMarkup(
            [[get_translation(context, 'go_back')]],
            resize_keyboard=True,
            one_time_keyboard=False
        )

        # First send the keyboard message
        try:
            await send_message(
                update,
                get_translation(context, 'voting_started'),
                reply_markup=reply_keyboard
            )
        except telegram.error.NetworkError as e:
            logger.error(f"Network error when sending initial message: {e}")
            # Try one more time
            await asyncio.sleep(1)
            await send_message(
                update,
                get_translation(context, 'voting_started'),
                reply_markup=reply_keyboard
            )

        # Then proceed to send the first video
        return await send_next_video_for_voting(update, context)
    except Exception as e:
        logger.error(f"Error in start_voting: {e}")
        await send_message(update, get_translation(context, 'technical_difficulty'))
        return await show_translator_menu(update, context)

async def send_next_video_for_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send the next video for the translator to vote on."""
    cancel_restarted_message(context)
    try:
        user_id = get_user_id_from_context(context, update)
        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        user_language = context.user_data.get('language', 'English')
        
        # Add retries for getting video
        max_retries = 3
        for attempt in range(max_retries):
            try:
                video_info = get_random_video_for_voting(user_id, user_language)
                if video_info:
                    video_id, file_path, sentence_content = video_info
                    if not os.path.exists(file_path):
                        logger.error(f"Video file not found: {file_path}")
                        continue

                    context.user_data['current_voting_video_id'] = video_id

                    buttons = [
                        [
                            InlineKeyboardButton(text=get_translation(context, 'up_vote'), callback_data='vote_up'),
                            InlineKeyboardButton(text=get_translation(context, 'down_vote'), callback_data='vote_down')
                        ]
                    ]
                    keyboard = InlineKeyboardMarkup(buttons)

                    with open(file_path, 'rb') as video_file:
                        try:
                            sent_message = await update.effective_message.reply_video(
                                video_file,
                                caption=get_translation(context, 'voting_sentence').format(sentence_content),
                                reply_markup=keyboard
                            )
                            context.user_data['current_voting_message_id'] = sent_message.message_id
                            return VOTING
                        except telegram.error.NetworkError as e:
                            logger.error(f"Network error when sending video (attempt {attempt + 1}): {e}")
                            if attempt == max_retries - 1:
                                raise
                            await asyncio.sleep(1)  # Wait before retry
                            continue
                else:
                    await send_message(update, get_translation(context, 'no_more_videos_to_vote'))
                    return await show_translator_menu(update, context)
            except Exception as e:
                logger.error(f"Error in attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise

        # If we get here, all retries failed
        await send_message(update, get_translation(context, 'technical_difficulty'))
        return await show_translator_menu(update, context)

    except Exception as e:
        logger.error(f"Error in send_next_video_for_voting: {e}")
        await send_message(update, get_translation(context, 'technical_difficulty'))
        return await show_translator_menu(update, context)



async def handle_voting_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    user_input = update.message.text.strip() if update.message else None

    user_id = get_user_id_from_context(context, update)
    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    video_id = context.user_data.get('current_voting_video_id')
    if video_id is None:
        await send_message(update, get_translation(context, 'voting_error'))
        return await show_translator_menu(update, context)

    if user_input == get_translation(context, 'up_vote'):
        # Update positive_scores
        increment_video_score(video_id, 'positive_scores')
        # Record the vote in votes table
        record_vote(user_id, video_id, 'up')
    elif user_input == get_translation(context, 'down_vote'):
        # Update negative_scores
        increment_video_score(video_id, 'negative_scores')
        # Record the vote in votes table
        record_vote(user_id, video_id, 'down')
    elif user_input == get_translation(context, 'go_back'):
        # Remove the reply keyboard
        await update.message.reply_text(
            get_translation(context, 'returning_to_menu'),
            reply_markup=ReplyKeyboardRemove()
        )
        # Return to the translator menu
        return await show_translator_menu(update, context)
    else:
        # Unrecognized input, prompt again
        await send_message(update, get_translation(context, 'invalid_option'))
        return VOTING

    # Delete the video message if necessary
    if context.user_data.get('current_voting_message_id'):
        chat_id = update.effective_chat.id
        message_id = context.user_data['current_voting_message_id']
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
        del context.user_data['current_voting_message_id']

    # Send the next video
    return await send_next_video_for_voting(update, context)




async def handle_vote_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    user_id = get_user_id_from_context(context, update)
    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    video_id = context.user_data.get('current_voting_video_id')
    if video_id is None:
        await send_message(update, get_translation(context, 'voting_error'))
        return await show_translator_menu(update, context)

    # Update positive_scores
    increment_video_score(video_id, 'positive_scores')

    # Record the vote in votes table
    record_vote(user_id, video_id, 'up')

    # Delete the message with the video and buttons
    await query.message.delete()

    # Send the next video
    return await send_next_video_for_voting(update, context)

async def handle_vote_down(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    user_id = get_user_id_from_context(context, update)
    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    video_id = context.user_data.get('current_voting_video_id')
    if video_id is None:
        await send_message(update, get_translation(context, 'voting_error'))
        return await show_translator_menu(update, context)

    # Update negative_scores
    increment_video_score(video_id, 'negative_scores')

    # Record the vote in votes table
    record_vote(user_id, video_id, 'down')

    # Delete the message with the video and buttons
    await query.message.delete()

    # Send the next video
    return await send_next_video_for_voting(update, context)


async def voting_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    user_input = update.message.text.strip() if update.message else None

    if user_input == get_translation(context, 'go_back'):
        # Delete the video message if necessary
        if context.user_data.get('current_voting_message_id'):
            chat_id = update.effective_chat.id
            message_id = context.user_data['current_voting_message_id']
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(f"Error deleting message {message_id}: {e}")
            del context.user_data['current_voting_message_id']

        # Remove the reply keyboard
        await update.message.reply_text(
            get_translation(context, 'returning_to_menu'),
            reply_markup=ReplyKeyboardRemove()
        )

        # Return to the translator menu
        return await show_translator_menu(update, context)
    else:
        # Unrecognized input, prompt again
        await send_message(update, get_translation(context, 'invalid_option'))
        return VOTING




async def handle_go_back_from_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    # Delete the video message if necessary
    if context.user_data.get('current_voting_message_id'):
        chat_id = update.effective_chat.id
        message_id = context.user_data['current_voting_message_id']
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
        del context.user_data['current_voting_message_id']

    # Return to the translator menu
    return await show_translator_menu(update, context)



# Handle user menu selections
async def handle_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Handle user menu selections."""
    user_choice = update.message.text

    if user_choice == get_translation(context, 'request_video'):
        return await handle_user_flow(update, context)
    elif user_choice == get_translation(context, 'view_videos'):
        return await handle_view_user_videos(update, context)
    elif user_choice == get_translation(context, 'cancel_button'):
        return await cancel(update, context)
    else:
        # Unrecognized input
        await update.message.reply_text(get_translation(context, 'invalid_option'))
        return await show_user_menu(update, context)

async def user_videos_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Handle navigation within the 'View Your Videos' menu."""
    user_input = update.message.text if update.message else None
    if user_input == get_translation(context, 'go_back'):
        # Go back to user menu
        return await show_user_menu(update, context)
    else:
        # Unrecognized input, prompt again
        await send_message(update, get_translation(context, 'invalid_option'))
        return USER_VIEW_VIDEOS

# Handle editing sentences
async def handle_edit_sentences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Edit Sentences' option for the translator with paging."""
    cancel_restarted_message(context)
    user_id = get_user_id_from_context(context, update)
    
    if not user_id:
        await send_message(update, get_translation(context, 'bot_restarted'))
        return ConversationHandler.END

    language = context.user_data.get('language', 'English')

    connection = connect_to_db()
    if not connection:
        return await show_translator_menu(update, context)

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                s.sentence_id,
                s.sentence_content,
                v.file_path,
                COALESCE(v.positive_scores, 0) as upvotes,
                COALESCE(v.negative_scores, 0) as downvotes
            FROM sentences s
            LEFT JOIN videos v ON s.sentence_id = v.text_id
            WHERE s.user_id = %s AND s.sentence_language = %s
            ORDER BY s.sentence_id DESC
        """, (user_id, language))
        
        results = cursor.fetchall()
        cursor.close()
        connection.close()

        if not results:
            await send_message(update, get_translation(context, 'no_sentences_found'))
            return await show_translator_menu(update, context)

        # Store the results in context
        context.user_data['sentences'] = [
            {
                'id': row[0],
                'sentence': row[1],
                'video_path': row[2],
                'upvotes': row[3],
                'downvotes': row[4]
            }
            for row in results
        ]
        
        # Reset pagination state
        context.user_data['current_page'] = 1
        context.user_data['items_per_page'] = 5

        # Display the first page
        await display_edit_sentences_page(update, context)
        return EDIT_SENTENCES

    except Exception as error:
        logger.error(f"Error in handle_edit_sentences: {error}")
        await send_message(update, get_translation(context, 'technical_difficulty'))
        return await show_translator_menu(update, context)

async def display_edit_sentences_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a page of sentences with voting information."""
    sentences = context.user_data.get('sentences', [])
    current_page = context.user_data.get('current_page', 1)
    items_per_page = context.user_data.get('items_per_page', 5)
    
    total_items = len(sentences)
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_items = sentences[start_idx:end_idx]
    total_pages = (total_items + items_per_page - 1) // items_per_page

    message_lines = [f"Cəmi Cümlələr: {total_items}\n"]
    
    for idx, item in enumerate(current_items, start=start_idx + 1):
        message_lines.append(
            f"{idx}. {item['sentence']}\n"
            f"    👍: {item['upvotes']}    👎: {item['downvotes']}\n"
        )
    
    message_text = "\n".join(message_lines)

    # Create buttons
    button_rows = []
    
    # Item selection buttons using absolute indices
    item_buttons = [
        InlineKeyboardButton(
            text=str(i),
            callback_data=f"view_item_{i-1}"
        ) for i in range(start_idx + 1, start_idx + len(current_items) + 1)
    ]
    if item_buttons:
        button_rows.append(item_buttons)
    
    # Navigation buttons in Azerbaijani
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Əvvəlki", callback_data="prev_page"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Növbəti ➡️", callback_data="next_page"))
    if nav_buttons:
        button_rows.append(nav_buttons)
    
    keyboard = InlineKeyboardMarkup(button_rows)

    # Send or update message
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(
                text=message_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            await update.callback_query.message.reply_text(
                text=message_text,
                reply_markup=keyboard
            )
    else:
        # First time display - also show the Go Back button
        reply_keyboard = ReplyKeyboardMarkup(
            [[get_translation(context, 'go_back')]],
            resize_keyboard=True
        )
        
        await send_message(
            update,
            message_text,
            reply_markup=keyboard
        )
        await send_message(
            update,
            get_translation(context, 'edit_menu_prompt'),
            reply_markup=reply_keyboard
        )

async def handle_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle prev/next page navigation."""
    query = update.callback_query
    await query.answer()
    
    current_page = context.user_data.get('current_page', 1)
    
    if query.data == "prev_page":
        context.user_data['current_page'] = max(1, current_page - 1)
    elif query.data == "next_page":
        total_items = len(context.user_data.get('sentences', []))
        items_per_page = context.user_data.get('items_per_page', 5)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        context.user_data['current_page'] = min(total_pages, current_page + 1)
    
    await display_edit_sentences_page(update, context)
    return EDIT_SENTENCES

async def show_sentence_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detail view for a selected sentence."""
    query = update.callback_query
    await query.answer()
    
    match = re.match(r"view_item_(\d+)", query.data)
    if not match:
        return EDIT_SENTENCES
    
    item_idx = int(match.group(1))
    sentences = context.user_data.get('sentences', [])
    
    if item_idx >= len(sentences):
        await query.message.reply_text("Item not found.")
        return EDIT_SENTENCES
    
    item = sentences[item_idx]
    
    # Create keyboard for detail view
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{item['id']}"),
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_list")
        ]
    ])
    
    # Delete the list message
    await query.message.delete()
    
    # Send video with just the sentence as caption
    if item['video_path'] and os.path.exists(item['video_path']):
        with open(item['video_path'], 'rb') as video_file:
            sent_message = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video_file,
                caption=item['sentence'],  # Just show the sentence
                reply_markup=keyboard
            )
            context.user_data['detail_message_id'] = sent_message.message_id
    else:
        await query.message.reply_text(
            "Video not found.",
            reply_markup=keyboard
        )
    
    return EDIT_SENTENCES


async def fetch_sentences_with_votes(user_id: int, language: str) -> list:
    """Fetch sentences with their vote counts."""
    connection = connect_to_db()
    if not connection:
        return []
        
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                s.sentence_id,
                s.sentence_content,
                v.file_path,
                COALESCE(v.positive_scores, 0) as upvotes,
                COALESCE(v.negative_scores, 0) as downvotes
            FROM sentences s
            LEFT JOIN videos v ON s.sentence_id = v.text_id
            WHERE s.user_id = %s AND s.sentence_language = %s
            ORDER BY s.sentence_id DESC
        """, (user_id, language))
        
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return [
            {
                'id': row[0],
                'sentence': row[1],
                'video_path': row[2],
                'upvotes': row[3],
                'downvotes': row[4]
            }
            for row in results
        ]
    except Exception as error:
        logger.error(f"Error fetching sentences with votes: {error}")
        return []

async def display_sentences_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a page of sentences with pagination."""
    cancel_restarted_message(context)
    
    # Get page from context or default to 1
    page = context.user_data.get('current_page', 1)
    
    language = context.user_data.get('language', 'English')
    sentences = get_all_sentences(language)
    
    # Calculate pagination
    items_per_page = 10
    total_pages = (len(sentences) + items_per_page - 1) // items_per_page
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    # Get sentences for current page
    current_sentences = sentences[start_idx:end_idx]
    
    if not current_sentences:
        message = get_translation(context, 'no_sentences_found')
    else:
        # Create numbered list of sentences
        message = f"{get_translation(context, 'available_sentences')}\n\n"
        for idx, sentence in enumerate(current_sentences, start=start_idx + 1):
            message += f"{idx}. {sentence}\n"
    
    # Create pagination keyboard
    keyboard = []
    row = []
    
    # Add previous page button if not on first page
    if page > 1:
        row.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))
    
    # Add current page indicator
    row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="current"))
    
    # Add next page button if not on last page
    if page < total_pages:
        row.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))
    
    keyboard.append(row)
    markup = InlineKeyboardMarkup(keyboard)
    
    # Add Go Back button in reply keyboard
    reply_keyboard = ReplyKeyboardMarkup(
        [[get_translation(context, 'go_back')]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    # Update or send message
    if update.callback_query:
        # Just update the text and pagination keyboard, don't send prompt again
        try:
            await update.callback_query.message.edit_text(
                text=message,
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Error updating message: {e}")
    else:
        # Only for first time viewing sentences
        try:
            await update.message.reply_text(
                text=message,
                reply_markup=markup
            )
            await update.message.reply_text(
                get_translation(context, 'edit_menu_prompt'),
                reply_markup=reply_keyboard
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await send_message(update, get_translation(context, 'technical_difficulty'))
            return await show_translator_menu(update, context)



async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detail view for a selected item."""
    query = update.callback_query
    await query.answer()
    
    match = re.match(r"view_item_(\d+)", query.data)
    if not match:
        return EDIT_SENTENCES
        
    item_idx = int(match.group(1))
    sentences = context.user_data.get('sentences', [])
    
    if item_idx >= len(sentences):
        await query.message.reply_text("Item not found.")
        return EDIT_SENTENCES
        
    item = sentences[item_idx]
    
    # Create keyboard for detail view
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Delete", callback_data=f"delete_{item['id']}"),
            InlineKeyboardButton("Go Back", callback_data="back_to_list")
        ]
    ])
    
    # Delete the list message
    await query.message.delete()
    
    # Send video with caption
    if item['video_path'] and os.path.exists(item['video_path']):
        with open(item['video_path'], 'rb') as video_file:
            sent_message = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video_file,
                caption=f"Sentence: {item['sentence']}\nUp votes: {item['upvotes']} Down votes: {item['downvotes']}",
                reply_markup=keyboard
            )
            context.user_data['detail_message_id'] = sent_message.message_id
    else:
        await query.message.reply_text(
            "Video not found.",
            reply_markup=keyboard
        )
    
    return EDIT_SENTENCES

async def handle_back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle returning to the list view from detail view."""
    query = update.callback_query
    await query.answer()
    
    # Delete the detail view message
    if 'detail_message_id' in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['detail_message_id']
            )
            del context.user_data['detail_message_id']
        except Exception as e:
            logger.error(f"Error deleting detail message: {e}")
    
    # Display the current page again
    await display_edit_sentences_page(update, context)
    return EDIT_SENTENCES

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pagination navigation."""
    query = update.callback_query
    await query.answer()
    
    current_page = context.user_data.get('current_page', 1)
    
    if query.data == "prev_page":
        context.user_data['current_page'] = max(1, current_page - 1)
    elif query.data == "next_page":
        total_items = len(context.user_data.get('sentences', []))
        items_per_page = context.user_data.get('items_per_page', 5)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        context.user_data['current_page'] = min(total_pages, current_page + 1)
    
    await display_sentences_page(update, context)
    return EDIT_SENTENCES

async def display_current_sentence_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cancel_restarted_message(context)
    sentences_videos = context.user_data.get('sentences_videos', [])
    current_index = context.user_data.get('current_index', 0)

    if len(sentences_videos) == 0:
        # No sentences left, return to menu
        await send_message(update, get_translation(context, 'no_sentences_found'))
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
        text=get_translation(context, 'delete_sentence'),
        callback_data=f"delete_{sentence_id}"
    )
    buttons.append([delete_button])

    # Add 'Previous' and 'Next' buttons in one horizontal line
    nav_buttons = []
    if current_index > 0:
        prev_button = InlineKeyboardButton(
            text=get_translation(context, 'previous'),
            callback_data="previous_sentence"
        )
        nav_buttons.append(prev_button)
    if current_index < len(sentences_videos) - 1:
        next_button = InlineKeyboardButton(
            text=get_translation(context, 'next'),
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
            await send_message(update, get_translation(context, 'video_not_found'))
            return
    else:
        # Send new message
        if video_file_path and os.path.exists(video_file_path):
            with open(video_file_path, 'rb') as video_file:
                sent_message = await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=f"• {sentence_content}",
                    reply_markup=keyboard
                )
                message_id = sent_message.message_id
                context.user_data['message_id'] = message_id
        else:
            await send_message(update, get_translation(context, 'video_not_found'))
            return

# Handle deletion of sentences
async def handle_delete_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle deletion of a sentence and refresh the view."""
    cancel_restarted_message(context)
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

        # Get updated list of sentences
        language = context.user_data.get('language', 'English')
        connection = connect_to_db()
        if not connection:
            return await show_translator_menu(update, context)

        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT 
                    s.sentence_id,
                    s.sentence_content,
                    v.file_path,
                    COALESCE(v.positive_scores, 0) as upvotes,
                    COALESCE(v.negative_scores, 0) as downvotes
                FROM sentences s
                LEFT JOIN videos v ON s.sentence_id = v.text_id
                WHERE s.user_id = %s AND s.sentence_language = %s
                ORDER BY s.sentence_id DESC
            """, (user_id, language))
            
            results = cursor.fetchall()
            cursor.close()
            connection.close()

            # Delete the current view
            try:
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

            # If there are no more sentences
            if not results:
                await query.message.reply_text(
                    get_translation(context, 'no_sentences_found'),
                    reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'go_back')]], resize_keyboard=True)
                )
                return EDIT_SENTENCES

            # Update the sentences in context
            context.user_data['sentences'] = [
                {
                    'id': row[0],
                    'sentence': row[1],
                    'video_path': row[2],
                    'upvotes': row[3],
                    'downvotes': row[4]
                }
                for row in results
            ]

            # Adjust current page if necessary
            sentences = context.user_data['sentences']
            current_page = context.user_data.get('current_page', 1)
            items_per_page = context.user_data.get('items_per_page', 5)
            total_pages = (len(sentences) + items_per_page - 1) // items_per_page
            
            if current_page > total_pages and total_pages > 0:
                context.user_data['current_page'] = total_pages

            # Send a new message with updated list
            await display_edit_sentences_page(update, context)
            return EDIT_SENTENCES

        except Exception as error:
            logger.error(f"Error updating view after deletion: {error}")
            await send_message(update, get_translation(context, 'technical_difficulty'))
            return await show_translator_menu(update, context)

    else:
        logger.error(f"Invalid callback data: {data}")
        return EDIT_SENTENCES


async def handle_next_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    # Increment the current index
    context.user_data['current_index'] += 1

    # Display the next sentence-video pair
    await display_current_sentence_video(update, context)

    return EDIT_SENTENCES

async def handle_previous_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    query = update.callback_query
    await query.answer()

    # Decrement the current index
    context.user_data['current_index'] -= 1

    # Display the previous sentence-video pair
    await display_current_sentence_video(update, context)

    return EDIT_SENTENCES

# Handle navigation in 'Edit Sentences' menu
async def edit_sentences_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle navigation within the Edit Sentences menu."""
    cancel_restarted_message(context)
    user_input = update.message.text if update.message else None

    if user_input == get_translation(context, 'go_back'):
        return await show_translator_menu(update, context)
    else:
        await send_message(update, get_translation(context, 'edit_menu_prompt'))
        return EDIT_SENTENCES

# Handle new sentence input from translator
async def handle_write_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Handle new sentence input from translator."""
    new_sentence = update.message.text
    # Check if cancel is pressed
    if new_sentence == get_translation(context, 'cancel_button'):
        return await cancel(update, context)
    # Proceed with handling the sentence if it's not a cancellation
    if check_sentence_exists(new_sentence):
        await update.message.reply_text(get_translation(context, 'sentence_exists'))
        return await show_translator_menu(update, context)
    else:
        context.user_data['sentence'] = new_sentence
        await update.message.reply_text(get_translation(context, 'video_prompt'))
        return TRANSLATOR_UPLOAD

# Function to generate the next available filename based on the username
def get_next_available_filename(directory, username, role, user_id):
    """Find the next available video filename for the user to avoid conflicts."""
    prefix = f"{role.lower()}_video_{user_id}_{username}_"
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
    cancel_restarted_message(context)
    """Download video from Telegram to local file system."""
    new_file = await context.bot.get_file(video.file_id)
    await new_file.download_to_drive(file_path)

# Handle video upload for translators
async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    if update.message.video:
        user_id = get_user_id_from_context(context, update)
        username = context.user_data.get('username')

        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        file_path = get_next_available_filename(TRANSLATOR_DIR, username, "translator", user_id)

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

    elif update.message.text:
        user_input = update.message.text
        if user_input == get_translation(context, 'cancel_button'):
            return await cancel(update, context)
        else:
            await update.message.reply_text(get_translation(context, 'valid_video_error'))
            return TRANSLATOR_UPLOAD

    else:
        await update.message.reply_text(get_translation(context, 'valid_video_error'))
        return TRANSLATOR_UPLOAD

# Handle user video request and upload
async def user_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    if update.message.video:
        user_id = get_user_id_from_context(context, update)
        username = context.user_data.get('username')
        user_language = context.user_data.get('language', 'English')
        translator_video_id = context.user_data.get('current_translator_video_id')

        if not user_id:
            await send_message(update, get_translation(context, 'bot_restarted'))
            return ConversationHandler.END

        # Retrieve the text_id of the translator's video
        translator_text_id = get_video_text_id(translator_video_id)

        file_path = get_next_available_filename(USER_DIR, username, "user", user_id)
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
            )
            return await show_user_menu(update, context)

    # Handle Skip button
    elif update.message.text == get_translation(context, 'skip_button'):
        current_video_id = context.user_data.get('current_translator_video_id')

        if current_video_id:
            # Add the current video to the skipped list
            skipped_videos = context.user_data.get('skipped_videos', set())
            skipped_videos.add(current_video_id)
            context.user_data['skipped_videos'] = skipped_videos
            logger.info(f"Skipped video ID: {current_video_id}")

        # Fetch the next video
        return await handle_user_flow(update, context)

    elif update.message.text == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    else:
        await update.message.reply_text(get_translation(context, 'valid_video_error'))
        return USER_REQUEST

# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cancel_restarted_message(context)
    """Handle cancellation of the conversation."""
    await update.message.reply_text(
        get_translation(context, 'cancel_message'),
        reply_markup=ReplyKeyboardRemove()
    )

    # Provide the "Start" button after cancellation
    await update.message.reply_text(
        get_translation(context, 'restart_message'),
        reply_markup=ReplyKeyboardMarkup([[get_translation(context, 'start_button')]], resize_keyboard=True, one_time_keyboard=True)
    )
    return ConversationHandler.END



def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOTOKEN).build()
    job_queue = application.job_queue
    job_queue.run_repeating(generate_random_otp, interval=300, first=1)
    # Set up conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE_SELECTION: [MessageHandler(filters.TEXT, with_fallback_timeout(language_selection))],
            USERNAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(handle_username_input))],
            ASK_PERMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(ask_permission))],
            ROLE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(role_selection))],
            TRANSLATOR_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(handle_translator_menu)),
                CallbackQueryHandler(with_fallback_timeout(handle_pagination_callback), pattern=r"^page_\d+$"),
                CallbackQueryHandler(with_fallback_timeout(handle_pagination_callback), pattern="^current$"),
            ],
            WRITE_SENTENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(handle_write_sentence))],
            TRANSLATOR_UPLOAD: [
                MessageHandler(filters.ALL | (filters.TEXT & ~filters.COMMAND), with_fallback_timeout(handle_video_upload)),
                CommandHandler("start", start)
            ],
            USER_REQUEST: [
                MessageHandler(filters.ALL | (filters.TEXT & ~filters.COMMAND), with_fallback_timeout(user_video_request)),
                CommandHandler("start", start)
            ],
            USER_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(handle_user_menu))],
            USER_VIEW_VIDEOS: [
                CallbackQueryHandler(with_fallback_timeout(handle_delete_user_video), pattern=r"^delete_user_video_\d+$"),
                CallbackQueryHandler(with_fallback_timeout(handle_next_user_video), pattern="^next_user_video$"),
                CallbackQueryHandler(with_fallback_timeout(handle_previous_user_video), pattern="^previous_user_video$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(user_videos_navigation))
            ],
            EDIT_SENTENCES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_sentences_navigation),
                CallbackQueryHandler(handle_delete_sentence, pattern=r"^delete_\d+$"),
                CallbackQueryHandler(show_sentence_detail, pattern=r"^view_item_\d+$"),
                CallbackQueryHandler(handle_back_to_list, pattern="^back_to_list$"),
                CallbackQueryHandler(handle_page_navigation, pattern="^(prev|next)_page$"),
            ],
            VOTING: [
                CallbackQueryHandler(with_fallback_timeout(handle_vote_up), pattern='^vote_up$'),
                CallbackQueryHandler(with_fallback_timeout(handle_vote_down), pattern='^vote_down$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, with_fallback_timeout(voting_navigation))
            ],

        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(MessageHandler(filters.ALL, global_fallback_handler), group=0)
    application.add_handler(conv_handler, group=1)

    # Test the database connection during bot initialization
    if connect_to_db():
        logger.info("Database connection tested successfully.")
    else:
        logger.error("Failed to connect to the database. Please check your database settings.")
    

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()