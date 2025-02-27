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
ADMIN_MENU = 50
HANDLE_USERS = 51
ASK_FILTER_VALUE = 52
FILTER_USERS  = 53

class AdminHandlers:
    def __init__(self, db_service, translation_manager):
        """
        :param db_service:          Instance of your DatabaseService class.
        :param translation_manager: Instance of your TranslationManager class.
        """
        self.db_service = db_service
        self.translation_manager = translation_manager
#=====================================================================================
#ADMIN MENU
#=====================================================================================
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Display the translator menu options:
          -Handle Users
          -xxxx
          -xxxx
          -xxxx
          -xxxx
        """
        menu_text = self.translation_manager.get_translation(context, 'admin_menu')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        handle_users = self.translation_manager.get_translation(context, 'handle_users')
        reply_keyboard = [
            [handle_users, cancel_text]
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

        return ADMIN_MENU
    
    async def handle_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        React to the translator's menu choice:
          - Handle Users
          - Cancel -> return or end
        """
        user_choice = update.message.text
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        handle_users = self.translation_manager.get_translation(context, 'handle_users')

        if user_choice == handle_users:
            return await self.show_user_management(update, context)

        elif user_choice == cancel_text:
            cancel_text=self.translation_manager.get_translation(context,'cancel_message')
            start_button=self.translation_manager.get_translation(context,'start_button')
            reply_keyboard=[[start_button]]
            await update.message.reply_text(
                cancel_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return ConversationHandler.END
     
#=====================================================================================
#USER MANAGEMENT
#=====================================================================================        
    async def show_user_management(self, update, context):
        """
        Display admin user management menu.
        """
        cancel_restarted_message(context)

        menu_text = "Select an action:"
        view_users = "View Users"
        filter_users = "Filter and View Users"
        update_user = "Update User"
        delete_user = "Delete User"
        back_text = "⬅️ Back to Admin Menu"

        keyboard = [
            [view_users, filter_users],
            [update_user, delete_user],
            [back_text]
        ]

        await update.message.reply_text(
            menu_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return HANDLE_USERS
    
    async def handle_user_choice(self, update, context):
        """
        Handle user selection from the admin menu.
        """
        cancel_restarted_message(context)
        choice = update.message.text
        view_users = "View Users"
        filter_users = "Filter and View Users"
        update_user = "Update User"
        delete_user = "Delete User"
        back_text = "⬅️ Back to Admin Menu"
        back_user_man_text = "⬅️ Back to User Management"

        if choice == view_users:
            return await self.view_users(update, context)
        elif choice == filter_users:
            return await self.ask_filter_criteria(update, context)
        elif choice == update_user:
            return await self.ask_update_details(update, context)
        elif choice == delete_user:
            return await self.ask_delete_user(update, context)
        elif choice == back_text:
            return await self.show_admin_menu(update, context)
        elif choice == back_user_man_text:
            return await self.show_user_management(update, context)
#=====================================================================================
#view_all_users
#=====================================================================================     

    USERS_PER_PAGE = 10

    async def view_users(self, update, context):
        cancel_restarted_message(context)
        """
        Retrieve and display users with pagination (15 users per page).
        """
        users = self.db_service.get_all_users()

        if not users:
            await update.message.reply_text("No users found.")
            return await self.show_admin_menu(update, context)

        context.user_data['users'] = users  # Store all users in context
        context.user_data['current_page'] = 0  # Start from the first page

        return await self.show_user_page(update, context, page=0)

    async def show_user_page(self, update, context, page=0):
        cancel_restarted_message(context)
        """
        Displays a specific page of users.
        """
        users = context.user_data.get('users', [])
        total_users = len(users)
        
        if total_users == 0:
            await update.message.reply_text("No users to display.")
            return await self.show_admin_menu(update, context)

        start_index = page * self.USERS_PER_PAGE
        end_index = min(start_index + self.USERS_PER_PAGE, total_users)
        
        page_users = users[start_index:end_index]
        user_list_text = "\n".join([
            f"ID: {u[0]} | Name: {u[1]} | 🌍 Country: {u[2]} | Role: {u[3]} | 📲 Telegram ID: {u[4]}\n-----------------------------------"
            for u in page_users
        ])

        pagination_buttons = []
        if start_index > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_users"))
        if end_index < total_users:
            pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"next_users"))

        keyboard = [pagination_buttons] if pagination_buttons else []
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        # Edit the message if a button was clicked, otherwise send a new message
        if update.callback_query:
            await update.callback_query.message.edit_text(user_list_text, reply_markup=reply_markup)
            await update.callback_query.answer()
        else:
            await update.message.reply_text(user_list_text, reply_markup=reply_markup)

        context.user_data['current_page'] = page
        return HANDLE_USERS

    async def handle_pagination(self, update, context):
        cancel_restarted_message(context)
        """
        Handles pagination for user list.
        """
        query = update.callback_query
        action = query.data

        current_page = context.user_data.get('current_page', 0)
        
        if action == "next_users":
            new_page = current_page + 1
        elif action == "prev_users":
            new_page = max(0, current_page - 1)
        else:
            return  # Invalid action

        return await self.show_user_page(update, context, new_page)

