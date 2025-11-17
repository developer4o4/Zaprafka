# bot.py
import asyncio
import logging
import os
import django
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from asgiref.sync import sync_to_async

# Django sozlamalari
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from main.models import FuelMessage

# Bot token
BOT_TOKEN = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'
ADMIN_CHAT_ID = '6094051871'

# Bot yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Async Django ORM funksiyalari
@sync_to_async
def get_fuel_message_by_callback(callback_data):
    """Callback data orqali FuelMessage ni topish"""
    try:
        # callback_data format: "confirm_fuel_1234567890_1234567890"
        fuel_id = callback_data.replace('confirm_', '').replace('reject_', '')
        return FuelMessage.objects.get(callback_data=fuel_id)
    except FuelMessage.DoesNotExist:
        return None

@sync_to_async
def update_fuel_message_status(fuel_message, status):
    """FuelMessage statusini yangilash"""
    fuel_message.status = status
    fuel_message.save()
    return True

@sync_to_async
def get_expired_pending_messages():
    """5 kun o'tgan pending xabarlarni olish"""
    from django.utils import timezone
    from datetime import timedelta
    
    five_days_ago = timezone.now() - timedelta(days=5)
    return list(FuelMessage.objects.filter(
        status=FuelMessage.STATUS_PENDING,
        created_at__lte=five_days_ago
    ))

@sync_to_async
def get_all_pending_messages():
    """Barcha pending xabarlarni olish"""
    return list(FuelMessage.objects.filter(status=FuelMessage.STATUS_PENDING))

# Start komandasi
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("🤖 Yoqilg'i Monitoring Boti ishga tushdi!")

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    """Admin uchun statistikalar"""
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        await message.answer("❌ Sizga ruxsat yo'q")
        return
    
    @sync_to_async
    def get_stats():
        total = FuelMessage.objects.count()
        pending = FuelMessage.objects.filter(status=FuelMessage.STATUS_PENDING).count()
        confirmed = FuelMessage.objects.filter(status=FuelMessage.STATUS_CONFIRMED).count()
        rejected = FuelMessage.objects.filter(status=FuelMessage.STATUS_REJECTED).count()
        
        # 5 kun o'tgan xabarlar
        expired = FuelMessage.objects.filter(
            status=FuelMessage.STATUS_PENDING,
            created_at__lte=timezone.now() - timedelta(days=5)
        ).count()
        
        return total, pending, confirmed, rejected, expired
    
    total, pending, confirmed, rejected, expired = await get_stats()
    
    stats_text = (
        "📊 *Bot Statistikasi*\n\n"
        f"📨 Jami xabarlar: {total}\n"
        f"⏳ Kutilayotgan: {pending}\n"
        f"✅ Tasdiqlangan: {confirmed}\n"
        f"❌ Rad etilgan: {rejected}\n"
        f"🚨 5 kun o'tgan: {expired}\n\n"
        f"⏰ Sana: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    await message.answer(stats_text, parse_mode='Markdown')

# Inline button callback
@dp.callback_query()
async def handle_callback(callback_query: types.CallbackQuery):
    callback_data = callback_query.data
    message = callback_query.message
    user = callback_query.from_user
    
    try:
        fuel_message = await get_fuel_message_by_callback(callback_data)
        
        if not fuel_message:
            await callback_query.answer("❌ Xabar topilmadi", show_alert=True)
            return
        
        if callback_data.startswith('confirm_'):
            # Tasdiqlash
            await update_fuel_message_status(fuel_message, FuelMessage.STATUS_CONFIRMED)
            
            # Xabarni yangilash
            try:
                if message.text:  # Matnli xabar
                    new_text = f"✅ TASDIQLANDI"
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        text=new_text,
                        reply_markup=None
                    )
                elif message.caption:  # Rasmli xabar
                    new_caption = f"✅ TASDIQLANDI\n"
                    await bot.edit_message_caption(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        caption=new_caption,
                        reply_markup=None
                    )
            except Exception as e:
                print(f"Xabarni yangilash xatosi: {e}")
            
            await callback_query.answer("✅ Yoqilg'i tasdiqlandi", show_alert=True)
            
            # Admin ga xabar berish
            admin_text = (
                f"✅ *Xabar Tasdiqlandi*\n\n"
                f"🏢 Guruh: {fuel_message.group_name}\n"
                f"👤 Foydalanuvchi: {user.full_name}\n"
                f"🆔 ID: {user.id}\n"
                f"⏰ Vaqt: {callback_query.message.date.strftime('%Y-%m-%d %H:%M')}"
            )
            
            await bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode='Markdown')
            
        elif callback_data.startswith('reject_'):
            # Rad etish
            await update_fuel_message_status(fuel_message, FuelMessage.STATUS_REJECTED)
            
            # Xabarni yangilash
            try:
                if message.text:  # Matnli xabar
                    new_text = f"❌ RAD ETILDI\n\n{message.text}"
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        text=new_text,
                        reply_markup=None
                    )
                elif message.caption:  # Rasmli xabar
                    new_caption = f"❌ RAD ETILDI\n\n{message.caption}"
                    await bot.edit_message_caption(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        caption=new_caption,
                        reply_markup=None
                    )
            except Exception as e:
                print(f"Xabarni yangilash xatosi: {e}")
            
            await callback_query.answer("❌ Yoqilg'i rad etildi", show_alert=True)
            
            # Admin ga xabar berish
            admin_text = (
                f"❌ *Xabar Rad Etildi*\n\n"
                f"🏢 Guruh: {fuel_message.group_name}\n"
                f"👤 Foydalanuvchi: {user.full_name}\n"
                f"🆔 ID: {user.id}\n"
                f"⏰ Vaqt: {callback_query.message.date.strftime('%Y-%m-%d %H:%M')}"
            )
            
            await bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode='Markdown')
            
    except Exception as e:
        await callback_query.answer("❌ Xatolik yuz berdi", show_alert=True)
        logging.error(f"Callback xatosi: {e}")

