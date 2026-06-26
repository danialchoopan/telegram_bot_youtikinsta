import logging
from telegram.ext import ApplicationBuilder

from bot.config import Config
from bot.database import Database
from bot.services.queue_worker import QueueWorker
from bot.handlers import start, download, admin, settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(Config.LOG_PATH / "bot.log")),
    ],
)
logger = logging.getLogger(__name__)


def main():
    Config.ensure_directories()
    Database()

    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()

    for handler in start.get_handlers():
        app.add_handler(handler)
    for handler in download.get_handlers():
        app.add_handler(handler)
    for handler in admin.get_handlers():
        app.add_handler(handler)
    for handler in settings.get_handlers():
        app.add_handler(handler)

    queue_worker = QueueWorker(app)

    async def post_init(application):
        await queue_worker.start()
        logger.info("Bot started and queue worker running")

    async def post_shutdown(application):
        await queue_worker.stop()
        logger.info("Bot shutting down")

    app.post_init = post_init
    app.post_shutdown = post_shutdown

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
