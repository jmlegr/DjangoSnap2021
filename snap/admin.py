from django.contrib import admin, messages

# Register your models here.
from .models import Document, Evenement, EvenementEPR, EvenementENV, \
        Eleve, Classe, EvenementSPR, ProgrammeBase,Block


class DocumentAdmin(admin.ModelAdmin):
    list_display=['description','user','document','uploaded_at']
    readonly_fields=['user','uploaded_at',]
    list_filter=('user__eleve__classe','uploaded_at')
    list_display_links = None

class ClasseAdmin(admin.ModelAdmin):
    model=Classe
    


class EleveAdmin(admin.ModelAdmin):    
    list_display=('user','classe','prg')
    list_editable=('prg',)
    #liste_select_related=('prg',)
    list_filter = (
        ('classe', admin.RelatedOnlyFieldListFilter),
    )
    actions=['copy_base_to_classe',]
    """
    def get_queryset(self, obj):
        qs=super(EleveAdmin,self).get_queryset(obj)
        return qs.prefetch_related('prg__id','prg__nom')
    """
    """
    def copy_base_to_classe(self, request, queryset):
        # do something with the queryset
        if queryset.count()!=1:
            self.message_user(request,'Il ne faut sélectionner qu\'UN seul élève!',level=messages.ERROR)
            return
        eleve=queryset[0]
        if eleve.prg is None:
            self.message_user(request,'Tous les élèves de la classe de '+eleve.user.username+' n\'ont plus de programme de séance',level=messages.WARNING )
        else:
            self.message_user(request,'ok copié'+eleve.prg.nom+' de '+eleve.user.username+'à tous les élèves de '+eleve.classe.nom)
        print('ok',queryset)
    copy_base_to_classe.short_description = 'Copier le programme de la séance à tous les élèves de la classe'
    """
    #list_filter=('actif',)
    #search_fields=['nom','prenom']
    #inlines=[Prg,]

class EvenementSPRAdmin(admin.ModelAdmin):
    model=EvenementSPR
    
admin.site.register(Classe,ClasseAdmin)
admin.site.register(Eleve,EleveAdmin)
admin.site.register(Document,DocumentAdmin)
admin.site.register(ProgrammeBase)
admin.site.register(Evenement)
admin.site.register(EvenementENV)
admin.site.register(EvenementEPR)
admin.site.register(EvenementSPR,EvenementSPRAdmin)
admin.site.register(Block)

