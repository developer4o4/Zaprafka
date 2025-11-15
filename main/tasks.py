# your_app/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import requests
import json
from .models import FuelMessage

@shared_task
def send_monitoring_report():
    """Tasdiqlanmagan xabarlarni tekshirish"""
    bot_token = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'
    admin_chat_id = '6094051871'
    
    five_days_ago = timezone.now() - timedelta(days=5)
    pending_messages = FuelMessage.objects.filter(
        status=FuelMessage.STATUS_PENDING,
        created_at__lte=five_days_ago
    )
    
    if pending_messages.exists():
        message_text = "🚨 *5 KUNLIK MONITORING HISOBOTI*\n\n"
        message_text += f"⏰ Sana: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
        message_text += f"📊 Tasdiqlanmagan xabarlar soni: {pending_messages.count()}\n\n"
        
        for msg in pending_messages:
            days_passed = msg.days_passed()
            message_text += f"🏢 *Guruh:* {msg.group_name}\n"
            message_text += f"📅 *Yuborilgan sana:* {msg.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            message_text += f"⏳ *O'tgan kunlar:* {days_passed} kun\n"
            message_text += f"🔗 *Xabar ID:* {msg.message_id}\n"
            message_text += "─" * 30 + "\n\n"
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': admin_chat_id,
            'text': message_text,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, json=payload)
            return f"Hisobot yuborildi: {pending_messages.count()} xabar"
        except Exception as e:
            return f"Xatolik: {e}"
    
    return "Tasdiqlanmagan xabarlar topilmadi"