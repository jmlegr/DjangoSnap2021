"""DjangoSnap URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.urls.conf import include
from django.contrib.auth import views as auth_views
from DjangoSnap.settings import DEBUG
from django.conf.urls import url
from django.views.generic.base import RedirectView
import snap



urlpatterns = [
    #path('accounts/login/', auth_views.LoginView.as_view()),
    
     url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
     path('accounts/', include('django.contrib.auth.urls')),
     path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html')),
    path('admin/', admin.site.urls),
    path('snap/',include('snap.urls')),
    path('boucles/',include('visualisation_boucles.urls')),
    path('celery/',include('rendu_celery.urls')),
    path('login/',snap.views.login_redirect),
    path('logout/',snap.views.logout_view,name='logout'),
    path(r'',auth_views.LoginView.as_view()),
         #RedirectView.as_view(url='/accounts/login/')),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if DEBUG:
    urlpatterns=urlpatterns+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
