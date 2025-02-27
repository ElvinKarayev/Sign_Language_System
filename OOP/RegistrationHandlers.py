import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)
from cancel import cancel_restarted_message
from TranslatorHandlers import TranslatorHandlers
from UserHandlers import UserHandlers
from AdminHandlers import AdminHandlers
logger = logging.getLogger(__name__)

# Example conversation states (you can import or define these enums elsewhere)
LANGUAGE_SELECTION = 1
ASK_PERMISSION = 2
ROLE_SELECTION = 3
TRANSLATOR_MENU = 4
USER_MENU = 5
ROLE_OTP_CHECK=6

class RegistrationHandlers:
    def __init__(self, db_service, translation_manager):
        """
        :param db_service: An instance of DatabaseService for DB queries.
        :param translation_manager: An instance of TranslationManager for i18n.
        """
        self.db_service = db_service
        self.translation_manager = translation_manager

        # If you want to store the OTP in this class, you can do so:

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        /start command handler. Checks if the user already exists
        in the database. If yes, go directly to user or translator menu.
        If no, prompt for language selection.
        """

        user = update.effective_user
        telegram_id = user.id
        telegram_username = user.username

        # Clear out user_data to start fresh
        context.user_data.clear()

        # Store the telegram_id and username for later use
        context.user_data['telegram_id'] = telegram_id
        context.user_data['telegram_username'] = telegram_username

        # Check if user exists in DB
        (db_user_id,
         existing_username,
         user_language_db,
         user_role) = self.db_service.check_user_exists(telegram_id)
        if db_user_id is not None:
            # User already exists
            context.user_data['user_id'] = db_user_id
            context.user_data['username'] = existing_username
            context.user_data['role'] = user_role
            context.user_data['language'] = user_language_db

            # If the existing user is a translator, go to translator menu
            if user_role == 'Translator':
                # Return the translator menu state
                translatorhandlers=TranslatorHandlers(self.db_service, self.translation_manager)
                
                return await translatorhandlers.show_translator_menu(update, context)
            elif user_role == 'Admin':
                adminhandler=AdminHandlers(self.db_service, self.translation_manager)
                
                return await adminhandler.show_admin_menu(update, context)
            else:
                userhandler=UserHandlers(self.db_service,self.translation_manager)
                
                # Return the user menu state
                return await userhandler.show_user_menu(update,context)
        else:
            # New user: ask them to select a language
            reply_keyboard = [["🇦🇿 Azerbaijani", "🇷🇺 Russian", "🇺🇦 Ukrainian"]]
            await update.message.reply_text(
                "Please select your language:",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                 resize_keyboard=True,
                                                 one_time_keyboard=True)
            )
            return LANGUAGE_SELECTION

    async def language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handle the user's chosen language. Store it in user_data. Then proceed
        to ask for consent (ASK_PERMISSION).
        """
        selected_language = update.message.text

        # Optionally map emojis to language names:
        if "🇦🇿" in selected_language:
            context.user_data['language'] = 'Azerbaijani'
        # elif "🇩🇪" in selected_language:
        #     context.user_data['language'] = 'German'
        # elif "🇬🇧" in selected_language:
        #     context.user_data['language'] = 'English'
        elif "🇷🇺" in selected_language:
            context.user_data['language'] = 'Russian'
        elif "🇺🇦" in selected_language:
            context.user_data['language'] = 'Ukrainian'
        else:
            # Handle invalid selection
            await update.message.reply_text("Please select a valid language option.")
            return LANGUAGE_SELECTION

        # If the user has a telegram username, we can store it, 
        # or default to something like "unknown"
        telegram_username = context.user_data.get('telegram_username')
        if not telegram_username:
            context.user_data['username'] = "unknown"
        else:
            context.user_data['username'] = telegram_username

        # Prompt for consent
        confirm_text = self.translation_manager.get_translation(context, 'confirm_button')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        consent_message = self.translation_manager.get_translation(context, 'consent_message')

        reply_keyboard = [[confirm_text, cancel_text]]
        await update.message.reply_text(
            consent_message,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             resize_keyboard=True,
                                             one_time_keyboard=True)
        )
        return ASK_PERMISSION

    async def ask_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handle the user's response to the consent prompt.
        If confirmed, proceed to role selection. If canceled, do a 'cancel' flow.
        """
        user_response = update.message.text
        confirm_text = self.translation_manager.get_translation(context, 'confirm_button')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')
        choose_role_text = self.translation_manager.get_translation(context, 'choose_role')

        if user_response == confirm_text:
            # Show role selection (translator/user)
            translator_button = self.translation_manager.get_translation(context, 'translator_button')
            user_button = self.translation_manager.get_translation(context, 'user_button')
            reply_keyboard = [[translator_button, user_button], [cancel_text]]

            await update.message.reply_text(
                choose_role_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                 resize_keyboard=True,
                                                 one_time_keyboard=True)
            )
            return ROLE_SELECTION
        elif user_response == cancel_text:
            cancel_text=self.translation_manager.get_translation(context,'cancel_message')
            start_button=self.translation_manager.get_translation(context,'start_button')
            reply_keyboard=[[start_button]]
            await update.message.reply_text(
                cancel_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return ConversationHandler.END
        else:
            # Unrecognized input
            await update.message.reply_text(invalid_option_text)
            return ASK_PERMISSION

    async def role_selection(self, update, context):
        cancel_restarted_message(context)
        
        user_choice = update.message.text

        translator_text = self.translation_manager.get_translation(context, 'translator_button')
        user_text = self.translation_manager.get_translation(context, 'user_button')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        technical_difficulty_text = self.translation_manager.get_translation(context, 'technical_difficulty')

        # If user chose Translator, prompt for OTP code and move to ROLE_OTP_CHECK
        if user_choice == translator_text:
            otp_code_prompt = self.translation_manager.get_translation(context, 'otp_code_prompt')
            await update.message.reply_text(otp_code_prompt)
            return ROLE_OTP_CHECK

        # If user chose normal User role, just add them to the DB right away
        elif user_choice == user_text:
            db_user_id = self._add_user_to_db(update, context, "User")
            userhandler=UserHandlers(self.db_service,self.translation_manager)
                
            if db_user_id is None:
                await update.message.reply_text(technical_difficulty_text)
            # Return the user menu state
            return await userhandler.show_user_menu(update,context)

        elif user_choice == cancel_text:
            cancel_text=self.translation_manager.get_translation(context,'cancel_message')
            start_button=self.translation_manager.get_translation(context,'start_button')
            reply_keyboard=[[start_button]]
            await update.message.reply_text(
                cancel_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return ConversationHandler.END

        else:
            # Not recognized, re-ask
            choose_role_text = self.translation_manager.get_translation(context, 'choose_role')
            await update.message.reply_text(choose_role_text)
            return ROLE_SELECTION

    async def role_otp_check(self, update, context):
        cancel_restarted_message(context)
        """
        This handler is invoked after we've asked the user to enter the OTP code
        (i.e., after the role_selection method returns ROLE_OTP_CHECK).
        """
        user_otp_input = update.message.text
        technical_difficulty_text = self.translation_manager.get_translation(context, 'technical_difficulty')
        otp_failed_text = self.translation_manager.get_translation(context, 'otp_failed')
        True_OTP_code=context.bot_data.get('latest_otp')
        if user_otp_input == str(True_OTP_code):
            # OTP is correct, add the user as a Translator
            db_user_id = self._add_user_to_db(update, context, "Translator")
            if db_user_id is None:
                await update.message.reply_text(technical_difficulty_text)
                return -1
            # If successful, proceed to translator menu
            translatorhandler=TranslatorHandlers(self.db_service,self.translation_manager)
            return await translatorhandler.show_translator_menu(update, context)
        else:
            # OTP incorrect
            cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
            translator_button = self.translation_manager.get_translation(context, 'translator_button')
            user_button = self.translation_manager.get_translation(context, 'user_button')
            reply_keyboard = [[translator_button, user_button], [cancel_text]]

            await update.message.reply_text(otp_failed_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             resize_keyboard=True,
                                             one_time_keyboard=True)
            )
            # Send them back to role selection or re-ask the OTP, your choice:
            return ROLE_SELECTION

    def _add_user_to_db(self, update, context, role_value):
        """
        Private helper that adds the user to the DB with the given role (User/Translator).
        """
        username = context.user_data.get('username', 'unknown')
        language = context.user_data.get('language', 'Azerbaijani')
        telegram_id = context.user_data.get('telegram_id')

        db_user_id = self.db_service.add_new_user(username, language, role_value, telegram_id)
        if db_user_id is not None:
            context.user_data['user_id'] = db_user_id
            context.user_data['role'] = role_value
        return db_user_id