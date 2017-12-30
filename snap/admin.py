from django.contrib import admin

# Register your models here.
from .models import ActionProgrammation, Bounds, DroppedBlock, Inputs, \
        Point, Document, Evenement, EvenementEPR, EvenementENV, ProgrammeBase


class DocumentAdmin(admin.ModelAdmin):
    readonly_fields=['uploaded_at',]
    

admin.site.register(ActionProgrammation)
admin.site.register(Bounds)
admin.site.register(DroppedBlock)
admin.site.register(Inputs)
admin.site.register(Point)
admin.site.register(Document,DocumentAdmin)
admin.site.register(Evenement)
admin.site.register(EvenementEPR)
admin.site.register(EvenementENV)
admin.site.register(ProgrammeBase)