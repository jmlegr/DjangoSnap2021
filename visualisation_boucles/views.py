from django.shortcuts import render

from rest_framework import viewsets
from snap.models import ProgrammeBase, EvenementEPR, EvenementENV, Evenement
from visualisation_boucles.serializers import ProgrammeBaseSerializer, EvenementENVSerializer, SimpleEvenementSerializer
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
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
    def list(self,request):
        queryset=EvenementENV.objects.filter(type='LOBA')\
                    .order_by('evenement__user','evenement__creation')\
                    .select_related('evenement')
        
        serializer=EvenementENVSerializer(queryset,many=True)
        return Response(serializer.data)
    
    def retrieve(self,request,pk=None):
        queryset=EvenementENV.objects.filter(type='LOBA',valueInt=pk)\
                    .order_by('evenement__user','evenement__creation')\
                    .select_related('evenement')        
        serializer=EvenementENVSerializer(queryset,many=True)
        return Response(serializer.data)
    
class SessionEvenementsViewset(viewsets.ViewSet):
    """
    viewset pour la liste des évenements constituants un ensemble d'action sur un même programme
    """
    def retrieve(self,request,pk=None):
        """
        pk contient l'evenement de départ, on renvoit tous les évènements de la même session
        jusqu'à un EPR LOAD ou NEW
        """
        evt=Evenement.objects.get(id=pk)
        firstEvt=EvenementEPR.objects.filter(evenement__session_key=evt.session_key,
                                               evenement__creation__gte=evt.creation,
                                               type__in=['LOAD','NEW'])\
                                               .earliest('evenement__creation')
        try:
            nextEvtEPR=EvenementEPR.objects.filter(evenement__session_key=firstEvt.evenement.session_key,
                                               evenement__creation__gt=firstEvt.evenement.creation,
                                               type__in=['LOAD','NEW'])\
                                               .earliest('evenement__creation')
            evts=Evenement.objects.filter(session_key=firstEvt.evenement.session_key,
                                          creation__gte=firstEvt.evenement.creation,
                                      creation__lt=nextEvtEPR.evenement.creation
                                      ).order_by('numero')
        
        except ObjectDoesNotExist:
            #ensemble d'action jusqu'à la fin de la session
            evts=Evenement.objects.filter(session_key=firstEvt.evenement.session_key,
                                          creation__gt=firstEvt.evenement.creation
                                          ).order_by('numero')
        serializer=SimpleEvenementSerializer(evts,many=True)
        return Response(serializer.data)
        
