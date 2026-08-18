from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RegisterForm, LoginForm, ProfileUpdateForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account has been created.")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next', '/')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            _send_barber_login_alert(user, request)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form, 'next': next_url})


def _send_barber_login_alert(user, request):
    """Email the barber a heads-up whenever their dashboard account signs in."""
    barber = getattr(user, 'barber_profile', None)
    if barber is None or not user.email:
        return

    ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown device')[:80]
    subject = f"24 K — {barber.name} logged in"
    message = (
        f"Hi {barber.name},\n\n"
        f"Your barber dashboard account just signed in.\n\n"
        f"  Time:   {timezone.localtime().strftime('%d %b %Y, %I:%M %p')}\n"
        f"  Device: {user_agent}\n"
        f"  IP:     {ip}\n\n"
        f"If this wasn't you, change your password in the shop admin right away.\n\n"
        f"— 24 K Barbershop"
    )
    send_mail(subject, message, None, [user.email], fail_silently=True)


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You've been logged out.")
    return redirect('home')


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            profile.phone = form.cleaned_data['phone']
            profile.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': profile.phone,
        })

    recent_bookings = user.bookings.select_related('service').order_by('-created_at')[:5]
    context = {'form': form, 'recent_bookings': recent_bookings}
    return render(request, 'users/profile.html', context)
