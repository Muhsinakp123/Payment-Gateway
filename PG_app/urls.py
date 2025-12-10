from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth APIs
    path('register/', views.register_user),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('products/', views.get_products),
    path('products/create/', views.create_product),
    path('products/<int:pk>/', views.get_single_product),
    path('products/<int:pk>/update/', views.update_product),
    path('products/<int:pk>/patch/', views.patch_product),
    path('products/<int:pk>/delete/', views.delete_product),
    
    path('order/', views.get_orders),
    path('order/create/', views.create_order),
    path('order/<int:pk>/', views.get_single_order),
    path('order/<int:pk>/update/', views.update_order),
    path('order/<int:pk>/patch/', views.patch_order),
    path('order/<int:pk>/delete/', views.delete_order),

    path('payments/create/', views.create_payment),
    path('payments/execute/', views.execute_payment),
    path('payments/cancel/', views.cancel_payment),
]
