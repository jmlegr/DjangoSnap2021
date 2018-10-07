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
urlpatterns = [
    path('base',views.choixbase,name='choix_base'),
    ]

urlpatterns += [
    url(r'^', include(router.urls))
]