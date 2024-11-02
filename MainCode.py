import logging
import os
import re
import psycopg2
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for conversation flow
LANGUAGE_SELECTION, ASK_PERMISSION, ROLE_SELECTION, TRANSLATOR_INPUT_SENTENCE, TRANSLATOR_UPLOAD, USER_REQUEST = range(6)
TRANSLATOR_MENU, VIEW_SENTENCES, WRITE_SENTENCE, EDIT_SENTENCES = range(6, 10)  # Continue from your last state number

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
            dbname="postgres",  # Updated to 'postgres'
            user="postgres",
            password="ubuntu",
            host="localhost",
            port="5432"
        )
        logger.info("Connected to the PostgreSQL database successfully.")
        return connection
    except Exception as error:
        logger.error(f"Error connecting to the database: {error}")
        return None

# Check if user exists in the database and return their language if they exist
def check_user_exists(username):
    """Checks if a user exists in the database by username and returns the user's language (country) if they exist."""
    connection = connect_to_db()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT country FROM public.users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return result[0]  # Return the language (country) if the user exists
        return None
    except Exception as error:
        logger.error(f"Error checking user in the database: {error}")
        return None

# Add a new user to the database
def add_new_user(username, language):
    """Inserts a new user into the database after getting consent."""
    connection = connect_to_db()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO public.users (username, country, consent_status)
            VALUES (%s, %s, %s)
        """, (username, language, True))  # Storing True for consent_status
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"New user {username} added to the database.")
    except Exception as error:
        logger.error(f"Error adding new user to the database: {error}")


def get_user_language(username):
    """Retrieves user's language (country) from the database."""
    connection = connect_to_db()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT country FROM public.users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return result[0]
        return None
    except Exception as error:
        logger.error(f"Error getting user language from database: {error}")
        return None

def save_video_info(username, file_path, role, language, sentence=None):
    """Saves video information and associated sentence to the database."""
    connection = connect_to_db()
    full_file_path=file_path.replace(".","/home/ubuntu/telegramBOT", 1)
    if not connection:
        return
    try:
        # First, if there's a sentence, save it to sentences table
        sentence_id = None
        if sentence:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO public.sentences (sentence_language, sentence_content)
                VALUES (%s, %s) RETURNING sentence_id
            """, (language, sentence))
            sentence_id = cursor.fetchone()[0]
            connection.commit()

        # Then save video information
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO public.videos 
            (username, file_path, text_id, language, uploaded_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (username, full_file_path, sentence_id, language))
        connection.commit()
        cursor.close()
        connection.close()
        logger.info(f"Video and sentence information saved for user {username}")
    except Exception as error:
        logger.error(f"Error saving video information to database: {error}")


def get_random_translator_video():
    """Fetches a random video from the database that was uploaded by a translator."""
    connection = connect_to_db()
    if not connection:
        return None, None

    try:
        cursor = connection.cursor()
        # Query to get a random video uploaded by a translator along with its associated sentence
        cursor.execute("""
            SELECT v.file_path, s.sentence_content 
            FROM public.videos v
            LEFT JOIN public.sentences s ON v.text_id = s.sentence_id
            WHERE v.file_path LIKE '%/Translator/%'
            ORDER BY RANDOM()
            LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return result[0], result[1]  # Returns tuple of (file_path, sentence)
        return None, None
    except Exception as error:
        logger.error(f"Error fetching random translator video: {error}")
        return None, None

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
        }
    }
    return menu_translations

