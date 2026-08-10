from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import Service, BusinessHour, Booking, Payment


# ──────────────────────────────────────────────────────────────
# Service Admin
# ──────────────────────────────────────────────────────────────

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_display', 'duration_display', 'is_active', 'sort_order', 'image_preview']
    list_editable = ['is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'price']
    actions = ['activate_services', 'deactivate_services']

    fieldsets = (
        ('Service Info', {
            'fields': ('name', 'description', 'icon', 'image', 'sort_order')
        }),
        ('Pricing & Duration', {
            'fields': ('price', 'duration')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def price_display(self, obj):
        return f"₹{int(obj.price):,}"
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'

    def duration_display(self, obj):
        return f"{obj.duration} min"
    duration_display.short_description = 'Duration'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.image.url)
        return '—'
    image_preview.short_description = 'Preview'

    @admin.action(description='Activate selected services')
    def activate_services(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} service(s) activated.")

    @admin.action(description='Deactivate selected services')
    def deactivate_services(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} service(s) deactivated.")


# ──────────────────────────────────────────────────────────────
# Business Hours Admin
# ──────────────────────────────────────────────────────────────

@admin.register(BusinessHour)
class BusinessHourAdmin(admin.ModelAdmin):
    list_display = ['get_day_display', 'opening_time', 'closing_time', 'is_closed']
    list_editable = ['opening_time', 'closing_time', 'is_closed']
    ordering = ['day']

    def get_day_display(self, obj):
        return obj.get_day_display()
    get_day_display.short_description = 'Day'
    get_day_display.admin_order_field = 'day'


# ──────────────────────────────────────────────────────────────
# Payment Inline
# ──────────────────────────────────────────────────────────────

class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ['transaction_id', 'payment_method', 'created_at', 'updated_at']
    fields = ['amount', 'status', 'transaction_id', 'payment_method', 'created_at', 'updated_at']


# ──────────────────────────────────────────────────────────────
# Booking Admin
# ──────────────────────────────────────────────────────────────

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_id', 'customer_name', 'service', 'booking_date',
        'booking_time_display', 'status_badge', 'amount_display', 'payment_status'
    ]
    list_filter = ['status', 'booking_date', 'service']
    search_fields = ['booking_id', 'customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['booking_id', 'created_at', 'updated_at', 'amount']
    date_hierarchy = 'booking_date'
    ordering = ['-booking_date', '-booking_time']
    inlines = [PaymentInline]
    actions = ['mark_completed', 'mark_cancelled']

    fieldsets = (
        ('Booking Info', {
            'fields': ('booking_id', 'service', 'booking_date', 'booking_time', 'amount', 'status')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'special_request')
        }),
        ('User Account', {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def booking_time_display(self, obj):
        return obj.booking_time.strftime('%I:%M %p')
    booking_time_display.short_description = 'Time'
    booking_time_display.admin_order_field = 'booking_time'

    def amount_display(self, obj):
        return f"₹{int(obj.amount):,}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#f59e0b',
            'CONFIRMED': '#10b981',
            'COMPLETED': '#6366f1',
            'CANCELLED': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def payment_status(self, obj):
        try:
            status = obj.payment.status
            colors = {
                'PENDING': '#f59e0b',
                'PAID': '#10b981',
                'FAILED': '#ef4444',
                'REFUNDED': '#6366f1',
            }
            color = colors.get(status, '#6b7280')
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
                color, status
            )
        except Payment.DoesNotExist:
            return '—'
    payment_status.short_description = 'Payment'

    @admin.action(description='Mark selected bookings as Completed')
    def mark_completed(self, request, queryset):
        count = queryset.filter(status=Booking.STATUS_CONFIRMED).update(status=Booking.STATUS_COMPLETED)
        self.message_user(request, f"{count} booking(s) marked as Completed.")

    @admin.action(description='Mark selected bookings as Cancelled')
    def mark_cancelled(self, request, queryset):
        count = queryset.exclude(
            status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_COMPLETED]
        ).update(status=Booking.STATUS_CANCELLED)
        self.message_user(request, f"{count} booking(s) marked as Cancelled.")


# ──────────────────────────────────────────────────────────────
# Payment Admin
# ──────────────────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['booking_link', 'amount_display', 'status_badge', 'payment_method', 'transaction_id', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['booking__booking_id', 'transaction_id', 'booking__customer_name']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def booking_link(self, obj):
        url = reverse('admin:booking_booking_change', args=[obj.booking.pk])
        return format_html('<a href="{}">{}</a>', url, obj.booking.booking_id)
    booking_link.short_description = 'Booking'

    def amount_display(self, obj):
        return f"₹{int(obj.amount):,}"
    amount_display.short_description = 'Amount'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#f59e0b',
            'PAID': '#10b981',
            'FAILED': '#ef4444',
            'REFUNDED': '#6366f1',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
