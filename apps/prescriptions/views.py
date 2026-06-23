from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.contrib import messages

from .models import Prescription, PrescriptionItem
from apps.notifications.models import Notification


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ==================== USER VIEWS ====================

class SubmitPrescriptionView(View):
    @method_decorator(login_required)
    def post(self, request):
        tracking_code = request.POST.get('tracking_code', '').strip()
        national_id = request.POST.get('national_id', '').strip()

        if not tracking_code or not national_id:
            return JsonResponse({'success': False, 'error': 'لطفاً تمام فیلدها را پر کنید.'})

        if len(national_id) != 10:
            return JsonResponse({'success': False, 'error': 'کد ملی باید ۱۰ رقم باشد.'})

        existing = Prescription.objects.filter(
            user=request.user,
            tracking_code=tracking_code,
            status__in=['pending', 'items_entered', 'ready']
        ).first()
        if existing:
            return JsonResponse({'success': False, 'error': 'این نسخه قبلاً ثبت شده است.'})

        prescription = Prescription.objects.create(
            user=request.user,
            tracking_code=tracking_code,
            national_id=national_id,
        )

        Notification.objects.create(
            user=request.user,
            title='نسخه دریافت شد',
            message=(
                f'نسخه با کد رهگیری {tracking_code} دریافت شد و در حال بررسی است. '
                f'داروساز کد را در سایت بیمه بررسی کرده و به زودی وضعیت اقلام را اعلام می‌کند.'
            ),
            notification_type='prescription'
        )

        return JsonResponse({
            'success': True,
            'message': f'نسخه با کد رهگیری {tracking_code} در حال بررسی است.'
        })


class MyPrescriptionsView(View):
    @method_decorator(login_required)
    def get(self, request):
        prescriptions = Prescription.objects.filter(
            user=request.user
        ).prefetch_related('items').order_by('-created_at')
        return render(request, 'prescriptions/list.html', {'prescriptions': prescriptions})


# ==================== ADMIN VIEWS ====================

class AdminDashboardView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request):
        total_users = Prescription.objects.values('user').distinct().count()
        pending = Prescription.objects.filter(status='pending').count()
        items_entered = Prescription.objects.filter(status='items_entered').count()
        ready = Prescription.objects.filter(status='ready').count()
        partial = Prescription.objects.filter(status='partial').count()
        recent_prescriptions = Prescription.objects.select_related('user').order_by('-created_at')[:10]

        context = {
            'total_users': total_users,
            'pending': pending,
            'items_entered': items_entered,
            'ready': ready,
            'partial': partial,
            'recent_prescriptions': recent_prescriptions,
        }
        return render(request, 'admin_panel/dashboard.html', context)


class AdminPrescriptionsView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request):
        status_filter = request.GET.get('status', '')
        prescriptions = Prescription.objects.select_related('user').order_by('-created_at')
        if status_filter:
            prescriptions = prescriptions.filter(status=status_filter)

        context = {
            'prescriptions': prescriptions,
            'status_filter': status_filter,
            'STATUS_CHOICES': Prescription.STATUS_CHOICES,
        }
        return render(request, 'admin_panel/prescriptions.html', context)


