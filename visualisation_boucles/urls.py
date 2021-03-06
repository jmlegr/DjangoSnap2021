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
    path('task_state/<str:task_id>/',views.task_state,name='task_state'),
    path('task_cancel/<str:task_id>/',views.task_cancel,name='task_cancel'),
    path('testadd/', views.testadd,name='testadd'),
    path('graph_boucles/',views.graph_boucles,name='graph_boucles'),
    path('celrep/',views.reperes,name="reperes"),
    path('sessionsMongo/',views.sessionsReconstruites,name='sessions_reconstruites')
    ]

urlpatterns += [
    url(r'^', include(router.urls))
]