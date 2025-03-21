from django.urls import path
from django.contrib.auth import views as auth_views
from .views import  ChangePasswordView
from .views import ProfileUpdateView, ProfileDetailView, UserRegisterView, UserLoginView, UserLogoutView

urlpatterns = [
    path('user/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('user/<slug:slug>/', ProfileDetailView.as_view(), name='profile_detail'),

    # path('signup/', SignUpView.as_view(), name='signup'),
    # path('login/', CustomLoginView.as_view(redirect_authenticated_user=True, template_name='registration2/login.html'), name='login'),
    # path('logout/', auth_views.LogoutView.as_view(template_name='registration2/logout.html'), name='logout'),
    # path('profile/', profile, name='users-profile'),


    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(template_name='accounts/logout.html'), name='logout'),
    path('password_change/', ChangePasswordView.as_view(), name='password_change'),

]