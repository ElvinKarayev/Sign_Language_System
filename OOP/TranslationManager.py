import os
import json
import logging

logger = logging.getLogger(__name__)

class TranslationManager:
    def __init__(self, translations_dir):
        """
        Initialize the TranslationManager by specifying the directory where
        translation JSON files are stored.

        :param translations_dir: The directory containing language JSON files.
                                Defaults to 'translations'.
        """
        self.translations_dir = translations_dir
        self.loaded_translations = {}  # Cache for already loaded languages
        # Map your supported language names to their file codes (if needed)
        self.language_codes = {
            # 'English': 'en',
            'Azerbaijani': 'az',
            # 'German': 'de',
            'Russian': 'ru',
            'Ukrainian': 'ua'
        }

    def get_translation(self, context, key):
        """
        Retrieve the translation string for a given key, based on the user's
        current language (stored in context.user_data['language']).

        :param context: The context from your Telegram handler, which should
                        include 'language' in context.user_data.
        :param key: The translation key to look up in the JSON file.
        :return: The translated string, or the key itself if not found.
        """
        # Determine the user’s language; default to 'English'
        language = context.user_data.get('language', 'English')
        # Map the language (e.g., 'English') to a file code (e.g., 'en')
        lang_code = self.language_codes.get(language, 'en')

        # If this language file isn't cached yet, load it from disk
        if lang_code not in self.loaded_translations:
            self._load_language_file(lang_code)

        # Return the translation for the given key, or the key if it doesn't exist
        return self.loaded_translations[lang_code].get(key, key)

    def _load_language_file(self, lang_code):
        """
        Private helper method that loads (or reloads) a language file into
        the loaded_translations cache.

        :param lang_code: The language code (e.g., 'en', 'az', 'de').
        """
        translation_file = os.path.join(self.translations_dir, f'{lang_code}.json')
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                self.loaded_translations[lang_code] = json.load(f)
                logger.info(f"Loaded translations for '{lang_code}' from {translation_file}.")
        except Exception as e:
            logger.error(f"Error loading translation file {translation_file}: {e}")
            # If the file fails to load, create an empty dict so we at least
            # have an entry for this language code.
            self.loaded_translations[lang_code] = {}



