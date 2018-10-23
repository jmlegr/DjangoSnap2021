from django.shortcuts import render

from rest_framework import viewsets
from snap.models import ProgrammeBase, EvenementEPR, EvenementENV, Evenement
from visualisation_boucles.serializers import ProgrammeBaseSerializer, EvenementENVSerializer, SimpleEvenementSerializer\
                    ,VerySimpleEvenementSerializer, ResumeSessionSerializer
               
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.db.models.aggregates import Min, Max, Count
# Create your views here.
def choixbase(request):
    """
    renvoit la page d'accueil de la visualisation des boucles
    (choix du programme de base)
    """
    return render(request,'visualisation_boucles/choixbase.html');
def selectSessions(request):
    return render(request,'visualisation_boucles/selectSessions.html')

class ProgrammeBaseViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour Programme de Base
    """
    queryset=ProgrammeBase.objects.all();
    serializer_class=ProgrammeBaseSerializer

    @detail_route()
    def sessions(self,request,pk=None):
        """
        renvoie la liste des sessions (au sens debut d'un travail) sur le programme donné
        """
        queryset=EvenementENV.objects.filter(type='LOBA',valueInt=pk)\
                    .order_by('evenement__user','evenement__creation')\
                    .select_related('evenement')        
        serializer=EvenementENVSerializer(queryset,many=True)
        return Response(serializer.data)
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
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer,)
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
        if request.accepted_renderer.format == 'html':
            return Response({'data':serializer.data},template_name='visualisation_boucles/actionsimple.html')
                            
        return Response(serializer.data)

from django.db import connection
class SimpleSessionViewset(viewsets.ViewSet): 
    renderer_classes = (JSONRenderer, )    

    
    def list(self,request):
        """
        renvoie la liste des sessions/utilisateurs, avec date de début et de fin, infos utilisateurs et classe,
        nbre d'évènements de chaque catégories, nombre de chargement et nom du programme chargé (si base) ou id (si document)
        """
        cursor=connection.cursor()
        req="""SELECT DISTINCT snap_evenement.session_key, snap_evenement.user_id as user, 
snap_eleve.id AS eleve_id, auth_user.username as user_nom, snap_eleve.classe_id as classe_id, snap_classe.nom as classe_nom,
MIN(snap_evenement.creation) AS debut, 
MAX(snap_evenement.creation) AS fin, 
COUNT(snap_evenement.session_key) AS nb_evts,
COUNT(CASE WHEN snap_evenement.type = 'ENV' then snap_evenement.id ELSE NULL END) as nbEnv,
COUNT(CASE WHEN snap_evenement.type = 'EPR' then snap_evenement.id ELSE NULL END) as nbEpr,
COUNT(CASE WHEN snap_evenement.type = 'SPR' then snap_evenement.id ELSE NULL END) as nbSpr,
COUNT(CASE WHEN snap_evenementepr.type = 'LOAD' THEN snap_evenement.id ELSE NULL END) as nbLoads,
COUNT(CASE WHEN snap_evenementepr.type = 'NEW' THEN snap_evenement.id ELSE NULL END) as nbNew,
COUNT(CASE WHEN snap_evenementenv.type = 'LANCE' THEN snap_evenement.id ELSE NULL END) as nbLance,
GROUP_CONCAT(distinct if (snap_evenementepr.type="LOAD",snap_evenementepr.detail,null) ) AS loads 
FROM snap_evenement 
INNER JOIN auth_user ON (snap_evenement.user_id = auth_user.id) 
LEFT OUTER JOIN snap_eleve ON (auth_user.id = snap_eleve.user_id) 
LEFT OUTER JOIN snap_classe ON (snap_eleve.classe_id = snap_classe.id)
LEFT OUTER JOIN snap_evenementepr ON (snap_evenement.id = snap_evenementepr.evenement_id) 
LEFT OUTER JOIN snap_evenementenv ON (snap_evenement.id = snap_evenementenv.evenement_id)
GROUP BY `snap_evenement`.`session_key`, `snap_evenement`.`user_id` ORDER BY NULL"""
        cursor.execute(req)
        columns = [col[0] for col in cursor.description]
        return Response([dict(zip(columns,row)) for row in cursor.fetchall()])

    @list_route()
    def listesimple(self,request):
        #queryset=Evenement.objects.filter(numero=1).values('creation').dates('creation','day')
        #evts=EvenementENV.objects.filter(type='LANCE').values_list('evenement',flat=True)
        sessions=Evenement.objects.order_by().values("session_key","user",
                                                     "user__username",
                                                     "user__eleve__classe",
                                                     "user__eleve__classe__nom").distinct()\
                .annotate(debut=Min('creation'),fin=Max('creation'),nb_evts=Count("session_key"))
        print(sessions)
        #queryset=Evenement.objects.filter(id__in=evts)
        #print(queryset)
        serializer=ResumeSessionSerializer(sessions,many=True)
        return Response(serializer.data)
        #return Response(evts)
    
    @list_route(methods=['post'])
    def visualise(self,request):
        #print(request.data)
        l=[i['session_key'] for i in request.data['data']  ]      
        evts=Evenement.objects.filter(session_key__in=l)\
                .select_related('user')\
                .prefetch_related('evenementspr','evenementepr','environnement','image',\
                                  'evenementspr__inputs','evenementspr__scripts')
        serializer=SimpleEvenementSerializer(evts,many=True)
        return Response(serializer.data)
    
    def visualiseConstruction(self,request):
        l=[i['session_key'] for i in request.data['data']  ]
        evts=Evenement.objects.filter(session_key__in=l,numero=1)