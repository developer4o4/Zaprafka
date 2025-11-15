from decimal import Decimal
import json
import base64
import calendar
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Max, Min
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, ExtractHour
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
import requests

from .models import *
from .forms import TashkilotForm, AvtoForm, YoqilgiTuriForm

# Telegram bot tokeni
TELEGRAM_BOT_TOKEN = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'

# ==================== AUTHENTICATION VIEWS ====================

def login_view(request):
    """Foydalanuvchi tizimga kirishi"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_panel')
            return redirect("home")
        else:
            return render(request, "login.html", {"error": "Login yoki parol noto'g'ri!"})
    
    return render(request, "login.html")

@login_required
def logout_view(request):
    """Foydalanuvchi tizimdan chiqishi"""
    logout(request)
    return redirect("login")

# ==================== DASHBOARD VIEWS ====================

@login_required
def home(request):
    """Bosh sahifa - foydalanuvchi turiga qarab sahifani ko'rsatish"""
    if request.user.is_superuser:
        return redirect('admin_panel')
    return home_worker(request)

@login_required
def home_worker(request):
    """Oddiy ishchi uchun bosh sahifa"""
    try:
        today = timezone.now().date()
        today_records = Compilated.objects.filter(created_ad__date=today)
        
        # Statistik ma'lumotlar
        stats = today_records.aggregate(
            total_fuel=Sum('hajm'),
            total_count=Count('id')
        )
        
        total_fuel = stats['total_fuel'] or 0
        total_count = stats['total_count'] or 0
        active_cars = today_records.values('avto').distinct().count()
        avg_fuel = round(total_fuel / active_cars, 1) if active_cars > 0 else 0
        
        # So'nggi faoliyat
        recent_activities = today_records.select_related('tashkilot', 'avto').order_by('-created_ad')[:5]
        
        context = {
            'total_fuel': round(total_fuel, 1),
            'total_count': total_count,
            'active_cars': active_cars,
            'avg_fuel': avg_fuel,
            'recent_activities': [
                {
                    'avto_title': activity.avto.title if activity.avto else 'Noma\'lum',
                    'avto_number': activity.avto.avto_number if activity.avto else '',
                    'tashkilot_title': activity.tashkilot.title if activity.tashkilot else 'Noma\'lum',
                    'hajm': activity.hajm,
                    'time': activity.created_ad.strftime('%H:%M')
                } for activity in recent_activities
            ],
            'tashkilotlar': Tashkilot.objects.all(),
        }
        
        return render(request, 'home.html', context)
        
    except Exception as e:
        context = {
            'total_fuel': 0,
            'total_count': 0,
            'active_cars': 0,
            'avg_fuel': 0,
            'recent_activities': [],
            'tashkilotlar': Tashkilot.objects.all(),
        }
        return render(request, 'home.html', context)

# ==================== ADMIN PANEL VIEWS ====================

@login_required
def admin_panel(request):
    """Admin panel sahifasi"""
    if not request.user.is_superuser:
        messages.error(request, "Sizda admin panelga kirish huquqi yo'q!")
        return redirect('home')
    
    context = {
        "users": User.objects.filter(is_superuser=False),
        'tashkilotlar': Tashkilot.objects.all(),
        'avto_list': Avto.objects.select_related('tashkilot').all(),
        "avtos": Avto.objects.all(),
        'yoqilgilar': Yoqilgi_turi.objects.all(),
    }
    return render(request, 'admin.html', context)

@login_required
def add_user(request):
    """Yangi foydalanuvchi qo'shish"""
    if not request.user.is_superuser:
        messages.error(request, "Sizda foydalanuvchi yaratish huquqi yo'q!")
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        phone = request.POST.get('tel')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, "Foydalanuvchi nomi va parol to'ldirilishi shart!")
            return render(request, "add_user.html")
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Bu foydalanuvchi nomi allaqachon mavjud!")
            return render(request, "add_user.html")
        
        try:
            user = User.objects.create_user(
                username=username, 
                phone=phone, 
                password=password
            )
            user.is_staff = False
            user.is_superuser = False
            user.save()
            
            messages.success(request, f"✅ {username} foydalanuvchisi muvaffaqiyatli yaratildi!")
            return redirect('admin_panel')
            
        except Exception as e:
            messages.error(request, f"Foydalanuvchi yaratishda xatolik: {str(e)}")
    
    return render(request, "add_user.html")

@login_required
def user_delete(request, pk):
    """Foydalanuvchini o'chirish"""
    if not request.user.is_superuser:
        messages.error(request, "Sizda bu amalni bajarish huquqi yo'q!")
        return redirect('home')
    
    user_to_delete = get_object_or_404(User, pk=pk)
    
    # O'zini o'chirishni oldini olish
    if request.user == user_to_delete:
        messages.error(request, 'Siz o\'zingizni o\'chira olmaysiz!')
        return redirect('admin_panel')
    
    if request.method == 'POST':
        try:
            username = user_to_delete.username
            user_to_delete.delete()
            messages.success(request, f'Foydalanuvchi "{username}" muvaffaqiyatli o\'chirildi!')
        except Exception as e:
            messages.error(request, f'Foydalanuvchini o\'chirishda xatolik: {str(e)}')
        
        return redirect('admin_panel')
    
    context = {'user_to_delete': user_to_delete}
    return render(request, 'user_delete.html', context)

# ==================== CRUD OPERATIONS ====================

# Tashkilot CRUD
@login_required
def add_tashkilot(request):
    """Yangi tashkilot qo'shish"""
    if request.method == "POST":
        title = request.POST.get("title")
        group_id = request.POST.get("group_id", 4885110792)
        
        if title:
            Tashkilot.objects.create(title=title, group_id=group_id)
            messages.success(request, f"✅ {title} tashkiloti muvaffaqiyatli qo'shildi!")
            return redirect("admin_panel")
        else:
            messages.error(request, "Tashkilot nomini kiriting!")
    
    return render(request, "add_tashkilot.html")

