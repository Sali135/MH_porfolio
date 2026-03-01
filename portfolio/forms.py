from django import forms

from .models import ContactMessage, Project


class ContactMessageForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("website"):
            raise forms.ValidationError("Spam detection triggered.")
        return cleaned_data


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("title", "description", "image", "url", "date", "is_featured")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
