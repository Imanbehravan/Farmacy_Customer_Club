from functools import wraps
import jdatetime 
from django.http import JsonResponse
from collections import OrderedDict
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .filters import PurchaseFilter
from .services import base_queryset,jalali_monthly , summary
from django.http import HttpResponse
from django.template.loader import render_to_string


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
    months = jalali_monthly(qs)

    chart_labels, chart_values, chart_counts = [], [], []
    prev_total = None
    for row in months:
        total = float(row["total"] or 0)

        if prev_total:
            row["change"] = round((total - prev_total) / prev_total * 100, 1)
            row["direction"] = "up" if row["change"] >= 0 else "down"
            row["change_abs"] = abs(row["change"])
        else:
            row["direction"] = ""
        prev_total = total

        chart_labels.append(row["label"])
        chart_values.append(total)
        chart_counts.append(row["count"])

    context = {
        "filter": f,
        "summary": summary(qs),
        "months": months,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "chart_counts": chart_counts,
    }
    return render(request, "reports/admin/sales_report.html", context)
@staff_only
def sales_feed(request):
    f, qs = _filtered(request)
    group = request.GET.get("group", "month")

    buckets = {}
    for p in qs.order_by("created_at"):
        j = jdatetime.datetime.fromgregorian(datetime=timezone.localtime(p.created_at))
        if group == "year":
            label = j.strftime("%Y")
        elif group == "day":
            label = j.strftime("%Y/%m/%d")
        else:
            label = j.strftime("%Y/%m")
        buckets[label] = buckets.get(label, 0) + float(p.amount or 0)

    rows = [{"label": k, "amount": v} for k, v in buckets.items()]
    if group == "day":
        rows = rows[-30:]    # ۳۰ روز آخر
    elif group == "month":
        rows = rows[-12:]    # ۱۲ ماه آخر

    return JsonResponse({"rows": rows, "summary": summary(qs)})

@staff_only
def sales_pdf(request):
    from weasyprint import HTML  # ایمپورت تنبل: اگه نصب نبود، بقیه‌ی صفحه‌ها خراب نمی‌شن

    f, qs = _filtered(request)
    rows = []
    for p in qs.select_related("user").order_by("-created_at"):
        t = jdatetime.datetime.fromgregorian(datetime=timezone.localtime(p.created_at))
        rows.append({
            "id": p.id,
            "date": t.strftime("%Y/%m/%d %H:%M"),
            "tracking_code": p.tracking_code,
            "phone": p.user.phone_number,
            "national_id": p.national_id,
            "insurance": p.get_insurance_short(),
            "status": p.get_status_display(),
            "original_amount": p.original_amount,
            "amount": p.amount,
            "discount": max(p.original_amount - p.amount, 0),
        })

    now = jdatetime.datetime.fromgregorian(datetime=timezone.localtime()).strftime("%Y/%m/%d %H:%M")
    html = render_to_string("reports/admin/Sales_pdf.html", {
        "rows": rows,
        "summary": summary(qs),
        "months": jalali_monthly(qs),
        "now": now,
    })
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'
    return resp