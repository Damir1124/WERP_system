from django.contrib import admin
from .models import Worker

class WorkerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'worker_type', 'created_at', 'updated_at')
    list_filter = ('worker_type', 'created_at')
    search_fields = ('full_name',)
    ordering = ('-created_at',)

admin.site.register(Worker, WorkerAdmin)

