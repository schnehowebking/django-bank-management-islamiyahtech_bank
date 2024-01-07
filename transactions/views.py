from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse, HttpResponseServerError
from django.views.generic import CreateView, ListView
from accounts.models import UserBankAccount
from transactions.constants import DEPOSIT, TRANSFER_TO_OTHER, WITHDRAWAL,LOAN, LOAN_PAID
from django.core.mail import EmailMessage, EmailMultiAlternatives

from django.template.loader import render_to_string
from datetime import datetime
from django.db.models import Sum
from transactions.forms import (
    DepositForm,
    TransferForm,
    WithdrawForm,
    LoanRequestForm,
)
from transactions.models import Transaction
from accounts.models import Bank


def send_transaction_email(user, amount, subject, template):
    message = render_to_string(template, {
        'user' : user,
        'amount' : amount,
    })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()


def send__money_transfer_email(user, recipient, amount, subject, template):
    message = render_to_string(template, {
        'user' : user,
        'amount' : amount,
        'recipient':recipient,
    })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()

class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) 
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        if Bank.objects.filter(is_bankrupt=True).exists():
            messages.error(
                self.request,
                "The Bank is bankrupt. No transactions are allowed at the moment."
            )
            return redirect('transaction_report')
        
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
      
        account.balance += amount
        account.save(
            update_fields=[
                'balance'
            ]
        )
        


        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )

        send_transaction_email(self.request.user, amount, "Deposite Message", "transactions/deposit_mail.html")

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        if Bank.objects.filter(is_bankrupt=True).exists():
            messages.error(
                self.request,
                "The Bank is bankrupt. No transactions are allowed at the moment."
            )
            return redirect('transaction_report')
        amount = form.cleaned_data.get('amount')
        if amount > self.request.user.account.balance:
            messages.error(
                self.request,
                "Bank is bankrupt! Unable to withdraw the requested amount."
            )
            return HttpResponseServerError("Bank is bankrupt! Unable to withdraw the requested amount.")

        self.request.user.account.balance -= form.cleaned_data.get('amount')
      
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        send_transaction_email(self.request.user, amount, "Withdrawal Message", "transactions/withdrawal_email.html")

        return super().form_valid(form)



class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        if Bank.objects.filter(is_bankrupt=True).exists():
            messages.error(
                self.request,
                "The Bank is bankrupt. No transactions are allowed at the moment."
            )
            return redirect('transaction_report')
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )

        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        if Bank.objects.filter(is_bankrupt=True).exists():
            messages.error(
                self.request,
                "The Bank is bankrupt. No transactions are allowed at the moment."
            )
            return redirect('transaction_report')
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
              
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' 
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    


class TransferMoneyView(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transfer_form.html' 
    form_class = TransferForm
    model = Transaction
    title = 'Transfer Money'
    success_url = reverse_lazy('transaction_report')

    def get_initial(self):
        initial = {'transaction_type': TRANSFER_TO_OTHER}
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def form_valid(self, form):
        if Bank.objects.filter(is_bankrupt=True).exists():
            messages.error(
                self.request,
                "The Bank is bankrupt. No transactions are allowed at the moment."
            )
            return redirect('transaction_report')
        amount = form.cleaned_data.get('amount')
        recipient_account_no =form.cleaned_data.get('recipient_account')

        account = self.request.user.account
        if amount > self.request.user.account.balance:
            messages.error(
                self.request,
                f'Insufficiant Balance to Transfer, Please Deposite First'
            )
            reverse_lazy('deposit')
        else:
            account.balance -= amount
            account.save(update_fields=['balance'])

            recipient_account = UserBankAccount.objects.get(account_no=recipient_account_no)
            recipient_account.balance += amount
            recipient_account.save()

            messages.success(
                self.request,
                f'Successfully transferred {"{:,.2f}".format(float(amount))}$ to the account {recipient_account}'
            )
            send__money_transfer_email(self.request.user,recipient_account, amount, "Transfer Money Message", "transactions/sender_transfermoney_email.html")
            send__money_transfer_email(self.request.user,recipient_account, amount, "Transfer Money Message", "transactions/receiver_transfermoney_email.html")
            

        return super().form_valid(form)