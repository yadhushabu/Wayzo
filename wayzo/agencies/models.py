from django.db import models
from django.conf import settings

class AgencyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    agency_name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100)
    license_document = models.FileField(upload_to='agency/licenses/',null=True,blank=True)
    place_id_proof = models.FileField(upload_to='agency/idproofs/',null=True,blank=True)

    address = models.TextField()
    mobile = models.CharField(max_length=15)
    city=models.CharField(max_length=20)
    state=models.CharField(max_length=20)

    is_approved = models.BooleanField(default=False)

