from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ContextTypes
)
import os
import datetime
from cancel import cancel_restarted_message
CONTACT_ADMIN = 99
async def handle_contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, translation_manager) -> int:
        """
        Step 1: Ask the user to describe their problem.
        """
        cancel_restarted_message(context)

        ask_problem_text = translation_manager.get_translation(context, 'ask_problem_admin')
        go_back_text = translation_manager.get_translation(context, 'go_back')

        await update.message.reply_text(
            ask_problem_text,
            reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=True)
        )

        return CONTACT_ADMIN  # Move to the next state

async def save_user_report(update: Update, context: ContextTypes.DEFAULT_TYPE, translation_manager, translator_handlers, user_handlers) -> int:
    """
    Step 2: Save the user's problem to a file and notify the admin.
    """
    cancel_restarted_message(context)

    # Fetch user data from context
    user_id = context.user_data.get('user_id')
    user_role = context.user_data.get('role')
    username = context.user_data.get('username', "unknown")
    language = context.user_data.get('language', 'English')
    user_text = update.message.text

    go_back_text = translation_manager.get_translation(context, 'go_back')
    report_saved_text = translation_manager.get_translation(context, 'report_saved')
    admin_notified_text = translation_manager.get_translation(context, 'admin_notified')

    # Handle cancellation
    if user_text.strip().lower() == go_back_text.lower():
        if user_role == 'Translator' and translator_handlers:
            return await translator_handlers.show_translator_menu(update, context)
        elif user_role == 'User' and user_handlers:
            return await user_handlers.show_user_menu(update, context)

    # Ensure reports directory exists
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    # Create a unique filename for the report
    file_name = f"user_{user_id}_{username}_report.txt"
    file_path = os.path.join(reports_dir, file_name)

    # Save the report to a file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 50 + "\n")  # Add a separator between reports
        f.write(f"New Report from @{username} (ID: {user_id})\n")
        f.write(f"Language: {language}\n")
        f.write(f"Problem: {user_text}\n")
        f.write(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Notify the user
    await update.message.reply_text(report_saved_text)
    if user_role == 'Translator':
        return await translator_handlers.show_translator_menu(update, context)
    else:
        return await user_handlers.show_user_menu(update, context)
