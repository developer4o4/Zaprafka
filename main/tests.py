import requests

def test_bot():
    bot_token = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'
    
    # 1. Bot ma'lumotlarini olish
    bot_info_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    bot_response = requests.get(bot_info_url)
    print("Bot info:", bot_response.json())
    
    # 2. Oxirgi yangilanishlarni olish
    updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    updates_response = requests.get(updates_url)
    print("Updates:", updates_response.json())
    
    # 3. Test xabar yuborish
    test_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Birinchi shaxsiy chatga yuborish
    test_payload = {
        'chat_id': "1006094051871",  # Sizning chat_id
        'text': "Bu test xabar"
    }
    
    test_response = requests.post(test_url, data=test_payload)
    print("Test response:", test_response.status_code, test_response.json())

test_bot() 