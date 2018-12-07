from django import forms
from snap.models import Document, ProgrammeBase
from django.forms.models import ModelForm

class ExportXMLForm(forms.Form):
    base=forms.BooleanField(initial=False, required=False)
    autosave=forms.BooleanField(initial=False, required=False)
    description=forms.CharField(max_length=255, required=False)
    nom=forms.CharField(max_length=50)
    document=forms.FileField()
    
class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ('description', 'document',  )
    
class ProgBaseForm(forms.ModelForm):
    class Meta:
        model=ProgrammeBase
        fields=('nom','file',)
