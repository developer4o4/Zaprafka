from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError

class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return self.username

class Ombor(models.Model):
    title = models.CharField(max_length=100)
    miqdori = models.FloatField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        if self.miqdori < 0:
            raise ValidationError("Miqdor manfiy bo'lishi mumkin emas")

    def __str__(self):
        return f"{self.title} - {self.miqdori} L"

class OmborTarix(models.Model):
    ombor = models.ForeignKey(Ombor, on_delete=models.CASCADE, related_name='tarixlar')
    miqdor_ozgarishi = models.FloatField()
    sana = models.DateTimeField(default=timezone.now)

    def __str__(self):
        belgi = "+" if self.miqdor_ozgarishi >= 0 else ""
        return f"{self.ombor.title} ({belgi}{self.miqdor_ozgarishi})"
class Tashkilot(models.Model):
    title = models.CharField(max_length=150)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    group_id = models.BigIntegerField(default=4885110792)
    max_qarz = models.DecimalField(max_digits=15, decimal_places=2, default=1000000, 
                                  verbose_name="Maksimal qarz miqdori")
    
    class Meta:
        verbose_name = "Tashkilot"
        verbose_name_plural = "Tashkilotlar"

    def __str__(self):
        balance_color = "🟢" if self.balance >= 0 else "🔴"
        return f"{self.title} {balance_color} {self.balance} so'm"

    def clean(self):
        """Max qarz chegarasini tekshirish"""
        if self.balance < -self.max_qarz:
            raise ValidationError(f"Qarz miqdori maksimal {self.max_qarz} so'm dan oshib ketdi")

    def can_afford(self, amount):
        """Tashkilot ma'lum miqdorni to'lashga qodir yoki yo'qligini tekshirish (qarzga oladi)"""
        return (self.balance - amount) >= -self.max_qarz

    def deduct_balance(self, amount):
        """Balansdan pul ayirish (qarzga oladi)"""
        if self.can_afford(amount):
            self.balance -= amount
            self.save()
            return True
        return False

    def add_balance(self, amount):
        """Balansga pul qo'shish"""
        self.balance += amount
        self.save()

    def get_balance_status(self):
        """Balans holatini qaytarish"""
        if self.balance > 0:
            return {
                'status': 'positive',
                'text': f'✅ {self.balance} so\'m',
                'color': '#28a745'
            }
        elif self.balance == 0:
            return {
                'status': 'zero',
                'text': '⚪ 0 so\'m',
                'color': '#6c757d'
            }
        else:
            return {
                'status': 'negative',
                'text': f'🔴 {abs(self.balance)} so\'m qarz',
                'color': '#dc3545'
            }

    @property
    def qarz_miqdori(self):
        """Qarz miqdorini qaytarish"""
        return abs(self.balance) if self.balance < 0 else 0

    @property
    def is_in_debt(self):
        """Qarzda ekanligini tekshirish"""
        return self.balance < 0

class Avto(models.Model):
    tashkilot = models.ForeignKey(Tashkilot, on_delete=models.CASCADE, default=1)
    title = models.CharField(max_length=100)
    avto_number = models.CharField(max_length=20)
    
    class Meta:
        verbose_name = "Avtomobil"
        verbose_name_plural = "Avtomobillar"

    def __str__(self):
        return f"{self.title} ({self.avto_number})"

