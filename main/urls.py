from django.urls import path
from . import views


urlpatterns = [
    # ==================== AUTHENTICATION URLs ====================
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==================== DASHBOARD URLs ====================
    path('home/', views.home, name='home'),
    path('home-worker/', views.home_worker, name='home_worker'),
    
    # ==================== ADMIN PANEL URLs ====================
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('add-user/', views.add_user, name='add_user'),
    path('user-delete/<int:pk>/', views.user_delete, name='user_delete'),
    
    # ==================== TASHKILOT CRUD URLs ====================
    path('add-tashkilot/', views.add_tashkilot, name='add_tashkilot'),
    path('tashkilot-edit/<int:pk>/', views.tashkilot_edit, name='tashkilot_edit'),
    path('tashkilot-delete/<int:pk>/', views.tashkilot_delete, name='tashkilot_delete'),
    
    # ==================== AVTO CRUD URLs ====================
    path('add-avto/', views.add_avto, name='add_avto'),
    path('avto-edit/<int:pk>/', views.avto_edit, name='avto_edit'),
    path('avto-delete/<int:pk>/', views.avto_delete, name='avto_delete'),
    
    # ==================== YOQILGI CRUD URLs ====================
    path('add-yoqilgi/', views.add_yoqilgi, name='add_yoqilgi'),
    path('yoqilgi-turi-edit/<int:pk>/', views.yoqilgi_turi_edit, name='yoqilgi_turi_edit'),
    path('yoqilgi-turi-delete/<int:pk>/', views.yoqilgi_turi_delete, name='yoqilgi_turi_delete'),
    
    # ==================== FUEL OPERATION URLs ====================
    path('yoqilgi-quyish/', views.yoqilgi_quyish, name='yoqilgi_quyish'),
    path('add-fuel/', views.add_fuel, name='add_fuel'),
    path('bugungi-yoqilgilar/', views.bugungi_yoqilgilar, name='bugungi_yoqilgilar'),
    
    # ==================== STATISTICS & REPORTS URLs ====================
    path('statistics/', views.statistics_view, name='statistics'),
    path('api/statistics/', views.get_statistics_data_all, name='get_statistics_data_all'),
    path('api/filter-options/', views.get_filter_options, name='get_filter_options'),
    
    # ==================== EXPORT URLs ====================
    path('export-statistics-excel/', views.export_statistics_excel, name='export_statistics_excel'),
    path('export-today-excel/', views.export_today_excel, name='export_today_excel'),
    
    # ==================== API ENDPOINT URLs ====================
    path('api/today-fuel/', views.get_today_fuel_api, name='get_today_fuel_api'),
    path('api/avtomobillar/', views.get_avtomobillar_api, name='get_avtomobillar_api'),
    path('api/today-report/', views.today_report_api, name='today_report_api'),
    path('api/umumiy-statistika/', views.umumiy_statistika_api, name='umumiy_statistika_api'),
    path('api/kunlik-hisobot/', views.kunlik_hisobot_api, name='kunlik_hisobot_api'),
    
    # ==================== TELEGRAM INTEGRATION URLs ====================
    path('end-day/', views.end_day_api, name='end_day_api'),
    path('add-fuel/', views.add_fuel, name='add_fuel'),
    path('send-telegram/', views.send_telegram, name='send_telegram'),
    path('telegram-callback/', views.handle_telegram_callback, name='telegram_callback'),
    # ==================== WORKER SPECIFIC URLs ====================
    path('add-tashkilot-worker/', views.add_tashkilot_worker, name='add_tashkilot_worker'),
    path('add-avto-worker/', views.add_avto_worker, name='add_avto_worker'),
    
    # ==================== WAREHOUSE MANAGEMENT URLs ====================
    path('ombor-list/', views.ombor_list, name='ombor_list'),
    path('add-ombor/', views.add_ombor, name='add_ombor'),
    path('ombor-tarix/<int:ombor_id>/', views.ombor_tarix, name='ombor_tarix'),
    path('ombor-miqdor-oshirish/<int:ombor_id>/', views.ombor_miqdor_oshirish, name='ombor_miqdor_oshirish'),
    path('ombor-statistika/', views.ombor_statistika, name='ombor_statistika'),

    # ==================== TASHKILOT STATISTIKA URLs ====================
    path('tashkilotlar-roxyati/', views.tashkilotlar_roxyati, name='tashkilotlar_roxyati'),
    path('tashkilot-detail/<int:tashkilot_id>/', views.tashkilot_detail, name='tashkilot_detail'),
    path('api/tashkilot-stats/', views.get_tashkilot_stats_api, name='get_tashkilot_stats_api'),

    # ==================== TASHKILOT BALANS URLs ====================
    path('tashkilotlar-balans/', views.tashkilotlar_balans, name='tashkilotlar_balans'),
    path('tashkilot-balans/<int:tashkilot_id>/', views.tashkilot_balans, name='tashkilot_balans'),
    path('tashkilot-balans-qoshish/<int:tashkilot_id>/', views.tashkilot_balans_qoshish, name='tashkilot_balans_qoshish'),
    path('qarzdor-tashkilotlar/', views.qarzdor_tashkilotlar, name='qarzdor_tashkilotlar'),
    path('tashkilot-qarz-tarix/<int:tashkilot_id>/', views.tashkilot_qarz_tarix, name='tashkilot_qarz_tarix'),
    # ==================== ERROR HANDLING ====================
    path('404/', views.custom_404_view, name='custom_404'),
]