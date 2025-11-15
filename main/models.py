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
    group_id = models.BigIntegerField(default=4885110792)
    
    class Meta:
        verbose_name = "Tashkilot"
        verbose_name_plural = "Tashkilotlar"

    def __str__(self):
        return self.title

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

    class Meta:
        indexes = [
            models.Index(fields=['created_ad']),
            models.Index(fields=['tashkilot', 'created_ad']),
            models.Index(fields=['avto', 'created_ad']),
        ]
        ordering = ['-created_ad']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
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
                            f"Omborda yetarli yoqilg'i yoq. "
                            f"Mavjud: {yoqilgi_turi_obj.ombor.miqdori} L, "
                            f"Kerak: {self.hajm} L"
                        )
            except Yoqilgi_turi.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
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
        
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.avto.title if self.avto else 'Noma\'lum'} - {self.hajm}L - {self.yoqilgi_turi}"