@login_required
def tashkilot_edit(request, pk):
    """Tashkilotni tahrirlash"""
    tashkilot = get_object_or_404(Tashkilot, pk=pk)
    
    if request.method == 'POST':
        form = TashkilotForm(request.POST, instance=tashkilot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tashkilot muvaffaqiyatli yangilandi!')
            return redirect('admin_panel')
    else:
        form = TashkilotForm(instance=tashkilot)
    
    return render(request, 'tashkilot_edit.html', {'form': form})

@login_required
def tashkilot_delete(request, pk):
    """Tashkilotni o'chirish"""
    tashkilot = get_object_or_404(Tashkilot, pk=pk)
    
    if request.method == 'POST':
        tashkilot.delete()
        messages.success(request, 'Tashkilot muvaffaqiyatli o\'chirildi!')
        return redirect('admin_panel')
    
    return render(request, 'tashkilot_delete.html', {'tashkilot': tashkilot})

# Avto CRUD
@login_required
def add_avto(request):
    """Yangi avtomobil qo'shish"""
    tashkilotlar = Tashkilot.objects.all()
    
    if request.method == 'POST':
        title = request.POST.get('title')
        avto_number = request.POST.get('avto_number')
        tashkilot_id = request.POST.get('tashkilot_id')
        
        tashkilot = get_object_or_404(Tashkilot, id=tashkilot_id)
        
        Avto.objects.create(
            title=title,
            avto_number=avto_number,
            tashkilot=tashkilot
        )
        
        messages.success(request, f"✅ {title} avtomobili muvaffaqiyatli qo'shildi!")
        return redirect('admin_panel')
    
    return render(request, 'admin.html', {'tashkilotlar': tashkilotlar})

@login_required
def avto_edit(request, pk):
    """Avtomobilni tahrirlash"""
    avto = get_object_or_404(Avto, pk=pk)
    tashkilotlar = Tashkilot.objects.all()
    
    if request.method == 'POST':
        form = AvtoForm(request.POST, instance=avto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Avtomobil muvaffaqiyatli yangilandi!')
            return redirect('admin_panel')
    else:
        form = AvtoForm(instance=avto)
    
    return render(request, 'avto_edit.html', {
        'form': form,
        "tashkilotlar": tashkilotlar
    })

@login_required
def avto_delete(request, pk):
    """Avtomobilni o'chirish"""
    avto = get_object_or_404(Avto, pk=pk)
    
    if request.method == 'POST':
        avto.delete()
        messages.success(request, 'Avtomobil muvaffaqiyatli o\'chirildi!')
        return redirect('admin_panel')
    
    return render(request, 'avto_delete.html', {'avto': avto})

# Yoqilgi CRUD
@login_required
def add_yoqilgi(request):
    """Yangi yoqilg'i turi qo'shish"""
    if request.method == "POST":
        title = request.POST.get("title")
        price = request.POST.get("price", 0)
        
        if title:
            Yoqilgi_turi.objects.create(title=title, price=price)
            messages.success(request, f"✅ {title} yoqilg'i turi muvaffaqiyatli qo'shildi!")
            return redirect("admin_panel")
        else:
            messages.error(request, "Yoqilg'i nomini kiriting!")
    
    return render(request, "add_yoqilgi.html")

@login_required
def yoqilgi_turi_edit(request, pk):
    """Yoqilg'i turini tahrirlash"""
    yoqilgi = get_object_or_404(Yoqilgi_turi, pk=pk)
    
    if request.method == 'POST':
        form = YoqilgiTuriForm(request.POST, instance=yoqilgi)
        if form.is_valid():
            form.save()
            messages.success(request, 'Yoqilg\'i turi muvaffaqiyatli yangilandi!')
            return redirect('admin_panel')
    else:
        form = YoqilgiTuriForm(instance=yoqilgi)
    
    return render(request, 'yoqilgi_turi_edit.html', {'form': form})

@login_required
def yoqilgi_turi_delete(request, pk):
    """Yoqilg'i turini o'chirish"""
    yoqilgi = get_object_or_404(Yoqilgi_turi, pk=pk)
    
    if request.method == 'POST':
        yoqilgi.delete()
        messages.success(request, 'Yoqilg\'i turi muvaffaqiyatli o\'chirildi!')
        return redirect('admin_panel')
    
    return render(request, 'yoqilgi_turi_delete.html', {'yoqilgi_turi': yoqilgi})

# ==================== FUEL OPERATIONS ====================

@login_required
def yoqilgi_quyish(request):
    """Yoqilg'i quyish sahifasi"""
    context = {
        'tashkilotlar': Tashkilot.objects.all(),
        'yoqilgi_turlari': Yoqilgi_turi.objects.all(),
    }
    return render(request, 'yoqilgi_quyish.html', context)

@login_required
def add_fuel(request):
    """Yoqilg'i qo'shish"""
    if request.method == 'POST':
        try:
            # Ma'lumotlarni olish
            tashkilot_id = request.POST.get('tashkilot')
            avto_id = request.POST.get('avtomobile')
            yoqilgi_id = request.POST.get('yoqilgi')
            miqdor = float(request.POST.get('miqdor', 0))
            all_price = Decimal(request.POST.get('all_price', 0))
            captured_image = request.POST.get('captured_image')
            confirmation_photo = request.POST.get('confirmation_photo')
            
            # Yoqilg'i turini olish
            yoqilgi_obj = get_object_or_404(Yoqilgi_turi, id=yoqilgi_id)
            
            # Rasmni saqlash funksiyasi
            def save_base64_image(base64_string, filename):
                if base64_string and base64_string != '':
                    try:
                        format, imgstr = base64_string.split(';base64,')
                        ext = format.split('/')[-1]
                        data = ContentFile(base64.b64decode(imgstr), name=f'{filename}.{ext}')
                        return data
                    except Exception as e:
                        print(f"Rasm saqlash xatosi: {e}")
                        return None
                return None
            
            # Ma'lumotlarni saqlash
            compilated = Compilated(
                tashkilot_id=tashkilot_id,
                avto_id=avto_id,
                yoqilgi_turi=yoqilgi_obj.title,
                who_user=request.user,
                hajm=miqdor,
                all_price=all_price,
            )
            
            # Rasmlarni saqlash
            timestamp = int(timezone.now().timestamp())
            process_photo_file = save_base64_image(
                captured_image, 
                f'process_{request.user.id}_{timestamp}'
            )
            process_photo_file_2 = save_base64_image(
                confirmation_photo, 
                f'confirmation_{request.user.id}_{timestamp}'
            )
            
            if process_photo_file:
                compilated.photo = process_photo_file
            if process_photo_file_2:
                compilated.photo_2 = process_photo_file_2
            
            compilated.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Xatolik: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET so'rovi uchun
    context = {
        'tashkilotlar': Tashkilot.objects.all(),
        'yoqilgi_turlari': Yoqilgi_turi.objects.all(),
    }
    return render(request, 'add_fuel.html', context)

@login_required
def bugungi_yoqilgilar(request):
    """Bugungi yoqilg'ilar sahifasi"""
    context = {
        'tashkilotlar': Tashkilot.objects.all(),
        'yoqilgi_turlari': Yoqilgi_turi.objects.all(),
    }
    return render(request, 'bugungi_yoqilgilar.html', context)

# ==================== STATISTICS & REPORTS ====================

@login_required
def statistics_view(request):
    """Statistika sahifasi"""
    # Oylar ro'yxati
    months = [
        {'number': i, 'name': calendar.month_name[i]} 
        for i in range(1, 13)
    ]
    
    # Joriy yil va oy
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # URL parametrlari
    selected_year = request.GET.get('year', current_year)
    selected_month = request.GET.get('month', current_month)
    
    try:
        selected_year = int(selected_year)
        selected_month = int(selected_month)
    except (ValueError, TypeError):
        selected_year = current_year
        selected_month = current_month
    
    # Tanlangan oy va yil bo'yicha filtrlash
    start_date = timezone.make_aware(datetime(selected_year, selected_month, 1))
    
    if selected_month == 12:
        next_month = timezone.make_aware(datetime(selected_year + 1, 1, 1))
    else:
        next_month = timezone.make_aware(datetime(selected_year, selected_month + 1, 1))
    
    end_date = next_month - timedelta(days=1)
    
    # Asosiy statistik ma'lumotlar
    compilated_data = Compilated.objects.filter(
        created_ad__gte=start_date,
        created_ad__lte=end_date
    )
    
    # Umumiy statistika
    total_records = compilated_data.count()
    total_hajm = compilated_data.aggregate(Sum('hajm'))['hajm__sum'] or 0
    total_price = compilated_data.aggregate(Sum('all_price'))['all_price__sum'] or 0
    
    # Turlicha statistikalar
    tashkilot_stats = compilated_data.values('tashkilot__title').annotate(
        total_hajm=Sum('hajm'), total_price=Sum('all_price'), count=Count('id')
    ).order_by('-total_hajm')
    
    avto_stats = compilated_data.values('avto__title', 'avto__avto_number').annotate(
        total_hajm=Sum('hajm'), total_price=Sum('all_price'), count=Count('id')
    ).order_by('-total_hajm')
    
    yoqilgi_stats = compilated_data.values('yoqilgi_turi').annotate(
        total_hajm=Sum('hajm'), total_price=Sum('all_price'), count=Count('id')
    ).order_by('-total_hajm')
    
    daily_stats = compilated_data.extra({'day': "date(created_ad)"}).values('day').annotate(
        daily_hajm=Sum('hajm'), daily_price=Sum('all_price'), daily_count=Count('id')
    ).order_by('day')
    excel_years = range(current_year - 5, current_year + 1)
    
    context = {
        'months': months,
        'selected_year': selected_year,
        'selected_month': selected_month,
        "excel_years":excel_years,
        'current_year': current_year,
        'total_records': total_records,
        'total_hajm': total_hajm,
        'total_price': total_price,
        'tashkilot_stats': tashkilot_stats,
        'avto_stats': avto_stats,
        'yoqilgi_stats': yoqilgi_stats,
        'daily_stats': daily_stats,
        'month_name': calendar.month_name[selected_month],
    }
    
    return render(request, 'stats.html', context)

@login_required
def get_statistics_data_all(request):
    """Statistika ma'lumotlarini JSON formatida qaytarish"""
    try:
        # Filtrlarni olish
        period = request.GET.get('period', '30')
        tashkilot_id = request.GET.get('tashkilot', 'all')
        yoqilgi_id = request.GET.get('yoqilgi', 'all')
        detail_period = request.GET.get('detail_period', 'daily')
        
        # Periodni tekshirish
        try:
            period_days = int(period)
            if period_days <= 0:
                period_days = 30
        except (ValueError, TypeError):
            period_days = 30
        
        # Sana oralig'ini belgilash
        end_date = timezone.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Compilated ma'lumotlarini filtrlash
        compilated_data = Compilated.objects.filter(
            created_ad__gte=start_date,
            created_ad__lte=end_date
        )
        
        # Qo'shimcha filtrlash
        if tashkilot_id != 'all':
            try:
                compilated_data = compilated_data.filter(tashkilot_id=int(tashkilot_id))
            except (ValueError, TypeError):
                pass
        
        if yoqilgi_id != 'all':
            try:
                compilated_data = compilated_data.filter(yoqilgi_turi_id=int(yoqilgi_id))
            except (ValueError, TypeError):
                pass
        
        # Ma'lumotlar mavjudligini tekshirish
        if not compilated_data.exists():
            return JsonResponse({
                'success': True,
                'summary': get_empty_summary(),
                'tashkilot_stats': [],
                'avto_stats': [],
                'daily_stats': [],
                'monthly_stats': [],
                'weekly_stats': [],
                'detailed_stats': [],
                'recent_records': []
            })
        
        # Umumiy statistik ma'lumotlar
        aggregates = compilated_data.aggregate(
            total=Sum('hajm'), avg=Avg('hajm'), max=Max('hajm'),
            min=Min('hajm'), count=Count('id')
        )
        
        total_fuel = aggregates['total'] or 0
        avg_daily = total_fuel / period_days if period_days > 0 else 0
        max_fuel = aggregates['max'] or 0
        min_fuel = aggregates['min'] or 0
        active_cars = compilated_data.values('avto').distinct().count()
        total_records = aggregates['count'] or 0
        
        # Turlicha statistikalar
        tashkilot_stats = get_tashkilot_stats(compilated_data)
        avto_stats = get_avto_stats(compilated_data)
        daily_stats = get_daily_stats(compilated_data)
        monthly_stats = get_monthly_stats(compilated_data)
        weekly_stats = get_weekly_stats(compilated_data)
        detailed_stats = get_detailed_stats(compilated_data, detail_period)
        recent_records = get_recent_records(compilated_data, request)
        
        response_data = {
            'success': True,
            'summary': {
                'total_fuel': round(float(total_fuel), 1),
                'avg_daily': round(float(avg_daily), 1),
                'max_fuel': round(float(max_fuel), 1),
                'min_fuel': round(float(min_fuel), 1),
                'active_cars': active_cars,
                'total_records': total_records,
                'period_days': period_days
            },
            'tashkilot_stats': tashkilot_stats,
            'avto_stats': avto_stats,
            'daily_stats': daily_stats,
            'monthly_stats': monthly_stats,
            'weekly_stats': weekly_stats,
            'detailed_stats': detailed_stats,
            'recent_records': recent_records
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            **get_empty_response()
        }, status=500)

# ==================== API ENDPOINTS ====================

@login_required
def get_today_fuel_api(request):
    """Bugungi yoqilg'ilarni olish API"""
    today = date.today()
    
    # Filtrlarni olish
    tashkilot_id = request.GET.get('tashkilot_id')
    avto_id = request.GET.get('avto_id')
    
    # Bugungi ma'lumotlarni olish
    compilated_data = Compilated.objects.filter(created_ad__date=today)
    
    # Filtrlash
    if tashkilot_id and tashkilot_id != 'all':
        compilated_data = compilated_data.filter(tashkilot_id=tashkilot_id)
    
    if avto_id and avto_id != 'all':
        compilated_data = compilated_data.filter(avto_id=avto_id)
    
    # Ma'lumotlarni tayyorlash
    records = []
    for record in compilated_data.select_related('tashkilot', 'avto', 'who_user'):
        records.append({
            'tashkilot_title': record.tashkilot.title,
            'avto_title': record.avto.title,
            'avto_number': record.avto.avto_number,
            'yoqilgi_turi': record.yoqilgi_turi,
            'hajm': record.hajm,
            'created_ad': record.created_ad.isoformat(),
            'user_name': record.who_user.username
        })
    
    # Statistik ma'lumotlar
    total_fuel = sum(record.hajm for record in compilated_data)
    
    response_data = {
        'summary': {
            'total_fuel': round(total_fuel, 1),
            'total_records': compilated_data.count(),
            'total_tashkilot': compilated_data.values('tashkilot').distinct().count(),
            'total_avto': compilated_data.values('avto').distinct().count()
        },
        'records': records
    }
    
    return JsonResponse(response_data)

@login_required
def get_avtomobillar_api(request):
    """Tashkilot bo'yicha avtomobillarni olish API"""
    tashkilot_id = request.GET.get('tashkilot_id')
    
    if tashkilot_id:
        avtomobillar = Avto.objects.filter(tashkilot_id=tashkilot_id)
    else:
        avtomobillar = Avto.objects.all()
    
    avto_list = [
        {
            'id': avto.id,
            'title': avto.title,
            'avto_number': avto.avto_number
        } for avto in avtomobillar
    ]
    
    return JsonResponse(avto_list, safe=False)

@login_required
def get_filter_options(request):
    """Filtrlash uchun variantlarni qaytarish"""
    try:
        response_data = {
            'success': True,
            'tashkilotlar': list(Tashkilot.objects.all().values('id', 'title').order_by('title')),
            'yoqilgi_turlari': list(Yoqilgi_turi.objects.all().values('id', 'title').order_by('title')),
            'avtomobillar': list(Avto.objects.select_related('tashkilot').values(
                'id', 'title', 'avto_number', 'tashkilot_id'
            ).order_by('title'))
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'tashkilotlar': [],
            'yoqilgi_turlari': [],
            'avtomobillar': []
        }, status=500)