class Yoqilgi_turi(models.Model):
    ombor = models.ForeignKey(Ombor, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    title = models.CharField(max_length=50)
    
    class Meta:
        verbose_name = "Yoqilg'i turi"
        verbose_name_plural = "Yoqilg'i turlari"

    def __str__(self):
        return self.title
    
class TashkilotBalansTarix(models.Model):
    tashkilot = models.ForeignKey(Tashkilot, on_delete=models.CASCADE, related_name='balans_tarix')
    miqdor = models.DecimalField(max_digits=12, decimal_places=2)
    qoldiq = models.DecimalField(max_digits=15, decimal_places=2)
    izoh = models.CharField(max_length=255)
    sana = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Tashkilot Balans Tarixi"
        verbose_name_plural = "Tashkilot Balans Tarixlari"
        ordering = ['-sana']
    
    def __str__(self):
        belgi = "+" if self.miqdor >= 0 else ""
        return f"{self.tashkilot.title}: {belgi}{self.miqdor} (Qoldiq: {self.qoldiq})"
class Compilated(models.Model):
    tashkilot = models.ForeignKey(Tashkilot, on_delete=models.SET_NULL, null=True, blank=True)
    avto = models.ForeignKey(Avto, on_delete=models.SET_NULL, null=True, blank=True)
    who_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    hajm = models.FloatField(default=0)
    created_ad = models.DateTimeField(default=timezone.now)
    photo = models.FileField(upload_to='images/', default="none.jpg") 
    photo_2 = models.FileField(upload_to='images/', default="none.jpg") 
    yoqilgi_turi = models.CharField(max_length=50, default="tanlanmagan")
    all_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ombordan_ayirilgan = models.BooleanField(default=False)
    tashkilotdan_ayirilgan = models.BooleanField(default=False)
    qarz_holatida = models.BooleanField(default=False)  # Yangi field: qarz holatida quyilganligi

    class Meta:
        indexes = [
            models.Index(fields=['created_ad']),
            models.Index(fields=['tashkilot', 'created_ad']),
            models.Index(fields=['avto', 'created_ad']),
        ]
        ordering = ['-created_ad']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Avvalgi logika (ombor bilan ishlash)
        if is_new and self.yoqilgi_turi != "tanlanmagan" and not self.ombordan_ayirilgan:
            try:
                yoqilgi_turi_obj = Yoqilgi_turi.objects.get(title=self.yoqilgi_turi)
                if yoqilgi_turi_obj.ombor:
                    if yoqilgi_turi_obj.ombor.miqdori >= self.hajm:
                        yoqilgi_turi_obj.ombor.miqdori -= self.hajm
                        yoqilgi_turi_obj.ombor.save()
                        
                        OmborTarix.objects.create(
                            ombor=yoqilgi_turi_obj.ombor,
                            miqdor_ozgarishi=-self.hajm,
                            sana=timezone.now()
                        )
                        
                        self.ombordan_ayirilgan = True
                    else:
                        raise ValueError(
                            f"Omborda yetarli yoqilg'i yo'q. "
                            f"Mavjud: {yoqilgi_turi_obj.ombor.miqdori} L, "
                            f"Kerak: {self.hajm} L"
                        )
            except Yoqilgi_turi.DoesNotExist:
                pass
        
        # Yangi logika: tashkilot balansidan ayirish (qarzga oladi)
        if is_new and self.tashkilot and not self.tashkilotdan_ayirilgan:
            if self.tashkilot.can_afford(self.all_price):
                old_balance = self.tashkilot.balance
                success = self.tashkilot.deduct_balance(self.all_price)
                
                if success:
                    self.tashkilotdan_ayirilgan = True
                    self.qarz_holatida = (old_balance - self.all_price) < 0
                    
                    # Tashkilot balans tarixini yozish
                    izoh = f"Yoqilg'i quyish: {self.avto.title if self.avto else 'Noma\'lum'} - {self.hajm}L"
                    if self.qarz_holatida:
                        izoh += f" (QARZ: {abs(self.tashkilot.balance)} so'm)"
                    
                    TashkilotBalansTarix.objects.create(
                        tashkilot=self.tashkilot,
                        miqdor=-self.all_price,
                        qoldiq=self.tashkilot.balance,
                        izoh=izoh,
                        sana=timezone.now()
                    )
                else:
                    raise ValueError("Balansdan ayirish amalga oshirilmadi")
            else:
                raise ValueError(
                    f"Tashkilot qarz chegarasidan oshib ketdi. "
                    f"Maksimal qarz: {self.tashkilot.max_qarz} so'm, "
                    f"Joriy balans: {self.tashkilot.balance} so'm, "
                    f"Kerak: {self.all_price} so'm"
                )
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Omborga qaytarish
        if self.ombordan_ayirilgan and self.yoqilgi_turi != "tanlanmagan":
            try:
                yoqilgi_turi_obj = Yoqilgi_turi.objects.get(title=self.yoqilgi_turi)
                if yoqilgi_turi_obj.ombor:
                    yoqilgi_turi_obj.ombor.miqdori += self.hajm
                    yoqilgi_turi_obj.ombor.save()
                    
                    OmborTarix.objects.create(
                        ombor=yoqilgi_turi_obj.ombor,
                        miqdor_ozgarishi=self.hajm,
                        sana=timezone.now()
                    )
            except Yoqilgi_turi.DoesNotExist:
                pass
        
        # Tashkilot balansiga qaytarish
        if self.tashkilotdan_ayirilgan and self.tashkilot:
            old_balance = self.tashkilot.balance
            self.tashkilot.add_balance(self.all_price)
            
            # Tashkilot balans tarixini yozish
            izoh = f"Yoqilg'i quyish bekor qilindi: {self.avto.title if self.avto else 'Noma\'lum'} - {self.hajm}L"
            if old_balance < 0 and self.tashkilot.balance >= 0:
                izoh += " (QARZ TO'LANDI!)"
            
            TashkilotBalansTarix.objects.create(
                tashkilot=self.tashkilot,
                miqdor=self.all_price,
                qoldiq=self.tashkilot.balance,
                izoh=izoh,
                sana=timezone.now()
            )
        
        super().delete(*args, **kwargs)

    def __str__(self):
        status = " (QARZ)" if self.qarz_holatida else ""
        return f"{self.avto.title if self.avto else 'Noma\'lum'} - {self.hajm}L - {self.yoqilgi_turi}{status}"
    

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
class FuelMessage(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_CONFIRMED, 'Tasdiqlandi'),
        (STATUS_REJECTED, 'Rad etildi'),
    ]
    
    group_id = models.CharField(max_length=100)
    group_name = models.CharField(max_length=255)
    message_id = models.IntegerField()
    fuel_data = models.JSONField(default=dict)  # Default qo'shildi
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    callback_data = models.CharField(max_length=100, unique=True)
    
    def is_expired(self):
        """5 kun o'tganligini tekshirish"""
        return timezone.now() - self.created_at > timedelta(days=5)
    
    def days_passed(self):
        """Necha kun o'tganligini hisoblash"""
        return (timezone.now() - self.created_at).days
    
    def __str__(self):
        return f"{self.group_name} - {self.get_status_display()} - {self.created_at.strftime('%d.%m.%Y')}"
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['callback_data']),
        ]
        verbose_name = 'Fuel Message'
        verbose_name_plural = 'Fuel Messages'
        ordering = ['-created_at']