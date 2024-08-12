import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ChatMemberStatus
from database import Channel, User, create_databases
from config import TOKEN, ADMINS
from aiogram.dispatcher.filters import Command, Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ParseMode
from aiogram.utils import markdown as md
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
import aiogram


create_databases()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


class AdminState(StatesGroup):
    MENU = State()
    SENDING_MESSAGE = State()

@dp.message_handler(Command('start'))
async def start(message: types.Message):
    user_id = message.from_user.id
    try:
        user = User.get(User.user_id == str(user_id))
    except User.DoesNotExist:
        User.create(user_id=str(user_id))
        await handle_start_or_subscribed(user_id, message)

    else:
        await handle_start_or_subscribed(user_id, message)



async def handle_start_or_subscribed(user_id, message):
    user_chat_id = message.chat.id
    channels_exist = Channel.select().exists()

    if user_chat_id > 0 and channels_exist:
        unsubscribed_channels = set()

        for channel in Channel.select():
            try:
                chat_member = await bot.get_chat_administrators(channel.channel_id, user_id)
                if chat_member.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
                    unsubscribed_channels.add(channel.name)
            except Exception as e:
                pass

        if unsubscribed_channels:
            buttons = [
                InlineKeyboardButton(f"Подписаться на {channel.name}", url=channel.link)
                for channel in Channel.select()
                if channel.name in unsubscribed_channels
            ]
            buttons.append(InlineKeyboardButton("Я подписался", callback_data="subscribed"))
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(*buttons)
            await bot.send_message(user_id, "Подпишитесь на следующие каналы, а после нажмите на кнопку, или пропишите /start:", reply_markup=keyboard)
        else:
            await archive(message)
    else:
        main_keyboard = InlineKeyboardMarkup(row_width=1)
        main_keyboard.add(InlineKeyboardButton("ссылки", callback_data="archive"))
        await bot.send_message(user_id, "Добро пожаловать!", reply_markup=main_keyboard)


@dp.callback_query_handler(Text(equals='subscribed'))
async def subscribed_button(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await handle_start_or_subscribed(user_id, callback_query.message)
    
@dp.callback_query_handler(Text(equals='archive'))
async def archive_button(callback_query: types.CallbackQuery):
    await archive(callback_query.message)


async def archive(query):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    button_categories = types.KeyboardButton("Категории")
    button_info = types.KeyboardButton("Информация")
    button_contact = types.KeyboardButton("Связь")
    
    keyboard.add(button_categories, button_info, button_contact)
    
    await bot.send_message(query.chat.id, "Добро Пожаловать", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "Категории")
async def categories(message: types.Message):
    inline_keyboard = types.InlineKeyboardMarkup(row_width=1)
    button_soft = types.InlineKeyboardButton("сюда вставить что нужно", callback_data='soft')
    inline_keyboard.add(button_soft)

    await message.answer("Выберите категорию:", reply_markup=inline_keyboard)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'soft')
async def send_soft_links(callback_query: types.CallbackQuery):
    await callback_query.message.answer(

    )
    
@dp.message_handler(lambda message: message.text == "Информация")
async def infa(message: types.Message):
    await message.answer("")
    
    
@dp.message_handler(lambda message: message.text == "Связь")
async def infa(message: types.Message):
    await message.answer("")
    

@dp.message_handler(Command('adm'))
async def admin_menu(message: types.Message):
    if message.from_user.id in ADMINS:
        admin_keyboard = InlineKeyboardMarkup(row_width=1)
        admin_keyboard.add(InlineKeyboardButton(text="Посмотреть каналы", callback_data="view_channels"))
        admin_keyboard.add(InlineKeyboardButton(text="Удалить канал", callback_data="delete_channel"))
        admin_keyboard.add(InlineKeyboardButton(text="Рассылка", callback_data="send_message"))
        admin_keyboard.add(InlineKeyboardButton(text="Статистика", callback_data="statistics"))

        await AdminState.MENU.set()
        await message.reply("Админ-панель:", reply_markup=admin_keyboard)
    else:
        await message.reply("У вас нет доступа к админ-панели.")



@dp.callback_query_handler(Text(equals='view_channels'))
async def view_channels(callback_query: types.CallbackQuery):
    channels = Channel.select()
    channels_info = "\n".join([f"{channel.id}: {channel.name} ({channel.link})" for channel in channels])
    await bot.send_message(callback_query.from_user.id, f"Список каналов:\n{channels_info}")
    
 


@dp.callback_query_handler(Text(equals='statistics'))
async def statistics(callback_query: types.CallbackQuery):
    user_count = User.select().count()
    await bot.send_message(callback_query.from_user.id, f"Количество пользователей в базе: {user_count}")


state_dict = {}


@dp.callback_query_handler(text='send_message', state="*")
async def process_send_message(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(data="data")
    state_dict[callback_query.from_user.id] = 'waiting_for_message'
    await bot.send_message(callback_query.from_user.id, "Введите текст или отправьте контент для рассылки:")


@dp.message_handler(lambda message: state_dict.get(message.from_user.id) == 'waiting_for_message', content_types=types.ContentTypes.ANY)
async def process_message(message: types.Message, state: FSMContext):
    del state_dict[message.from_user.id]
    user_ids = [user.user_id for user in User.select(User.user_id)]
    sent_count = 0
    not_sent_count = 0
    async with state.proxy() as data:
        data_value = data.get('data')

    for user_id in user_ids:
        try:
            if message.text:
                await bot.send_message(user_id, message.text, parse_mode=ParseMode.HTML)
            elif message.photo:
                await bot.copy_message(user_id, message.chat.id, message.message_id)
            elif message.document:
                await bot.copy_message(user_id, message.chat.id, message.message_id)
            elif message.audio:
                await bot.copy_message(user_id, message.chat.id, message.message_id)
            elif message.video:
                await bot.copy_message(user_id, message.chat.id, message.message_id)

            sent_count += 1
        except Exception as e:
            not_sent_count += 1
    report_text = f"Рассылка завершена:\n\nОтправлено: {sent_count}\nНе отправлено: {not_sent_count}"
    await bot.send_message(message.from_user.id, report_text)
    
    
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
