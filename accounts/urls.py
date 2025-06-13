from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import CustomPasswordResetForm
from .views import ChangePasswordView
from .views import ProfileUpdateView, ProfileDetailView, UserRegisterView, UserLoginView, UserLogoutView

urlpatterns = [
    # path("social-auth/", views.SocialAuthView.as_view(), name="social_auth"),

    # path('vkid/callback/', views.vkid_callback, name='vkid_callback'),
    path('complete/vk-app/', views.vkid_token, name='vkid_callback'),

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

    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             form_class=CustomPasswordResetForm,
             template_name='accounts/password_reset/password_reset_form.html',
             email_template_name='accounts/password_reset/password_reset_email.html'
         ),
         name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset/password_reset_done.html', ),
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),

    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset/password_reset_complete.html'
         ),
         name='password_reset_complete'),

]