# Monitoring funksiyasi
async def check_pending_messages():
    """Tasdiqlanmagan xabarlarni tekshirish"""
    while True:
        try:
            pending_messages = await get_expired_pending_messages()
            
            if pending_messages:
                message_text = "🚨 *5 KUNLIK MONITORING HISOBOTI*\n\n"
                message_text += f"⏰ Sana: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                message_text += f"📊 Tasdiqlanmagan xabarlar soni: {len(pending_messages)}\n\n"
                
                for i, msg in enumerate(pending_messages, 1):
                    days_passed = msg.days_passed()
                    message_text += f"{i}. 🏢 *Guruh:* {msg.group_name}\n"
                    message_text += f"   📅 *Sana:* {msg.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    message_text += f"   ⏳ *Kunlar:* {days_passed} kun\n"
                    message_text += f"   🔗 *Xabar ID:* {msg.message_id}\n\n"
                
                message_text += "⚠️ *Eslatma:* Guruh adminlariga xabar bering!"
                
                await bot.send_message(
                    ADMIN_CHAT_ID,
                    message_text,
                    parse_mode='Markdown'
                )
                
                print(f"✅ Monitoring hisoboti yuborildi: {len(pending_messages)} xabar")
            else:
                print("✅ Tasdiqlanmagan xabarlar topilmadi")
            
            # 24 soat kutish
            await asyncio.sleep(5)  # 24 soat
            
        except Exception as e:
            print(f"❌ Monitoring xatosi: {e}")
            await asyncio.sleep(3600)  # 1 soat kutish

# Botni ishga tushirish
async def main():
    print("🤖 Bot ishga tushmoqda...")
    
    # Bot haqida ma'lumot olish
    bot_info = await bot.get_me()
    print(f"Bot: @{bot_info.username} - {bot_info.full_name}")
    
    # Monitoringni background da ishga tushirish
    asyncio.create_task(check_pending_messages())
    
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Django timezone import
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
    except Exception as e:
        print(f"Bot xatosi: {e}")