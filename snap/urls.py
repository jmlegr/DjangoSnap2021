'''
Created on 4 déc. 2017

@author: duff
'''
from django.urls import path

from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import TemplateView

admin.site.site_header = 'Snap4Gironde'
admin.site.site_title='Snap4Gironde'
router = DefaultRouter()
router.register(r'progs', views.ProgrammeBaseViewset)
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'evenement',views.EvenementViewset)
router.register(r'epr',views.EvenementEPRViewset)
router.register(r'env',views.EvenementENVViewset)
router.register(r'spr',views.EvenementSPRViewset)
router.register(r'spropen',views.EvenementSPROpenViewset)
router.register(r'spr/block',views.BlockViewSet)

urlpatterns = [
   
    path('test',views.testsnap,name='snaptest'),    
    path('pageref',views.pageref),
     path('pagedon',views.pagedon),
     path('ups',views.simple_upload),  
     path('up',views.model_form_upload),
    # path('upload',views.upload),
    path('fichier',views.return_fichier),
    path('fichier/<int:file_id>', views.return_fichier_eleve),
    #path('cd',views.current_datetime),
    path('cd',views.return_files),    
    path('liste/',views.liste),
    path('liste/<str:nom>/',views.liste),
    path('sessions',views.listeSessions),
    path('session/<str:id>/',views.session),
    path('opens',views.listeOpens),
    #path('open/',views.listeOpen),
    #path('open/<str:id>/',views.listeOpen),
    path('cyto',views.cyto),
    path('cyto/<str:id>/',views.cyto,),
    path('cyto2',views.cyto3),
    path('tb',views.testblock),
    path('tb/<str:id>/',views.testblock),
    path('d33',TemplateView.as_view(template_name='index.html')),
    path('d3',TemplateView.as_view(template_name='representation.html')),
     path('c2',TemplateView.as_view(template_name='testcyto2.html')),
     path('ajax',views.testAjax),
    ]

urlpatterns += [
    url(r'^', include(router.urls))
]
urlpatterns += [url(r'^silk/', include('silk.urls', namespace='silk'))]

