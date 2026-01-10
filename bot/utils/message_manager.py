"""
Утилита для управления сообщениями бота.
Автоматически удаляет старые сообщения, чтобы не засорять чат.
"""
import logging
from typing import Optional, List
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> bool:
    """
    Безопасно удалить сообщение с обработкой ошибок.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения
        
    Returns:
        True если сообщение удалено успешно, False в противном случае
    """
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except TelegramBadRequest as e:
        # Сообщение уже удалено или не существует
        logger.debug(f"Failed to delete message {message_id} in chat {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting message {message_id} in chat {chat_id}: {e}")
        return False


async def delete_previous_messages(bot: Bot, db, user_id: int, chat_id: int, keep_last: int = 0) -> int:
    """
    Удалить предыдущие сообщения бота из чата.
    
    Args:
        bot: Экземпляр бота
        db: Экземпляр базы данных
        user_id: ID пользователя
        chat_id: ID чата
        keep_last: Сколько последних сообщений оставить (по умолчанию 0 - удалить все)
        
    Returns:
        Количество удаленных сообщений
    """
    # Получаем список сообщений для удаления
    messages = await db.get_bot_messages(user_id, chat_id)
    
    if not messages:
        return 0
    
    # Оставляем последние N сообщений, если указано
    if keep_last > 0 and len(messages) > keep_last:
        messages_to_delete = messages[:-keep_last]
    else:
        messages_to_delete = messages
    
    deleted_count = 0
    message_ids_to_remove = []
    
    # Удаляем сообщения
    for message in messages_to_delete:
        message_id = message['message_id']
        if await safe_delete_message(bot, chat_id, message_id):
            deleted_count += 1
            message_ids_to_remove.append(message_id)
    
    # Удаляем записи из базы данных
    if message_ids_to_remove:
        await db.remove_bot_messages(message_ids_to_remove)
    
    logger.info(f"Deleted {deleted_count} messages for user {user_id} in chat {chat_id}")
    return deleted_count


async def track_bot_message(db, user_id: int, chat_id: int, message_id: int):
    """
    Сохранить ID сообщения бота для последующего удаления.
    
    Args:
        db: Экземпляр базы данных
        user_id: ID пользователя
        chat_id: ID чата
        message_id: ID сообщения
    """
    await db.add_bot_message(user_id, chat_id, message_id)
    logger.debug(f"Tracked message {message_id} for user {user_id} in chat {chat_id}")
