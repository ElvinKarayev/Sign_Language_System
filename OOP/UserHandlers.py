import logging
import os
import re
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InputMediaVideo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
   
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)
from cancel import cancel_restarted_message
from telegram.ext import ContextTypes
from admin import handle_contact_admin
logger = logging.getLogger(__name__)

# Example conversation states (import or define them as needed)
USER_MENU = 5
USER_VIEW_VIDEOS = 11
USER_REQUEST = 12

class UserHandlers:
    def __init__(self, db_service, translation_manager):
        """
        :param db_service:   An instance of your DatabaseService class
                             (for all DB queries).
        :param translation_manager: An instance of your TranslationManager class
                             for retrieving localized strings.
        """
        self.db_service = db_service
        self.translation_manager = translation_manager

    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Display the main user menu with options:
          - Request a video
          - View your own videos
          - Cancel / go back
        """
        user_menu_text = self.translation_manager.get_translation(context, 'user_menu')
        request_video_text = self.translation_manager.get_translation(context, 'request_video')
        view_videos_text = self.translation_manager.get_translation(context, 'view_videos')
        contact_admin_text =  self.translation_manager.get_translation(context, 'contact_admin')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')

         # 1) Add a new translation key for "show_my_rank" in your translation files
        show_my_rank_text = self.translation_manager.get_translation(context, 'show_my_rank')

        reply_keyboard = [
            [request_video_text, view_videos_text],
            [show_my_rank_text, contact_admin_text],
            [cancel_text]
        ]

        message = update.message if update.message else update.callback_query.message

        if message:
            # Send the video first
            try:
                with open('/home/ubuntu/Sign_Language_System/assets/instruction.mp4', 'rb') as video:
                    await message.reply_video(video)
            except Exception as e:
                logger.error(f"Error sending instruction video: {e}")

            # Send the user menu text with the keyboard
            await message.reply_text(
                user_menu_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
        else:
            logger.error("Both update.message and callback_query.message are None.")
        
        return USER_MENU

    

    async def handle_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)  # <-- THIS LINE WAS MISSING
        """
        Respond to a user's choice on the user menu.
        - 'Request a video' -> handle_user_flow
        - 'View your videos' -> handle_view_user_videos
        - 'Cancel' -> e.g., end or go back
        """
        user_choice = update.message.text
        request_video_text = self.translation_manager.get_translation(context, 'request_video')
        view_videos_text = self.translation_manager.get_translation(context, 'view_videos')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        contact_admin_text =  self.translation_manager.get_translation(context, 'contact_admin')
        # The new menu text we added
        show_my_rank_text = self.translation_manager.get_translation(context, 'show_my_rank')

        if user_choice == request_video_text:
            return await self.handle_user_flow(update, context)

        elif user_choice == view_videos_text:
            return await self.handle_view_user_videos(update, context)

        elif user_choice == contact_admin_text:
            return await handle_contact_admin(update, context, self.translation_manager)

        elif user_choice == show_my_rank_text:
            return await self.handle_show_user_rank(update, context)

        elif user_choice == cancel_text:
            # Existing cancel logic...
            cancel_text = self.translation_manager.get_translation(context, 'cancel_message')
            start_button = self.translation_manager.get_translation(context, 'start_button')
            reply_keyboard = [[start_button]]
            await update.message.reply_text(
                cancel_text,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return ConversationHandler.END

        else:
            invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')
            await update.message.reply_text(invalid_option_text)
            return await self.show_user_menu(update,context)


    async def handle_user_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        The user requests a random translator video to respond to.
        We get a random translator video from DB, show it, and
        prompt the user to upload a response or skip.
        """
        user_language = context.user_data.get('language', 'English')
        skipped_videos = context.user_data.get('skipped_videos', set())

        logger.info(f"Handling user flow for language: {user_language}, skipped: {skipped_videos}")

        # Fetch a random translator video, excluding the user's own videos or skipped ones
        file_path, sentence = self.db_service.get_random_translator_video(user_language, context, exclude_ids=skipped_videos)
        if file_path:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as video_file:
                        await update.message.reply_video(video_file)
                    if sentence:
                        msg = self.translation_manager.get_translation(context, 'translated_sentence')
                        await update.message.reply_text(msg.format(sentence))
                    
                    # Prompt user with skip/cancel options
                    cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
                    skip_text = self.translation_manager.get_translation(context, 'skip_button')
                    user_prompt_text = self.translation_manager.get_translation(context, 'user_prompt')

                    reply_keyboard = [[cancel_text, skip_text]]
                    await update.message.reply_text(
                        user_prompt_text,
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
                    )
                    return USER_REQUEST

                except Exception as e:
                    logger.error(f"Error sending video: {e}")
                    await update.message.reply_text("Sorry, there was an error sending the video.")
                    # Possibly return to user menu
                    return USER_MENU
            else:
                logger.error(f"Video file not found at path: {file_path}")
                await update.message.reply_text("call support team to fix this problem")
                return await self.show_user_menu(update,context)
        else:
            no_videos_text = self.translation_manager.get_translation(context, 'no_more_videos')
            await update.message.reply_text(no_videos_text)
            return await self.show_user_menu(update,context)

    async def user_video_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        This method handles the user either uploading a video or skipping/canceling
        after seeing a translator video. If they upload a video, we store it and
        then fetch the next one. If skip, we mark the video as skipped, then fetch next.
        If cancel, we end or go back to user menu.
        """
        user_input = update.message.text if update.message else None
        user_video = update.message.video if update.message and update.message.video else None

        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        skip_text = self.translation_manager.get_translation(context, 'skip_button')
        valid_video_error = self.translation_manager.get_translation(context, 'valid_video_error')
        bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
        thank_you_response_text = self.translation_manager.get_translation(context, 'continue_exchange')
        no_more_videos_text = self.translation_manager.get_translation(context, 'no_more_videos')

        # If the user uploads a video
        if user_video:
            user_id = self._get_user_id_from_context(context, update)
            if not user_id:
                await update.message.reply_text(bot_restarted_text)
                return -1  # or ConversationHandler.END

            # We need to store the user's response referencing the translator video
            translator_video_id = context.user_data.get('current_translator_video_id')
            translator_text_id = self.db_service.get_video_text_id(translator_video_id)

            # Generate a file path and save video
            file_path = self._get_next_available_filename(update, context, role="user")
            await self._download_video(user_video, file_path, context)
            
            # Insert DB row referencing the translator video
            user_language = context.user_data.get('language', 'English')
            self.db_service.save_video_info(
                user_id=user_id,
                file_path=file_path,
                language=user_language,
                sentence=None,
                reference_id=translator_video_id,
                sentence_id=translator_text_id
            )

            await update.message.reply_text(thank_you_response_text)

            # Fetch next translator video
            file_path2, sentence = self.db_service.get_random_translator_video(user_language, context)
            if file_path2 and os.path.exists(file_path2):
                with open(file_path2, 'rb') as video_file:
                    await update.message.reply_video(video_file)
                if sentence:
                    trans_sentence_msg = self.translation_manager.get_translation(context, 'translated_sentence')
                    await update.message.reply_text(trans_sentence_msg.format(sentence))
                # Prompt user again
                cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
                skip_text = self.translation_manager.get_translation(context, 'skip_button')
                user_prompt_text = self.translation_manager.get_translation(context, 'user_prompt')

                reply_keyboard = [[cancel_text, skip_text]]
                await update.message.reply_text(
                    user_prompt_text,
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
                )
                return USER_REQUEST
            else:
                await update.message.reply_text(no_more_videos_text)
                return await self.show_user_menu(update,context)

        elif user_input == skip_text:
            # Mark current video as "skipped"
            current_video_id = context.user_data.get('current_translator_video_id')
            if current_video_id:
                skipped_videos = context.user_data.get('skipped_videos', set())
                skipped_videos.add(current_video_id)
                context.user_data['skipped_videos'] = skipped_videos
                logger.info(f"Skipped video ID: {current_video_id}")

            # Fetch next video
            return await self.handle_user_flow(update, context)

        elif user_input == cancel_text:
            # Possibly go back to user menu
            return await self.show_user_menu(update,context)
        else:
            # If they typed something else or just a text, but we want a video
            await update.message.reply_text(valid_video_error)
            return USER_REQUEST

    async def handle_view_user_videos(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Shows a paginated list of the user's own videos + the corresponding translator videos.
        Then calls display_current_user_video_group to show them in pairs.
        """
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await update.message.reply_text(bot_restarted_text)
            return -1

        user_videos = self.db_service.get_user_videos_and_translator_videos(user_id)
        no_uploaded_videos_text = self.translation_manager.get_translation(context, 'no_uploaded_videos')
        edit_menu_prompt_text = self.translation_manager.get_translation(context, 'edit_menu_prompt')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')

        if not user_videos:
            await update.message.reply_text(no_uploaded_videos_text)
            return await self.show_user_menu(update,context)

        # Store them in context and start at index 0
        context.user_data['user_videos'] = user_videos
        context.user_data['current_index'] = 0
        context.user_data.pop('message_ids', None)  # Reset

        reply_keyboard = ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(edit_menu_prompt_text, reply_markup=reply_keyboard)

        # Display the first group
        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS

    async def user_videos_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handle simple text-based navigation within the 'View Your Videos' menu.
        If user says 'Go back', return to user menu; otherwise repeat the prompt.
        """
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')

        user_input = update.message.text
        if user_input == go_back_text:
            return await self.show_user_menu(update,context)
        else:
            await update.message.reply_text(invalid_option_text)
            return USER_VIEW_VIDEOS


    async def display_current_user_video_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Show the user's current video + translator video side by side using
        messages with 'Next', 'Previous', and 'Delete' buttons.
        Also display upvote/downvote counts for the user's video.
        """
        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)

        if not user_videos:
            no_uploaded_videos_text = self.translation_manager.get_translation(context, 'no_uploaded_videos')
            message = update.message if update.message else update.callback_query.message
            if message:
                await message.reply_text(no_uploaded_videos_text)
            return await self.show_user_menu(update, context)

        # Bound check
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

        # [UPDATED LINE: Retrieve upvote/downvote counts for the user's video]
        user_upvotes = video_pair.get('user_upvotes', 0)
        user_downvotes = video_pair.get('user_downvotes', 0)

        # Build inline keyboard (delete / next / prev)
        delete_text = self.translation_manager.get_translation(context, 'delete')
        delete_callback_data = f"delete_user_video_{user_video_id}"
        delete_button = InlineKeyboardButton(text=delete_text, callback_data=delete_callback_data)

        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("Previous", callback_data="previous_user_video"))
        if current_index < len(user_videos) - 1:
            nav_buttons.append(InlineKeyboardButton("Next", callback_data="next_user_video"))

        # Combine rows
        keyboard_rows = [[delete_button]]
        if nav_buttons:
            keyboard_rows.append(nav_buttons)

        markup = InlineKeyboardMarkup(keyboard_rows)

        # Determine the message to edit/reply to
        message = update.message if update.message else update.callback_query.message
        if not message:
            return

        chat_id = message.chat_id
        message_ids = context.user_data.get('message_ids', {})

        # 1) Show/Update translator video
        translator_caption = self.translation_manager.get_translation(context, 'translator_video')
        translator_not_found = self.translation_manager.get_translation(context, 'translator_video_not_available')

        if 'translator' in message_ids:
            existing_msg_id = message_ids['translator']
            if translator_video_path and os.path.exists(translator_video_path):
                await self._edit_video_message(
                    context, chat_id, existing_msg_id,
                    translator_video_path, translator_caption
                )
            else:
                await self._edit_text_message(
                    context, chat_id, existing_msg_id,
                    translator_not_found
                )
        else:
            if translator_video_path and os.path.exists(translator_video_path):
                msg = await message.reply_video(
                    video=open(translator_video_path, 'rb'),
                    caption=translator_caption
                )
                message_ids['translator'] = msg.message_id
            else:
                msg = await message.reply_text(translator_not_found)
                message_ids['translator'] = msg.message_id

        # 2) Show/Update user video
        user_video_caption = self.translation_manager.get_translation(context, 'your_video')
        user_video_not_found = self.translation_manager.get_translation(context, 'your_video_not_available')

        # [UPDATED LINE: Retrieve the "vote_count_format" translation and apply it]
        vote_count_format = self.translation_manager.get_translation(context, 'vote_count_format')
        # e.g. "    👍: {}    👎: {}\n" or something similar

        # [UPDATED LINE: Append upvote/downvote counts to the user's video caption]
        user_video_caption += "\n" + vote_count_format.format(user_upvotes, user_downvotes)

        if 'user' in message_ids:
            existing_msg_id = message_ids['user']
            if user_video_path and os.path.exists(user_video_path):
                await self._edit_video_message(
                    context, chat_id, existing_msg_id,
                    user_video_path, user_video_caption,
                    markup
                )
            else:
                await self._edit_text_message(
                    context, chat_id, existing_msg_id,
                    user_video_not_found,
                    markup
                )
        else:
            if user_video_path and os.path.exists(user_video_path):
                msg = await message.reply_video(
                    video=open(user_video_path, 'rb'),
                    caption=user_video_caption,
                    reply_markup=markup
                )
                message_ids['user'] = msg.message_id
            else:
                msg = await message.reply_text(user_video_not_found, reply_markup=markup)
                message_ids['user'] = msg.message_id

        context.user_data['message_ids'] = message_ids


    async def handle_next_user_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Callback for the "Next" button in the inline keyboard.
        Increments current index, shows the next video group.
        """
        query = update.callback_query
        await query.answer()

        context.user_data['current_index'] += 1
        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS

    async def handle_previous_user_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Callback for the "Previous" button in the inline keyboard.
        Decrements current index, shows the previous video group.
        """
        query = update.callback_query
        await query.answer()

        context.user_data['current_index'] -= 1
        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS

    async def handle_delete_user_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Callback for the "Delete" button in the inline keyboard.
        Deletes the user's video from DB/filesystem, re-renders the list.
        """
        query = update.callback_query
        await query.answer()
        data = query.data

        match = re.match(r"delete_user_video_(\d+)", data)
        if not match:
            logger.error(f"Invalid callback data: {data}")
            return USER_VIEW_VIDEOS

        user_video_id = int(match.group(1))
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await query.message.reply_text(bot_restarted_text)
            return -1

        # Delete from DB
        self.db_service.delete_user_video(user_video_id, user_id)

        # Remove from context's user_videos
        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)

        for i, video_pair in enumerate(user_videos):
            if video_pair['user_video_id'] == user_video_id:
                user_videos.pop(i)
                if current_index >= len(user_videos):
                    current_index = len(user_videos) - 1
                context.user_data['current_index'] = current_index
                break

        context.user_data['user_videos'] = user_videos

        # Delete old messages visually
        chat_id = update.effective_chat.id
        message_ids = context.user_data.get('message_ids', {})
        for mid in message_ids.values():
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception as e:
                logger.error(f"Error deleting message {mid}: {e}")
        context.user_data.pop('message_ids', None)

        # If no videos left
        if not user_videos:
            no_videos_text = self.translation_manager.get_translation(context, 'your_video_not_available')
            start_text = self.translation_manager.get_translation(context, 'start_button')
            await query.message.reply_text(
                no_videos_text,
                reply_markup=ReplyKeyboardMarkup([[start_text]], one_time_keyboard=True)
            )
            return await self.show_user_menu(update,context)
        
        # Else, show the updated group
        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS


    # --------------------------------------------------------------------------
    # SHOW USER RANK
    # --------------------------------------------------------------------------

    async def handle_show_user_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Use whichever message is actually present (text vs. callback)
        message = update.message if update.message else update.callback_query.message
        
        # Try the existing approach to get user_id
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await message.reply_text(bot_restarted_text)  # <-- note using `message`, not `update.message`
            return -1  # or return USER_MENU, etc.

        # Existing logic continues...
        rank_info = self.db_service.get_user_rank_info(user_id, role="User")
        if not rank_info:
            ranking_no_data_text = self.translation_manager.get_translation(context, 'ranking_no_data')
            await message.reply_text(ranking_no_data_text)
            return await self.show_user_menu(update, context)

        score = rank_info['score']
        rank = rank_info['rank']
        video_count = rank_info['video_count']

        ranking_message_text = self.translation_manager.get_translation(context, 'ranking_message')
        msg = ranking_message_text.format(score=score, rank=rank, video_count=video_count)

        await message.reply_text(msg)  # <-- also use `message`
        return await self.show_user_menu(update, context)

    # --------------------------------------------------------------------------
    # INTERNAL / HELPER METHODS
    # --------------------------------------------------------------------------

    def _get_user_id_from_context(self, context, update) -> int:
        """
        Retrieves user_id from context, or tries to fetch from DB
        via telegram_id if not found. Returns None if not available.
        """
        user_id = context.user_data.get('user_id')
        if user_id:
            return user_id
        else:
            # Try to re-check DB
            telegram_id = context.user_data.get('telegram_id')
            if not telegram_id:
                # Should not happen, but just in case
                return None
            (db_user_id, _, _, _) = self.db_service.check_user_exists(telegram_id)
            if db_user_id:
                context.user_data['user_id'] = db_user_id
                return db_user_id
        return None

    def _get_next_available_filename(self, update, context, role="user"):
        """
        Generate the next available filename for a user's or translator's
        uploaded video (like in your original get_next_available_filename).
        """
        user_id = self._get_user_id_from_context(context, update)
        username = context.user_data.get('username', 'unknown')

        if role.lower() == "user":
            directory = "/home/ubuntu/Sign_Language_System/Video/User"
        else:
            directory = "/home/ubuntu/Sign_Language_System/Video/Translator"

        # Ensure the directory exists
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
        Download a Telegram video to the local file system.
        """
        new_file = await context.bot.get_file(video.file_id)
        await new_file.download_to_drive(file_path)

    async def _edit_video_message(self, context, chat_id, message_id, video_path, caption, markup=None):
        """
        Helper to edit an existing message with a new video (InputMediaVideo).
        """

        media = InputMediaVideo(media=open(video_path, 'rb'), caption=caption)
        try:
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Error editing message media: {e}")

    async def _edit_text_message(self, context, chat_id, message_id, text, markup=None):
        """
        Helper to edit an existing message with plain text if the video is not found.
        """
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Error editing message text: {e}")



