from django.contrib import admin

# Register your models here.
from .models import Question, ActionProgrammation, Bounds, DroppedBlock, Inputs, Point

admin.site.register(Question)
admin.site.register(ActionProgrammation)
admin.site.register(Bounds)
admin.site.register(DroppedBlock)
admin.site.register(Inputs)
admin.site.register(Point)