# ==================== EXPORT FUNCTIONS ====================

@login_required
def export_statistics_excel(request):
    """Statistika ma'lumotlarini Excel fayl sifatida eksport qilish"""
    try:
        # URL parametrlarini olish
        year = request.GET.get('year')
        month = request.GET.get('month')
        
        # Filtrlash
        compilated_data = Compilated.objects.all()
        
        # Agar yil va oy tanlangan bo'lsa
        if year and month:
            try:
                year = int(year)
                month = int(month)
                start_date = timezone.make_aware(datetime(year, month, 1))
                
                if month == 12:
                    next_month = timezone.make_aware(datetime(year + 1, 1, 1))
                else:
                    next_month = timezone.make_aware(datetime(year, month + 1, 1))
                
                end_date = next_month - timedelta(days=1)
                
                compilated_data = compilated_data.filter(
                    created_ad__gte=start_date,
                    created_ad__lte=end_date
                )
                
                file_name = f"statistika_{year}_{month:02d}.xlsx"
                
            except (ValueError, TypeError):
                file_name = "barcha_statistika.xlsx"
        else:
            file_name = "barcha_statistika.xlsx"
        
        # Excel fayl yaratish
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        # Ma'lumotlarni tayyorlash
        data_list = []
        for record in compilated_data.select_related('tashkilot', 'avto', 'who_user'):
            data_list.append({
                'Sana': record.created_ad.strftime('%Y-%m-%d %H:%M'),
                'Tashkilot': record.tashkilot.title if record.tashkilot else '',
                'Avtomobil': record.avto.title if record.avto else '',
                'Avtomobil raqami': record.avto.avto_number if record.avto else '',
                'Yoqilg\'i turi': record.yoqilgi_turi,
                'Miqdor (L)': float(record.hajm) if record.hajm else 0,
                'Jami narx': float(record.all_price) if record.all_price else 0,
                'Foydalanuvchi': record.who_user.username if record.who_user else '',
            })
        
        df = pd.DataFrame(data_list)
        
        # Excel faylini yaratish
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            # Asosiy ma'lumotlar
            if not df.empty:
                df.to_excel(writer, sheet_name='Yoqilg\'i Quyishlar', index=False)
            
            # Statistika jadvali
            summary_data = create_summary_data(compilated_data, year, month)
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Statistika', index=False)
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })

