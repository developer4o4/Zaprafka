from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
class User(AbstractUser):
    phone = models.CharField(max_length=15)
    
    def __str__(self):
        return self.username

class Tashkilot(models.Model):
    title = models.CharField(max_length=150)
    group_id = models.IntegerField(default=4885110792)
    def __str__(self):
        return self.title
class Avto(models.Model):
    tashkilot = models.ForeignKey(Tashkilot,on_delete=models.CASCADE,default=1,)
    title = models.CharField(max_length=100)
    avto_number = models.CharField(max_length=20)
    def __str__(self):
        return self.title
class Yoqilgi_turi(models.Model):
    price = models.DecimalField(max_digits=50, decimal_places=2, default=0)
    title = models.CharField(max_length=50)
    def __str__(self):
        return self.title
class Compilated(models.Model):
    tashkilot = models.ForeignKey(Tashkilot,on_delete=models.DO_NOTHING)
    avto = models.ForeignKey(Avto,on_delete=models.DO_NOTHING)
    who_user = models.ForeignKey(User,on_delete=models.DO_NOTHING)
    hajm = models.FloatField(default=0)
    created_ad = models.DateTimeField(default=timezone.now)
    photo = models.FileField(upload_to='images/',default="none.jpg") 
    photo_2 = models.FileField(upload_to='images/',default="none.jpg") 
    yoqilgi_turi = models.CharField(max_length=50,default="tanlanmagan")
    all_price = models.DecimalField(max_digits=50, decimal_places=2, default=0)