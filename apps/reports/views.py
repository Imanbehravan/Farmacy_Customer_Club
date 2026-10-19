from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .filters import PurchaseFilter
from .services import base_queryset, monthly_totals, summary


def staff_only(view):
    """فقط کاربر واردشده با دسترسی staff. کاربر ناشناس به صفحه ورود می‌رود، بقیه خطای ۴۰۳ می‌گیرند"""
    @login_required(login_url="login")
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def _filtered(request):
    f = PurchaseFilter(request.GET, queryset=base_queryset())
    return f, f.qs


def _dates(f):
    """بازه تاریخ تمیزشده فرم (یا None اگر خالی یا نامعتبر بود)"""
    f.form.is_valid()
    data = getattr(f.form, "cleaned_data", {})
    return data.get("date_from"), data.get("date_to")


@staff_only
def sales_report(request):
    f, qs = _filtered(request)
    context = {
        "filter": f,
        "summary": summary(qs),
        "months": monthly_totals(qs),
    }
    return render(request, "reports/sales_report.html", context)