#=====================================================================================
#VIEW FILTERED USERS
#=====================================================================================     

    async def ask_filter_criteria(self, update, context):
        cancel_restarted_message(context)
        """
        Ask the admin which column to filter by.
        """
        back_user_man_text="⬅️ Back to User Management"
        
        await update.message.reply_text(
            "Enter the column name to filter by (e.g., role, country):",
            reply_markup=ReplyKeyboardMarkup([[back_user_man_text]], resize_keyboard=True, one_time_keyboard=True)
        )
        
        return ASK_FILTER_VALUE

    async def filter_users(self, update, context):
        cancel_restarted_message(context)
        """
        Get users filtered by the admin's input.
        """
        back_user_man_text="⬅️ Back to User Management"
        user_input = update.message.text
        if user_input == back_user_man_text:
            return await self.show_user_management(update, context)
        valid_columns = self.db_service.get_user_table_columns()
    
        if user_input not in valid_columns:
            column_list = ", ".join(valid_columns)
            await update.message.reply_text(
                f"❌ Invalid column: {user_input}\n\nPlease choose from: {column_list}",
                reply_markup=ReplyKeyboardMarkup([[back_user_man_text]], resize_keyboard=True, one_time_keyboard=True)
            )
            return ASK_FILTER_VALUE
        context.user_data['filter_column'] = user_input
        
        
        await update.message.reply_text(
            f"Enter the value for {context.user_data['filter_column']}:",
            reply_markup=ReplyKeyboardMarkup([[back_user_man_text]], resize_keyboard=True, one_time_keyboard=True)
        )
        
        return FILTER_USERS




    async def show_filtered_users(self, update, context):
        cancel_restarted_message(context)
        """
        Display users filtered by the chosen column and value with pagination.
        """
        if update.callback_query:
            return await self.handle_filtered_pagination(update, context)  # ✅ Handle Next/Prev clicks
        back_user_man_text="⬅️ Back to User Management"
        # ✅ Handle when user types a filter value
        user_input = update.message.text
        if user_input == back_user_man_text:
            return await self.show_user_management(update, context)

        column = context.user_data.get('filter_column')
        value = user_input

        users = self.db_service.get_users_filtered(column, value)

        if not users:
            await update.message.reply_text("❌ No users found matching the criteria.")
            return HANDLE_USERS

        # ✅ Store data & initialize pagination
        context.user_data['filtered_users'] = users
        context.user_data['filtered_page'] = 0  

        return await self.show_filtered_user_page(update, context, page=0)



    async def show_filtered_user_page(self, update, context, page=0):
        """
        Display a specific page of filtered users.
        """
        users = context.user_data.get('filtered_users', [])
        total_users = len(users)

        if total_users == 0:
            await update.message.reply_text("❌ No users to display.")
            return HANDLE_USERS

        USERS_PER_PAGE = 10  # ✅ Set pagination limit
        start_index = page * USERS_PER_PAGE
        end_index = min(start_index + USERS_PER_PAGE, total_users)

        # ✅ Format user data for display
        page_users = users[start_index:end_index]
        user_list_text = "\n".join([
            f"ID: {u[0]} | Name: {u[1]} | 🌍 Country: {u[2]} | Role: {u[3]} | 📲 Telegram ID: {u[4]}\n-----------------------------------"
            for u in page_users
        ])

        # ✅ Navigation Buttons (Only show if needed)
        pagination_buttons = []
        if start_index > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data="prev_filtered_users"))
        if end_index < total_users:
            pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data="next_filtered_users"))

        reply_markup = InlineKeyboardMarkup([pagination_buttons]) if pagination_buttons else None

        # ✅ Edit message if callback_query, otherwise send a new message
        if update.callback_query:
            await update.callback_query.message.edit_text(user_list_text, reply_markup=reply_markup)
            await update.callback_query.answer()
        else:
            await update.message.reply_text(user_list_text, reply_markup=reply_markup)

        # ✅ Store current page number
        context.user_data['filtered_page'] = page
        return HANDLE_USERS



    async def handle_filtered_pagination(self, update, context):
        """
        Handles Next/Previous pagination for filtered users.
        """
        query = update.callback_query
        action = query.data

        current_page = context.user_data.get('filtered_page', 0)  # ✅ Get current page number

        if action == "next_filtered_users":
            new_page = current_page + 1
        elif action == "prev_filtered_users":
            new_page = max(0, current_page - 1)
        else:
            return  # ❌ Invalid action

        context.user_data['filtered_page'] = new_page  # ✅ Store new page number
        return await self.show_filtered_user_page(update, context, new_page)






    # async def ask_update_details(self, update, context):
    #     """
    #     Ask for the user ID to update.
    #     """
    #     await update.message.reply_text("Enter the user ID to update:")
    #     return ASK_COLUMN

    # async def ask_column_to_update(self, update, context):
    #     """
    #     Ask which column should be updated.
    #     """
    #     context.user_data['user_id'] = update.message.text
    #     await update.message.reply_text("Enter the column you want to update (e.g., user_role, country):")
    #     return ASK_VALUE

    # async def ask_new_value(self, update, context):
    #     """
    #     Ask for the new value of the selected column.
    #     """
    #     context.user_data['column'] = update.message.text
    #     await update.message.reply_text(f"Enter the new value for {context.user_data['column']}:")
    #     return UPDATE_USER

    # async def update_user(self, update, context):
    #     """
    #     Update the user with the provided details.
    #     """
    #     user_id = context.user_data['user_id']
    #     column = context.user_data['column']
    #     new_value = update.message.text

    #     success = self.db_service.update_user_info(user_id, column, new_value)
    #     message = f"User ID {user_id} updated successfully!" if success else "Failed to update user."
    #     await update.message.reply_text(message)
    #     return HANDLE_USERS
