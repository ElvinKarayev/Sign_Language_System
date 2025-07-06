import psycopg2
import logging
import os

from BucketService import BucketService

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
            self.connection = self.connect_to_db()
    
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
        
    def get_last_video_file_path(self, user_id):
        connection = self.connection
        if not connection:
            return None
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT file_path
                FROM public.videos
                WHERE user_id = %s
                ORDER BY uploaded_at DESC
                LIMIT 1
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error retrieving last video path: {e}")
            return None

    
    
    def check_user_exists(self, telegram_id):
        """
        Checks if a user exists in the database by telegram_id or username 
        and returns the user's id, username, language, and role if they exist.
        """
        connection = self.connection
        if not connection:
            return None, None, None, None, None
        
        try:
            cursor = connection.cursor()
            # Attempt to find user by telegram_id
            if telegram_id:
                cursor.execute(
                        "SELECT user_id, username, country, user_role, joined_classroom "
                        "FROM public.users WHERE telegram_id = %s",
                        (telegram_id,)
                )
                result = cursor.fetchone()
                if result:
                    cursor.close()

                    return result[0], result[1], result[2], result[3], result[4]
            cursor.close()
            return None, None, None, None, None
        except Exception as error:
            logger.error(f"Error checking user in the database: {error}")
            return None, None, None, None, None

    def add_new_user(self, username, language, role, telegram_id):
        """
        Inserts a new user into the database after getting consent,
        with role preference.
        """
        connection = self.connection
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
            logger.info(
                f"New user {username} added to the database with role {role} "
                f"and telegram_id {telegram_id}."
            )
            return db_user_id
        except psycopg2.IntegrityError as error:
            connection.rollback()
            cursor.close()
            logger.error(f"IntegrityError: {error}")
            return None
        except Exception as error:
            connection.rollback()
            cursor.close()
            logger.error(f"Error adding new user to the database: {error}")
            return None

    def get_user_language(self, user_id):
        """
        Retrieves user's language (country) from the database.
        """
        connection = self.connection
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
            if result:
                return result[0]
            return None
        except Exception as error:
            logger.error(f"Error getting user language from database: {error}")
            return None

    def save_video_info(self, user_id, file_path, language, sentence=None, reference_id=None, sentence_id=None, classroom_id=None):
        connection = self.connection
        if not connection:
            return
        try:
            if sentence and not sentence_id:
                existing_id = self._find_sentence_id_if_exists(sentence, language)
                if existing_id:
                    # Reuse that row
                    sentence_id = existing_id
                    logger.info(f"Reusing existing sentence_id={sentence_id} for content='{sentence}'")
                else:
                    # Insert a new row
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

            # 2) Insert row in 'videos' referencing that sentence_id
            cursor = connection.cursor()
            if classroom_id:
                cursor.execute(
                    """
                    INSERT INTO public.videos
                        (user_id, file_path, text_id, language, video_reference_id, uploaded_at, classroom_id)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                    """,
                    (user_id, file_path, sentence_id, language, reference_id, str(classroom_id))
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO public.videos
                        (user_id, file_path, text_id, language, video_reference_id, uploaded_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (user_id, file_path, sentence_id, language, reference_id)
                )
            connection.commit()
            cursor.close()
            logger.info(f"Video + sentence stored for user {user_id}")
        except Exception as error:
            logger.error(f"Error saving video info: {error}")


    
    def _find_sentence_id_if_exists(self, sentence, language):
        """
        Returns the existing sentence_id (int) if `sentence_content` + `language` 
        already exists in 'sentences'. Otherwise returns None.
        """
        conn = self.connect_to_db()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            # case-insensitive match if you want EXACT duplicates ignoring case:
            cur.execute(
                """
                SELECT sentence_id 
                FROM sentences
                WHERE sentence_language = %s
                AND LOWER(sentence_content) = LOWER(%s)
                LIMIT 1
                """,
                (language, sentence)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error in _find_sentence_id_if_exists: {e}")
            return None



    def get_random_translator_video(self, user_language, context=None, classroom_id=None, exclude_ids=None):
        """
        Fetch a random translator video (video_reference_id IS NULL) for the
        given user_language. Optionally exclude a list of video IDs (exclude_ids),
        and exclude videos already responded to or uploaded by the same user.
        """
        connection = self.connection
        if not connection:
            logger.error("Failed to connect to database")
            return None, None
        
        try:
            cursor = connection.cursor()
            user_id = context.user_data.get('user_id') if context else None
            
            exclude_clause = "AND v.video_id NOT IN %s" if exclude_ids else ""
            classroom_clause = "AND v.classroom_id = %s" if classroom_id else ""
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
                  {classroom_clause}
                  {exclude_clause}
            """
            
            params = [user_language, user_id, user_id]
            if classroom_id:
                params.append(classroom_id)
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
                return file_path, sentence
            else:
                cursor.close()
                return None, None
        except Exception as error:
            logger.error(f"Error fetching translator video: {error}")
            return None, None

    def get_video_text_id(self, video_id):
        """
        Retrieve the text_id associated with a video.
        """
        connection = self.connection
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
        connection = self.connection
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
            return count > 0
        except Exception as error:
            logger.error(f"Error checking sentence existence: {error}")
            return False

    def get_all_sentences(self, language):
        """
        Retrieve all sentences for a specific language from the database,
        ordered by descending sentence_id.
        """
        connection = self.connection
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
            return results
        except Exception as error:
            logger.error(f"Error retrieving sentences: {error}")
            return []

    def get_translator_videos(self, user_id, language, classroom_id=None):
        """
        Return a list of dicts with:
        [ { 'id': int, 'sentence': str, 'video_path': str, 'upvotes': int, 'downvotes': int }, ... ]
        for a specific translator (user_id) and language.
        """
        if not user_id:
            return []

        connection = self.connection
        if not connection:
            return []

        try:
            cursor = connection.cursor()
            query ="""
                SELECT v.video_id,
                    s.sentence_id, 
                    s.sentence_content,
                    v.file_path,
                    COALESCE(v.positive_scores, 0) AS upvotes,
                    COALESCE(v.negative_scores, 0) AS downvotes
                FROM sentences s
                LEFT JOIN videos v ON s.sentence_id = v.text_id
                WHERE v.user_id = %s
                AND s.sentence_language = %s AND v.video_reference_id is NULL
                """
            params = [user_id, language]
            if classroom_id:
                query += " AND v.classroom_id = %s"
                params.append(classroom_id)
            query += " ORDER BY s.sentence_id DESC, v.uploaded_at DESC"
            cursor.execute(query,tuple(params))
            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                results.append({
                    'video_id': row[0],
                    'sentence_id': row[1],
                    'sentence': row[2],
                    'video_path': row[3],
                    'upvotes': row[4],
                    'downvotes': row[5]
                })
            return results

        except Exception as e:
            logger.error(f"get_translator_videos error: {e}")
            return []
    def update_user_classroom_status(self, user_id, classroom_id):
        """
        Updates the 'joined_classroom' column for the user in the database to the classroom_id.
        Uses a prepared statement to prevent SQL injection.
        """
        connection = self.connection
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            
            # Prepared statement (parameterized query) to prevent SQL injection
            query = """
                UPDATE public.users
                SET joined_classroom = %s
                WHERE user_id = %s
            """
            
            # The %s placeholders will be safely replaced by the parameters below
            cursor.execute(query, (classroom_id, user_id))
            
            connection.commit()
            cursor.close()
            logger.info(f"User {user_id} successfully joined classroom {classroom_id}.")
            return True
        except Exception as error:
            logger.error(f"Error updating classroom status for user {user_id}: {error}")
            return False
    def remove_user_from_classroom(self, user_id: int):
        """
        Removes the user from the classroom by setting the classroom_id to NULL.
        Returns:
            - True if successful.
            - False if an error occurred.
        """
        connection = self.connection
        if not connection:
            logger.error("Database connection is not available.")
            return False

        try:
            cursor = connection.cursor()

            # SQL query to remove user from classroom by setting classroom_id to NULL
            query = """
                UPDATE public.users
                SET joined_classroom = NULL
                WHERE user_id = %s
            """
            cursor.execute(query, (user_id,))  # Use prepared statement to avoid SQL injection
            connection.commit()  # Commit the transaction

            cursor.close()
            
            logger.info(f"User {user_id} successfully removed from classroom.")
            return True  # Return True if successful

        except Exception as error:
            logger.error(f"Error removing user {user_id} from classroom: {error}")
            connection.rollback()  # Rollback in case of error
            return False  # Return False in case of any error    
    def validate_classroom_credentials(self, classroom_id: str, password: str):
        """
        Validates the classroom credentials (classroom_id and password).
        Returns:
            - True if valid credentials.
            - False if invalid credentials.
        """
        connection = self.connection
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            logger.debug(f"Validating classroom credentials: classroom_id={classroom_id}, password={password}")
            # SQL query to check if the classroom ID and password both match
            query = """
                SELECT classroom_id
                FROM public.classroom
                WHERE classroom_id = %s AND password = %s
            """
            cursor.execute(query, (classroom_id, password))  # Use prepared statement to avoid SQL injection
            result = cursor.fetchone()  # Fetch the result
            logger.debug(f"Classroom credentials validation result: {result}")

            cursor.close()

            if result:
                return True  # Credentials are valid (classroom_id exists in DB)
            else:
                return False

        except Exception as error:
            logger.error(f"Error validating classroom credentials: {error}")
            return False  # Return False in case of any error
            
    def delete_sentence_and_video(self, sentence_id, user_id, video_id):
        """
        The 'legacy' approach for when there's exactly 1 video referencing the sentence:
        - If multiple videos share sentence_id, we call delete_single_video(...) instead.
        - Otherwise, remove the 'sentences' row (which cascades to remove the 1 referencing 'videos' row).
            Also remove the video file if we find it.
        """

        connection = self.connection
        if not connection:
            return

        try:
            cursor = connection.cursor()

            # A) Count how many videos reference this sentence
            cursor.execute(
                """
                SELECT COUNT(video_id)
                FROM videos
                WHERE text_id = %s
                """,
                (sentence_id,)
            )
            vids_count = cursor.fetchone()[0]  # the integer count

            if vids_count > 1:
                # => multiple references => do NOT do the old full-sentence removal
                cursor.close()
                logger.info(
                    f"Multiple videos found for sentence_id={sentence_id}. "
                    f"Forwarding to delete_single_video with video_id={video_id}."
                )
                # Call our single-video deletion
                self.delete_single_video(video_id, user_id)
                return
            else:
                # => only 1 (or 0) referencing videos => old logic

                # 1) get the file_path of THIS specific video (video_id, user_id)
                cursor.execute(
                    """
                    SELECT v.file_path
                    FROM videos v
                    WHERE v.text_id = %s
                    AND v.user_id = %s
                    AND v.video_id = %s
                    """,
                    (sentence_id, user_id, video_id)
                )
                result = cursor.fetchone()
                video_file_path = result[0] if result else None

                # 2) Delete the 'sentences' row => ON DELETE CASCADE 
                #    => that one referencing 'videos' row also goes away
                cursor.execute(
                    """
                    DELETE FROM sentences
                    WHERE sentence_id = %s
                    AND user_id = %s
                    """,
                    (sentence_id, user_id)
                )
                connection.commit()

                # 3) If you want to remove the file on disk
                if video_file_path and os.path.exists(video_file_path):
                    os.remove(video_file_path)
                    logger.info(f"Deleted video file {video_file_path}")

                cursor.close()
                logger.info(
                    f"Deleted sentence {sentence_id} (and associated single video) for user {user_id}"
                )
        except Exception as error:
            logger.error(f"Error in delete_sentence_and_video: {error}")


    def delete_single_video(self, video_id, user_id):
        """
        Removes exactly one 'videos' row that matches (video_id, user_id).
        Then checks whether any videos remain referencing that sentence_id.
        If none remain, delete the parent 'sentences' row.
        If some remain and the deleted user's ID was also the sentence's owner,
        reassign the sentence's user_id to another referencing user.
        Also remove the file on disk if desired.
        """

        connection = self.connection
        if not connection:
            return

        try:
            cursor = connection.cursor()
            # 1) Identify which sentence_id this video references & the file_path
            cursor.execute(
                """
                SELECT v.text_id, s.user_id, v.file_path
                FROM videos v
                JOIN sentences s ON v.text_id = s.sentence_id
                WHERE v.video_id = %s
                AND v.user_id = %s
                """,
                (video_id, user_id)
            )
            row = cursor.fetchone()
            if not row:
                # No matching video row for this (video_id, user_id).
                cursor.close()
                return

            sentence_id, sentence_owner_id, file_path = row

            # 1a) Remove the file on disk if it exists
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted video file {file_path}")

            # 2) Delete just this one 'videos' row
            cursor.execute(
                """
                DELETE FROM videos
                WHERE video_id = %s
                AND user_id = %s
                """,
                (video_id, user_id)
            )
            connection.commit()

            # 3) Check how many videos still reference this sentence
            cursor.execute(
                """
                SELECT video_id, user_id
                FROM videos
                WHERE text_id = %s
                """,
                (sentence_id,)
            )
            remaining = cursor.fetchall()

            if not remaining:
                # (3a) If none remain, remove the parent sentence row
                cursor.execute(
                    "DELETE FROM sentences WHERE sentence_id = %s",
                    (sentence_id,)
                )
                connection.commit()
                logger.info(f"Deleted sentence {sentence_id} because no more videos reference it.")
            else:
                # (3b) Some remain referencing the same sentence -> keep the sentence row
                # If the original sentence owner was the same as the user we just removed,
                # we reassign 'sentences.user_id' to another referencing user
                if sentence_owner_id == user_id:
                    new_owner = None
                    for (vid, vuser) in remaining:
                        if vuser != user_id:
                            new_owner = vuser
                            break
                    if new_owner:
                        cursor.execute(
                            """
                            UPDATE sentences
                            SET user_id = %s
                            WHERE sentence_id = %s
                            """,
                            (new_owner, sentence_id)
                        )
                        connection.commit()
                        logger.info(
                            f"Reassigned sentence {sentence_id} owner from {user_id} to {new_owner}"
                        )

            cursor.close()

        except Exception as e:
            logger.error(f"Error in delete_single_video: {e}")



    def get_user_videos_and_translator_videos(self, user_id):
        """
        Fetch the user's videos and corresponding translator videos,
        along with upvote/downvote counts from the videos table
        (i.e. positive_scores / negative_scores).
        
        Returns a list of dicts like:
        [
        {
            'user_video_id': ...,
            'user_video_path': ...,
            'translator_video_path': ...,
            'user_upvotes': ...,
            'user_downvotes': ...
        },
        ...
        ]
        """
        if not user_id:
            return []
        
        connection = self.connection
        if not connection:
            return []
        
        try:
            cursor = connection.cursor()

            # Use videos.positive_scores and videos.negative_scores
            cursor.execute(
                """
                SELECT
                    uv.video_id        AS user_video_id,
                    uv.file_path       AS user_video_path,
                    tv.file_path       AS translator_video_path,
                    COALESCE(uv.positive_scores, 0) AS user_upvotes,
                    COALESCE(uv.negative_scores, 0) AS user_downvotes
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

            videos = []
            for row in results:
                videos.append({
                    'user_video_id':         row[0],
                    'user_video_path':       row[1],
                    'translator_video_path': row[2],
                    'user_upvotes':          row[3],  # now from uv.positive_scores
                    'user_downvotes':        row[4],  # now from uv.negative_scores
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
        connection = self.connection
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
                logger.info(f"Deleted user video {video_id} for user {user_id}")
            else:
                logger.error(f"Video with id {video_id} not found for user {user_id}")
                cursor.close()
        except Exception as error:
            logger.error(f"Error deleting user video: {error}")

    def get_random_video_for_voting(self, user_id, language):
        """
        Fetch a random video (user or translator) not uploaded by the current user,
        and not yet voted on by the current user.
        Returns (video_id, file_path, sentence_content) or None if no video found.
        """
        connection = self.connection
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
                return video_id, file_path, sentence_content
            else:
                cursor.close()
                return None
        except Exception as error:
            logger.error(f"Error fetching random video for voting: {error}")
            return None

    def increment_video_score(self, video_id, score_type):
        """
        Increment the positive_scores or negative_scores column for a video.
        score_type must be either 'positive_scores' or 'negative_scores'.
        """
        if score_type not in ['positive_scores', 'negative_scores']:
            logger.error(f"Invalid score type: {score_type}")
            return
        
        connection = self.connection
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
        except Exception as error:
            logger.error(f"Error updating {score_type} for video {video_id}: {error}")


    def record_vote(self, user_id, video_id, vote_type):
        """
        Record a vote in the votes table. vote_type should be 'up' or 'down'.
        Returns the newly inserted vote_id.
        """
        if vote_type not in ['up', 'down']:
            logger.error(f"Invalid vote type: {vote_type}")
            return None  # Or raise an exception
        
        connection = self.connection
        if not connection:
            return None
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO votes (user_id, video_id, vote_type, vote_timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING vote_id
                """,
                (user_id, video_id, vote_type)
            )
            new_vote_id = cursor.fetchone()[0]  # Grab the newly created vote_id
            connection.commit()
            cursor.close()
            return new_vote_id
        except Exception as error:
            logger.error(f"Error recording vote: {error}")
            return None

    def update_vote_feedback(self, vote_id, feedback_text):
        """
        Update the feedback column for the specified vote_id.
        """
        connection = self.connection
        if not connection:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE votes
                SET feedback = %s
                WHERE vote_id = %s
                """,
                (feedback_text, vote_id)
            )
            connection.commit()
            cursor.close()
            logger.info(f"Feedback updated for vote_id={vote_id}")
        except Exception as error:
            logger.error(f"Error updating feedback for vote_id={vote_id}: {error}")

  
    def get_user_rank(self, user_id: int, user_role: str):
        """
        Retrieves the rank and points of a specific user within their own role category (User or Translator).
        If the user is a Translator, also fetches the top 5 Translators.
        """
        
        connection = self.connection
        if not connection:
            return None, []

        try:
            cursor = connection.cursor()

            # Query to get user's rank and points within their role category
            get_user_rank_score = """
                SELECT points, rank FROM (
                    SELECT user_id, points,
                        RANK() OVER (ORDER BY points DESC) as rank
                    FROM users
                    WHERE user_role = %s
                ) ranked_users
                WHERE user_id = %s;
            """
            cursor.execute(get_user_rank_score, (user_role, user_id))
            user_rank_score = cursor.fetchone()  # Fetch one row (since we expect a single user)

            # If the user is a Translator, fetch the Top 5 Translators
            top_5_translators = []
            if user_role == 'Translator':
                query_top_5 = """
                    SELECT username, points
                    FROM users
                    WHERE user_role = 'Translator'
                    ORDER BY points DESC
                    LIMIT 5;
                """
                cursor.execute(query_top_5)
                top_5_translators = cursor.fetchall()  # Fetch all rows for the top 5

            cursor.close()
            return user_rank_score, top_5_translators

        except Exception as error:
            logger.error(f"Error retrieving user rank: {error}")
            return None, []
    def get_all_users(self):
        """
        Retrieve all users from the database.
        """
        connection = self.connection
        if not connection:
            return []

        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT user_id, username, country, user_role, telegram_id FROM public.users ORDER BY user_id ASC"
            )
            users = cursor.fetchall()
            cursor.close()

            return users
        except Exception as error:
            logger.error(f"Error retrieving all users: {error}")
            return []

    def get_users_filtered(self, column, value):
        """
        Retrieve users filtered by a specific column (e.g., role, status).
        :param column: Column to filter by.
        :param value: Value to filter for.
        """
        connection = self.connection
        if not connection:
            return []

        try:
            cursor = connection.cursor()
            query = f"SELECT user_id, username, country, user_role, telegram_id FROM public.users WHERE {column} = %s ORDER BY user_id ASC"
            cursor.execute(query, (value,))
            users = cursor.fetchall()
            cursor.close()

            return users
        except Exception as error:
            logger.error(f"Error retrieving users by filter ({column}={value}): {error}")
            return []

    def update_user_info(self, user_id, column, new_value):
        """
        Update a specific column for a user.
        :param user_id: The ID of the user to update.
        :param column: The column to update (e.g., "user_role", "country").
        :param new_value: The new value to assign.
        """
        connection = self.connection
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            query = f"UPDATE public.users SET {column} = %s WHERE user_id = %s"
            cursor.execute(query, (new_value, user_id))
            connection.commit()
            success = cursor.rowcount > 0  # Check if any row was updated
            cursor.close()

            return success
        except Exception as error:
            logger.error(f"Error updating user {user_id}: {error}")
            return False
    def delete_user(self, user_id):
        """
        Deletes a user from the database.
        :param user_id: The ID of the user to delete.
        """
        connection = self.connection
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM public.users WHERE user_id = %s", (user_id,))
            connection.commit()
            success = cursor.rowcount > 0  # Check if any row was deleted
            cursor.close()

            return success
        except Exception as error:
            logger.error(f"Error deleting user {user_id}: {error}")
            return False
        
    def get_user_table_columns(self):
        """
        Fetch the column names of the 'users' table.
        """
        connection = self.connection
        if not connection:
            return []

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                """
            )
            columns = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return columns
        except Exception as error:
            logger.error(f"Error fetching user table columns: {error}")
            return []


    def get_feedback_for_video(self, video_id):
        """
        Returns a list of feedback (strings) from the votes table
        for a given video_id.
        """
        connection = self.connection
        if not connection:
            return []
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT feedback
                FROM public.votes
                WHERE video_id = %s
                AND feedback IS NOT NULL
                AND feedback <> ''
                """,
                (video_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            
            # Each row is a tuple with one item: the feedback text
            feedback_list = [row[0] for row in rows]
            return feedback_list
        
        except Exception as e:
            logger.error(f"Error fetching feedback for video {video_id}: {e}")
            return []


    def check_if_feedback_exists(self, video_id):
        """
        Returns True if there is at least one feedback for the given video_id,
        otherwise False.
        """
        connection = self.connection
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM public.votes
                WHERE video_id = %s
                AND feedback IS NOT NULL
                AND feedback <> ''
                LIMIT 1
                """,
                (video_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error checking feedback existence for video {video_id}: {e}")
            return False
    
    def get_classrooms_for_user(self, user_id):
        """
        Retrieves the list of classrooms owned by a specific user, including passwords.
        Returns None if no classrooms exist.
        """
        connection = self.connection
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT classname, classroom_id, password 
                FROM public.classroom 
                WHERE owner = %s
                """,
                (user_id,)
            )
            results = cursor.fetchall()
            cursor.close()

            if not results:
                return None  # Return None if the user has no classrooms

            # Convert results to a list of dictionaries
            return [{'classname': row[0], 'classroom_id': str(row[1]), 'password': row[2]} for row in results]

        except Exception as error:
            logger.error(f"Error retrieving classrooms for user {user_id}: {error}")
            return None
        
        
    def create_classroom(self, user_id, classname, password):
        """
        Inserts a new classroom for the given user.
        Returns the new classroom ID if successful, or None if an error occurs.
        """
        connection = self.connection
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO public.classroom (owner, classname, password)
                VALUES (%s, %s, %s)
                RETURNING classroom_id
                """,
                (user_id, classname, password)
            )
            new_classroom_id = cursor.fetchone()[0]
            connection.commit()
            cursor.close()
            return new_classroom_id
        except Exception as error:
            logger.error(f"Error creating classroom: {error}")
            return None
    def delete_classroom(self, classroom_id: str) -> bool:
        """
        Deletes a classroom from the database.
        :param classroom_id: The ID of the classroom to delete.
        :return: True if deletion was successful, False otherwise.
        """
        connection = self.connection
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM public.classroom WHERE classroom_id = %s", (classroom_id,))
            connection.commit()
            cursor.close()
            return True  # ✅ Deletion successful
        except Exception as error:
            logger.error(f"Error deleting classroom {classroom_id}: {error}")
            return False  # ❌ Deletion failed
    def get_classroom_sentences(self, classroom_id, language):
        """
        Fetch all sentences from videos that belong to a specific classroom.
        

        :return: A list of unique sentences for the given classroom.
        """
        connection = self.connection
        if not connection:
            return []

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT s.sentence_content
                FROM public.videos v
                JOIN public.sentences s ON v.text_id = s.sentence_id
                WHERE v.classroom_id = %s AND s.sentence_language = %s AND v.video_reference_id is NULL
                ORDER BY v.uploaded_at DESC
                """,
                (classroom_id, language)
            )
            sentences = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return sentences
        except Exception as error:
            logger.error(f"Error retrieving classroom sentences for {classroom_id}: {error}")
            return []

