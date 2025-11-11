from io import BytesIO
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
from BucketService import BucketService
from cancel import cancel_restarted_message
from telegram.ext import ContextTypes
from admin import handle_contact_admin
logger = logging.getLogger(__name__)

# Example conversation states (import or define them as needed)
USER_MENU = 5
USER_VIEW_VIDEOS = 11
USER_REQUEST = 12
CLASS_PASSWORD = 13
JOIN_CLASSROOM = 14

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
        user_buttons_info =  self.translation_manager.get_translation(context, 'user_info')
        show_my_rank_text = self.translation_manager.get_translation(context, 'show_my_rank')
        join_classroom_text = self.translation_manager.get_translation(context, 'join_classroom')

        if context.user_data.get('classroom_view', False):
            # User is viewing the classroom
            go_back_to_main_menu_text = self.translation_manager.get_translation(context, 'go_back_to_main_menu')
            remove_classroom_text = self.translation_manager.get_translation(context, 'remove_classroom')
            user_menu_text = self.translation_manager.get_translation(context, 'classroom_menu')
            reply_keyboard = [
                [request_video_text, view_videos_text, go_back_to_main_menu_text],
                [contact_admin_text],
                [user_buttons_info],
                [remove_classroom_text]
            ]
        else:
            # User is not viewing the classroom
            if context.user_data.get("classroom_id", None):
                # User is part of a classroom, so show "Open Classroom" button
                open_classroom_text = self.translation_manager.get_translation(context, 'open_classroom')
                show_my_rank_text = self.translation_manager.get_translation(context, 'show_my_rank')
                
                reply_keyboard = [
                    [request_video_text, view_videos_text, open_classroom_text],
                    [show_my_rank_text, contact_admin_text],
                    [user_buttons_info],
                    [cancel_text]
                ]
            else:
                # User is not part of any classroom
                reply_keyboard = [
                    [request_video_text, view_videos_text, join_classroom_text],
                    [show_my_rank_text,contact_admin_text],
                    [user_buttons_info],
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
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        show_my_rank_text = self.translation_manager.get_translation(context, 'show_my_rank')
        user_buttons_info =  self.translation_manager.get_translation(context, 'user_info')
        join_classroom_text = self.translation_manager.get_translation(context, 'join_classroom')
        open_classroom = self.translation_manager.get_translation(context, 'open_classroom')
        close_classroom = self.translation_manager.get_translation(context, 'go_back_to_main_menu')
        remove_classroom = self.translation_manager.get_translation(context, 'remove_classroom')
        
        if user_choice == request_video_text:
            context.user_data['skipped_videos']=set()
            return await self.handle_user_flow(update, context)
        elif user_choice == open_classroom:
            context.user_data['classroom_view'] = True  # Set classroom_view to True
            return await self.show_user_menu(update, context)
        elif user_choice == close_classroom:
            context.user_data['classroom_view'] = False  # Set classroom_view back to False
            return await self.show_user_menu(update, context)
        elif user_choice == join_classroom_text:
            join_classroom_prompt = self.translation_manager.get_translation(context, 'enter_classroom_id')
            reply_keyboard = [[cancel_text]]
            await update.message.reply_text(
                join_classroom_prompt, 
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return CLASS_PASSWORD
        elif user_choice == remove_classroom:
            success_message = self.translation_manager.get_translation(context, 'classroom_remove_success')
            failure_message = self.translation_manager.get_translation(context, 'classroom_remove_failure')
            user_id = self._get_user_id_from_context(context, update)
            if user_id:
                success = self.db_service.remove_user_from_classroom(user_id)
                if success:
                    context.user_data['classroom_id'] = None  # Set classroom_id to None
                    context.user_data['classroom_view'] = False  # Set classroom_view to None
                    await update.message.reply_text(success_message)
                else:
                    await update.message.reply_text(failure_message)
        
            return await self.show_user_menu(update, context)
        elif user_choice == go_back_text:
            return await self.show_user_menu(update, context)

        elif user_choice == view_videos_text:
            return await self.handle_view_user_videos(update, context)

        elif user_choice == contact_admin_text:
            return await handle_contact_admin(update, context, self.translation_manager)
        
        elif user_choice == show_my_rank_text:
            return await self.handle_show_user_rank(update, context)
        
        elif user_choice == user_buttons_info:
            return await self.handle_user_info(update, context)
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
        
    async def handle_class_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        user_input = update.message.text
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        if user_input == cancel_text:
        # If user pressed cancel, return to the user menu
            return await self.show_user_menu(update, context)
        # got classroom_ID from user_input then here prompts for the password
        context.user_data['temporary_classroom_id'] = user_input
        
        reply_keyboard = [[cancel_text]]  # Show only the Cancel button
        enter_password_prompt = self.translation_manager.get_translation(context, 'enter_classroom_password')
        # Send the password prompt with the updated keyboard
        await update.message.reply_text(
            enter_password_prompt,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )    
        return JOIN_CLASSROOM
    
    async def handle_join_classroom(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        user_input = update.message.text
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        if user_input == cancel_text:
        # If user pressed cancel, return to the user menu
            return await self.show_user_menu(update, context)
        # Retrieve the temporary classroom ID from the context
        classroom_id = context.user_data.get('temporary_classroom_id')
        password = user_input
        if not classroom_id:
            # If no classroom ID is found in the context, return an error message.
            await update.message.reply_text("Error: No classroom ID stored.")
            return USER_MENU
        
        # Validate the classroom ID and password in the database
        is_valid = self.db_service.validate_classroom_credentials(classroom_id, password)
        
        if is_valid:
            # If the credentials are valid, proceed to mark the user as joined
            context.user_data['classroom_id'] = classroom_id  # Store the valid classroom ID

            # Update the user's status in the database (set 'joined_classroom' to True)
            user_id = self._get_user_id_from_context(context, update)  # Get the user ID from the context or DB
            if user_id:
                self.db_service.update_user_classroom_status(user_id, classroom_id)

            # Success message
            success_message = self.translation_manager.get_translation(context, 'classroom_join_success')
            await update.message.reply_text(success_message)

            return await self.show_user_menu(update,context)  # Return to the user menu

        else:
            # If the credentials are invalid, return a failure message
            failure_message = self.translation_manager.get_translation(context, 'classroom_join_failure')
            await update.message.reply_text(failure_message)

            return await self.show_user_menu(update,context) # Return to the user menu after failure

        
    
        
    async def handle_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Show the detailed explanation of the buttons
        """
        request_video_text = self.translation_manager.get_translation(context, 'request_video')
        view_videos_text = self.translation_manager.get_translation(context, 'view_videos')
        contact_admin_text =  self.translation_manager.get_translation(context, 'contact_admin')
        show_my_rank_text = self.translation_manager.get_translation(context, 'show_my_rank')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        
        
        Buttons_explanation=f"""
        📌 {self.translation_manager.get_translation(context, 'user_menu_options')}

        🔹 {request_video_text} – {self.translation_manager.get_translation(context, 'request_video_explanation')}
        🔹 {view_videos_text} – {self.translation_manager.get_translation(context, 'view_videos_explanation')}
        🔹 {show_my_rank_text} – {self.translation_manager.get_translation(context, 'show_my_rank_explanation')}
        🔹 {contact_admin_text} – {self.translation_manager.get_translation(context, 'contact_admin_explanation')}
        """
        
        
        await update.message.reply_text(
            Buttons_explanation,
            reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=True)
        )
        return USER_MENU


    async def handle_user_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        The user requests a random translator video to respond to.
        We get a random translator video from DB, show it, and
        prompt the user to upload a response or skip.
        """
        user_language = context.user_data.get('language', 'English')
        skipped_videos = context.user_data.get('skipped_videos', set())

        logger.info(f"Handling user flow for language: {user_language}, skipped: {skipped_videos}")
        classroom_id = context.user_data.get('classroom_id') if context.user_data.get('classroom_view') else None
        # Fetch a random translator video, excluding the user's own videos or skipped ones
        file_path, sentence = self.db_service.get_random_translator_video(user_language, context, exclude_ids=skipped_videos, classroom_id=classroom_id)
        if file_path:
            try:
                bucketUrl = BucketService.view_bucket_video(file_path_url=file_path) 
                await update.message.reply_video(
                    video=bucketUrl
                )
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
                return await self.show_user_menu(update,context)  # or ConversationHandler.END

            # We need to store the user's response referencing the translator video
            translator_video_id = context.user_data.get('current_translator_video_id')
            translator_text_id = self.db_service.get_video_text_id(translator_video_id)

            # Generate a file path and save video
            file_path = self._get_next_available_filename(update, context, role="user")
            # Download video to memory
            file = await context.bot.get_file(user_video.file_id)
            file_stream = BytesIO()
            await file.download_to_memory(out=file_stream)
            file_stream.seek(0)

            # Upload to S3 using exact path
            BucketService.addToBucket(file_stream, file_path)
            
            # Insert DB row referencing the translator video
            user_language = context.user_data.get('language', 'English')
            classroom_id = context.user_data.get('classroom_id')
            if context.user_data.get('classroom_view') and classroom_id:
                self.db_service.save_video_info(
                    user_id=user_id,
                    file_path=file_path,
                    language=user_language,
                    sentence=None,
                    reference_id=translator_video_id,
                    sentence_id=translator_text_id,
                    classroom_id=classroom_id  # Store the classroom_id for classroom-related videos
                )
            else:
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
            file_path2, sentence = self.db_service.get_random_translator_video(user_language, context, classroom_id=classroom_id)
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
        Show the user's current video + translator video side by side with:
        - Delete button
        - Next/Previous navigation
        - (Optional) View/Hide Feedback button
        Also display upvote/downvote counts for the user's video.
        """
        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)
        
        # --------------------------------------------------------------------------------
        # 1) If the user has no videos
        # --------------------------------------------------------------------------------
        if not user_videos:
            # Was hardcoded: "You have no uploaded videos."
            # Now from JSON:
            no_uploaded_videos_text = self.translation_manager.get_translation(context, 'no_uploaded_videos')
            
            message = update.message if update.message else update.callback_query.message
            if message:
                await message.reply_text(no_uploaded_videos_text)
            return  # Possibly return to some menu
        
        # Ensure current_index is within valid range
        if current_index >= len(user_videos):
            current_index = len(user_videos) - 1
            context.user_data['current_index'] = current_index
        elif current_index < 0:
            current_index = 0
            context.user_data['current_index'] = current_index

        # Extract data from the current pair
        video_pair = user_videos[current_index]
        user_video_id = video_pair['user_video_id']
        user_video_path = video_pair['user_video_path']
        translator_video_path = video_pair['translator_video_path']

        # Upvotes/Downvotes
        user_upvotes = video_pair.get('user_upvotes', 0)
        user_downvotes = video_pair.get('user_downvotes', 0)

        # --------------------------------------------------------------------------------
        # 2) Build Captions
        # --------------------------------------------------------------------------------
        # Hardcoded: "Translator's Video" / "Your Video"
        # Now from JSON:
        translator_caption = self.translation_manager.get_translation(context, 'translator_video')
        user_video_caption = self.translation_manager.get_translation(context, 'your_video')
        
        # Hardcoded: "Upvotes: {} | Downvotes: {}"
        # We have a key like "vote_count_format": "Upvotes: {} | Downvotes: {}"
        vote_count_format = self.translation_manager.get_translation(context, 'vote_count_format')
        user_video_caption += "\n" + vote_count_format.format(user_upvotes, user_downvotes)

        # --------------------------------------------------------------------------------
        # 3) Build Inline Keyboard
        # --------------------------------------------------------------------------------
        # Hardcoded: "Delete"
        # Now from JSON:
        delete_text = self.translation_manager.get_translation(context, 'delete')
        delete_callback_data = f"delete_user_video_{user_video_id}"
        delete_button = InlineKeyboardButton(delete_text, callback_data=delete_callback_data)

        # feedback_exists = self.db_service.check_if_feedback_exists(user_video_id)
        feedback_exists = True
        feedback_shown_map = context.user_data.get("feedback_shown", {})
        feedback_shown = feedback_shown_map.get(user_video_id, False)

        # Hardcoded: "View Feedback" / "Hide Feedback"
        # Add keys in JSON if missing: "view_feedback" and "hide_feedback"
        row1 = [delete_button]
        if feedback_exists:
            feedback_text = (self.translation_manager.get_translation(context, 'hide_feedback')
                            if feedback_shown
                            else self.translation_manager.get_translation(context, 'view_feedback'))
            feedback_callback_data = f"toggle_feedback_{user_video_id}"
            feedback_button = InlineKeyboardButton(feedback_text, callback_data=feedback_callback_data)
            row1.append(feedback_button)

        # Hardcoded: "Previous" / "Next"
        # We have "previous_page" and "next_page" in JSON
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    self.translation_manager.get_translation(context, 'previous_page'),
                    callback_data="previous_user_video"
                )
            )
        if current_index < len(user_videos) - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    self.translation_manager.get_translation(context, 'next_page'),
                    callback_data="next_user_video"
                )
            )

        keyboard_rows = [row1]
        if nav_buttons:
            keyboard_rows.append(nav_buttons)

        markup = InlineKeyboardMarkup(keyboard_rows)

        message = update.message if update.message else update.callback_query.message
        if not message:
            return
        chat_id = message.chat_id

        message_ids = context.user_data.get('message_ids', {})

        # --------------------------------------------------------------------------------
        # 4) Show/Update Translator Video
        # --------------------------------------------------------------------------------
        # Hardcoded: "Translator video not available."
        translator_not_found = self.translation_manager.get_translation(context, 'translator_video_not_available')
        
        if 'translator' in message_ids:
            existing_msg_id = message_ids['translator']
            if translator_video_path:
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
            if translator_video_path:
                signed_url = BucketService.view_bucket_video(translator_video_path)
                if signed_url:
                    msg = await message.reply_video(
                        video=signed_url,
                        caption=translator_caption
                    )
                #else error cixart logger.error
                message_ids['translator'] = msg.message_id
            else:
                msg = await message.reply_text(translator_not_found)
                message_ids['translator'] = msg.message_id

        # --------------------------------------------------------------------------------
        # 5) Show/Update User Video
        # --------------------------------------------------------------------------------
        # Hardcoded: "Your video not available."
        user_video_not_found = self.translation_manager.get_translation(context, 'your_video_not_available')
        
        if 'user' in message_ids:
            existing_msg_id = message_ids['user']
            if user_video_path:
                await self._edit_video_message(
                    context, chat_id, existing_msg_id,
                    user_video_path, user_video_caption, markup
                )
            else:
                await self._edit_text_message(
                    context, chat_id, existing_msg_id,
                    user_video_not_found, markup
                )
        else:
            if user_video_path:
                signed_url = BucketService.view_bucket_video(user_video_path)
                msg = await message.reply_video(
                    video=signed_url,
                    caption=user_video_caption,
                    reply_markup=markup
                )
                message_ids['user'] = msg.message_id
            else:
                msg = await message.reply_text(
                    user_video_not_found,
                    reply_markup=markup
                )
                message_ids['user'] = msg.message_id

        context.user_data['message_ids'] = message_ids
        
    

    async def handle_next_user_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)  # If needed to reset fallback

        query = update.callback_query
        await query.answer()

        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)

        # 1) Hide feedback from current video (if any)
        if 0 <= current_index < len(user_videos):
            current_video_id = user_videos[current_index]['user_video_id']
            await self.hide_feedback_for_video(context, current_video_id, query.message.chat_id)

        # 2) Now move to the next video
        context.user_data['current_index'] = current_index + 1

        # 3) Redisplay
        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS


    async def handle_previous_user_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)

        query = update.callback_query
        await query.answer()

        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)

        # Hide old feedback
        if 0 <= current_index < len(user_videos):
            current_video_id = user_videos[current_index]['user_video_id']
            await self.hide_feedback_for_video(context, current_video_id, query.message.chat_id)

        context.user_data['current_index'] = current_index - 1

        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS


    async def handle_delete_user_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)  # If you use this pattern to reset fallback.
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

        # 1) HIDE FEEDBACK (if any) BEFORE DELETING
        await self.hide_feedback_for_video(context, user_video_id, query.message.chat_id)

        # 2) Delete from DB
        self.db_service.delete_user_video(user_video_id, user_id)
        # 3)bucket elave ele

        # 4) Remove from context's user_videos
        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)

        for i, video_pair in enumerate(user_videos):
            if video_pair['user_video_id'] == user_video_id:
                user_videos.pop(i)
                # adjust the current_index if needed
                if current_index >= len(user_videos):
                    current_index = len(user_videos) - 1
                context.user_data['current_index'] = current_index
                break

        context.user_data['user_videos'] = user_videos

        # 4) Delete old messages (the user & translator videos) from chat
        chat_id = update.effective_chat.id
        message_ids = context.user_data.get('message_ids', {})
        for mid in message_ids.values():
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception as e:
                logger.error(f"Error deleting message {mid}: {e}")
        context.user_data.pop('message_ids', None)

        # 5) If no videos left, show user a "no more videos" message
        if not user_videos:
            no_videos_text = self.translation_manager.get_translation(context, 'your_video_not_available')
            start_text = self.translation_manager.get_translation(context, 'start_button')
            await query.message.reply_text(
                no_videos_text,
                reply_markup=ReplyKeyboardMarkup([[start_text]], one_time_keyboard=True)
            )
            return await self.show_user_menu(update, context)
        
        # 6) Else, show updated group
        await self.display_current_user_video_group(update, context)
        return USER_VIEW_VIDEOS



    # --------------------------------------------------------------------------
    # SHOW USER RANK
    # --------------------------------------------------------------------------

    async def handle_show_user_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Displays the leaderboard with the user's rank, their points, and (if they are a Translator) the top 5 Translators.
        """

        user_id = context.user_data.get("user_id")  # Get user_id from context

        user_role = context.user_data.get("role")  # Get user role from context


        if not user_id:
            await update.message.reply_text("⚠️ Error")
            return await self.show_translator_menu(update, context)

        user_rank_data, _ = self.db_service.get_user_rank(user_id, user_role)       

        user_points, rank = user_rank_data  # Extract only points & rank

        # Get translated texts from JSON
        user_rank_text = self.translation_manager.get_translation(context, 'user_rank')  # 🏆 Sənin Reytinqin:
        user_points_text = self.translation_manager.get_translation(context, 'user_points')  # 📊 Sənin Xalın:

        leaderboard_text = f"{user_rank_text} {rank}\n"
        leaderboard_text += f"{user_points_text} {user_points}\n"
        # Back button
        go_back_text = self.translation_manager.get_translation(context, 'go_back')

        await update.message.reply_text(
            leaderboard_text,
            reply_markup=ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True, one_time_keyboard=True)
        )

        return USER_MENU

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
            directory = "https://vesilebucket.s3.amazonaws.com/sign-language-videos/User/"
            prefix = "user_video"

            # Ensure the directory exists

       
        #check user videos from database, return the file_path of the last video and cahnge the last num of file path and +1
        #exaple: https://vesilebucket.s3.amazonaws.com/sign-language-videos/Translator/translator_video_2_unknown_2.mp4
        #if the last number is 2 add one 
        #updated file path is: 
        #https://vesilebucket.s3.amazonaws.com/sign-language-videos/Translator/translator_video_2_unknown_3.mp4
        #if not found make the num 1
        
        last_path = self.db_service.get_last_video_file_path(user_id)
        number = 1
        
        if last_path:
            last_filename = last_path.split("/")[-1]
            match = re.search(rf"{prefix}_\d+_[^_]+_(\d+)", last_filename)
            if match:
                number = int(match.group(1)) + 1

        new_filename = f"{prefix}_{user_id}_{username}_{number}.mp4"
        return directory + new_filename



    async def _edit_video_message(self, context, chat_id, message_id, video_path, caption, markup=None):
        """
        Helper to edit an existing message with a new video (InputMediaVideo).
        """
        signed_url = BucketService.view_bucket_video(video_path)
        if not signed_url:
            logger.error("Either file_Path or Bucket_service went down")
            return
        
        media = InputMediaVideo(media=signed_url, caption=caption)
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

    async def handle_toggle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cancel_restarted_message(context)
        query = update.callback_query
        await query.answer()  # acknowledge to remove loading spinner

        data = query.data  # e.g. "toggle_feedback_123"
        match = re.match(r"toggle_feedback_(\d+)", data)
        if not match:
            logger.error(f"Invalid callback data: {data}")
            return

        video_id = int(match.group(1))

        # Retrieve or init the dictionary that tracks which videos' feedback is shown
        feedback_shown_map = context.user_data.get("feedback_shown", {})
        currently_shown = feedback_shown_map.get(video_id, False)

        # If feedback was not being shown, we need to show it
        if not currently_shown:
            feedback_list = self.db_service.get_feedback_for_video(video_id)
            if not feedback_list:
                await query.message.reply_text("No feedback for this video yet.")
                return

            # Build feedback text
            feedback_text = "\n".join([f"• {feedback}" for feedback in feedback_list])
            feedback_msg = await query.message.reply_text(f"Feedback:\n{feedback_text}")

            # Mark it as shown
            feedback_shown_map[video_id] = True
            context.user_data["feedback_shown"] = feedback_shown_map

            # Store the feedback message ID so we can delete it later
            if "feedback_message_ids" not in context.user_data:
                context.user_data["feedback_message_ids"] = {}
            context.user_data["feedback_message_ids"][video_id] = feedback_msg.message_id

        # If feedback was being shown, hide (delete) the feedback message
        else:
            feedback_message_ids = context.user_data.get("feedback_message_ids", {})
            feedback_msg_id = feedback_message_ids.get(video_id)
            if feedback_msg_id:
                try:
                    await context.bot.delete_message(
                        chat_id=query.message.chat.id,
                        message_id=feedback_msg_id
                    )
                except Exception as e:
                    logger.error(f"Error deleting feedback message: {e}")

            feedback_shown_map[video_id] = False
            context.user_data["feedback_shown"] = feedback_shown_map

        # After toggling, we need to update the inline keyboard
        await self._update_user_video_keyboard(update, context, video_id)
            
    async def hide_feedback_for_video(self, context, video_id: int, chat_id: int):
        """
        Hides (deletes) the feedback message for a given video_id if it's currently visible,
        and updates context to mark feedback as hidden.
        """
        feedback_shown_map = context.user_data.get("feedback_shown", {})
        currently_shown = feedback_shown_map.get(video_id, False)

        if currently_shown:
            # If feedback was visible, find its message ID and delete it
            feedback_message_ids = context.user_data.get("feedback_message_ids", {})
            msg_id = feedback_message_ids.get(video_id)
            if msg_id:
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=msg_id
                    )
                except Exception as e:
                    logger.error(f"Error deleting feedback message: {e}")

                # Remove from the dictionary so we don't double-delete
                feedback_message_ids.pop(video_id, None)
                context.user_data["feedback_message_ids"] = feedback_message_ids

            # Mark it as hidden
            feedback_shown_map[video_id] = False
            context.user_data["feedback_shown"] = feedback_shown_map

    async def _update_user_video_keyboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: int):
        # Get the current index from context, etc.
        user_videos = context.user_data.get('user_videos', [])
        current_index = context.user_data.get('current_index', 0)
        if current_index >= len(user_videos):
            return

        # Build the new keyboard based on updated feedback_shown state
        feedback_exists = self.db_service.check_if_feedback_exists(video_id)
        feedback_shown_map = context.user_data.get("feedback_shown", {})
        feedback_shown = feedback_shown_map.get(video_id, False)

        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("Previous", callback_data="previous_user_video"))
        if current_index < len(user_videos) - 1:
            nav_buttons.append(InlineKeyboardButton("Next", callback_data="next_user_video"))

        delete_callback_data = f"delete_user_video_{video_id}"
        delete_button = InlineKeyboardButton("Delete", callback_data=delete_callback_data)
        
        row1 = [delete_button]
        if feedback_exists:
            feedback_text = "Hide Feedback" if feedback_shown else "View Feedback"
            row1.append(InlineKeyboardButton(feedback_text, callback_data=f"toggle_feedback_{video_id}"))

        keyboard_rows = [row1]
        if nav_buttons:
            keyboard_rows.append(nav_buttons)

        markup = InlineKeyboardMarkup(keyboard_rows)

        # Now edit the existing user video message to update only the keyboard
        message_ids = context.user_data.get('message_ids', {})
        user_msg_id = message_ids.get('user')  # "user" is how you track the user's video message ID
        if not user_msg_id:
            return

        chat_id = update.effective_chat.id
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=user_msg_id,
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Error updating user video keyboard: {e}")
