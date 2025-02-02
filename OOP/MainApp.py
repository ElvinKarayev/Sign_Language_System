import logging
import random
from cancel import cancel_restarted_message

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

from apscheduler.jobstores.base import JobLookupError

# =========================
# 1) Import your classes and states from each module
#    (Adjust the import paths if your files are named differently or in subfolders)
# =========================

from DatabaseService import DatabaseService
from TranslationManager import TranslationManager
# RegistrationHandlers file has the class + the states: LANGUAGE_SELECTION, ASK_PERMISSION, ROLE_SELECTION
from RegistrationHandlers import (
    RegistrationHandlers,
    LANGUAGE_SELECTION,
    ASK_PERMISSION,
    ROLE_SELECTION,
    ROLE_OTP_CHECK
)
# UserHandlers file has the class + states: USER_MENU, USER_REQUEST, USER_VIEW_VIDEOS
from UserHandlers import (
    UserHandlers,
    USER_MENU,
    USER_REQUEST,
    USER_VIEW_VIDEOS,
)
# TranslatorHandlers file has the class + states: TRANSLATOR_MENU, WRITE_SENTENCE, TRANSLATOR_UPLOAD, EDIT_SENTENCES, VOTING
from TranslatorHandlers import (
    TranslatorHandlers,
    TRANSLATOR_MENU,
    WRITE_SENTENCE,
    TRANSLATOR_UPLOAD,
    EDIT_SENTENCES,
    VOTING,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# We’ll schedule a restart message if no user handler responds in time
RESTART_JOB_KEY = 'restart_job'

# If you want a global OTP
latest_otp = None

def read_bot_token(token_file="token.txt") -> str:
    """
    Reads the Telegram bot token from a file (token.txt).
    File should contain only the token with no extra spaces or lines.
    """
    with open(token_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

# ====================================================================
# FALLBACK / CANCEL / "BOT RESTARTED" LOGIC
# ====================================================================

async def send_bot_restarted(context: ContextTypes.DEFAULT_TYPE):
    """
    This job is triggered if no other handler claims the update
    within a certain time, instructing the user to /start again.
    """
    job = context.job
    chat_id = job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text="Bot restarted. Please press the /start button to begin again.",
        reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True, one_time_keyboard=True)
    )

def schedule_restarted_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Schedules 'send_bot_restarted' after, e.g., 20 seconds,
    unless a handler cancels it via cancel_restarted_message.
    """
    if RESTART_JOB_KEY in context.user_data:
        old_job = context.user_data[RESTART_JOB_KEY]
        try:
            old_job.schedule_removal()
        except JobLookupError:
            pass
        del context.user_data[RESTART_JOB_KEY]

    # Example: 20 seconds
    job = context.application.job_queue.run_once(
        send_bot_restarted,
        when=2,
        chat_id=update.effective_chat.id,
        name=str(update.effective_chat.id)
    )
    context.user_data[RESTART_JOB_KEY] = job


def with_fallback_timeout(handler_func):
    """
    Decorator that schedules the fallback job before calling 'handler_func'.
    The handler itself can call cancel_restarted_message(context) if it responds.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        schedule_restarted_message(update, context)
        result = await handler_func(update, context)
        return result
    return wrapper

