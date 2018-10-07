from django.shortcuts import render

from rest_framework import viewsets
from snap.models import ProgrammeBase, EvenementEPR
from visualisation_boucles.serializers import ProgrammeBaseSerializer
# Create your views here.
def choixbase(request):
    """
    renvoit la page d'accueil de la visualisation des boucles
    (choix du programme de base)
    """
    return render(request,'visualisation_boucles/choixbase.html');
    
class ProgrammeBaseViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour Programme de Base
    """
    queryset=ProgrammeBase.objects.all();
    serializer_class=ProgrammeBaseSerializer

class SessionsProgViewset(viewsets.ViewSet):
    """
    Viewset pour liste des sessions d'un programme de base
    """
    def retrieve(self,request,pk=None):
        queryset=EvenementEPR.objects.all()
        EvenementEPR.objects.filter(type__in=['NEW','LOAD']).select_related('evenement','evenement__user').order_by('-evenement__creation')
