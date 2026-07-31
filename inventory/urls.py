from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("stock/", views.stock_entry, name="stock_entry"),
    path("register/", views.stock_register, name="stock_register"),
    path("upload/", views.upload_consumption, name="upload_consumption"),
    path("reports/", views.consumption_report, name="consumption_report"),
]
