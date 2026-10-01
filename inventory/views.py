from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Главный дашборд — заглушка. Будет реализован на Дне 15."""
    return render(request, 'inventory/dashboard.html')
