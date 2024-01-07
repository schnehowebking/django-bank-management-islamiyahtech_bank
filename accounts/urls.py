
from django.urls import path
from .views import *
 
urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),
    path('profile/', UserBankAccountUpdateView.as_view(), name='profile' )
]