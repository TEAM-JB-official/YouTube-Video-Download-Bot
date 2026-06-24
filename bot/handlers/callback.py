from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("Use /help for full list.")
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^plans$"))
async def plans_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("Use /plan for details.")
    await callback_query.answer()
