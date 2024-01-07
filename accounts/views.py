from django.shortcuts import render
from django.views.generic import FormView
from .forms import *
# from .forms import UserRegistrationForm,UserUpdateForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.views import View
from django.shortcuts import redirect
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
# from transactions.views import 

def send_transaction_email(user, subject, template):
    message = render_to_string(template, {
        'user' : user,
    })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()


class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile')
    
    def form_valid(self,form):
        print(form.cleaned_data)
        user = form.save()
        login(self.request, user)
        print(user)
        return super().form_valid(form)
    

class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    def get_success_url(self):
        return reverse_lazy('home')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Password changed successfully.')
            send_transaction_email(request.user, "Password Changed", "accounts/change_password_mail.html")
            return redirect('profile')
    else:
        form = UserPasswordChangeForm(request.user)
    return render(request, './accounts/change_password.html', {'form': form})



@login_required
def user_logout(request):
    logout(request)
    return redirect('home')

class UserBankAccountUpdateView(View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile') 
        return render(request, self.template_name, {'form': form})
    
    
    