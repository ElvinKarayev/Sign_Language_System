import logging
import os
import re
import datetime
from cancel import cancel_restarted_message
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)
from admin import handle_contact_admin

logger = logging.getLogger(__name__)

# Example conversation states (define or import them as needed):
TRANSLATOR_MENU = 4
WRITE_SENTENCE = 21
TRANSLATOR_UPLOAD = 22
EDIT_SENTENCES = 23
VOTING = 24
WAITING_FOR_FEEDBACK = 25
CLASSROOM_MENU = 101
CLASSROOM_PASSWORD = 102
CLASSROOM_CREATION = 103
CLASSROOM_DELETION = 104


class TranslatorHandlers:
    def __init__(self, db_service, translation_manager):
        """
        :param db_service:          Instance of your DatabaseService class.
        :param translation_manager: Instance of your TranslationManager class.
        """
        self.db_service = db_service
        self.translation_manager = translation_manager

    # --------------------------------------------------------------------------
    # MENU AND BASIC FLOWS
    # --------------------------------------------------------------------------

    async def show_translator_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Display the translator menu options:
          - View Sentences
          - Write Sentence
          - Edit Sentences
          - Vote
          - Generate OTP
          - Contact Admin
          - My Classrooms
          - Cancel
        """
        menu_text = self.translation_manager.get_translation(context, 'menu')
        view_sentences_text = self.translation_manager.get_translation(context, 'view_sentences')
        write_sentence_text = self.translation_manager.get_translation(context, 'write_sentence')
        edit_sentences_text = self.translation_manager.get_translation(context, 'edit_sentences')
        vote_text = self.translation_manager.get_translation(context, 'vote')
        generate_otp_text = self.translation_manager.get_translation(context, 'generate_otp')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        contact_admin_text =  self.translation_manager.get_translation(context, 'contact_admin')
        translator_buttons_info =  self.translation_manager.get_translation(context, 'translator_info')
        rank_text = self.translation_manager.get_translation(context, 'show_my_rank')
        my_classrooms_text = self.translation_manager.get_translation(context, 'my_classrooms')
        reply_keyboard = [
            [view_sentences_text, write_sentence_text],
            [edit_sentences_text, vote_text],
            [generate_otp_text, contact_admin_text],
            [translator_buttons_info, rank_text],
            [my_classrooms_text],
            [cancel_text]
        ]

        if update.message:
            await update.message.reply_text(
            menu_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        else:  # Handle case where `update.message` is None (e.g., inline button press)
            await update.callback_query.message.reply_text(
            menu_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return TRANSLATOR_MENU

    async def handle_translator_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        React to the translator's menu choice:
          - View Sentences -> display_sentences_page
          - Write Sentence -> go to WRITE_SENTENCE
          - Edit Sentences -> handle_edit_sentences
          - Vote -> start_voting
          - Contact Admin -> handle_contact_admin
          - Generate OTP -> handle_view_otp
          - INFO -> handle_view_INFO
          - My Classrooms -> show_classroom
          - Cancel -> return or end
        """
        user_choice = update.message.text

        view_sentences_text = self.translation_manager.get_translation(context, 'view_sentences')
        write_sentence_text = self.translation_manager.get_translation(context, 'write_sentence')
        edit_sentences_text = self.translation_manager.get_translation(context, 'edit_sentences')
        vote_text = self.translation_manager.get_translation(context, 'vote')
        generate_otp_text = self.translation_manager.get_translation(context, 'generate_otp')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        contact_admin_text =  self.translation_manager.get_translation(context, 'contact_admin')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')
        translator_buttons_info =  self.translation_manager.get_translation(context, 'translator_info')
        rank_text = self.translation_manager.get_translation(context, 'show_my_rank')
        my_classrooms_text = self.translation_manager.get_translation(context, 'my_classrooms')

        if user_choice == view_sentences_text:
            # If you have a separate function to display all sentences (paged)
            context.user_data['current_page'] = 1
            await self.display_sentences_page(update, context)

            return TRANSLATOR_MENU
        elif user_choice == go_back_text:
            return await self.show_translator_menu(update, context)

        elif user_choice == write_sentence_text:
            please_write_sentence_text = self.translation_manager.get_translation(context, 'please_write_sentence')
            cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
            await update.message.reply_text(
                please_write_sentence_text,
                reply_markup=ReplyKeyboardMarkup([[cancel_text]], resize_keyboard=True, one_time_keyboard=True)
            )
            return WRITE_SENTENCE

        elif user_choice == edit_sentences_text:
            return await self.handle_edit_sentences(update, context)
        
        elif user_choice == rank_text:
            return await self.handle_show_leaderboard(update, context)
        
        elif user_choice == vote_text:
            return await self.start_voting(update, context)
        
        elif user_choice == translator_buttons_info:
            return await self.handle_translator_info(update, context)
        
        elif user_choice == generate_otp_text:
            return await self.handle_view_otp(update, context)
        
        elif user_choice == contact_admin_text:
            return await handle_contact_admin(update, context, self.translation_manager)
        
        elif user_choice == my_classrooms_text:
            print("Transitioning to CLASSROOM_MENU")  # Debugging log
            return await self.show_classrooms_menu(update, context)
        
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
            # Unrecognized input
            await update.message.reply_text(invalid_option_text)
            return await self.show_translator_menu(update, context)
        
    
    # --------------------------------------------------------------------------
    # CLASSROOM MANAGEMENT
    # --------------------------------------------------------------------------
    async def show_classrooms_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Fetch and display the list of classrooms the user owns, including their passwords.
        Store the classroom count and indexed list in context for easier selection later.
        """
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        go_back_list_text = self.translation_manager.get_translation(context, 'go_back_classroom_list')
        no_classrooms_text = self.translation_manager.get_translation(context, 'no_classrooms')
        create_classroom_text = self.translation_manager.get_translation(context, 'create_classroom')
        delete_classroom_text = self.translation_manager.get_translation(context, 'remove_classroom')
        classroom_choose_an_action_text = self.translation_manager.get_translation(context, 'classroom_choose_an_action')
        classroom_name_text = self.translation_manager.get_translation(context, 'classroom_name')
        classroom_password_text = self.translation_manager.get_translation(context, 'classroom_password')
        
        user_id = self._get_user_id_from_context(context, update)
        message_target = update.message or update.callback_query.message
        if not user_id:
            await message_target.reply_text("⚠️ Error: Could not retrieve user ID.")
            return await self.show_translator_menu(update, context)

        classrooms = self.db_service.get_classrooms_for_user(user_id)

        # Store classroom count and list in context
        context.user_data['classroom_count'] = len(classrooms) if classrooms else 0
        context.user_data['classrooms_list'] = classrooms  # Store for selection later

        # Get the selected classroom (if any)
        selected_classroom = context.user_data.get("selected_classroom")

        if not classrooms:
            await message_target.reply_text(
                no_classrooms_text,
                reply_markup=ReplyKeyboardMarkup(
                    [[create_classroom_text], [go_back_text]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return CLASSROOM_MENU
        if selected_classroom:
            view_sentences_text = self.translation_manager.get_translation(context, 'view_sentences')
            write_sentence_text = self.translation_manager.get_translation(context, 'write_sentence')
            edit_sentences_text = self.translation_manager.get_translation(context, 'edit_sentences')
            vote_text = self.translation_manager.get_translation(context, 'vote')
            
            classroom_text = (
                "🏫 Classroom:\n\n"
                f"📌 {classroom_name_text}: {selected_classroom['classname']}\n"
                f"🔑 {classroom_password_text}: {selected_classroom['password']}\n"
                f"🆔 Classroom ID: {selected_classroom['classroom_id']}\n\n"
            )
            
            reply_keyboard_buttons = [
                                        [view_sentences_text, write_sentence_text],
                                        [edit_sentences_text,vote_text],
                                        [delete_classroom_text], [go_back_list_text]
                                        ]
            
            await message_target.reply_text(
                classroom_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard_buttons, resize_keyboard=True, one_time_keyboard=True)
            )

            return CLASSROOM_MENU
        # Format the classroom list with numbering
        classrooms_text = "🏫 Your Classrooms:\n\n"
        inline_keyboard_buttons = []
        
        for index, classroom in enumerate(classrooms, start=1):
            classrooms_text += (
                f"{index}. 📌 {classroom_name_text}: {classroom['classname']}\n"
                f"   🔑 {classroom_password_text}: {classroom['password']}\n"
                f"   🆔 Classroom ID: {classroom['classroom_id']}\n\n"
            )
            # Add inline selection button (only numbers)
            inline_keyboard_buttons.append(InlineKeyboardButton(str(index), callback_data=f"select_classroom_{index}"))

        # Send the classroom list with inline selection buttons
        await message_target.reply_text(
            classrooms_text,
            reply_markup=InlineKeyboardMarkup([inline_keyboard_buttons])
        )

        # Prepare the reply keyboard for other actions
        reply_keyboard_buttons = [[create_classroom_text], [go_back_text]]
        
        if selected_classroom:
            reply_keyboard_buttons[0].insert(0, delete_classroom_text)  # Delete button on top if a classroom is selected

        await message_target.reply_text(
            classroom_choose_an_action_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard_buttons, resize_keyboard=True, one_time_keyboard=True)
        )

        return CLASSROOM_MENU
    
    
    async def select_classroom_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the selection of a classroom when the user clicks an inline button.
        """
        query = update.callback_query
        await query.answer()  # Acknowledge the callback

        selected_index = int(query.data.replace("select_classroom_", "")) - 1  # Convert callback_data to index
        classrooms = context.user_data.get("classrooms_list", [])

        if 0 <= selected_index < len(classrooms):
            # Store the selected classroom in context
            selected_classroom = classrooms[selected_index]
            context.user_data["selected_classroom"] = selected_classroom

            # Send confirmation message
            selected_text = f"✅ Classroom {selected_index + 1}: {selected_classroom['classname']}."
            await query.message.reply_text(selected_text)

            # Refresh classroom menu to show "Delete Classroom" option
            return await self.show_classrooms_menu(update, context)

        else:
            await query.message.reply_text("⚠️ Invalid selection.")
            return CLASSROOM_MENU

    
    async def handle_classroom(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handle user actions in the classroom menu:
        - Create a new classroom
        - Go back to the translator menu
        """
        user_choice = update.message.text

        create_classroom_text = self.translation_manager.get_translation(context, 'create_classroom')
        delete_classroom_text = self.translation_manager.get_translation(context, 'remove_classroom')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        go_back_list_text = self.translation_manager.get_translation(context, 'go_back_classroom_list')
        classroom_name_text = self.translation_manager.get_translation(context, 'classroom_name')
        classroom_password_text = self.translation_manager.get_translation(context, 'classroom_password')
        confirm_delete_text = self.translation_manager.get_translation(context, 'confirm_delete')
        delete_text = self.translation_manager.get_translation(context, 'delete')
        cancel_delete_text = self.translation_manager.get_translation(context, 'cancel_button')
        no_classroom_selected_text = self.translation_manager.get_translation(context, 'no_classroom_selected')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')
        view_sentences_text = self.translation_manager.get_translation(context, 'view_sentences')
        write_sentence_text = self.translation_manager.get_translation(context, 'write_sentence')
        edit_sentences_text = self.translation_manager.get_translation(context, 'edit_sentences')
        vote_text = self.translation_manager.get_translation(context, 'vote')
        go_back_classroom_text = self.translation_manager.get_translation(context, 'go_back_classroom')
        
        if user_choice == view_sentences_text:
            # If you have a separate function to display all sentences (paged)
            context.user_data['current_page'] = 1
            await self.display_sentences_page(update, context)
            return CLASSROOM_MENU
        
        elif user_choice == write_sentence_text:
            please_write_sentence_text = self.translation_manager.get_translation(context, 'please_write_sentence')
            cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
            await update.message.reply_text(
                please_write_sentence_text,
                reply_markup=ReplyKeyboardMarkup([[cancel_text]], resize_keyboard=True, one_time_keyboard=True)
            )
            return WRITE_SENTENCE
        
        elif user_choice == edit_sentences_text:
            return await self.handle_edit_sentences(update, context)
        
        elif user_choice == vote_text:
            return await self.start_voting(update, context)
        
        elif user_choice == create_classroom_text:
            classroom_count = context.user_data.get('classroom_count', 0)

            if classroom_count >= 5:
                limit_exceeded_text = self.translation_manager.get_translation(context, 'classroom_limit_exceeded')
                await update.message.reply_text(limit_exceeded_text)
                return await self.show_classrooms_menu(update, context)

            # Proceed to classroom creation if limit not reached
            return await self.prompt_create_classroom(update, context)
        elif user_choice == delete_classroom_text:
            selected_classroom = context.user_data.get("selected_classroom")
            if not selected_classroom:
                await update.message.reply_text(no_classroom_selected_text)
                return await self.show_classrooms_menu(update, context)

            # ✅ Ask for confirmation before deleting
            confirm_text = (
                f"{confirm_delete_text}\n\n"
                f"📌 {classroom_name_text}: {selected_classroom['classname']}\n"
                f"🔑 {classroom_password_text}: {selected_classroom['password']}\n"
                f"🆔 Classroom ID: {selected_classroom['classroom_id']}\n\n"
            )

            await update.message.reply_text(
                confirm_text,
                reply_markup=ReplyKeyboardMarkup(
                    [[delete_text], [cancel_delete_text]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return CLASSROOM_DELETION
        
        elif user_choice == go_back_text:
            return await self.show_translator_menu(update, context)
        
        elif user_choice == go_back_classroom_text:
            return await self.show_classrooms_menu(update, context)
        
        elif user_choice == go_back_list_text:
            context.user_data["selected_classroom"] = None
            return await self.show_classrooms_menu(update, context)
        else:
            await update.message.reply_text(invalid_option_text)
            return await self.show_classrooms_menu(update, context)
    
    
    async def confirm_classroom_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handles the confirmation response:
        - If 'Yes, delete' -> Calls `delete_classroom` to remove it from DB
        - If 'Cancel' -> Returns to the classroom menu
        """
        user_choice = update.message.text
        selected_classroom = context.user_data.get("selected_classroom")

        # ✅ Get localized translations
        delete_text = self.translation_manager.get_translation(context, 'delete')
        cancel_delete_text = self.translation_manager.get_translation(context, 'cancel_button')
        successful_deletion_text = self.translation_manager.get_translation(context, 'classroom_successful_deletion')
        no_classroom_selected_text = self.translation_manager.get_translation(context, 'no_classroom_selected')
        deletion_error_text = self.translation_manager.get_translation(context, 'classroom_deletion_error')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')

        if user_choice == delete_text:
            if not selected_classroom:
                await update.message.reply_text(no_classroom_selected_text)
                return await self.show_classrooms_menu(update, context)

            classroom_id = selected_classroom['classroom_id']
            delete_success = self.db_service.delete_classroom(classroom_id)

            if delete_success:
                context.user_data["selected_classroom"] = None  # ✅ Reset selection
                success_text = f"✅ {successful_deletion_text.format(selected_classroom['classname'])}"
                await update.message.reply_text(success_text)
            else:
                await update.message.reply_text(deletion_error_text)

            return await self.show_classrooms_menu(update, context)

        elif user_choice == cancel_delete_text:
            return await self.show_classrooms_menu(update, context)

        else:
            await update.message.reply_text(invalid_option_text)
            return CLASSROOM_DELETION


    
    async def prompt_create_classroom(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Ask the user to enter a name for the new classroom.
        """
        enter_classname_text = self.translation_manager.get_translation(context, 'enter_classname')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')

        await update.message.reply_text(
            enter_classname_text,
            reply_markup=ReplyKeyboardMarkup([[cancel_text]], resize_keyboard=True, one_time_keyboard=True)
        )

        return CLASSROOM_PASSWORD
    
    
    async def prompt_classroom_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Store the classroom name and ask the user to enter a password.
        """
        classroom_name = update.message.text.strip()
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')

        if classroom_name == cancel_text:
            return await self.show_classrooms_menu(update, context)

        # Store the classroom name in context
        context.user_data['classroom_name'] = classroom_name

        enter_password_text = self.translation_manager.get_translation(context, 'enter_classroom_password')
        await update.message.reply_text(
            enter_password_text,
            reply_markup=ReplyKeyboardMarkup([[cancel_text]], resize_keyboard=True, one_time_keyboard=True)
        )

        return CLASSROOM_CREATION
    
    
    async def create_classroom(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Create a new classroom with the stored name and provided password.
        """
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            await update.message.reply_text("⚠️ Error: Could not retrieve user ID.")
            return await self.show_classrooms_menu(update, context)

        classroom_name = context.user_data.get('classroom_name', '').strip()
        classroom_password = update.message.text.strip()
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')

        if classroom_password == cancel_text:
            return await self.show_classrooms_menu(update, context)

        # Securely hash the password before storing it
        hashed_password = classroom_password

        # Insert classroom into database
        new_classroom_id = self.db_service.create_classroom(user_id, classroom_name, hashed_password)

        if new_classroom_id:
            success_text = self.translation_manager.get_translation(context, 'classroom_created').format(classroom_name)
            await update.message.reply_text(success_text)
        else:
            error_text = self.translation_manager.get_translation(context, 'classroom_creation_failed')
            await update.message.reply_text(error_text)

        return await self.show_classrooms_menu(update, context)
    
    #===========================================================
    # LEADERBOARD -- RANK
    #============================================================
    async def handle_show_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Displays the leaderboard with the user's rank, their points, and (if they are a Translator) the top 5 Translators.
        """

        user_id = context.user_data.get("user_id")  # Get user_id from context
        print(user_id)
        user_role = context.user_data.get("role")  # Get user role from context
        print(user_role)

        if not user_id:
            await update.message.reply_text("⚠️ Error")
            return await self.show_translator_menu(update, context)

        user_rank_data, top_5_translators = self.db_service.get_user_rank(user_id, user_role)

        # Check if the return type is tuple (Translator) or single value (User)
       

        user_points, rank = user_rank_data  # Extract only points & rank

        # Get translated texts from JSON
        user_rank_text = self.translation_manager.get_translation(context, 'user_rank')  # 🏆 Sənin Reytinqin:
        user_points_text = self.translation_manager.get_translation(context, 'user_points')  # 📊 Sənin Xalın:
        top_5_translators_text = self.translation_manager.get_translation(context, 'top_5_translators')  # 🌟 Ən Yaxşı 5 Tərcüməçi:

        

        # If the user is a Translator, show the Top 5 Translators
        leaderboard_text = f"{top_5_translators_text}\n"
        for index, (translator_name, translator_points) in enumerate(top_5_translators, start=1):
            leaderboard_text += f"{index}. {translator_name} - {translator_points} points\n"
        leaderboard_text += f"{user_rank_text} {rank}\n"
        leaderboard_text += f"{user_points_text} {user_points}\n"
        # Back button
        go_back_text = self.translation_manager.get_translation(context, 'go_back')

        await update.message.reply_text(
            leaderboard_text,
            reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=True)
        )

        return TRANSLATOR_MENU


    #===========================================================
    # INFO
    #============================================================
        
    async def handle_translator_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Show the detailed explanation of the buttons
        """
        view_sentences_text = self.translation_manager.get_translation(context, 'view_sentences')
        write_sentence_text = self.translation_manager.get_translation(context, 'write_sentence')
        edit_sentences_text = self.translation_manager.get_translation(context, 'edit_sentences')
        vote_text = self.translation_manager.get_translation(context, 'vote')
        generate_otp_text = self.translation_manager.get_translation(context, 'generate_otp')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        contact_admin_text =  self.translation_manager.get_translation(context, 'contact_admin')
        
        
        Buttons_explanation=f"""
        📌 {self.translation_manager.get_translation(context, 'translator_menu_options')}

        🔹 {view_sentences_text} – {self.translation_manager.get_translation(context, 'view_sentences_explanation')}
        🔹 {write_sentence_text} – {self.translation_manager.get_translation(context, 'write_sentence_explanation')}
        🔹 {edit_sentences_text} – {self.translation_manager.get_translation(context, 'edit_sentences_explanation')}
        🔹 {vote_text} – {self.translation_manager.get_translation(context, 'vote_explanation')}
        🔹 {generate_otp_text} – {self.translation_manager.get_translation(context, 'code_for_translator_explanation')}
        🔹 {contact_admin_text} – {self.translation_manager.get_translation(context, 'contact_admin_explanation')}
        """
        
        
        await update.message.reply_text(
            Buttons_explanation,
            reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=True)
        )
        return TRANSLATOR_MENU

    async def handle_view_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Show the current global OTP (if you're using a single global code).
        """
        OTP_code=context.bot_data.get('latest_otp')
        otp_message = str(OTP_code)
        go_back_text = self.translation_manager.get_translation(context, 'go_back')

        await update.message.reply_text(
            otp_message,
            reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=True)
        )
        
        return TRANSLATOR_MENU

    # --------------------------------------------------------------------------
    # SENTENCE MANAGEMENT
    # --------------------------------------------------------------------------


 
    async def handle_write_sentence(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        After user is prompted to "Please write sentence", they type the sentence here.
        If they typed 'cancel_button', we end or go back.
        Otherwise, we check if the sentence exists, if not we prompt for a video upload.
        """
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        sentence_exists_text = self.translation_manager.get_translation(context, 'sentence_exists')
        video_prompt_text = self.translation_manager.get_translation(context, 'video_prompt')
        user_text = update.message.text if update.message else None  # Extract text if available
        new_sentence = user_text if user_text else None  # Ensure it's either a valid sentence or None
        selected_classroom = context.user_data.get("selected_classroom")
        classroom_id = selected_classroom["classroom_id"] if selected_classroom else None

        if new_sentence == cancel_text or new_sentence == None:

            if not classroom_id:
                return await self.show_translator_menu(update,context)  # or translator menu, etc.
            return await self.show_classrooms_menu(update,context)
        
        # Check if sentence already exists
        if self.db_service.check_sentence_exists(new_sentence):
        # Instead of blocking, do: 
            await update.message.reply_text(sentence_exists_text)
        # either way, proceed to "please upload video"
        context.user_data['sentence'] = new_sentence
        await update.message.reply_text(video_prompt_text)
        return TRANSLATOR_UPLOAD
    

    async def handle_video_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handle the translator uploading the video for the newly written sentence.
        If user sent a valid video, we store it in DB and go back to translator menu.
        Otherwise, ask again or handle cancel.
        """
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        thank_you_video_text = self.translation_manager.get_translation(context, 'thank_you_video')
        valid_video_error_text = self.translation_manager.get_translation(context, 'valid_video_error')
        bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')

        user_video = update.message.video if update.message else None
        user_input = update.message.text if update.message else None
        
        selected_classroom = context.user_data.get("selected_classroom")
        classroom_id = selected_classroom["classroom_id"] if selected_classroom else None
        
        if user_video:
            user_id = self._get_user_id_from_context(context, update)
            if not user_id:
                await update.message.reply_text(bot_restarted_text)
                return -1

            # We'll generate a file path
            file_path = self._get_next_available_filename(update, context, role="translator")

            # Download the video
            await self._download_video(user_video, file_path, context)

            # Save to DB
            user_language = context.user_data.get('language', 'English')
            sentence = context.user_data.get('sentence')
            selected_classroom = context.user_data.get("selected_classroom")
            classroom_id = selected_classroom["classroom_id"] if selected_classroom else None
            self.db_service.save_video_info(user_id, file_path, user_language, sentence, classroom_id=classroom_id)

            await update.message.reply_text(thank_you_video_text)
            if not classroom_id:
                return await self.show_translator_menu(update, context)
            return await self.show_classrooms_menu(update, context)

        elif user_input == cancel_text:
            return await self.show_translator_menu(update, context)
        else:
            # Not a valid video message
            await update.message.reply_text(valid_video_error_text)
            return TRANSLATOR_UPLOAD
        

    async def display_sentences_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Displays sentences with pagination.
        """
        cancel_restarted_message(context)
        selected_classroom = context.user_data.get("selected_classroom")
        classroom_id = selected_classroom["classroom_id"] if selected_classroom else None
        # Get the current page from context, default to 1
        page = context.user_data.get('current_page', 1)
        language = context.user_data.get('language', 'English')

        if classroom_id:
            sentences = self.db_service.get_classroom_sentences(classroom_id, language)
        else:
            sentences = self.db_service.get_all_sentences(language)
        items_per_page = 10
        total_pages = (len(sentences) + items_per_page - 1) // items_per_page  # Calculate total pages

        # Prevent invalid page numbers
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        # Store the page in context
        context.user_data['current_page'] = page

        # Extract the current page's sentences
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_sentences = sentences[start_idx:end_idx]

        if not current_sentences:
            message = self.translation_manager.get_translation(context, 'no_sentences_found')
        else:
            message = f"{self.translation_manager.get_translation(context, 'available_sentences')}\n\n"
            for idx, sentence in enumerate(current_sentences, start=start_idx + 1):
                message += f"{idx}. {sentence}\n"

        # Inline keyboard for pagination
        keyboard = []
        row = []

        # Add "Previous Page" button if applicable
        if page > 1:
            row.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))

        # Show current page indicator
        row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="current"))

        # Add "Next Page" button if applicable
        if page < total_pages:
            row.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))

        keyboard.append(row)
        markup = InlineKeyboardMarkup(keyboard)
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        go_back_classroom = self.translation_manager.get_translation(context, 'go_back_classroom')
        

        reply_keyboard = ReplyKeyboardMarkup(
            [[go_back_text]], resize_keyboard=True, one_time_keyboard=True
        ) if not classroom_id else ReplyKeyboardMarkup(
            [[go_back_classroom]], resize_keyboard=True, one_time_keyboard=True
        )
        # Update or send message
        if update.callback_query:
            try:
                await update.callback_query.answer()  # Acknowledge button click
                await update.callback_query.message.edit_text(
                    text=message,
                    reply_markup=markup
                )
            except Exception as e:
                logger.error(f"Error updating message: {e}")
        else:
            try:
                await update.message.reply_text(
                    text=message,
                    reply_markup=markup
                )
                await update.message.reply_text(
                    self.translation_manager.get_translation(context, 'edit_menu_prompt'),
                    reply_markup=reply_keyboard
                )
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return await self.show_translator_menu(update, context)



    # --------------------------------------------------------------------------
    # EDIT SENTENCES
    # --------------------------------------------------------------------------

    async def handle_edit_sentences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        1) Fetch translator’s own sentences from DB (via a single method),
        2) Store them in context for pagination,
        3) Show the first page of results.
        """
        cancel_restarted_message(context)

        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            await update.message.reply_text("Bot restarted or user not found.")
            return ConversationHandler.END

        language = context.user_data.get('language', 'English')

        # Single DB call - no repetitive queries here!
        selected_classroom = context.user_data.get("selected_classroom")
        classroom_id = selected_classroom["classroom_id"] if selected_classroom else None
        results = self.db_service.get_translator_videos(user_id, language, classroom_id) if classroom_id else self.db_service.get_translator_videos(user_id, language) 
        if not results:
            no_sentences_text = self.translation_manager.get_translation(context, 'no_sentences_found')
            await update.message.reply_text(no_sentences_text)
            if not classroom_id:
                return await self.show_translator_menu(update, context)
            return await self.show_classrooms_menu(update, context)

        # Save to context
        context.user_data['my_sentences'] = results
        context.user_data['current_page'] = 1
        context.user_data['items_per_page'] = 5

        # Render the page
        await self.render_edit_sentences_list(update, context, is_new_message=True)
        return EDIT_SENTENCES


    async def edit_sentences_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles all inline button actions within EDIT_SENTENCES flow:
          - prev_page / next_page
          - view_item_X
          - delete_X
          - back_to_list (if needed)
        """
        cancel_restarted_message(context)
        query = update.callback_query
        await query.answer()

        data = query.data
        logger.info(f"edit_sentences_callback data: {data}")

        # PREV PAGE
        if data == "prev_page":
            context.user_data['current_page'] = max(1, context.user_data['current_page'] - 1)
            await self.render_edit_sentences_list(update, context)
            return EDIT_SENTENCES

        # NEXT PAGE
        elif data == "next_page":
            # Bump page up, or ensure it doesn't exceed total pages
            context.user_data['current_page'] += 1
            await self.render_edit_sentences_list(update, context)
            return EDIT_SENTENCES

        # VIEW ITEM
        elif data.startswith("view_item_"):
            match = re.match(r"view_item_(\d+)", data)
            if match:
                item_idx = int(match.group(1))
                await self.render_sentence_detail(update, context, item_idx)
            return EDIT_SENTENCES

        # DELETE SENTENCE
        elif data.startswith("delete_"):
            match = re.match(r"delete_(\d+)", data)
            if match:
                video_id = int(match.group(1))
                await self.delete_video_item(update, context, video_id)
            return EDIT_SENTENCES

        # If there's a "back_to_list" button or something similar:
        elif data == "back_to_list":
            await query.message.delete()
            await self.render_edit_sentences_list(update, context)
            return EDIT_SENTENCES

        # Default fallback
        return EDIT_SENTENCES


    async def render_edit_sentences_list(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_new_message=False
    ):
        """
        Renders the translator's sentences in a paginated list with inline buttons:
          - "prev_page" / "next_page"
          - "view_item_X"
        Also includes a standard "Go back" text button if you want.
        """
        sentences = context.user_data.get('my_sentences', [])
        page = context.user_data.get('current_page', 1)
        items_per_page = context.user_data.get('items_per_page', 5)

        total_items = len(sentences)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        if total_pages == 0:
            # No items, possibly show a message or return
            return

        # Bound-check the page
        if page < 1: 
            page = 1
        elif page > total_pages:
            page = total_pages
        context.user_data['current_page'] = page

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_items = sentences[start_idx:end_idx]

        # Build the message text
        total_sentences_text = self.translation_manager.get_translation(context, 'total_sentences')
        vote_count_format_text = self.translation_manager.get_translation(context, 'vote_count_format')
        lines = [total_sentences_text.format(total_items)]
        idx_label = start_idx + 1
        for item in current_items:
            line = (f"{idx_label}. {item['sentence']} \n"
                    + vote_count_format_text.format(item['upvotes'], item['downvotes']))
            lines.append(line)
            idx_label += 1
        message_text = "\n".join(lines)

        # Inline keyboard: 
        # Row 1: one button per item -> "view_item_0", "view_item_1", etc.
        item_buttons = []
        for i in range(len(current_items)):
            absolute_idx = start_idx + i
            button_label = str(absolute_idx + 1)
            item_buttons.append(InlineKeyboardButton(button_label, callback_data=f"view_item_{absolute_idx}"))
        
        # Row 2: pagination
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("Prev", callback_data="prev_page"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next", callback_data="next_page"))
        
        keyboard_rows = []
        if item_buttons:
            keyboard_rows.append(item_buttons)
        if nav_buttons:
            keyboard_rows.append(nav_buttons)

        keyboard = InlineKeyboardMarkup(keyboard_rows)

        # Decide whether to send a new message or edit an existing one
        if is_new_message:
            await update.message.reply_text(message_text, reply_markup=keyboard)
            # Optional text keyboard
            go_back_text = self.translation_manager.get_translation(context, 'go_back')
            await update.message.reply_text(
                self.translation_manager.get_translation(context, 'edit_menu_prompt'),
                reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True)
            )
        else:
            # We are in a callback, so we edit the message
            query = update.callback_query
            try:
                await query.message.edit_text(message_text, reply_markup=keyboard)
            except Exception as e:
                logger.warning(f"Couldn't edit the existing message: {e}")
                await query.message.reply_text(message_text, reply_markup=keyboard)


    async def render_sentence_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_idx: int):
        """
        Shows the detail for one selected sentence item,
        including the video preview if found, 
        plus a "Delete" and "Back" button.
        """
        sentences = context.user_data.get('my_sentences', [])
        if item_idx < 0 or item_idx >= len(sentences):
            item_not_found_text = self.translation_manager.get_translation(context, 'item_not_found')
            await update.callback_query.message.reply_text(item_not_found_text)
            return

        item = sentences[item_idx]
        delete_button_text = self.translation_manager.get_translation(context, 'delete_button')
        back_button_text = self.translation_manager.get_translation(context, 'back_button')

        buttons = [
            [
                InlineKeyboardButton(delete_button_text, callback_data=f"delete_{item['video_id']}"),
                InlineKeyboardButton(back_button_text, callback_data="back_to_list")
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        # Delete previous message
        query = update.callback_query
        await query.message.delete()

        caption = (
            f"{item['sentence']}\n"
            f"Up votes: {item['upvotes']}  Down votes: {item['downvotes']}"
        )
        # If video file exists, send it
        if item['video_path'] and os.path.exists(item['video_path']):
            with open(item['video_path'], 'rb') as f:
                await query.message.reply_video(f, caption=caption, reply_markup=keyboard)
        else:
            video_not_found_text = self.translation_manager.get_translation(context, 'video_not_found')
            await query.message.reply_text(f"{caption}\n\n{video_not_found_text}", reply_markup=keyboard)


    async def delete_video_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: int):
        query = update.callback_query
        await query.answer()

        # 1) Remove the detail message (the “Are you sure?” or detail info)
        await query.message.delete()

        # 2) Find the item in memory so we can get the sentence_id
        old_list = context.user_data.get('my_sentences', [])
        item = next((x for x in old_list if x['video_id'] == video_id), None)
        if not item:
            # No matching item found in local memory
            logger.warning(f"No local data found for video_id={video_id}")
            return

        sentence_id = item['sentence_id']

        # 3) Call the “universal” function that decides whether to remove just the one video
        #    or remove the entire sentence row if there is only that single referencing video
        user_id = self._get_user_id_from_context(context, update)
        self.db_service.delete_sentence_and_video(sentence_id, user_id, video_id)

        # 4) Remove from local memory
        new_list = [x for x in old_list if x['video_id'] != video_id]
        context.user_data['my_sentences'] = new_list

        # 5) If no items remain, optionally show a “no sentences found” message
        if not new_list:
            await query.message.reply_text(
                self.translation_manager.get_translation(context, 'no_sentences_found')
            )
            return

        # 6) Adjust pagination if the current_page is now out-of-bounds
        items_per_page = context.user_data.get('items_per_page', 5)
        total_items = len(new_list)
        current_page = context.user_data.get('current_page', 1)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        if current_page > total_pages:
            context.user_data['current_page'] = total_pages

        # 7) Re-render your main list
        await self.render_edit_sentences_list(update, context)



    async def edit_sentences_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        user_input = update.message.text
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        if user_input == go_back_text:
            selected_classroom = context.user_data.get("selected_classroom")
            classroom_id = selected_classroom["classroom_id"] if selected_classroom else None
            if not classroom_id:
                return await self.show_translator_menu(update, context)
            return await self.show_classrooms_menu(update, context)
        else:
            # Just prompt again
            prompt_text = self.translation_manager.get_translation(context, 'edit_menu_prompt')
            await update.message.reply_text(prompt_text)
            return EDIT_SENTENCES
   

    # --------------------------------------------------------------------------
    # VOTING
    # --------------------------------------------------------------------------

    async def start_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Start the voting flow:
         - Show a 'Voting Started' message
         - Immediately fetch/send the first video to vote on
        """
        voting_started_text = self.translation_manager.get_translation(context, 'voting_started')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')

        reply_keyboard = ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(voting_started_text, reply_markup=reply_keyboard)

        return await self.send_next_video_for_voting(update, context)

    async def send_next_video_for_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Fetch the next random video not uploaded by the translator, not yet voted on by them.
        Display it with up/down vote buttons.
        """
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await update.message.reply_text(bot_restarted_text)
            return -1

        user_language = context.user_data.get('language', 'English')
        no_more_videos_text = self.translation_manager.get_translation(context, 'no_more_videos_to_vote')
        voting_sentence_text = self.translation_manager.get_translation(context, 'voting_sentence')
        up_vote_text = self.translation_manager.get_translation(context, 'up_vote')
        down_vote_text = self.translation_manager.get_translation(context, 'down_vote')

        # Attempt to fetch a random video for voting
        try:
            video_info = self.db_service.get_random_video_for_voting(user_id, user_language)
            if video_info is None:
                await update.message.reply_text(no_more_videos_text)
                return TRANSLATOR_MENU

            (video_id, file_path, sentence_content) = video_info
            if not os.path.exists(file_path):
                logger.error(f"Voting video not found: {file_path}")
                await update.message.reply_text("Video file missing. Try again.")
                return await self.show_translator_menu(update, context)

            # Store the current video id for reference
            context.user_data['current_voting_video_id'] = video_id

            # Build inline keyboard for up/down
            buttons = [
                [
                    InlineKeyboardButton(text=up_vote_text, callback_data='vote_up'),
                    InlineKeyboardButton(text=down_vote_text, callback_data='vote_down')
                ]
            ]
            keyboard = InlineKeyboardMarkup(buttons)
            message_target = update.message or update.callback_query.message
            # Send the video + voting keyboard
            with open(file_path, 'rb') as video_file:
                sent_message = await message_target.reply_video(
                    video_file,
                    caption=voting_sentence_text.format(sentence_content),
                    reply_markup=keyboard
                )
                context.user_data['current_voting_message_id'] = sent_message.message_id

            return VOTING
        except Exception as e:
            logger.error(f"Error in send_next_video_for_voting: {e}")
            return await self.show_translator_menu(update, context)

    async def handle_voting_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        If you're allowing text-based voting, you'd handle it here (like user typing "up_vote" or "down_vote").
        Otherwise, you can rely purely on callback queries with handle_vote_up / handle_vote_down.
        """
        user_input = update.message.text
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await update.message.reply_text(bot_restarted_text)
            return -1

        video_id = context.user_data.get('current_voting_video_id')
        if video_id is None:
            voting_error_text = self.translation_manager.get_translation(context, 'voting_error')
            await update.message.reply_text(voting_error_text)
            return TRANSLATOR_MENU

        up_vote_text = self.translation_manager.get_translation(context, 'up_vote')
        down_vote_text = self.translation_manager.get_translation(context, 'down_vote')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')

        if user_input == up_vote_text:
            self.db_service.increment_video_score(video_id, 'positive_scores')
            self.db_service.record_vote(user_id, video_id, 'up')
        elif user_input == down_vote_text:
            self.db_service.increment_video_score(video_id, 'negative_scores')
            self.db_service.record_vote(user_id, video_id, 'down')
        elif user_input == go_back_text:
            return await self.show_translator_menu(update, context)
        else:
            await update.message.reply_text(invalid_option_text)
            return VOTING

        # Remove the old message
        if 'current_voting_message_id' in context.user_data:
            chat_id = update.effective_chat.id
            message_id = context.user_data['current_voting_message_id']
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(f"Error deleting voting message: {e}")
            del context.user_data['current_voting_message_id']

        # Move on to the next video
        return await self.send_next_video_for_voting(update, context)

    async def handle_vote_up(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Callback version for 'vote_up'.
        """
        query = update.callback_query
        await query.answer()

        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await query.message.reply_text(bot_restarted_text)
            return -1

        video_id = context.user_data.get('current_voting_video_id')
        if video_id is None:
            voting_error_text = self.translation_manager.get_translation(context, 'voting_error')
            await query.message.reply_text(voting_error_text)
            return TRANSLATOR_MENU

        # Record up vote
        self.db_service.increment_video_score(video_id, 'positive_scores')
        self.db_service.record_vote(user_id, video_id, 'up')

        await query.message.delete()

        # Next video
        return await self.send_next_video_for_voting(update, context)


    async def handle_vote_down(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Callback version for 'vote_down'.
        """
        # 1) Cancel any pending fallback job immediately
        cancel_restarted_message(context)
        
        query = update.callback_query
        await query.answer()  # Acknowledge the callback

        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await query.message.reply_text(bot_restarted_text)
            return -1

        video_id = context.user_data.get('current_voting_video_id')
        if video_id is None:
            voting_error_text = self.translation_manager.get_translation(context, 'voting_error')
            await query.message.reply_text(voting_error_text)
            return await self.show_translator_menu(update, context)

        # 2) Increment negative score
        self.db_service.increment_video_score(video_id, 'negative_scores')

        # 3) Insert the 'down' vote and retrieve the newly created vote_id
        vote_id = self.db_service.record_vote(user_id, video_id, 'down')

        # 4) Save vote_id to context so we can update its feedback later
        context.user_data['current_vote_id'] = vote_id

        # 5) Prompt user for feedback
        downvote_feedback_prompt = self.translation_manager.get_translation(context, 'downvote_feedback_prompt')
        # (You can translate the prompt_text as needed)
        await query.message.reply_text(downvote_feedback_prompt)

        # 6) Return a new state: WAITING_FOR_FEEDBACK
        return WAITING_FOR_FEEDBACK


    async def handle_negative_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        User has typed feedback text after downvoting a video.
        """
        # 1) Cancel any pending fallback job immediately
        cancel_restarted_message(context)

        user_feedback = update.message.text
        vote_id = context.user_data.get('current_vote_id')

        # Safety check
        if not vote_id:
            await update.message.reply_text("Something went wrong. Let's go back to main menu.")
            return await self.show_translator_menu(update, context)

        # 2) Update the DB with the feedback
        self.db_service.update_vote_feedback(vote_id, user_feedback)

        # 3) Clean up the context
        del context.user_data['current_vote_id']

        # 4) Optionally remove the old "voting message"
        if 'current_voting_message_id' in context.user_data:
            chat_id = update.effective_chat.id
            message_id = context.user_data['current_voting_message_id']
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.error(f"Error deleting voting message: {e}")
            del context.user_data['current_voting_message_id']

        # 5) Finally, move on to the next video
        return await self.send_next_video_for_voting(update, context)


    async def voting_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        If you're allowing user to type commands like 'Go back' while in VOTING state.
        """
        user_input = update.message.text.strip() if update.message else None
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')

        if user_input == go_back_text:
            # Possibly remove the current video message
            if 'current_voting_message_id' in context.user_data:
                chat_id = update.effective_chat.id
                msg_id = context.user_data['current_voting_message_id']
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    logger.error(f"Error deleting voting message: {e}")
                del context.user_data['current_voting_message_id']

            return await self.show_translator_menu(update, context)
        else:
            await update.message.reply_text(invalid_option_text)
            return VOTING

    # --------------------------------------------------------------------------
    # INTERNAL / HELPER METHODS
    # --------------------------------------------------------------------------

    def _get_user_id_from_context(self, context, update) -> int:
        """
        Retrieves user_id from context, or tries to fetch from DB if not in context.
        """
        user_id = context.user_data.get('user_id')
        if user_id:
            return user_id

        telegram_id = context.user_data.get('telegram_id')
        if not telegram_id:
            return None

        db_user_id, _, _, _ = self.db_service.check_user_exists(telegram_id)
        if db_user_id:
            context.user_data['user_id'] = db_user_id
            return db_user_id
        return None

    def _get_next_available_filename(self, update, context, role="translator"):
        """
        A direct port of your 'get_next_available_filename' logic, 
        but we choose the directory based on 'role'.
        """
        user_id = self._get_user_id_from_context(context, update)
        username = context.user_data.get('username', 'unknown')

        if role.lower() == "translator":
            directory = "/home/ubuntu/Sign_Language_System/Video/Translator"
        else:
            directory = "/home/ubuntu/Sign_Language_System/Video/User"

        os.makedirs(directory, exist_ok=True)

        prefix = f"{role.lower()}_video_{user_id}_{username}_"
        existing_files = [f for f in os.listdir(directory) if f.startswith(prefix)]

        max_number = 0
        for file in existing_files:
            match = re.search(rf"{prefix}(\d+)\.mp4", file)
            if match:
                file_number = int(match.group(1))
                max_number = max(max_number, file_number)

        next_number = max_number + 1
        return os.path.join(directory, f"{prefix}{next_number}.mp4")

    async def _download_video(self, video, file_path, context):
        """
        Download the given Telegram video to local storage.
        """
        new_file = await context.bot.get_file(video.file_id)
        await new_file.download_to_drive(file_path)


