"""User profile model extending Django auth user with avatar and bio."""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from services.utils import unique_slugify


class Profile(models.Model):
    """Stores additional display information for an authenticated user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    slug = models.SlugField(verbose_name='URL', max_length=255, blank=True, unique=True)
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='images/avatars/%Y/%m/%d/',
        default='images/avatars/default.jpg',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=('png', 'jpg', 'jpeg', 'dmg'))])
    bio = models.TextField('О себе', blank=True, null=True)

    class Meta:
        """Order profiles by user and provide readable admin names."""
        ordering = ('user',)
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def save(self, *args, **kwargs):
        """Ensure slug defaults to username when not provided."""
        if not self.slug:
            self.slug = unique_slugify(self, self.user.username, self.slug)
        super().save(*args, **kwargs)

    def __str__(self):
        """Return username for admin representations."""
        return self.user.username

    def get_absolute_url(self):
        """Return canonical URL of the profile detail page."""
        return reverse('profile_detail', kwargs={'slug': self.slug})
