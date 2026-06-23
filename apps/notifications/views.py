from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.contrib import messages

import jdatetime
from django.utils import timezone as tz
from .models import Notification, BroadcastMessage


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─────────────────────────────────────────────
#  API اعلان‌های کاربر
# ─────────────────────────────────────────────
class NotificationsAPIView(View):
    @method_decorator(login_required)
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:20]
        data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'created_at': jdatetime.datetime.fromgregorian(datetime=tz.localtime(n.created_at)).strftime('%Y/%m/%d %H:%M'),
        } for n in notifications]
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return JsonResponse({'notifications': data, 'unread_count': unread_count})

    @method_decorator(login_required)
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})


class MarkReadView(View):
    @method_decorator(login_required)
    def post(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, user=request.user)
            n.is_read = True
            n.save(update_fields=['is_read'])
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False})


# ─────────────────────────────────────────────
#  پیام همگانی (ادمین)
# ─────────────────────────────────────────────
class AdminBroadcastView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request):
        broadcasts = BroadcastMessage.objects.order_by('-sent_at')
        from apps.accounts.models import User
        user_count = User.objects.filter(is_active=True, is_staff=False).count()
        return render(request, 'admin_panel/broadcast.html', {
            'broadcasts': broadcasts,
            'user_count': user_count,
        })

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def post(self, request):
        from apps.accounts.models import User

        title      = request.POST.get('title', '').strip()
        message    = request.POST.get('message', '').strip()
        disc_pct   = request.POST.get('discount_percentage', '').strip()
        target     = request.POST.get('target', 'all')  # all / active

        if not title or not message:
            messages.error(request, 'عنوان و متن پیام الزامی هستند.')
            return redirect('admin_broadcast')

        discount_percentage = int(disc_pct) if disc_pct.isdigit() else None

        # Determine recipients
        users = User.objects.filter(is_active=True, is_staff=False)
        if target == 'active':
            # users who bought something in last 3 months
            from django.utils import timezone
            from datetime import timedelta
            from apps.customer_club.models import Purchase
            three_months_ago = timezone.now() - timedelta(days=90)
            active_user_ids = Purchase.objects.filter(
                purchase_date__gte=three_months_ago
            ).values_list('user_id', flat=True).distinct()
            users = users.filter(id__in=active_user_ids)

        # Build notification message
        full_message = message
        if discount_percentage:
            full_message += f'\n\n🎁 تخفیف ویژه {discount_percentage}٪ برای اقلام آرایشی-بهداشتی فعال شد!'

        # Create notifications for all users
        notifications = [
            Notification(
                user=u,
                title=title,
                message=full_message,
                notification_type='broadcast'
            ) for u in users
        ]
        Notification.objects.bulk_create(notifications)

        # If there's a discount, create/activate a global campaign automatically
        if discount_percentage:
            from apps.customer_club.models import GlobalDiscount
            from django.utils import timezone
            from datetime import timedelta
            GlobalDiscount.objects.create(
                name=title,
                description=message,
                percentage=discount_percentage,
                category='cosmetic',
                expires_at=timezone.now() + timedelta(days=30),
                created_by=request.user,
            )

        count = len(notifications)
        BroadcastMessage.objects.create(
            title=title,
            message=full_message,
            discount_percentage=discount_percentage,
            sent_by=request.user,
            recipient_count=count,
        )

        messages.success(request, f'پیام همگانی برای {count} کاربر ارسال شد.')
        return redirect('admin_broadcast')