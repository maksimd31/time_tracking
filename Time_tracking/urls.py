from django.contrib.sitemaps.views import sitemap
from time_tracking_or.sitemaps import TimeIntervalSitemap
from django.urls import re_path
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

sitemaps = {
    'TimeInterval': TimeIntervalSitemap,
}

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('', include('accounts.urls')),
                  path('', include("time_tracking_or.urls")),
                  path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
                  # path('auth/', include('rest_framework_social_oauth2.urls', namespace='rest_framework_social_oauth2')),
                  # path('social/', include('social_django.urls', namespace='social')),
                  # path('auth/', include('social_django.urls', namespace='social')),
                  # re_path(r'^oauth/', include('social_django.urls', namespace='social')),
                  path('social-auth/', include('social_django.urls', namespace='social')),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]

# http://127.0.0.1:8000/accounts/login/

# accounts/login/ [name='login']
# accounts/logout/ [name='logout']
# accounts/password_change/ [name='password_change']
# accounts/password_change/done/ [name='password_change_done']
# accounts/password_reset/ [name='password_reset']
# accounts/password_reset/done/ [name='password_reset_done']
# accounts/reset/<uidb64>/<token>/ [name='password_reset_confirm']
# accounts/reset/done/ [name='password_reset_complete']
