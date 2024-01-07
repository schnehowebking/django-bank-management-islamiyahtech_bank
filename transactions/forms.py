from django import forms
from .models import Transaction
from django.core.exceptions import ObjectDoesNotExist
from accounts.models import UserBankAccount


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'amount',
            'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].disabled = True 
        self.fields['transaction_type'].widget = forms.HiddenInput()

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()


class DepositForm(TransactionForm):
    def clean_amount(self): 
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount') 
        if amount < min_deposit_amount:
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} $'
            )

        return amount


class WithdrawForm(TransactionForm):

    def clean_amount(self):
        account = self.account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance
        amount = self.cleaned_data.get('amount')
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $'
            )

        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $'
            )

        if amount > balance:
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not withdraw more than your account balance'
            )

        return amount



class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        return amount
    

class TransferForm(TransactionForm):
    recipient_account = forms.CharField(label='Recipient Account Number', max_length=50)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['amount'].widget.attrs['class'] = 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight border rounded-md border-gray-500 focus:outline-none focus:shadow-outline'
        self.fields['amount'].label = 'Amount'
        self.fields['amount'].label_tag = lambda attrs=None: self.label_tag(attrs, contents=self.fields['amount'].label)
        
        self.fields['recipient_account'].widget.attrs['class'] = 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight border rounded-md border-gray-500 focus:outline-none focus:shadow-outline'
        self.fields['recipient_account'].label = 'Recipient Account Number'
        self.fields['recipient_account'].label_tag = lambda attrs=None: self.label_tag(attrs, contents=self.fields['recipient_account'].label)


    def clean_amount(self):
        min_transfer_amount = 150
        amount = self.cleaned_data.get('amount')

        if amount < min_transfer_amount:
            raise forms.ValidationError(
                f'The transfer amount must be at least {min_transfer_amount} $'
            )
        elif self.account.balance<amount:
            raise forms.ValidationError(
                f'Insufficient funds for the transfer!'
            )

        return amount

    def clean_recipient_account(self):
        recipient_account = self.cleaned_data.get('recipient_account')

        try:
            recipient_account_obj = UserBankAccount.objects.get(account_no=recipient_account)
        except ObjectDoesNotExist:
            raise forms.ValidationError('Recipient account does not exist.')

        if recipient_account_obj == self.account:
            raise forms.ValidationError('Cannot transfer to your own account.')

        return recipient_account

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance

        recipient_account = UserBankAccount.objects.get(account_no=self.cleaned_data.get('recipient_account'))
        recipient_account.balance += self.cleaned_data.get('amount')
        recipient_account.save()

        self.instance.recipient_account = self.cleaned_data.get('recipient_account')
        return super().save()