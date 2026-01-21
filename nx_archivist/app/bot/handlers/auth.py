from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.services.uploader import Uploader
import logging

auth_router = Router()
uploader = Uploader()

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()

@auth_router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    if await uploader.is_authorized():
        await message.answer("✅ Ви вже авторизовані!")
        return
        
    await message.answer("📱 Будь ласка, введіть ваш номер телефону у міжнародному форматі (наприклад, +380991234567):")
    await state.set_state(AuthState.waiting_for_phone)

@auth_router.message(AuthState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    
    try:
        await uploader.send_code(phone)
        await message.answer("📩 Код надіслано! Будь ласка, введіть код, який ви отримали від Telegram:")
        await state.set_state(AuthState.waiting_for_code)
    except Exception as e:
        logging.error(f"Error sending code: {e}")
        await message.answer(f"❌ Помилка при надсиланні коду: {e}")
        await state.clear()

@auth_router.message(AuthState.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    
    try:
        await uploader.sign_in(phone, code)
        await message.answer("🎉 Авторизація успішна! Тепер ви можете завантажувати файли.")
        await state.clear()
    except Exception as e:
        logging.error(f"Error signing in: {e}")
        await message.answer(f"❌ Помилка авторизації: {e}\nСпробуйте ще раз /login")
        await state.clear()
