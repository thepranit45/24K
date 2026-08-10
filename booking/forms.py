from django import forms
from .models import Booking


class CustomerDetailsForm(forms.Form):
    """Step 3 of booking wizard — customer contact details."""
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'})
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'})
    )
    special_request = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Any special requests? (optional)',
            'rows': 3,
        })
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) < 10:
            raise forms.ValidationError("Please enter a valid phone number with at least 10 digits.")
        return phone
