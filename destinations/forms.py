from django import forms
from .models import Attraction, Destination, AttractionCost

class DestinationForm(forms.ModelForm):
    class Meta:
        model = Destination
        fields = '__all__'

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Manali, Goa, Darjeeling'
            }),

            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated (leave blank)'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),

            'state': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'country': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any'
            }),

            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any'
            }),

            'best_season': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'comma separated (e.g. beach, adventure)'
            }),

            'avg_budget_per_day': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'how_to_reach': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),

            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'is_popular': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    # ✅ VALIDATIONS

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or len(name) < 3:
            raise forms.ValidationError('Minimum 3 characters required')
        return name.title()

    def clean_description(self):
        desc = self.cleaned_data.get('description')
        if not desc or len(desc) < 100:
            raise forms.ValidationError('Minimum 100 characters required')
        return desc

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is not None and (lat < -90 or lat > 90):
            raise forms.ValidationError('Latitude must be between -90 and 90')
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data.get('longitude')
        if lng is not None and (lng < -180 or lng > 180):
            raise forms.ValidationError('Longitude must be between -180 and 180')
        return lng

    def clean_tags(self):
        tags = self.cleaned_data.get('tags')

        valid_tags = [
            'beach', 'hill-station', 'adventure', 'honeymoon',
            'pilgrimage', 'heritage', 'wildlife', 'trekking',
            'backwaters', 'desert', 'cultural'
        ]

        if tags:
            tag_list = [t.strip().lower() for t in tags.split(',')]
            invalid = [t for t in tag_list if t not in valid_tags]

            if invalid:
                raise forms.ValidationError(
                    f'Invalid tags: {", ".join(invalid)}'
                )

        return tags
    

class AttractionForm(forms.ModelForm):
    class Meta:
        model = Attraction
        fields = '__all__'

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),

            'entry_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'extra_cost_per_person': forms.NumberInput(attrs={'class': 'form-control'}),
            'group_cost': forms.NumberInput(attrs={'class': 'form-control'}),

            'activities': forms.TextInput(attrs={'class': 'form-control'}),
            'best_months': forms.TextInput(attrs={'class': 'form-control'}),

            'difficulty_level': forms.Select(attrs={'class': 'form-control'}),

            'important_rules': forms.Textarea(attrs={'class': 'form-control'}),

            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class AttractionCostForm(forms.ModelForm):
    class Meta:
        model = AttractionCost
        fields = ['title', 'price']

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    

from django.forms import inlineformset_factory

AttractionCostFormSet = inlineformset_factory(
    Attraction,
    AttractionCost,
    form=AttractionCostForm,
    extra=2,
    can_delete=True
)