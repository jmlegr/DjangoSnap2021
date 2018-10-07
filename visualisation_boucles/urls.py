'''
Created on 7 oct. 2018

@author: duff
'''
from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url
from . import views
router = DefaultRouter()
router.register(r'progs', views.ProgrammeBaseViewset)
router.register(r'bases',views.SessionsProgViewset,base_name='sessionsprog')
router.register(r'actions',views.SessionEvenementsViewset,base_name='actions')
urlpatterns = [
    path('base',views.choixbase,name='choixprg_base'),
    ]

urlpatterns += [
    url(r'^', include(router.urls))
]