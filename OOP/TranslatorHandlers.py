import logging
import os
import re
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

logger = logging.getLogger(__name__)

# Example conversation states (define or import them as needed):
TRANSLATOR_MENU = 4
WRITE_SENTENCE = 21
TRANSLATOR_UPLOAD = 22
EDIT_SENTENCES = 23
VOTING = 24

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
          - Cancel
        """
        menu_text = self.translation_manager.get_translation(context, 'menu')
        view_sentences_text = self.translation_manager.get_translation(context, 'view_sentences')
        write_sentence_text = self.translation_manager.get_translation(context, 'write_sentence')
        edit_sentences_text = self.translation_manager.get_translation(context, 'edit_sentences')
        vote_text = self.translation_manager.get_translation(context, 'vote')
        generate_otp_text = self.translation_manager.get_translation(context, 'generate_otp')
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')

        reply_keyboard = [
            [view_sentences_text, write_sentence_text],
            [edit_sentences_text, vote_text],
            [generate_otp_text],
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
          - Generate OTP -> handle_view_otp
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
        invalid_option_text = self.translation_manager.get_translation(context, 'invalid_option')

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

        elif user_choice == vote_text:
            return await self.start_voting(update, context)

        elif user_choice == generate_otp_text:
            return await self.handle_view_otp(update, context)

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
        new_sentence = update.message.text
        cancel_text = self.translation_manager.get_translation(context, 'cancel_button')
        sentence_exists_text = self.translation_manager.get_translation(context, 'sentence_exists')
        video_prompt_text = self.translation_manager.get_translation(context, 'video_prompt')


        if new_sentence == cancel_text:
            return await self.show_translator_menu(update,context)  # or translator menu, etc.

        # Check if sentence already exists
        if self.db_service.check_sentence_exists(new_sentence):
            await update.message.reply_text(sentence_exists_text)
            return TRANSLATOR_MENU
        else:
            # Store sentence in user_data, prompt for video
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
            self.db_service.save_video_info(user_id, file_path, user_language, sentence)

            await update.message.reply_text(thank_you_video_text)
            return await self.show_translator_menu(update, context)

        elif user_input == cancel_text:
            return await self.show_translator_menu(update, context)
        else:
            # Not a valid video message
            await update.message.reply_text(valid_video_error_text)
            return TRANSLATOR_UPLOAD

    async def handle_edit_sentences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Fetch translator's own sentences, store in context, display them in a paged list.
        """
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await update.message.reply_text(bot_restarted_text)
            return -1

        language = context.user_data.get('language', 'English')
        technical_difficulty_text = self.translation_manager.get_translation(context, 'technical_difficulty')
        no_sentences_found_text = self.translation_manager.get_translation(context, 'no_sentences_found')

        # Retrieve the translator's sentences + associated videos
        connection = self.db_service.connect_to_db()
        if not connection:
            await update.message.reply_text(technical_difficulty_text)
            return TRANSLATOR_MENU

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT s.sentence_id, s.sentence_content, v.file_path,
                       COALESCE(v.positive_scores, 0) as upvotes,
                       COALESCE(v.negative_scores, 0) as downvotes
                FROM sentences s
                LEFT JOIN videos v ON s.sentence_id = v.text_id
                WHERE s.user_id = %s
                  AND s.sentence_language = %s
                ORDER BY s.sentence_id DESC
                """,
                (user_id, language)
            )
            results = cursor.fetchall()
            cursor.close()
            connection.close()

            if not results:
                await update.message.reply_text(no_sentences_found_text)
                return TRANSLATOR_MENU

            # Store in context
            context.user_data['sentences'] = []
            for row in results:
                context.user_data['sentences'].append({
                    'id': row[0],
                    'sentence': row[1],
                    'video_path': row[2],
                    'upvotes': row[3],
                    'downvotes': row[4]
                })

            context.user_data['current_page'] = 1
            context.user_data['items_per_page'] = 5

            await self.display_edit_sentences_page(update, context)
            return EDIT_SENTENCES

        except Exception as e:
            logger.error(f"Error in handle_edit_sentences: {e}")
            await update.message.reply_text(technical_difficulty_text)
            return TRANSLATOR_MENU
        

    async def display_sentences_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Displays sentences with pagination.
        """
        cancel_restarted_message(context)

        # Get the current page from context, default to 1
        page = context.user_data.get('current_page', 1)
        language = context.user_data.get('language', 'English')

        sentences = self.db_service.get_all_sentences(language)  # Fetch sentences
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
        reply_keyboard = ReplyKeyboardMarkup(
            [[go_back_text]], resize_keyboard=True, one_time_keyboard=True
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



    async def display_edit_sentences_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Show a page of translator's own sentences with up/down votes, plus
        pagination and item detail buttons.
        """
        sentences = context.user_data.get('sentences', [])
        current_page = context.user_data.get('current_page', 1)
        items_per_page = context.user_data.get('items_per_page', 5)

        total_items = len(sentences)
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_items = sentences[start_idx:end_idx]
        total_pages = (total_items + items_per_page - 1) // items_per_page

        total_sentences_text = self.translation_manager.get_translation(context, 'total_sentences')
        vote_count_format_text = self.translation_manager.get_translation(context, 'vote_count_format')
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        edit_menu_prompt_text = self.translation_manager.get_translation(context, 'edit_menu_prompt')

        message_lines = [total_sentences_text.format(total_items)]
        idx_number = start_idx + 1
        for item in current_items:
            line = f"{idx_number}. {item['sentence']}\n" + vote_count_format_text.format(item['upvotes'], item['downvotes'])
            message_lines.append(line)
            idx_number += 1
        message_text = "\n".join(message_lines)

        # Build buttons
        button_rows = []
        # 1) item selection
        item_buttons = []
        for i in range(start_idx + 1, start_idx + len(current_items) + 1):
            callback_data = f"view_item_{i-1}"
            item_buttons.append(InlineKeyboardButton(str(i), callback_data=callback_data))
        if item_buttons:
            button_rows.append(item_buttons)

        # 2) pagination
        previous_page_text = self.translation_manager.get_translation(context, 'previous_page')
        next_page_text = self.translation_manager.get_translation(context, 'next_page')

        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton(previous_page_text, callback_data="prev_page"))
        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton(next_page_text, callback_data="next_page"))
        if nav_buttons:
            button_rows.append(nav_buttons)

        keyboard = InlineKeyboardMarkup(button_rows)

        if update.callback_query:
            # Just edit existing message
            try:
                await update.callback_query.message.edit_text(message_text, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error updating message: {e}")
                await update.callback_query.message.reply_text(message_text, reply_markup=keyboard)
        else:
            # First time display: also show a "Go back" button in normal keyboard
            reply_keyboard = ReplyKeyboardMarkup([[go_back_text]], resize_keyboard=True)
            await update.message.reply_text(message_text, reply_markup=keyboard)
            await update.message.reply_text(edit_menu_prompt_text, reply_markup=reply_keyboard)

    async def handle_page_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        cancel_restarted_message(context)
        """
        Handle 'prev_page' or 'next_page' callbacks in the edit sentences list.
        """
        query = update.callback_query
        await query.answer()

        current_page = context.user_data.get('current_page', 1)
        items_per_page = context.user_data.get('items_per_page', 5)
        sentences = context.user_data.get('sentences', [])
        total_items = len(sentences)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        if query.data == "prev_page":
            context.user_data['current_page'] = max(1, current_page - 1)
        elif query.data == "next_page":
            context.user_data['current_page'] = min(total_pages, current_page + 1)

        await self.display_edit_sentences_page(update, context)
        return EDIT_SENTENCES

    async def show_sentence_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Show details for a selected sentence: its text, video (if available),
        up/down votes, plus Delete and Back buttons.
        """
        query = update.callback_query
        await query.answer()

        match = re.match(r"view_item_(\d+)", query.data)
        if not match:
            return EDIT_SENTENCES

        item_idx = int(match.group(1))
        sentences = context.user_data.get('sentences', [])
        if item_idx >= len(sentences):
            item_not_found_text = self.translation_manager.get_translation(context, 'item_not_found')
            await query.message.reply_text(item_not_found_text)
            return EDIT_SENTENCES

        item = sentences[item_idx]

        delete_button_text = self.translation_manager.get_translation(context, 'delete_button')
        back_button_text = self.translation_manager.get_translation(context, 'back_button')

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(delete_button_text, callback_data=f"delete_{item['id']}"),
                InlineKeyboardButton(back_button_text, callback_data="back_to_list")
            ]
        ])

        await query.message.delete()

        if item['video_path'] and os.path.exists(item['video_path']):
            with open(item['video_path'], 'rb') as f:
                caption = f"{item['sentence']}\nUp votes: {item['upvotes']} Down votes: {item['downvotes']}"
                sent_message = await query.message.reply_video(f, caption=caption, reply_markup=keyboard)
                context.user_data['detail_message_id'] = sent_message.message_id
        else:
            video_not_found_text = self.translation_manager.get_translation(context, 'video_not_found')
            caption = f"{item['sentence']}\nUp votes: {item['upvotes']} Down votes: {item['downvotes']}"
            await query.message.reply_text(f"{caption}\n\n{video_not_found_text}", reply_markup=keyboard)

        return EDIT_SENTENCES

    async def edit_sentences_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        If the user typed text (like 'Go back') while in EDIT_SENTENCES flow.
        """
        user_input = update.message.text
        go_back_text = self.translation_manager.get_translation(context, 'go_back')
        edit_menu_prompt_text = self.translation_manager.get_translation(context, 'edit_menu_prompt')

        if user_input == go_back_text:
            # Return to translator menu
            return await self.show_translator_menu(update, context)
        else:
            await update.message.reply_text(edit_menu_prompt_text)
            return EDIT_SENTENCES

    async def handle_delete_sentence(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Callback for deleting a sentence (and its associated video).
        """
        query = update.callback_query
        await query.answer()

        data = query.data
        match = re.match(r"delete_(\d+)", data)
        if not match:
            logger.error(f"Invalid callback data: {data}")
            return EDIT_SENTENCES

        sentence_id = int(match.group(1))
        user_id = self._get_user_id_from_context(context, update)
        if not user_id:
            bot_restarted_text = self.translation_manager.get_translation(context, 'bot_restarted')
            await query.message.reply_text(bot_restarted_text)
            return -1

        self.db_service.delete_sentence_and_video(sentence_id, user_id)

        # Refresh the list
        language = context.user_data.get('language', 'English')
        no_sentences_found_text = self.translation_manager.get_translation(context, 'no_sentences_found')
        technical_difficulty_text = self.translation_manager.get_translation(context, 'technical_difficulty')

        connection = self.db_service.connect_to_db()
        if not connection:
            await query.message.reply_text(technical_difficulty_text)
            return TRANSLATOR_MENU

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT s.sentence_id, s.sentence_content, v.file_path,
                       COALESCE(v.positive_scores, 0) as upvotes,
                       COALESCE(v.negative_scores, 0) as downvotes
                FROM sentences s
                LEFT JOIN videos v ON s.sentence_id = v.text_id
                WHERE s.user_id = %s
                  AND s.sentence_language = %s
                ORDER BY s.sentence_id DESC
                """,
                (user_id, language)
            )
            results = cursor.fetchall()
            cursor.close()
            connection.close()

            # Delete old detail message
            try:
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

            if not results:
                await query.message.reply_text(no_sentences_found_text)
                return EDIT_SENTENCES

            context.user_data['sentences'] = []
            for row in results:
                context.user_data['sentences'].append({
                    'id': row[0],
                    'sentence': row[1],
                    'video_path': row[2],
                    'upvotes': row[3],
                    'downvotes': row[4]
                })

            # Re-adjust pagination if needed
            items_per_page = context.user_data.get('items_per_page', 5)
            total = len(context.user_data['sentences'])
            pages = (total + items_per_page - 1) // items_per_page
            current_page = context.user_data.get('current_page', 1)
            if current_page > pages and pages > 0:
                context.user_data['current_page'] = pages

            await self.display_edit_sentences_page(update, context)
            return EDIT_SENTENCES

        except Exception as e:
            logger.error(f"Error updating view after deletion: {e}")
            await query.message.reply_text(technical_difficulty_text)
            return TRANSLATOR_MENU

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
                return self.show_translator_menu(update, context)

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
        cancel_restarted_message(context)
        """
        Callback version for 'vote_down'.
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
            return await self.show_translator_menu(update, context)

        self.db_service.increment_video_score(video_id, 'negative_scores')
        self.db_service.record_vote(user_id, video_id, 'down')

        await query.message.delete()

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
