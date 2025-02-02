import psycopg2
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, config_path='./config.txt'):
            """
            Initialize the DatabaseService by reading database credentials
            from a config file. The file is expected to have lines of the form:
            
                db_name=your_database
                db_user=your_username
                db_password=your_password
                db_host=your_host
                db_port=your_port
            
            :param config_path: Path to the config file containing DB credentials.
            """
            creds = self._read_config_file(config_path)
            self.dbname = creds.get('db_name')
            self.user = creds.get('db_user')
            self.password = creds.get('db_password')
            self.host = creds.get('db_host')
            self.port = creds.get('db_port')
    
    def _read_config_file(self, config_path):
        """
        Private helper method that reads the config file and returns a dictionary
        of key-value pairs. Adjust parsing logic if your config file format differs.
        """
        config_data = {}
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            return config_data
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        # Skip empty lines or commented lines
                        continue
                    key, sep, value = line.partition('=')
                    if sep == '=':
                        config_data[key.strip()] = value.strip()
            logger.info(f"Config file loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error reading config file {config_path}: {e}")
        
        return config_data

    def connect_to_db(self):
        """
        Establishes and returns a connection to the PostgreSQL database
        using credentials loaded from the config file.
        """
        try:
            connection = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            logger.info("Connected to the PostgreSQL database successfully.")
            return connection
        except Exception as error:
            logger.error(f"Error connecting to the database: {error}")
            return None

    def check_user_exists(self, telegram_id):
        """
        Checks if a user exists in the database by telegram_id or username 
        and returns the user's id, username, language, and role if they exist.
        """
        connection = self.connect_to_db()
        if not connection:
            return None, None, None, None
        
        try:
            cursor = connection.cursor()
            # Attempt to find user by telegram_id
            if telegram_id:
                cursor.execute(
                    "SELECT user_id, username, country, user_role "
                    "FROM public.users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                result = cursor.fetchone()
                if result:
                    cursor.close()
                    connection.close()
                    return result[0], result[1], result[2], result[3]
            cursor.close()
            connection.close()
            return None, None, None, None
        except Exception as error:
            logger.error(f"Error checking user in the database: {error}")
            return None, None, None, None

    def add_new_user(self, username, language, role, telegram_id):
        """
        Inserts a new user into the database after getting consent,
        with role preference.
        """
        connection = self.connect_to_db()
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO public.users (username, country, consent_status, user_role, telegram_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
                """,
                (username, language, True, role, telegram_id)
            )
            db_user_id = cursor.fetchone()[0]
            connection.commit()
            cursor.close()
            connection.close()
            logger.info(
                f"New user {username} added to the database with role {role} "
                f"and telegram_id {telegram_id}."
            )
            return db_user_id
        except psycopg2.IntegrityError as error:
            connection.rollback()
            cursor.close()
            connection.close()
            logger.error(f"IntegrityError: {error}")
            return None
        except Exception as error:
            connection.rollback()
            cursor.close()
            connection.close()
            logger.error(f"Error adding new user to the database: {error}")
            return None

    def get_user_language(self, user_id):
        """
        Retrieves user's language (country) from the database.
        """
        connection = self.connect_to_db()
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT country FROM public.users WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            if result:
                return result[0]
            return None
        except Exception as error:
            logger.error(f"Error getting user language from database: {error}")
            return None

    def save_video_info(self, user_id, file_path, language,
                        sentence=None, reference_id=None, sentence_id=None):
        """
        Saves video information and associated sentence to the database.
        If 'sentence' is provided and 'sentence_id' is not provided, it also
        inserts the new sentence into the 'sentences' table.
        """
        connection = self.connect_to_db()
        if not connection:
            return
        
        # Normalize file path (replace backslashes on Windows, etc.)
        full_file_path = os.path.abspath(file_path).replace('\\', '/')
        
        try:
            if sentence and not sentence_id:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO public.sentences (sentence_language, sentence_content, user_id)
                    VALUES (%s, %s, %s)
                    RETURNING sentence_id
                    """,
                    (language, sentence, user_id)
                )
                sentence_id = cursor.fetchone()[0]
                connection.commit()
                cursor.close()
            
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO public.videos
                (user_id, file_path, text_id, language, video_reference_id, uploaded_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (user_id, full_file_path, sentence_id, language, reference_id)
            )
            connection.commit()
            cursor.close()
            connection.close()
            logger.info(f"Video and (optional) sentence information saved for user {user_id}")
        except Exception as error:
            logger.error(f"Error saving video information to database: {error}")

    def get_random_translator_video(self, user_language, context=None, exclude_ids=None):
        """
        Fetch a random translator video (video_reference_id IS NULL) for the
        given user_language. Optionally exclude a list of video IDs (exclude_ids),
        and exclude videos already responded to or uploaded by the same user.
        """
        connection = self.connect_to_db()
        if not connection:
            logger.error("Failed to connect to database")
            return None, None
        
        try:
            cursor = connection.cursor()
            user_id = context.user_data.get('user_id') if context else None
            
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
            
            cursor.execute(query, params)
            all_results = cursor.fetchall()
            
            import random
            if all_results:
                chosen_result = random.choice(all_results)
                video_id, file_path, sentence = chosen_result
                if context:
                    context.user_data['current_translator_video_id'] = video_id
                cursor.close()
                connection.close()
                return file_path, sentence
            else:
                cursor.close()
                connection.close()
                return None, None
        except Exception as error:
            logger.error(f"Error fetching translator video: {error}")
            if connection:
                connection.close()
            return None, None

    def get_video_text_id(self, video_id):
        """
        Retrieve the text_id associated with a video.
        """
        connection = self.connect_to_db()
        if not connection:
            return None
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT text_id FROM public.videos WHERE video_id = %s",
                (video_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            if result:
                return result[0]
            return None
        except Exception as error:
            logger.error(f"Error retrieving text_id for video_id {video_id}: {error}")
            return None

    def check_sentence_exists(self, sentence):
        """
        Check if a sentence already exists in the database
        (case-insensitive match).
        """
        connection = self.connect_to_db()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM public.sentences
                WHERE LOWER(sentence_content) = LOWER(%s)
                """,
                (sentence,)
            )
            count = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return count > 0
        except Exception as error:
            logger.error(f"Error checking sentence existence: {error}")
            return False

    def get_all_sentences(self, language):
        """
        Retrieve all sentences for a specific language from the database,
        ordered by descending sentence_id.
        """
        connection = self.connect_to_db()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT sentence_content
                FROM public.sentences
                WHERE sentence_language = %s
                ORDER BY sentence_id DESC
                """,
                (language,)
            )
            results = [row[0] for row in cursor.fetchall()]
            cursor.close()
            connection.close()
            return results
        except Exception as error:
            logger.error(f"Error retrieving sentences: {error}")
            return []

    def get_sentences_and_videos(self, user_id, language):
        """
        Fetch sentences and associated translator videos for a given user_id
        and language. Returns list of tuples: (sentence_id, sentence_content, file_path).
        """
        if not user_id:
            return []
        connection = self.connect_to_db()
        if not connection:
            return []
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT s.sentence_id, s.sentence_content, v.file_path
                FROM public.sentences s
                LEFT JOIN public.videos v ON s.sentence_id = v.text_id
                                       AND v.video_reference_id IS NULL
                WHERE s.user_id = %s
                  AND s.sentence_language = %s
                ORDER BY s.sentence_id DESC
                """,
                (user_id, language)
            )
            results = cursor.fetchall()
            cursor.close()
            connection.close()
            return results
        except Exception as error:
            logger.error(f"Error fetching sentences and videos: {error}")
            return []

    def delete_sentence_and_video(self, sentence_id, user_id):
        """
        Delete a sentence and its associated video from the database
        (and file system), provided the sentence is owned by user_id.
        """
        if not user_id:
            return
        connection = self.connect_to_db()
        if not connection:
            return
        try:
            cursor = connection.cursor()
            # Get the video file path before any deletion
            cursor.execute(
                """
                SELECT v.file_path
                FROM public.videos v
                WHERE v.text_id = %s
                  AND v.user_id = %s
                """,
                (sentence_id, user_id)
            )
            result = cursor.fetchone()
            video_file_path = result[0] if result else None

            # Delete the sentence (if using CASCADE, the video record is also deleted)
            cursor.execute(
                """
                DELETE FROM public.sentences
                WHERE sentence_id = %s
                  AND user_id = %s
                """,
                (sentence_id, user_id)
            )
            connection.commit()

            # Delete the video file from the file system
            if video_file_path and os.path.exists(video_file_path):
                os.remove(video_file_path)
                logger.info(f"Deleted video file {video_file_path}")

            cursor.close()
            connection.close()
            logger.info(f"Deleted sentence {sentence_id} and associated video for user {user_id}")
        except Exception as error:
            logger.error(f"Error deleting sentence and video: {error}")

    def get_user_videos_and_translator_videos(self, user_id):
        """
        Fetch user's videos and corresponding translator videos.
        Returns a list of dicts:
          [{ 'user_video_id': ..., 'user_video_path': ..., 'translator_video_path': ... }, ...]
        """
        if not user_id:
            return []
        connection = self.connect_to_db()
        if not connection:
            return []
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT uv.video_id     AS user_video_id,
                       uv.file_path    AS user_video_path,
                       tv.file_path    AS translator_video_path
                FROM public.videos uv
                LEFT JOIN public.videos tv
                       ON uv.video_reference_id = tv.video_id
                WHERE uv.user_id = %s
                ORDER BY uv.uploaded_at DESC
                """,
                (user_id,)
            )
            results = cursor.fetchall()
            cursor.close()
            connection.close()

            videos = []
            for row in results:
                videos.append({
                    'user_video_id': row[0],
                    'user_video_path': row[1],
                    'translator_video_path': row[2]
                })
            return videos
        except Exception as error:
            logger.error(f"Error fetching user's videos: {error}")
            return []

    def delete_user_video(self, video_id, user_id):
        """
        Delete a user's video from the database and file system.
        """
        if not user_id:
            return
        connection = self.connect_to_db()
        if not connection:
            return
        try:
            cursor = connection.cursor()
            # Get the video file path before deletion
            cursor.execute(
                """
                SELECT file_path
                FROM public.videos
                WHERE video_id = %s
                  AND user_id = %s
                """,
                (video_id, user_id)
            )
            result = cursor.fetchone()
            if result:
                video_file_path = result[0]
                # Delete the video record
                cursor.execute(
                    """
                    DELETE FROM public.videos
                    WHERE video_id = %s
                      AND user_id = %s
                    """,
                    (video_id, user_id)
                )
                connection.commit()

                # Delete the file from the file system
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

    def get_random_video_for_voting(self, user_id, language):
        """
        Fetch a random video (user or translator) not uploaded by the current user,
        and not yet voted on by the current user.
        Returns (video_id, file_path, sentence_content) or None if no video found.
        """
        connection = self.connect_to_db()
        if not connection:
            logger.error("Failed to connect to database")
            return None
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT v.video_id, v.file_path, s.sentence_content
                FROM videos v
                LEFT JOIN sentences s ON v.text_id = s.sentence_id
                WHERE v.language = %s
                  AND v.user_id != %s
                  AND v.video_id NOT IN (
                      SELECT video_id FROM votes WHERE user_id = %s
                  )
                """,
                (language, user_id, user_id)
            )
            all_results = cursor.fetchall()
            if all_results:
                import random
                chosen_result = random.choice(all_results)
                video_id, file_path, sentence_content = chosen_result
                cursor.close()
                connection.close()
                return video_id, file_path, sentence_content
            else:
                cursor.close()
                connection.close()
                return None
        except Exception as error:
            logger.error(f"Error fetching random video for voting: {error}")
            if connection:
                connection.close()
            return None

    def increment_video_score(self, video_id, score_type):
        """
        Increment the positive_scores or negative_scores column for a video.
        score_type must be either 'positive_scores' or 'negative_scores'.
        """
        if score_type not in ['positive_scores', 'negative_scores']:
            logger.error(f"Invalid score type: {score_type}")
            return
        
        connection = self.connect_to_db()
        if not connection:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                UPDATE videos
                SET {score_type} = COALESCE({score_type}, 0) + 1
                WHERE video_id = %s
                """,
                (video_id,)
            )
            connection.commit()
            cursor.close()
            connection.close()
        except Exception as error:
            logger.error(f"Error updating {score_type} for video {video_id}: {error}")

    def record_vote(self, user_id, video_id, vote_type):
        """
        Record a vote in the votes table. vote_type should be 'up' or 'down'.
        """
        if vote_type not in ['up', 'down']:
            logger.error(f"Invalid vote type: {vote_type}")
            return
        
        connection = self.connect_to_db()
        if not connection:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO votes (user_id, video_id, vote_type, vote_timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (user_id, video_id, vote_type)
            )
            connection.commit()
            cursor.close()
            connection.close()
        except Exception as error:
            logger.error(f"Error recording vote: {error}")