@login_required
def export_today_excel(request):
    """Bugungi ma'lumotlarni Excel faylga eksport qilish"""
    try:
        today = timezone.now().date()
        
        # Filtrlarni olish
        tashkilot_id = request.GET.get('tashkilot_id', 'all')
        
        # Bugungi ma'lumotlarni olish
        compilated_data = Compilated.objects.filter(created_ad__date=today)
        
        if tashkilot_id != 'all':
            compilated_data = compilated_data.filter(tashkilot_id=tashkilot_id)
        
        # Excel fayl yaratish
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Bugungi barcha yozuvlar
            main_data = []
            for record in compilated_data.select_related('tashkilot', 'avto', 'who_user').order_by('-created_ad'):
                main_data.append({
                    'Vaqt': record.created_ad.strftime('%H:%M'),
                    'Tashkilot': record.tashkilot.title,
                    'Avtomobil': record.avto.title,
                    'Avtomobil Raqami': record.avto.avto_number,
                    'Yoqilgʻi Turi': record.yoqilgi_turi,
                    'Yoqilgʻi Miqdori (L)': record.hajm,
                    'Foydalanuvchi': record.who_user.username,
                    'Rasm Fayli': record.photo.name if record.photo else 'Mavjud emas'
                })
            
            df_main = pd.DataFrame(main_data)
            df_main.to_excel(writer, sheet_name="Bugungi Maʼlumotlar", index=False)
            
            # Bugungi statistika
            stats_data = create_today_stats(compilated_data, today)
            df_stats = pd.DataFrame(stats_data)
            df_stats.to_excel(writer, sheet_name='Bugungi Statistika', index=False)
        
        # HTTP response yaratish
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f"bugungi_yoqilgi_{today.strftime('%Y%m%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ==================== TELEGRAM INTEGRATION ====================
def send_photo_with_caption(bot_token, chat_id, photo_data, caption, reply_markup=None):
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    
    # Base64 rasmni yuborish
    payload = {
        'chat_id': f"-{chat_id}",
        'caption': caption,
        'photo': photo_data
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    response = requests.post(url, json=payload)
    return response.json()

def get_group_name(bot_token, group_id):
    """Guruh nomini olish"""
    try:
        url = f'https://api.telegram.org/bot{bot_token}/getChat'
        payload = {'chat_id': f"-{group_id}"}
        response = requests.post(url, json=payload)
        result = response.json()
        
        if result.get('ok'):
            chat = result['result']
            return chat.get('title', f"Guruh {group_id}")
        return f"Guruh {group_id}"
    except:
        return f"Guruh {group_id}"
import time
@csrf_exempt
def send_telegram(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            group_id = data.get('group_id')
            message = data.get('message')
            process_photo = data.get('process_photo')
            confirmation_photo = data.get('confirmation_photo')
            inline_keyboard = data.get('inline_keyboard')  # INLINE KEYBOARD QABUL QILISH
            fuel_id = data.get('fuel_id')
            # Telegram bot tokeni
            bot_token = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'
            
            # Chat ID ni formatlash
            chat_id = f"-{group_id}"    
            group_name = get_group_name(bot_token, group_id)
            
            # Callback data yaratish
            callback_data = f"fuel_{fuel_id}_{int(time.time())}"
            
            # Inline keyboard yangilash
            if inline_keyboard:
                inline_keyboard['inline_keyboard'][0][0]['callback_data'] = f"confirm_{callback_data}"
                inline_keyboard['inline_keyboard'][0][1]['callback_data'] = f"reject_{callback_data}"
                reply_markup = json.dumps(inline_keyboard)
            else:
                reply_markup = None
            # Agar inline keyboard bo'lsa, uni tayyorlash
            reply_markup = None
            if inline_keyboard:
                reply_markup = json.dumps(inline_keyboard)
            
            # 1. Avval matnli xabarni yuborish (agar rasm bo'lmasa)
            if not process_photo and not confirmation_photo:
                url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                payload = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML',
                    'reply_markup': reply_markup  # INLINE BUTTON QO'SHISH
                }
                
                response = requests.post(url, json=payload)
                print(f"Matn xabari status: {response.status_code}")
                return JsonResponse({'success': True})
            
            # 2. Rasmlarni yuborish
            def create_media_group(photos_data, caption):
                media = []
                
                for i, photo_data in enumerate(photos_data):
                    if photo_data and photo_data != '':
                        try:
                            # Base64 rasmni faylga aylantirish
                            photo_data_clean = photo_data.split(',')[1] if ',' in photo_data else photo_data
                            photo_bytes = base64.b64decode(photo_data_clean)
                            
                            # Fayl nomi
                            file_key = f'photo_{i}'
                            
                            # Har bir rasm uchun media ob'ekt yaratish
                            media_item = {
                                'type': 'photo',
                                'media': f'attach://{file_key}'
                            }
                            
                            # Faqat birinchi rasmga caption qo'shish
                            if i == 0:
                                media_item['caption'] = caption
                                if reply_markup:
                                    media_item['parse_mode'] = 'HTML'
                            
                            media.append(media_item)
                            
                        except Exception as e:
                            print(f"Rasm tayyorlash xatosi: {e}")
                            continue
                
                return media
            
            # Rasmlar ro'yxatini tayyorlash
            photos_data = []
            
            if process_photo and process_photo != '':
                photos_data.append(process_photo)
            
            if confirmation_photo and confirmation_photo != '':
                photos_data.append(confirmation_photo)
            
            # Agar ikkala rasm ham mavjud bo'lsa, albom shaklida yuborish
            if len(photos_data) >= 1:
                if len(photos_data) == 2:
                    print("Ikkita rasm albom shaklida yuborilmoqda...")
                    # Ikkala rasmni albom shaklida yuborish
                    url = f'https://api.telegram.org/bot{bot_token}/sendMediaGroup'
                    
                    media = create_media_group(photos_data, message)
                    files = {}
                    
                    for i, photo_data in enumerate(photos_data):
                        if photo_data and photo_data != '':
                            try:
                                # Base64 rasmni faylga aylantirish
                                photo_data_clean = photo_data.split(',')[1] if ',' in photo_data else photo_data
                                photo_bytes = base64.b64decode(photo_data_clean)
                                
                                # Fayl nomi
                                file_key = f'photo_{i}'
                                files[file_key] = (f'photo_{i}.jpg', photo_bytes, 'image/jpeg')
                                
                            except Exception as e:
                                print(f"Rasm {i} tayyorlash xatosi: {e}")
                                continue
                    
                    if media:
                        payload = {
                            'chat_id': chat_id,
                            'media': json.dumps(media)
                        }
                        
                        response = requests.post(url, data=payload, files=files)
                        print(f"Albom status: {response.status_code}")
                        
                        # Albom yuborilgandan so'ng, alohida xabar yuboramiz
                        if response.status_code == 200 and reply_markup:
                            try:
                                result = response.json()
                                if result.get('ok'):
                                    messages = result.get('result', [])
                                    if messages:
                                        # Oxirgi xabarni olamiz (albomdagi oxirgi rasm)
                                        last_message = messages[-1]
                                        last_message_id = last_message.get('message_id')
                                        
                                        # Albomdan keyin inline buttonli xabar yuboramiz
                                        url_message = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                                        payload_message = {
                                            'chat_id': chat_id,
                                            'text': "📋 Ma'lumotlar to'g'riligini tekshiring:",
                                            'reply_markup': reply_markup,
                                            'reply_to_message_id': last_message_id  # Albomga reply qilish
                                        }
                                        
                                        response_message = requests.post(url_message, json=payload_message)
                                        print(f"Button xabari status: {response_message.status_code}")
                                        
                            except Exception as e:
                                print(f"Button xabar yuborish xatosi: {e}")
                        
                else:
                    # Faqat bitta rasm bo'lsa, oddiy yuborish
                    print("Bitta rasm yuborilmoqda...")
                    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
                    
                    photo_data = photos_data[0]
                    photo_data_clean = photo_data.split(',')[1] if ',' in photo_data else photo_data
                    photo_bytes = base64.b64decode(photo_data_clean)
                    
                    files = {
                        'photo': ('photo.jpg', photo_bytes, 'image/jpeg')
                    }
                    data = {
                        'chat_id': chat_id,
                        'caption': message,
                        'parse_mode': 'HTML',
                        'reply_markup': reply_markup  # INLINE BUTTON QO'SHISH
                    }
                    
                    response = requests.post(url, files=files, data=data)
                    print(f"Bitta rasm status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    message_id = result['result']['message_id']
                    
                    # FuelMessage yaratish
                    fuel_message = FuelMessage.objects.create(
                        group_id=group_id,
                        group_name=group_name,
                        message_id=message_id,
                        fuel_data={
                            'message': message,
                            'fuel_id': fuel_id,
                            'created_at': timezone.now().isoformat()
                        },
                        callback_data=callback_data,
                        status=FuelMessage.STATUS_PENDING
                    )
                    
                    print(f"Xabar saqlandi: {fuel_message.id}")
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Telegram xatosi: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi qabul qilinadi'})

@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("Webhook data:", data)
            
            if 'callback_query' in data:
                callback_query = data['callback_query']
                callback_data = callback_query.get('data')
                message = callback_query.get('message')
                chat_id = message.get('chat', {}).get('id')
                message_id = message.get('message_id')
                
                bot_token = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'
                
                if callback_data.startswith('confirm_'):
                    # Tasdiqlash
                    callback_id = callback_data.replace('confirm_', '')
                    fuel_message = FuelMessage.objects.get(callback_data=callback_id)
                    fuel_message.status = FuelMessage.STATUS_CONFIRMED
                    fuel_message.save()
                    
                    answer_text = "✅ Yoqilg'i ma'lumotlari tasdiqlandi"
                    answer_callback_query(bot_token, callback_query['id'], answer_text)
                    
                    # Xabarni yangilash
                    new_text = "✅ TASDIQLANDI\n\n" + message.get('text', '')
                    edit_message_text(bot_token, chat_id, message_id, new_text, None)
                    
                elif callback_data.startswith('reject_'):
                    # Rad etish
                    callback_id = callback_data.replace('reject_', '')
                    fuel_message = FuelMessage.objects.get(callback_data=callback_id)
                    fuel_message.status = FuelMessage.STATUS_REJECTED
                    fuel_message.save()
                    
                    answer_text = "❌ Yoqilg'i ma'lumotlari rad etildi"
                    answer_callback_query(bot_token, callback_query['id'], answer_text)
                    
                    # Xabarni yangilash
                    new_text = "❌ RAD ETILDI\n\n" + message.get('text', '')
                    edit_message_text(bot_token, chat_id, message_id, new_text, None)
                
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Webhook xatosi: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi'})

def check_pending_messages():
    """Tasdiqlanmagan xabarlarni tekshirish"""
    bot_token = '8384548755:AAE_O3g_2Q971QHNU8eqk3NCo7bxTAZrf9o'
    admin_chat_id = '6094051871'  # Monitoring uchun admin chat ID
    
    # 5 kun o'tgan tasdiqlanmagan xabarlarni topish
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
        
        # Admin ga xabar yuborish
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': admin_chat_id,
            'text': message_text,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"Monitoring hisoboti yuborildi: {pending_messages.count()} xabar")
            else:
                print(f"Xatolik: {response.text}")
        except Exception as e:
            print(f"Monitoring xatosi: {e}")
    
    else:
        print("Tasdiqlanmagan xabarlar topilmadi")
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import requests
import json
# Django management command
class Command(BaseCommand):
    help = 'Check pending fuel messages and send report to admin'
    
    def handle(self, *args, **options):
        check_pending_messages()
        self.stdout.write(
            self.style.SUCCESS('Monitoring bajarildi')
        )

@csrf_exempt
def handle_telegram_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            callback_data = data.get('callback_data')
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')
            
            if callback_data.startswith('confirm_fuel_'):
                # Tasdiqlash logikasi
                return confirm_fuel(request, callback_data, message_id, chat_id)
            elif callback_data.startswith('reject_fuel_'):
                # Rad etish logikasi
                return reject_fuel(request, callback_data, message_id, chat_id)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def confirm_fuel(request, callback_data, message_id, chat_id):
    # Yoqilg'ini tasdiqlash logikasi
    bot_token = 'YOUR_BOT_TOKEN'
    
    # Xabarni yangilash - tasdiqlangan deb belgilash
    edit_message_text(
        bot_token, chat_id, message_id,
        "✅ Yoqilg'i ma'lumotlari tasdiqlandi",
        None  # Inline buttonlarni olib tashlash
    )
    
    return JsonResponse({'success': True})

def reject_fuel(request, callback_data, message_id, chat_id):
    # Yoqilg'ini rad etish logikasi
    bot_token = 'YOUR_BOT_TOKEN'
    
    # Xabarni yangilash - rad etilgan deb belgilash
    edit_message_text(
        bot_token, chat_id, message_id,
        "❌ Yoqilg'i ma'lumotlari rad etildi",
        None  # Inline buttonlarni olib tashlash
    )
    
    return JsonResponse({'success': True})

def edit_message_text(bot_token, chat_id, message_id, text, reply_markup=None):
    url = f'https://api.telegram.org/bot{bot_token}/editMessageText'
    
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    response = requests.post(url, json=payload)
    return response.json()

def send_message_with_keyboard(bot_token, chat_id, text, reply_markup=None):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    response = requests.post(url, json=payload)
    return response.json()
def send_telegram_photos(chat_id, photos_data, caption):
    """Telegramga rasmlarni yuborish"""
    if len(photos_data) == 2:
        # Ikkala rasmni albom shaklida yuborish
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup'
        
        media = []
        files = {}
        
        for i, photo_data in enumerate(photos_data):
            if photo_data and photo_data != '':
                try:
                    photo_data_clean = photo_data.split(',')[1] if ',' in photo_data else photo_data
                    photo_bytes = base64.b64decode(photo_data_clean)
                    
                    file_key = f'photo_{i}'
                    files[file_key] = (f'photo_{i}.jpg', photo_bytes, 'image/jpeg')
                    
                    media_item = {
                        'type': 'photo',
                        'media': f'attach://{file_key}'
                    }
                    
                    if i == 0:
                        media_item['caption'] = caption
                    
                    media.append(media_item)
                    
                except Exception as e:
                    print(f"Rasm {i} tayyorlash xatosi: {e}")
                    continue
        
        if media:
            payload = {
                'chat_id': chat_id,
                'media': json.dumps(media)
            }
            
            requests.post(url, data=payload, files=files)
    else:
        # Faqat bitta rasm bo'lsa
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
        
        photo_data = photos_data[0]
        photo_data_clean = photo_data.split(',')[1] if ',' in photo_data else photo_data
        photo_bytes = base64.b64decode(photo_data_clean)
        
        files = {'photo': ('photo.jpg', photo_bytes, 'image/jpeg')}
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        requests.post(url, files=files, data=data)
def send_message_with_keyboard(bot_token, chat_id, text, reply_markup=None):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    response = requests.post(url, json=payload)
    return response.json()
# ==================== WORKER SPECIFIC FUNCTIONS ====================

@login_required
def add_tashkilot_worker(request):
    """Oddiy ishchi uchun tashkilot qo'shish"""
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            group_id = request.POST.get('group_id', 4885110792)
            
            if not title:
                messages.error(request, 'Tashkilot nomini kiriting!')
                return redirect('home')
            
            Tashkilot.objects.create(title=title, group_id=group_id)
            messages.success(request, f'"{title}" tashkiloti muvaffaqiyatli qo\'shildi!')
            
        except Exception as e:
            messages.error(request, f'Tashkilot qo\'shishda xatolik: {str(e)}')
    
    return redirect('home')

@login_required
def add_avto_worker(request):
    """Oddiy ishchi uchun avtomobil qo'shish"""
    if request.method == 'POST':
        try:
            tashkilot_id = request.POST.get('tashkilot_id')
            title = request.POST.get('title')
            avto_number = request.POST.get('avto_number')
            
            if not all([tashkilot_id, title, avto_number]):
                messages.error(request, 'Barcha maydonlarni to\'ldiring!')
                return redirect('home')
            
            tashkilot = get_object_or_404(Tashkilot, id=tashkilot_id)
            
            Avto.objects.create(
                tashkilot=tashkilot,
                title=title,
                avto_number=avto_number
            )
            
            messages.success(request, f'"{title}" avtomobili muvaffaqiyatli qo\'shildi!')
            
        except Exception as e:
            messages.error(request, f'Avtomobil qo\'shishda xatolik: {str(e)}')
    
    return redirect('home')

# ==================== END OF DAY FUNCTIONS ====================

@csrf_exempt
@require_POST
def end_day_api(request):
    """Kunni yakunlash va hisobotni Telegramga yuborish"""
    try:
        today = date.today()
        now = timezone.now()
        activities = Compilated.objects.filter(created_ad__date=today).select_related('avto', 'tashkilot', 'who_user')
        
        # Telegram xabarini tayyorlash
        message = create_daily_report(activities, today, now, request.user)
        
        # Telegramga xabarni yuborish
        success, result_message = send_telegram_message(message)
        
        # Ma'lumotlarni o'chirish
        deleted_count, _ = activities.delete()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Kun muvaffaqiyatli yakunlandi va hisobot yuborildi',
                'total_activities': activities.count(),
                'deleted_count': deleted_count,
                'telegram_status': 'sent'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': f'Kun yakunlandi, lekin Telegramga yuborishda xatolik: {result_message}',
                'total_activities': activities.count(),
                'deleted_count': deleted_count,
                'telegram_status': 'failed',
                'telegram_error': result_message
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def send_telegram_message(message):
    """Telegramga xabar yuborish"""
    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        if len(message) > 4000:
            message = message[:4000] + "..."
        
        payload = {
            'chat_id': "352987963",
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(telegram_url, data=payload, timeout=10)
        
        if response.status_code == 200:
            return True, "Xabar muvaffaqiyatli yuborildi"
        else:
            return False, f"Telegram xatosi: {response.status_code}"
            
    except Exception as e:
        return False, f"Xabar yuborishda xatolik: {str(e)}"

def create_daily_report(activities, today, now, user):
    """Kunlik hisobot matnini yaratish"""
    message = f"📊 *Kunlik Yoqilg'i Hisoboti* 📊\n"
    message += f"📅 *Sana:* {today.strftime('%Y-%m-%d')}\n"
    message += f"⏰ *Yakunlangan vaqt:* {now.strftime('%H:%M')}\n"
    message += f"👤 *Yakunlovchi:* {user.get_full_name() or user.username}\n\n"
    
    total_fuel = 0
    total_price = 0
    activity_count = activities.count()
    
    if activity_count > 0:
        # Tashkilotlar bo'yicha guruhlash
        org_data = {}
        for activity in activities:
            org_name = activity.tashkilot.title
            if org_name not in org_data:
                org_data[org_name] = []
            org_data[org_name].append(activity)
        
        # Xabarni tuzish
        for org_name, org_activities in org_data.items():
            message += f"🏢 *{org_name}*\n"
            org_total_fuel = 0
            org_total_price = 0
            
            for activity in org_activities:
                activity_price = float(activity.all_price or 0)
                
                message += f"  • {activity.avto.title} ({activity.avto.avto_number}):\n"
                message += f"    - Yoqilg'i: {activity.hajm} L\n"
                message += f"    - Turi: {activity.yoqilgi_turi}\n"
                message += f"    - Narx: {activity_price:,.0f} so'm\n"
                message += f"    - Vaqt: {activity.created_ad.strftime('%H:%M')}\n\n"
                
                org_total_fuel += activity.hajm
                org_total_price += activity_price
                total_fuel += activity.hajm
                total_price += activity_price
            
            message += f"  *Jami yoqilg'i: {org_total_fuel:.2f} L*\n"
            message += f"  *Jami narx: {org_total_price:,.0f} so'm*\n\n"
        
        message += f"📈 *UMUMIY HISOBOT:*\n"
        message += f"  • Yoqilg'i: {total_fuel:.2f} L\n"
        message += f"  • Narx: {total_price:,.0f} so'm\n"
        message += f"  • Avtomobillar: {activity_count} ta\n"
    else:
        message += "Bugun hech qanday yoqilg'i quyilmadi."
    
    message += f"\n---\n🔄 *Sistema:* Zaprafka\n👤 *Operator:* {user.get_full_name() or user.username}"
    
    return message

# ==================== WAREHOUSE MANAGEMENT ====================

@login_required
def ombor_list(request):
    """Omborlar ro'yxati"""
    omborlar = Ombor.objects.all().order_by('-created_at')
    return render(request, 'ombor_list.html', {'omborlar': omborlar})

@login_required
def add_ombor(request):
    """Yangi ombor qo'shish"""
    if request.method == 'POST':
        title = request.POST.get('title')
        miqdori = request.POST.get('miqdori', 0)

        if title:
            Ombor.objects.create(title=title, miqdori=miqdori)
            messages.success(request, f"✅ Yangi ombor '{title}' muvaffaqiyatli qo'shildi.")
            return redirect('ombor_list')
        else:
            messages.error(request, "❌ Ombor nomi kiritilishi shart.")
    
    return render(request, 'add_ombor.html')

@login_required
def ombor_tarix(request, ombor_id):
    """Ombor tarixi"""
    ombor = get_object_or_404(Ombor, id=ombor_id)
    tarixlar = OmborTarix.objects.filter(ombor=ombor).order_by('-sana')
    return render(request, 'ombor_tarix.html', {
        'ombor': ombor,
        'tarixlar': tarixlar
    })

@login_required
def ombor_miqdor_oshirish(request, ombor_id):
    """Ombor miqdorini oshirish"""
    ombor = get_object_or_404(Ombor, id=ombor_id)

    if request.method == 'POST':
        miqdor = int(request.POST.get('miqdor', 0))

        if miqdor != 0:
            OmborTarix.objects.create(
                ombor=ombor,
                miqdor_ozgarishi=miqdor,
                sana=timezone.now()
            )
            messages.success(request, f"{ombor.title} uchun {miqdor} miqdor qo'shildi.")
        else:
            messages.error(request, "Miqdor 0 bo'lishi mumkin emas.")

        return redirect('ombor_list')

    return render(request, 'ombor_miqdor_oshirish.html', {'ombor': ombor})

@login_required
def ombor_statistika(request):
    """Ombor statistikasi"""
    context = {
        'omborlar': Ombor.objects.all(),
        'yoqilgi_turlari': Yoqilgi_turi.objects.select_related('ombor'),
        'bugungi_quyishlar': Compilated.objects.filter(created_ad__date=date.today()),
        'bugungi_jami': Compilated.objects.filter(created_ad__date=date.today()).aggregate(total=Sum('hajm'))['total'] or 0,
    }
    return render(request, 'ombor_statistika.html', context)

# ==================== HELPER FUNCTIONS ====================

def get_empty_summary():
    """Bo'sh statistika ma'lumotlari"""
    return {
        'total_fuel': 0,
        'avg_daily': 0,
        'max_fuel': 0,
        'min_fuel': 0,
        'active_cars': 0,
        'total_records': 0
    }

def get_empty_response():
    """Bo'sh response ma'lumotlari"""
    return {
        'summary': get_empty_summary(),
        'tashkilot_stats': [],
        'avto_stats': [],
        'daily_stats': [],
        'monthly_stats': [],
        'weekly_stats': [],
        'detailed_stats': [],
        'recent_records': []
    }

def get_tashkilot_stats(compilated_data):
    """Tashkilotlar statistikasi"""
    return list(compilated_data.values(
        'tashkilot__id', 'tashkilot__title'
    ).annotate(
        total_fuel=Sum('hajm'),
        record_count=Count('id'),
        avg_fuel=Avg('hajm')
    ).order_by('-total_fuel'))

def get_avto_stats(compilated_data):
    """Avtomobillar statistikasi"""
    return list(compilated_data.values(
        'avto__id', 'avto__title', 'avto__avto_number'
    ).annotate(
        total_fuel=Sum('hajm'),
        record_count=Count('id'),
        avg_fuel=Avg('hajm')
    ).order_by('-total_fuel')[:10])

def get_daily_stats(compilated_data):
    """Kunlik statistika"""
    return list(compilated_data.annotate(
        day=TruncDay('created_ad')
    ).values('day').annotate(
        daily_total=Sum('hajm'),
        record_count=Count('id')
    ).order_by('day'))

def get_monthly_stats(compilated_data):
    """Oylik statistika"""
    return list(compilated_data.annotate(
        month=TruncMonth('created_ad')
    ).values('month').annotate(
        monthly_total=Sum('hajm'),
        record_count=Count('id')
    ).order_by('month'))

def get_weekly_stats(compilated_data):
    """Haftalik statistika"""
    return list(compilated_data.annotate(
        week=TruncWeek('created_ad')
    ).values('week').annotate(
        weekly_total=Sum('hajm'),
        record_count=Count('id')
    ).order_by('week'))

def get_detailed_stats(compilated_data, detail_period):
    """Batafsil statistika"""
    if detail_period == 'daily':
        detailed_stats = compilated_data.annotate(period=TruncDay('created_ad'))
    elif detail_period == 'weekly':
        detailed_stats = compilated_data.annotate(period=TruncWeek('created_ad'))
    else:  # monthly
        detailed_stats = compilated_data.annotate(period=TruncMonth('created_ad'))
    
    return list(detailed_stats.values('period').annotate(
        total_fuel=Sum('hajm'),
        record_count=Count('id'),
        tashkilot_count=Count('tashkilot', distinct=True),
        avto_count=Count('avto', distinct=True),
        avg_fuel=Avg('hajm')
    ).order_by('-period'))

def get_recent_records(compilated_data, request):
    """So'nggi yozuvlar"""
    recent_records = compilated_data.select_related(
        'tashkilot', 'avto', 'who_user'
    ).order_by('-created_ad')[:10]
    
    recent_records_list = []
    for record in recent_records:
        photo_url = None
        if record.photo and hasattr(record.photo, 'url') and record.photo.name != 'none.jpg':
            try:
                photo_url = request.build_absolute_uri(record.photo.url)
            except:
                photo_url = None
        
        recent_records_list.append({
            'id': record.id,
            'tashkilot_title': record.tashkilot.title if record.tashkilot else 'Noma\'lum',
            'avto_title': record.avto.title if record.avto else 'Noma\'lum',
            'avto_number': record.avto.avto_number if record.avto else '',
            'user_name': record.who_user.username if record.who_user else 'Noma\'lum',
            'hajm': float(record.hajm) if record.hajm else 0,
            'yoqilgi_turi': record.yoqilgi_turi if record.yoqilgi_turi else 'Noma\'lum',
            'all_price': float(record.all_price) if record.all_price else 0,
            'created_ad': record.created_ad.strftime('%Y-%m-%d %H:%M') if record.created_ad else 'Noma\'lum',
            'photo_url': photo_url
        })
    
    return recent_records_list

def create_summary_data(compilated_data, year, month):
    """Statistika summary ma'lumotlari"""
    total_records = compilated_data.count()
    total_hajm = compilated_data.aggregate(Sum('hajm'))['hajm__sum'] or 0
    total_price = compilated_data.aggregate(Sum('all_price'))['all_price__sum'] or 0
    
    return {
        'Ko\'rsatkich': [
            'Jami yozuvlar soni',
            'Jami yoqilg\'i (L)',
            'Jami summa',
            'Davr'
        ],
        'Qiymat': [
            total_records,
            float(total_hajm),
            float(total_price),
            f"{year}-{month:02d}" if year and month else "Barcha davr"
        ]
    }

def create_today_stats(compilated_data, today):
    """Bugungi statistika ma'lumotlari"""
    total_fuel = compilated_data.aggregate(total=Sum('hajm'))['total'] or 0
    
    return {
        'Ko\'rsatkich': [
            'Sana',
            'Umumiy Yoqilgʻi (L)',
            'Jami Yozuvlar',
            'Faol Avtomobillar',
            'Faol Tashkilotlar'
        ],
        'Qiymat': [
            today.strftime('%Y-%m-%d'),
            round(total_fuel, 1),
            compilated_data.count(),
            compilated_data.values('avto').distinct().count(),
            compilated_data.values('tashkilot').distinct().count()
        ]
    }

# ==================== ERROR HANDLING ====================

def custom_404_view(request, exception=None):
    """404 xato sahifasi"""
    return render(request, '404.html', status=404)

# ==================== ADDITIONAL API ENDPOINTS ====================

@login_required
def today_report_api(request):
    """Bugungi hisobotni JSON formatida qaytaradi"""
    today = date.today()
    activities = Compilated.objects.filter(created_ad__date=today).select_related('avto', 'tashkilot')
    
    activity_data = [
        {
            'avto_title': activity.avto.title,
            'avto_number': activity.avto.avto_number,
            'hajm': activity.hajm,
            'tashkilot_title': activity.tashkilot.title,
            'time': activity.created_ad.strftime('%H:%M')
        } for activity in activities
    ]
    
    return JsonResponse({
        'activities': activity_data,
        'total_count': len(activity_data)
    })

@login_required
def umumiy_statistika_api(request):
    """Umumiy statistika API"""
    # Oxirgi 30 kunlik ma'lumotlar
    start_date = timezone.now() - timedelta(days=30)
    
    statistika = {
        'omborlar': [],
        'yoqilgi_turlari_bo_yicha': [],
        'tashkilotlar_bo_yicha': [],
        'avtomobillar_bo_yicha': []
    }
    
    # Omborlar statistikasi
    for ombor in Ombor.objects.all():
        statistika['omborlar'].append({
            'nomi': ombor.title,
            'miqdori': ombor.miqdori,
            'oxirgi_harakat': OmborTarix.objects.filter(ombor=ombor).last().sana if OmborTarix.objects.filter(ombor=ombor).exists() else None
        })
    
    # Yoqilg'i turlari bo'yicha
    yoqilgi_stat = Compilated.objects.filter(created_ad__gte=start_date).values(
        'yoqilgi_turi'
    ).annotate(
        total_hajm=Sum('hajm'),
        total_count=Count('id'),
        total_price=Sum('all_price')
    )
    
    for stat in yoqilgi_stat:
        statistika['yoqilgi_turlari_bo_yicha'].append({
            'yoqilgi_turi': stat['yoqilgi_turi'],
            'total_hajm': stat['total_hajm'],
            'total_count': stat['total_count'],
            'total_price': stat['total_price']
        })
    
    return JsonResponse(statistika)

@login_required
def kunlik_hisobot_api(request):
    """Kunlik hisobot API"""
    today = date.today()
    
    hisobot = {
        'sana': today,
        'quyishlar': [],
        'jami': {
            'hajm': 0,
            'narx': 0,
            'count': 0
        }
    }
    
    # Kunlik quyishlar
    quyishlar = Compilated.objects.filter(created_ad__date=today).select_related('avto', 'tashkilot')
    
    for quyish in quyishlar:
        hisobot['quyishlar'].append({
            'avto': quyish.avto.title if quyish.avto else 'Noma\'lum',
            'avto_number': quyish.avto.avto_number if quyish.avto else '',
            'tashkilot': quyish.tashkilot.title if quyish.tashkilot else 'Noma\'lum',
            'yoqilgi_turi': quyish.yoqilgi_turi,
            'hajm': quyish.hajm,
            'narx': float(quyish.all_price),
            'vaqt': quyish.created_ad.strftime('%H:%M')
        })
    
    # Jami hisob
    jami = quyishlar.aggregate(
        total_hajm=Sum('hajm'),
        total_narx=Sum('all_price'),
        total_count=Count('id')
    )
    
    hisobot['jami'] = {
        'hajm': jami['total_hajm'] or 0,
        'narx': float(jami['total_narx'] or 0),
        'count': jami['total_count'] or 0
    }
    
    return JsonResponse(hisobot)

@login_required
def tashkilotlar_roxyati(request):
    """Tashkilotlar ro'yxati va ularning statistikasi"""
    # Tashkilotlar bo'yicha statistika
    tashkilot_stats = Compilated.objects.values(
        'tashkilot__id', 'tashkilot__title'
    ).annotate(
        total_fuel=Sum('hajm'),
        total_records=Count('id'),
        avto_count=Count('avto', distinct=True),
        last_activity=Max('created_ad')
    ).order_by('-total_fuel')
    
    context = {
        'tashkilot_stats': tashkilot_stats,
    }
    return render(request, 'tashkilotlar_roxyati.html', context)

@login_required
def tashkilot_detail(request, tashkilot_id):
    """Tashkilotning batafsil ma'lumotlari"""
    tashkilot = get_object_or_404(Tashkilot, id=tashkilot_id)
    
    # Tashkilot bo'yicha ma'lumotlar
    compilated_data = Compilated.objects.filter(tashkilot=tashkilot).select_related('avto', 'who_user')
    
    # Umumiy statistika
    total_fuel = compilated_data.aggregate(total=Sum('hajm'))['total'] or 0
    total_records = compilated_data.count()
    avto_count = compilated_data.values('avto').distinct().count()
    
    # Oxirgi 30 kunlik ma'lumotlar
    start_date = timezone.now() - timedelta(days=30)
    recent_data = compilated_data.filter(created_ad__gte=start_date)
    
    # Kunlik statistika
    daily_stats = recent_data.annotate(
        day=TruncDay('created_ad')
    ).values('day').annotate(
        daily_total=Sum('hajm'),
        record_count=Count('id')
    ).order_by('-day')
    
    # Avtomobillar bo'yicha statistika
    avto_stats = compilated_data.values(
        'avto__title', 'avto__avto_number'
    ).annotate(
        total_fuel=Sum('hajm'),
        record_count=Count('id'),
        last_refuel=Max('created_ad')
    ).order_by('-total_fuel')
    
    # Yoqilgi turlari bo'yicha
    yoqilgi_stats = compilated_data.values('yoqilgi_turi').annotate(
        total_fuel=Sum('hajm'),
        record_count=Count('id')
    ).order_by('-total_fuel')
    
    context = {
        'tashkilot': tashkilot,
        'total_fuel': total_fuel,
        'total_records': total_records,
        'avto_count': avto_count,
        'daily_stats': daily_stats,
        'avto_stats': avto_stats,
        'yoqilgi_stats': yoqilgi_stats,
        'recent_records': compilated_data.order_by('-created_ad')[:10]
    }
    
    return render(request, 'tashkilot_detail.html', context)

@login_required
def get_tashkilot_stats_api(request):
    """Tashkilotlar statistikasini JSON formatida qaytarish"""
    try:
        tashkilot_stats = Compilated.objects.values(
            'tashkilot__id', 'tashkilot__title'
        ).annotate(
            total_fuel=Sum('hajm'),
            total_records=Count('id'),
            avto_count=Count('avto', distinct=True),
            last_activity=Max('created_ad')
        ).order_by('-total_fuel')
        
        stats_list = []
        for stat in tashkilot_stats:
            stats_list.append({
                'id': stat['tashkilot__id'],
                'title': stat['tashkilot__title'],
                'total_fuel': round(float(stat['total_fuel'] or 0), 1),
                'total_records': stat['total_records'],
                'avto_count': stat['avto_count'],
                'last_activity': stat['last_activity'].strftime('%Y-%m-%d %H:%M') if stat['last_activity'] else 'Mavjud emas'
            })
        
        return JsonResponse({
            'success': True,
            'tashkilotlar': stats_list
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    
@login_required
def tashkilot_balans(request, tashkilot_id):
    """Tashkilot balansi va tarixi"""
    tashkilot = get_object_or_404(Tashkilot, id=tashkilot_id)
    balans_tarix = TashkilotBalansTarix.objects.filter(tashkilot=tashkilot).order_by('-sana')
    
    context = {
        'tashkilot': tashkilot,
        'balans_tarix': balans_tarix,
    }
    return render(request, 'tashkilot_balans.html', context)

@login_required
def tashkilot_balans_qoshish(request, tashkilot_id):
    """Tashkilot balansiga pul qo'shish"""
    tashkilot = get_object_or_404(Tashkilot, id=tashkilot_id)
    
    if request.method == 'POST':
        miqdor = Decimal(request.POST.get('miqdor', 0))
        izoh = request.POST.get('izoh', '')
        
        if miqdor > 0:
            # Balansga qo'shish
            tashkilot.add_balance(miqdor)
            
            # Tarixga yozish
            TashkilotBalansTarix.objects.create(
                tashkilot=tashkilot,
                miqdor=miqdor,
                qoldiq=tashkilot.balance,
                izoh=izoh or f"Balans to'ldirildi",
                sana=timezone.now()
            )
            
            messages.success(request, f"✅ {tashkilot.title} balansi {miqdor} so'm ga to'ldirildi!")
            return redirect('tashkilot_balans', tashkilot_id=tashkilot_id)
        else:
            messages.error(request, "❌ Miqdor 0 dan katta bo'lishi kerak!")
    
    context = {
        'tashkilot': tashkilot,
    }
    return render(request, 'tashkilot_balans_qoshish.html', context)

@login_required
def tashkilotlar_balans(request):
    """Barcha tashkilotlar balansi"""
    tashkilotlar = Tashkilot.objects.all().order_by('-balance')
    
    # Umumiy statistika
    total_balance = sum(t.balance for t in tashkilotlar)
    tashkilot_count = tashkilotlar.count()
    
    context = {
        'tashkilotlar': tashkilotlar,
        'total_balance': total_balance,
        'tashkilot_count': tashkilot_count,
    }
    return render(request, 'tashkilotlar_balans.html', context)
# views.py ga qo'shing

@login_required
def qarzdor_tashkilotlar(request):
    """Qarzdor tashkilotlar ro'yxati"""
    qarzdor_tashkilotlar = Tashkilot.objects.filter(balance__lt=0).order_by('balance')
    
    # Umumiy qarz miqdori
    total_qarz = sum(t.qarz_miqdori for t in qarzdor_tashkilotlar)
    
    context = {
        'qarzdor_tashkilotlar': qarzdor_tashkilotlar,
        'total_qarz': total_qarz,
        'qarzdor_count': qarzdor_tashkilotlar.count(),
    }
    return render(request, 'qarzdor_tashkilotlar.html', context)

@login_required
def tashkilot_qarz_tarix(request, tashkilot_id):
    """Tashkilotning qarz operatsiyalari tarixi"""
    tashkilot = get_object_or_404(Tashkilot, id=tashkilot_id)
    
    # Faqat qarz bilan bog'liq operatsiyalar
    qarz_tarix = TashkilotBalansTarix.objects.filter(
        tashkilot=tashkilot,
        miqdor__lt=0  # Faqat chiqim operatsiyalari
    ).order_by('-sana')
    
    # Qarz holatidagi yoqilg'i quyishlar
    qarz_quyishlar = Compilated.objects.filter(
        tashkilot=tashkilot,
        qarz_holatida=True
    ).order_by('-created_ad')
    
    context = {
        'tashkilot': tashkilot,
        'qarz_tarix': qarz_tarix,
        'qarz_quyishlar': qarz_quyishlar,
    }
    return render(request, 'tashkilot_qarz_tarix.html', context)
