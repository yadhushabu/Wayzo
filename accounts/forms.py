from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import CustomUser

from travellers.models import TravellerProfile
from agencies.models import AgencyProfile
from restaurants.models import RestaurantProfile



# ---------------- TRAVELLER ----------------
class TravellerSignUpForm(UserCreationForm):
    profile_picture=forms.ImageField(required=True)
    first_name = forms.CharField()
    last_name = forms.CharField()
    mobile = forms.CharField()
    age = forms.IntegerField()
    gender = forms.ChoiceField(
        choices=(('male','Male'), ('female','Female'), ('other','Other'))
    )
    address=forms.CharField(widget=forms.Textarea)
    city=forms.CharField()
    state=forms.CharField()

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'traveller'
        user.profile_picture = self.cleaned_data.get('profile_picture')
        if commit:
            user.save()
            TravellerProfile.objects.create(
                user=user,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                mobile=self.cleaned_data['mobile'],
                age=self.cleaned_data['age'],
                gender=self.cleaned_data['gender'],
                address=self.cleaned_data['address'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
                )
        return user




# ---------------- AGENCY ----------------
class AgencySignUpForm(UserCreationForm):
    profile_picture=forms.ImageField(required=True)
    agency_name = forms.CharField()
    license_number = forms.CharField()
    license_document = forms.FileField()
    id_proof = forms.FileField()
    address = forms.CharField(widget=forms.Textarea)
    mobile = forms.CharField()
    city=forms.CharField()
    state=forms.CharField()

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email',
            'password1', 'password2'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'agency'
        user.profile_picture = self.cleaned_data.get('profile_picture')
        user.is_approved = False

        if commit:
            user.save()
            AgencyProfile.objects.create(
                user=user,
                agency_name=self.cleaned_data['agency_name'],
                license_number=self.cleaned_data['license_number'],
                license_document=self.cleaned_data['license_document'],
                id_proof=self.cleaned_data['id_proof'],
                address=self.cleaned_data['address'],
                mobile=self.cleaned_data['mobile'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'] 
            )
        return user


# ---------------- RESTAURANT ----------------
class RestaurantSignUpForm(UserCreationForm):

    profile_picture = forms.ImageField(required=True)
    restaurant_name = forms.CharField()

    property_type = forms.ChoiceField(
    choices=RestaurantProfile._meta.get_field('property_type').choices,
    label="Property Type",
    required=True
)

    fssai_license_number = forms.CharField()
    license_document = forms.FileField()
    id_proof = forms.FileField()
    address = forms.CharField(widget=forms.Textarea)
    mobile = forms.CharField()
    city = forms.CharField()
    state = forms.CharField()

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'password1',
            'password2',
            'property_type'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'restaurant'
        user.profile_picture = self.cleaned_data.get('profile_picture')
        user.is_approved = False

        if commit:
            user.save()

            RestaurantProfile.objects.create(
                user=user,
                restaurant_name=self.cleaned_data['restaurant_name'],
                property_type=self.cleaned_data['property_type'],
                fssai_license_number=self.cleaned_data['fssai_license_number'],
                license_document=self.cleaned_data['license_document'],
                id_proof=self.cleaned_data['id_proof'],
                address=self.cleaned_data['address'],
                mobile=self.cleaned_data['mobile'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
            )

        return user