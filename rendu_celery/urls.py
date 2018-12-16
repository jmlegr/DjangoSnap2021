'''
Created on 16 déc. 2018

@author: duff
'''
from django.urls import path

from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
#router.register(r'progs', views.ProgrammeBaseViewset)

urlpatterns = [
    path('add',views.celery_add,name='celery_add'),
    path('poll_state', views.poll_state,name='poll_state'),
    ]

urlpatterns += [
    url(r'^', include(router.urls))
]