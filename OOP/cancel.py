
from telegram.ext import (
    ContextTypes,
)

from apscheduler.jobstores.base import JobLookupError
RESTART_JOB_KEY = 'restart_job'

def cancel_restarted_message(context: ContextTypes.DEFAULT_TYPE):
    """
    Cancels the 'bot restarted' job once a handler actually responds.
    """
    old_job = context.user_data.pop(RESTART_JOB_KEY, None)
    if old_job:
        try:
            old_job.schedule_removal()
        except JobLookupError:
            pass