async def show_translator_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the translator menu options."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')
    
    reply_keyboard = [
        [menu_translations['view_sentences'][language], menu_translations['write_sentence'][language]],
        [menu_translations['edit_sentences'][language], menu_translations['change_language'][language]],
        [get_translation(context, 'cancel_button')]
    ]
    
    await update.message.reply_text(
        menu_translations['menu'][language],
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return TRANSLATOR_MENU

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

async def handle_translator_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle translator menu selections."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')
    user_choice = update.message.text

    if user_choice == menu_translations['view_sentences'][language]:
        sentences = get_all_sentences(language)
        if sentences:
            message = "Available sentences:\n\n" + "\n".join(f"- {sentence}" for sentence in sentences)
        else:
            message = "No sentences found for your language."
        await update.message.reply_text(message)
        return await show_translator_menu(update, context)

    elif user_choice == menu_translations['write_sentence'][language]:
        await update.message.reply_text("Please write your sentence:")
        return WRITE_SENTENCE

    elif user_choice == menu_translations['change_language'][language]:
        reply_keyboard = [["🇬🇧 English", "🇩🇪 German", "🇦🇿 Azerbaijani"]]
        await update.message.reply_text(
            "Please select your new language:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return LANGUAGE_SELECTION

    elif user_choice == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    return TRANSLATOR_MENU

async def handle_write_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new sentence input from translator."""
    menu_translations = add_translator_menu_translations()
    language = context.user_data.get('language', 'English')
    new_sentence = update.message.text

    if check_sentence_exists(new_sentence):
        await update.message.reply_text(menu_translations['sentence_exists'][language])
        return await show_translator_menu(update, context)
    else:
        context.user_data['sentence'] = new_sentence
        await update.message.reply_text(get_translation(context, 'video_prompt'))
        return TRANSLATOR_UPLOAD

# Define translations
translations = {
    'English': {
        'consent_message': "Hi! To proceed, we need your consent to use the videos you provide for translation. Please confirm.",
        'confirm_button': "Confirm",
        'cancel_button': "Cancel",
        'choose_role': "Are you a Translator or a User?",
        'translator_button': "Translator",
        'user_button': "User",
        'translator_prompt': "Please write the sentence you want to translate.",
        'video_prompt': "Now, please upload the video for the translation.",
        'user_prompt': "Please upload your video for translation.",
        'valid_video_error': "Please upload a valid video.",
        'thank_you_video': "Video received. Thank you! To start again, type /start.",
        'thank_you_response': "Your response video has been received. Thank you!",
        'cancel_message': "Operation canceled. To start again, type /start.",
        'no_videos_available': "Sorry, no translator videos are available at the moment.",
        'translated_sentence': "Translated sentence: {}",
        'continue_exchange': "Thank you for your video! Here's another translation for you:",
        'no_more_videos': "There are no more translator videos available at the moment."
    },
    'German': {
        'consent_message': "Hallo! Um fortzufahren, benötigen wir Ihre Zustimmung zur Verwendung der von Ihnen bereitgestellten Videos zur Übersetzung. Bitte bestätigen Sie.",
        'confirm_button': "Bestätigen",
        'cancel_button': "Abbrechen",
        'choose_role': "Sind Sie ein Übersetzer oder ein Benutzer?",
        'translator_button': "Übersetzer",
        'user_button': "Benutzer",
        'translator_prompt': "Bitte schreiben Sie den Satz, den Sie übersetzen möchten.",
        'video_prompt': "Laden Sie nun bitte das Video für die Übersetzung hoch.",
        'user_prompt': "Bitte laden Sie Ihr Video zur Übersetzung hoch.",
        'valid_video_error': "Bitte laden Sie ein gültiges Video hoch.",
        'thank_you_video': "Video empfangen. Vielen Dank! Um neu zu starten, tippen Sie /start.",
        'thank_you_response': "Ihr Antwortvideo wurde empfangen. Vielen Dank!",
        'cancel_message': "Vorgang abgebrochen. Um neu zu starten, tippen Sie /start.",
        'no_videos_available': "Entschuldigung, derzeit sind keine Übersetzervideos verfügbar.",
        'translated_sentence': "Übersetzter Satz: {}",
        'restart_message': "Um neu zu starten, drücken Sie die /start-Taste.",
        'continue_exchange': "Thank you for your video! Here's another translation for you to respond to:",
        'no_more_videos': "There are no more translator videos available at the moment. Type /start to begin again when more videos are available.",
        'stop_exchange': "To stop receiving videos and end the exchange, type /start",
        'continue_exchange': "Danke für Ihr Video! Hier ist eine weitere Übersetzung:",
        'no_more_videos': "Derzeit sind keine weiteren Übersetzervideos verfügbar."
    
        
    },
    'Azerbaijani': {
        'consent_message': "Salam! Davam etmək üçün təqdim etdiyiniz videoların tərcüməsi üçün istifadəsinə razılıq verməyiniz lazımdır. Təsdiq edin.",
        'confirm_button': "Təsdiq edin",
        'cancel_button': "Ləğv edin",
        'choose_role': "Tərcüməçi, yoxsa istifadəçisiniz?",
        'translator_button': "Tərcüməçi",
        'user_button': "İstifadəçi",
        'translator_prompt': "Tərcümə etmək istədiyiniz cümləni yazın.",
        'video_prompt': "İndi tərcümə üçün videonuzu yükləyin.",
        'user_prompt': "Tərcümə üçün videonuzu yükləyin.",
        'valid_video_error': "Etibarlı bir video yükləyin.",
        'thank_you_video': "Video qəbul edildi. Çox sağ olun! Yenidən başlamaq üçün /start yazın.",
        'thank_you_response': "Cavab videonuz qəbul edildi. Çox sağ olun!",
        'cancel_message': "Əməliyyat ləğv edildi. Yenidən başlamaq üçün /start yazın.",
        'no_videos_available': "Üzr istəyirik, hal-hazırda tərcüməçi videoları mövcud deyil.",
        'translated_sentence': "Tərcümə edilmiş cümlə: {}",
        'restart_message': "Yenidən başlamaq üçün /start düyməsini basın.",
        'continue_exchange': "Videonuz üçün təşəkkür edirik! Növbəti tərcümə budur:",
        'no_more_videos': "Hal-hazırda başqa tərcüməçi videoları mövcud deyil."
    
    }
}

# Function to get translation based on selected language
def get_translation(context, key):
    language = context.user_data.get('language', 'English')
    return translations[language][key]

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bot by checking if user exists and using their language, or asking for language selection if new."""
    username = update.message.from_user.username

    # Check if the user already exists in the database and retrieve their language
    user_language = check_user_exists(username)

    if user_language:
        # If the user exists, set their language automatically
        context.user_data['language'] = user_language
        await update.message.reply_text(
            f"Welcome back! Using your preferred language: {user_language}.",
        )
        
        # Proceed directly to role selection
        reply_keyboard = [[get_translation(context, 'translator_button'), get_translation(context, 'user_button')], [get_translation(context, 'cancel_button')]]
        await update.message.reply_text(
            get_translation(context, 'choose_role'),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return ROLE_SELECTION

    # If the user does not exist, ask for language selection
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

    # Proceed to ask for user consent after language selection
    reply_keyboard = [[get_translation(context, 'confirm_button'), get_translation(context, 'cancel_button')]]
    await update.message.reply_text(
        get_translation(context, 'consent_message'),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ASK_PERMISSION

# Handle the confirmation (permission)
async def ask_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text
    username = update.message.from_user.username

    if user_response == get_translation(context, 'confirm_button'):
        # Add new user to the database after consent
        add_new_user(username, context.user_data['language'])

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
    user_role = update.message.text
    
    # Check if cancel is pressed
    if user_role == get_translation(context, 'cancel_button'):
        return await cancel(update, context)
    
    # Validate user input
    if user_role not in [get_translation(context, 'translator_button'), get_translation(context, 'user_button')]:
        await update.message.reply_text(
            get_translation(context, 'choose_role')
        )
        return ROLE_SELECTION
    
    context.user_data['role'] = user_role  # Store role in user_data

    # Continue with the flow depending on the role
    if user_role == get_translation(context, 'translator_button'):
        # Show translator menu instead of going directly to sentence input
        menu_translations = add_translator_menu_translations()
        language = context.user_data.get('language', 'English')
        
        reply_keyboard = [
            [menu_translations['view_sentences'][language], menu_translations['write_sentence'][language]],
            [menu_translations['edit_sentences'][language], menu_translations['change_language'][language]],
            [get_translation(context, 'cancel_button')]
        ]
        
        await update.message.reply_text(
            menu_translations['menu'][language],
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return TRANSLATOR_MENU
    else:
        # User flow remains unchanged
        video_path, sentence = get_random_translator_video()
        
        if video_path and os.path.exists(video_path):
            # Send the video and the associated sentence if it exists
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
        else:
            await update.message.reply_text(get_translation(context, 'no_videos_available'))
            return ConversationHandler.END

# Handle translator sentence input
async def handle_translator_sentence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sentence = update.message.text

    # Check if cancel is pressed
    if sentence == get_translation(context, 'cancel_button'):
        return await cancel(update, context)

    context.user_data['sentence'] = sentence  # Store the sentence

    # After the sentence is received, ask for video upload
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
        username = update.message.from_user.username or "unknown_user"
        file_path = get_next_available_filename(TRANSLATOR_DIR, username, "translator")
        
        # Get user's language from database
        user_language = get_user_language(username)
        if not user_language:
            logger.error(f"Could not find language for user {username}")
            user_language = "unknown"  # Default fallback
        
        # Get the sentence from context
        sentence = context.user_data.get('sentence')
        
        # Download the video
        await download_video(update.message.video, file_path, context)
        
        # Save video information with language and sentence
        # The function will handle both sentence and video storage
        save_video_info(username, file_path, "translator", user_language, sentence)
        
        await update.message.reply_text(get_translation(context, 'thank_you_video'))
        return ConversationHandler.END
    else:
        await update.message.reply_text(get_translation(context, 'valid_video_error'))
        return TRANSLATOR_UPLOAD
    

# Handle user video request and upload
async def user_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Check if user typed /start
    if update.message.text and update.message.text == '/start':
        # Call the existing start function
        return await start(update, context)

    if update.message.video:
        username = update.message.from_user.username or "unknown_user"
        file_path = get_next_available_filename(USER_DIR, username, "user")
        
        # Get user's language from database
        user_language = get_user_language(username)
        if not user_language:
            logger.error(f"Could not find language for user {username}")
            user_language = "unknown"
        
        # Download the video
        await download_video(update.message.video, file_path, context)
        
        # Save video information with language
        save_video_info(username, file_path, "user", user_language)
        
        # Send confirmation and get next video
        await update.message.reply_text(get_translation(context, 'continue_exchange'))
        
        # Get and send the next random video
        video_path, sentence = get_random_translator_video()
        
        if video_path and os.path.exists(video_path):
            # Send the video and the associated sentence if it exists
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(video_file)
                if sentence:
                    await update.message.reply_text(f"Translated sentence: {sentence}")
            
            # Continue in the same state to allow another video upload
            return USER_REQUEST
        else:
            # If no more videos are available, end the conversation
            await update.message.reply_text(get_translation(context, 'no_more_videos'))
            return ConversationHandler.END
    else:
        await update.message.reply_text(get_translation(context, 'valid_video_error'))
        return USER_REQUEST


# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of the conversation."""
    await update.message.reply_text(
        get_translation(context, 'cancel_message')
    )

    # Provide the "Start" button after cancellation
    await update.message.reply_text(
        get_translation(context, 'restart_message'),
        reply_markup=ReplyKeyboardMarkup([['/start']], one_time_keyboard=True)
    )
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    application = Application.builder().token("7383040553:AAE8DlZSc0PKB-UbsY5eZRB6lQmBSpuxnJU").build()

    # Set up conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_selection)],
            ASK_PERMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_permission)],
            ROLE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, role_selection)],
            TRANSLATOR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translator_menu)],
            VIEW_SENTENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_translator_menu)],
            WRITE_SENTENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_write_sentence)],
            TRANSLATOR_INPUT_SENTENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translator_sentence),
                CommandHandler("start", start)
            ],
            TRANSLATOR_UPLOAD: [
                MessageHandler(filters.VIDEO | filters.TEXT & ~filters.COMMAND, handle_video_upload),
                CommandHandler("start", start)
            ],
            USER_REQUEST: [
                MessageHandler(filters.VIDEO | filters.TEXT & ~filters.COMMAND, user_video_request),
                CommandHandler("start", start)  # Add start command handler here
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Test the database connection during bot initialization
    if connect_to_db():
        logger.info("Database connection tested successfully.")

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()