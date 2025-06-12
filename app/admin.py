from django.contrib import admin
from .models import File, Translation

# Register your models here.
@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'status', 'created_at')
    list_filter = ('status', 'created_at')

@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'src_language', 'dst_language', 'status', 'created_at')
    list_filter = ('status', 'src_language', 'dst_language')
