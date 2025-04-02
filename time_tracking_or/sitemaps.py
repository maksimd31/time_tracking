# карта сайта
from django.contrib.sitemaps import Sitemap
from .models import TimeInterval


class TimeIntervalSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return TimeInterval.objects.all()

    def lastmod(self, obj):
        return obj.updated

# нужно добавить в модели get_absolute_url().