@with_fallback_timeout
async def global_fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    A 'global fallback' that doesn't respond.
    If no other handler or state picks up the update,
    eventually 'send_bot_restarted' runs.
    """
    pass

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    If user types /cancel or "cancel", we end the conversation.
    """
    cancel_restarted_message(context)
    await update.message.reply_text(
        "Canceled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ====================================================================
# MAIN APPLICATION CLASS (OOP) tying everything together
# ====================================================================
class MainApplication:
    def __init__(self, config_path='config.txt', translations_dir='translations', token_file='token.txt'):
        """
        Sets up DB/translation services, the handler classes, 
        and the Telegram application.
        """
        # 1) Load the bot token from token.txt
        self.token = read_bot_token(token_file)

        # 2) Initialize database and translation managers
        self.db_service = DatabaseService(config_path)
        self.translation_manager = TranslationManager(translations_dir)

    
        self.registration_handlers = RegistrationHandlers(self.db_service, self.translation_manager)
        self.user_handlers = UserHandlers(self.db_service, self.translation_manager)
        self.translator_handlers = TranslatorHandlers(self.db_service, self.translation_manager)

        # 4) Build the Telegram application
        self.application = Application.builder().token(self.token).build()

    async def generate_random_otp(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Example scheduled job that updates your global 'latest_otp'.
        Adjust or remove as needed.
        """
        global latest_otp
        latest_otp = random.randint(100000, 999999)
        context.bot_data['latest_otp'] = latest_otp
        logger.info(f"Generated OTP: {latest_otp}")

    async def handle_page_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handles inline button presses for pagination.
        """
        query = update.callback_query
        await query.answer()  # Acknowledge button press

        callback_data = query.data  # Example: "page_2"

        if callback_data.startswith("page_"):
            new_page = int(callback_data.split("_")[1])
            context.user_data['current_page'] = new_page  # Update stored page number
            return await self.translator_handlers.display_sentences_page(update, context)  # Refresh page display


    def setup_jobs(self):
        """
        Set up any scheduled jobs, like generating OTP every 5 minutes.
        """
        job_queue = self.application.job_queue
        job_queue.run_repeating(self.generate_random_otp, interval=300, first=1)
    def setup_conversation_handler(self):
        """
        Create the ConversationHandler referencing the states from your OOP classes,
        and wrapping their methods with 'with_fallback_timeout' for the fallback scheduling.
        """

        
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", with_fallback_timeout(self.registration_handlers.start))
            ],
            states={
                # ===== Registration Flow =====
                LANGUAGE_SELECTION: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.registration_handlers.language_selection))
                ],
                ASK_PERMISSION: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.registration_handlers.ask_permission))
                ],
                ROLE_SELECTION: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.registration_handlers.role_selection))
                ],
                ROLE_OTP_CHECK: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.registration_handlers.role_otp_check))
                ],

                # ===== User Flow =====
                USER_MENU: [
                    MessageHandler(filters.ALL, with_fallback_timeout(self.user_handlers.handle_user_menu))  # Accept any message
                ],
                USER_REQUEST: [
                    MessageHandler(filters.ALL, with_fallback_timeout(self.user_handlers.user_video_request))
                ],
                USER_VIEW_VIDEOS: [
                    # Example callback queries for next/previous/deletion
                    CallbackQueryHandler(with_fallback_timeout(self.user_handlers.handle_delete_user_video), pattern=r"^delete_user_video_\d+$"),
                    CallbackQueryHandler(with_fallback_timeout(self.user_handlers.handle_next_user_video), pattern="^next_user_video$"),
                    CallbackQueryHandler(with_fallback_timeout(self.user_handlers.handle_previous_user_video), pattern="^previous_user_video$"),
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.user_handlers.user_videos_navigation))
                ],

                # ===== Translator Flow =====
                TRANSLATOR_MENU: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.translator_handlers.handle_translator_menu)),
                    # Callback queries for pagination, e.g. "prev_page" or "next_page"
                    CallbackQueryHandler(with_fallback_timeout(self.translator_handlers.handle_page_navigation), pattern="^(prev_page|next_page)$"),
                    CallbackQueryHandler(self.handle_page_navigation, pattern=r"^page_\d+$")
                ],
                WRITE_SENTENCE: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.translator_handlers.handle_write_sentence))
                ],
                TRANSLATOR_UPLOAD: [
                    MessageHandler(filters.ALL, with_fallback_timeout(self.translator_handlers.handle_video_upload))
                ],
                EDIT_SENTENCES: [
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.translator_handlers.edit_sentences_navigation)),
                    # e.g. callback queries for detail, deletion, etc.
                    CallbackQueryHandler(self.translator_handlers.handle_delete_sentence, pattern=r"^delete_\d+$"),
                    CallbackQueryHandler(self.translator_handlers.show_sentence_detail, pattern=r"^view_item_\d+$"),
                    CallbackQueryHandler(self.translator_handlers.handle_page_navigation, pattern="^(prev|next)_page$"),
                ],
                VOTING: [
                    # Inline up/down vote:
                    CallbackQueryHandler(with_fallback_timeout(self.translator_handlers.handle_vote_up), pattern="^vote_up$"),
                    CallbackQueryHandler(with_fallback_timeout(self.translator_handlers.handle_vote_down), pattern="^vote_down$"),
                    # If text-based votes:
                    MessageHandler(filters.TEXT, with_fallback_timeout(self.translator_handlers.handle_voting_response))
                ],
            },
            fallbacks=[

                MessageHandler(filters.Regex("(?i)^cancel$"), cancel_handler)
            ],
        )

        return conv_handler

    def run(self):
        """
        Orchestrates:
         1) scheduling OTP (if desired),
         2) adding global fallback,
         3) adding conversation handler,
         4) running the bot.
        """
        # 1) Set up scheduled jobs
        self.setup_jobs()

        # 2) Add the global fallback (group=0)
        self.application.add_handler(MessageHandler(filters.ALL, global_fallback_handler), group=0)

        # 3) Create and add the conversation handler (group=1)
        conv_handler = self.setup_conversation_handler()
        self.application.add_handler(conv_handler, group=1)

        logger.info("Starting the bot. Press Ctrl+C to stop.")
        self.application.run_polling()
        logger.info("Bot has stopped.")


if __name__ == "__main__":
    # You can set up logging here if needed.
    logging.basicConfig(level=logging.INFO)

    # Create your main app with the relevant file paths
    app = MainApplication(
        config_path="/home/ubuntu/Sign_Language_System/OOP/config.txt",
        translations_dir="/home/ubuntu/Sign_Language_System/translations",
        token_file="/home/ubuntu/Sign_Language_System/OOP/token.txt"  # The file containing your bot token
    )

    app.run()
