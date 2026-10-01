from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages


def login_view(request):
    """Заглушка для страницы входа. Будет реализована на Дне 9."""
    return render(request, 'accounts/login.html')


def logout_view(request):
    """Выход из системы."""
    logout(request)
    return redirect('accounts:login')


def register_view(request):
    """Заглушка для страницы регистрации. Будет реализована на Дне 9."""
    return render(request, 'accounts/register.html')
