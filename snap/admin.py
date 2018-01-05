from django.contrib import admin

# Register your models here.
from .models import Document, Evenement, EvenementEPR, EvenementENV, \
        Eleve, Classe


class DocumentAdmin(admin.ModelAdmin):
    list_display=['description','user','document','uploaded_at']
    readonly_fields=['user','uploaded_at',]
    list_filter=('user__eleve__classe','uploaded_at')
    list_display_links = None

class ClasseAdmin(admin.ModelAdmin):
    model=Classe
    
    
class EleveAdmin(admin.ModelAdmin):    
    list_display=('user','classe','prg')
    list_editable=('classe','prg')
    list_filter = (
        ('classe', admin.RelatedOnlyFieldListFilter),
    )
    #list_filter=('actif',)
    #search_fields=['nom','prenom']
    #inlines=[Prg,]
    

    

admin.site.register(Document,DocumentAdmin)
admin.site.register(Evenement)
admin.site.register(EvenementEPR)
admin.site.register(EvenementENV)
admin.site.register(Classe,ClasseAdmin)
admin.site.register(Eleve,EleveAdmin)

