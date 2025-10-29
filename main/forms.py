from django import forms
from .models import Tashkilot, Avto, Yoqilgi_turi

class TashkilotForm(forms.ModelForm):
    class Meta:
        model = Tashkilot
        fields = ['title', 'group_id']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tashkilot nomi'
            }),
            'group_id': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Telegram guruh ID'
            })
        }
        labels = {
            'title': 'Tashkilot Nomi',
            'group_id': 'Telegram Gruh ID'
        }

class AvtoForm(forms.ModelForm):
    class Meta:
        model = Avto
        fields = ['tashkilot', 'title', 'avto_number']
        widgets = {
            'tashkilot': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Avtomobil nomi'
            }),
            'avto_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Avtomobil raqami'
            })
        }
        labels = {
            'tashkilot': 'Tashkilot',
            'title': 'Avtomobil Nomi',
            'avto_number': 'Avtomobil Raqami'
        }

class YoqilgiTuriForm(forms.ModelForm):
    class Meta:
        model = Yoqilgi_turi
        fields = ['title', 'price']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Yoqilg\'i turi nomi'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Narxi',
                'step': '0.01'
            })
        }
        labels = {
            'title': 'Yoqilg\'i Turi',
            'price': 'Narxi (so\'m)'
        }