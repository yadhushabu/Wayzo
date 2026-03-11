

# Create your models here.
from django.db import models
from django.conf import settings

class TravellerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    age = models.PositiveIntegerField()
    gender = models.CharField(
        max_length=10,
        choices=(('male','Male'),('female','Female'),('other','Other'))
    )
    address=models.TextField()
    city=models.CharField(max_length=20)
    state=models.CharField(max_length=20)
