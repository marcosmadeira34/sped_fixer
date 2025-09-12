# apps/core/forms.py
from django import forms
from .models import Upload

class UploadForm(forms.ModelForm):
    class Meta:
        model = Upload
        fields = ["file"]

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith((".txt", ".sped")):
            raise forms.ValidationError("Envie um arquivo .txt/.sped")
        return f