from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Bank)
admin.site.register(UserBankAccount)
admin.site.register(UserAddress)