class AdminPrescriptionDetailView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request, pk):
        prescription = get_object_or_404(
            Prescription.objects.prefetch_related('items'), pk=pk
        )
        return render(request, 'admin_panel/prescription_detail.html', {
            'prescription': prescription,
        })

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def post(self, request, pk):
        prescription = get_object_or_404(Prescription, pk=pk)
        action = request.POST.get('action')

        # ── Step 1: Add a single drug item ──
        if action == 'add_item':
            drug_name = request.POST.get('drug_name', '').strip()
            quantity = request.POST.get('quantity', '').strip()
            dosage = request.POST.get('dosage', '').strip()
            is_available = request.POST.get('is_available', 'true') == 'true'

            if not drug_name or not quantity:
                messages.error(request, 'نام دارو و مقدار الزامی هستند.')
            else:
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    drug_name=drug_name,
                    quantity=quantity,
                    dosage=dosage,
                    is_available=is_available,
                )
                # Update status to items_entered
                if prescription.status == 'pending':
                    prescription.status = 'items_entered'
                    prescription.save(update_fields=['status'])
                messages.success(request, f'قلم «{drug_name}» اضافه شد.')
            return redirect('admin_prescription_detail', pk=pk)

        # ── Step 2: Delete an item ──
        if action == 'delete_item':
            item_id = request.POST.get('item_id')
            PrescriptionItem.objects.filter(pk=item_id, prescription=prescription).delete()
            messages.success(request, 'قلم حذف شد.')
            return redirect('admin_prescription_detail', pk=pk)

        # ── Step 3: Toggle item availability ──
        if action == 'toggle_item':
            item_id = request.POST.get('item_id')
            try:
                item = PrescriptionItem.objects.get(pk=item_id, prescription=prescription)
                item.is_available = not item.is_available
                item.save(update_fields=['is_available'])
            except PrescriptionItem.DoesNotExist:
                pass
            return redirect('admin_prescription_detail', pk=pk)

        # ── Step 4: Finalize — All Ready ──
        if action == 'ready':
            if not prescription.items.exists():
                messages.error(request, 'ابتدا اقلام نسخه را وارد کنید.')
                return redirect('admin_prescription_detail', pk=pk)

            notes = request.POST.get('admin_notes', '').strip()
            prescription.status = 'ready'
            prescription.admin_notes = notes
            prescription.save()

            items_list = '\n'.join(
                f"✅ {i.drug_name} — {i.quantity}" + (f" | {i.dosage}" if i.dosage else "")
                for i in prescription.items.all()
            )

            Notification.objects.create(
                user=prescription.user,
                title='نسخه آماده تحویل است ✅',
                message=(
                    f'نسخه شما با کد رهگیری {prescription.tracking_code} آماده است.\n\n'
                    f'اقلام آماده:\n{items_list}\n\n'
                    f'برای دریافت داروها به داروخانه مراجعه کنید.'
                ),
                notification_type='prescription'
            )
            messages.success(request, 'نسخه «آماده» اعلام شد و کاربر مطلع گردید.')
            return redirect('admin_prescription_detail', pk=pk)

        # ── Step 5b: Mark as Delivered ──
        if action == 'delivered':
            prescription.status = 'delivered'
            prescription.save(update_fields=['status'])

            Notification.objects.create(
                user=prescription.user,
                title='داروهای شما تحویل داده شد ✅',
                message=(
                    f'داروهای نسخه با کد رهگیری {prescription.tracking_code} '
                    f'با موفقیت تحویل داده شد. ممنون از اعتماد شما.'
                ),
                notification_type='prescription'
            )
            messages.success(request, 'وضعیت نسخه به «تحویل داده شده» تغییر یافت.')
            return redirect('admin_prescription_detail', pk=pk)

        # ── Step 5: Finalize — Partial ──
        if action == 'partial':
            if not prescription.items.exists():
                messages.error(request, 'ابتدا اقلام نسخه را وارد کنید.')
                return redirect('admin_prescription_detail', pk=pk)

            notes = request.POST.get('admin_notes', '').strip()
            if not notes:
                messages.error(request, 'لطفاً توضیحات اقلام ناموجود را وارد کنید.')
                return redirect('admin_prescription_detail', pk=pk)

            prescription.status = 'partial'
            prescription.admin_notes = notes
            prescription.save()

            unavailable = prescription.unavailable_items()
            unavail_list = '\n'.join(
                f"❌ {i.drug_name} — {i.quantity}" for i in unavailable
            )
            available = prescription.items.filter(is_available=True)
            avail_list = '\n'.join(
                f"✅ {i.drug_name} — {i.quantity}" for i in available
            )

            Notification.objects.create(
                user=prescription.user,
                title='موجودی نسخه ناقص است ⚠️',
                message=(
                    f'نسخه شما با کد رهگیری {prescription.tracking_code} بررسی شد.\n\n'
                    f'اقلام موجود:\n{avail_list}\n\n'
                    f'اقلام ناموجود:\n{unavail_list}\n\n'
                    f'توضیحات داروساز: {notes}'
                ),
                notification_type='prescription'
            )
            messages.success(request, 'وضعیت «موجودی ناقص» ثبت شد و کاربر مطلع گردید.')
            return redirect('admin_prescription_detail', pk=pk)

        messages.error(request, 'عملیات نامعتبر.')
        return redirect('admin_prescription_detail', pk=pk)


class DeletePrescriptionView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def post(self, request, pk):
        prescription = get_object_or_404(Prescription, pk=pk)
        tracking_code = prescription.tracking_code
        prescription.delete()
        messages.success(request, f'نسخه با کد رهگیری {tracking_code} حذف شد.')
        return redirect('admin_prescriptions')