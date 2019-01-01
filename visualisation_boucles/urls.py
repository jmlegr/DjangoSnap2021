'''
Created on 7 oct. 2018

@author: duff
'''
from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url
from visualisation_boucles import views

router = DefaultRouter()
router.register(r'progs', views.ProgrammeBaseViewset)
router.register(r'bases',views.SessionsProgViewset,base_name='sessionsprog')
router.register(r'actions',views.SessionEvenementsViewset,base_name='actions')
router.register(r'sessions',views.SimpleSessionViewset,base_name='sessions')
urlpatterns = [
    path('base',views.choixbase,name='choixprg_base'),
    path('select',views.selectSessions),
    #path('toliste/<str:session_key>/',reconstitution.listeblock),
    path('toliste/<str:session_key>/',views.celery_listeblock,name='celery_listeblock'),
    path('toliste$',views.celery_listeblock,name='celery_listeblock'),
    path('tolisteblock_state/<str:task_id>/',views.listeblock_state,name='listeblock_state'),
    path('tolisteblock_cancel/<str:task_id>/', views.listeblock_cancel,name='listeblock_cancel'),
    path('testadd_state/<str:task_id>/',views.testadd_state,name='testadd_state'),
    path('testadd', views.testadd,name='testadd'),
    path('boucle',views.graph_boucles,name='graph_boucles'),
    ]

urlpatterns += [
    url(r'^', include(router.urls))
]