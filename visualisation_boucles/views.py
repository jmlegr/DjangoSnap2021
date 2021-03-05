from django.shortcuts import render

from rest_framework import viewsets
from snap.models import ProgrammeBase, EvenementEPR, EvenementENV, Evenement,\
    SnapSnapShot, EvenementSPR
from visualisation_boucles.serializers import ProgrammeBaseSerializer, EvenementENVSerializer, SimpleEvenementSerializer\
                    ,VerySimpleEvenementSerializer, ResumeSessionSerializer,\
                    ReperesEPRSerializer, SimpleSPRSerializer
               
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import detail_route, list_route, renderer_classes,\
    api_view
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer,\
    StaticHTMLRenderer
from django.db.models.aggregates import Min, Max, Count
import itertools
from django.http.response import HttpResponse, HttpResponseRedirect
from DjangoSnap.celery import app
import json
from celery.result import AsyncResult

from django.urls.base import reverse
from visualisation_boucles.tasks import reconstruit, add, celery_graph_boucles, celery_liste_reperes
from django.db.models.query import prefetch_one_level
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
    #renderer_classes = (JSONRenderer,StaticHTMLRenderer )    
    
    @renderer_classes((JSONRenderer,))
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
    @renderer_classes((JSONRenderer,))
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
    
    @detail_route(url_path='reperes')
    @renderer_classes((JSONRenderer,))
    def reperes_detail(self,request,pk=None):
        """
        éléments clés de la session pk
        """
        reperes=EvenementEPR.objects.filter(evenement__session_key=pk,type__in=["LOAD","SAVE","NEW"])\
                .order_by('evenement__time')\
                .select_related('evenement',
                                'evenement__user',
                                'evenement__user__eleve',
                                'evenement__user__eleve__classe')
        serializer=ReperesEPRSerializer(reperes,many=True)
        return Response(serializer.data)
    
    @list_route(['post'],url_path='reperes')
    @renderer_classes((JSONRenderer,))
    def reperes_list(self,request):
        reperes=EvenementEPR.objects.filter(evenement__session_key__in=request.data['data']
                                            ,type__in=["LOAD","SAVE","NEW"])\
                                            .order_by('evenement__user','evenement__time')\
                                            .select_related('evenement',
                                                            'evenement__user',
                                                            'evenement__user__eleve',
                                                            'evenement__user__eleve__classe')
        for e in reperes:
            #recherche du dernier snap
            try:
                
                snaps=SnapSnapShot.objects.filter(evenement__user=e.evenement.user,
                                              evenement__session_key=e.evenement.session_key,
                                              evenement__time__lt=e.evenement.time,
                                              evenement__type=Evenement.ETAT_PROGRAMME                                              
                                              ).select_related('evenement').prefetch_related('evenement__evenementepr').order_by('-evenement__time')
                #on ne prend que les snaps de fin ou stop 
                snaps=[s for s in snaps if s.evenement.getEvenementType().type=='SNP' 
                                        and s.evenement.getEvenementType().detail[:3] in ["STO","FIN"]]
                print ([s.evenement.getEvenementType() for s in snaps])
                e.snapshot=snaps[0]
                #print("snap",snaps[0])
                
            except IndexError:
                snap=None
                #print("pasnsap")
        lances=EvenementENV.objects.filter(evenement__session_key__in=request.data['data']
                                            ,type__in=["LANCE","IMPORT","EXPORT"])\
                                            .order_by('evenement__user','evenement__time')\
                                            .select_related('evenement',
                                                            'evenement__user',
                                                            'evenement__user__eleve',
                                                            'evenement__user__eleve__classe')
        lasts=[]
        for session in request.data['data']:
            last=Evenement.objects.filter(session_key=session)\
                                            .select_related('user',
                                                            'user__eleve',
                                                            'user__eleve__classe')\
                                            .latest('time')\
                                            .getEvenementType() 
            if last not in reperes:
                lasts.append(last)
        #print("LAST",lasts)
        for e in lasts:
            #recherche du dernier snap
            try:
                snaps=SnapSnapShot.objects.filter(evenement__user=e.evenement.user,
                                              evenement__session_key=e.evenement.session_key,
                                              evenement__time__lte=e.evenement.time
                                              ).order_by('-evenement__time')
                e.snapshot=snaps[0]
                #print("snap",snaps[0])
                
            except IndexError:
                snap=None
                #print("pasnsap")
        queryset=itertools.chain(lances,reperes,lasts)
        serializer=ReperesEPRSerializer(queryset,many=True)
        data=sorted(serializer.data,key= lambda x:x['evenement']['time'])              
        return Response(data)
    
        
    @list_route(methods=['post'])
    @renderer_classes((JSONRenderer,))
    def visualise(self,request):
        #print(request.data)
        l=[i['session_key'] for i in request.data['data']  ]      
        evts=Evenement.objects.filter(session_key__in=l)\
                .select_related('user')\
                .prefetch_related('evenementspr','evenementepr','environnement','image',\
                                  'evenementspr__inputs','evenementspr__scripts')
        serializer=SimpleEvenementSerializer(evts,many=True)
        return Response(serializer.data)
    
    @renderer_classes((JSONRenderer,))
    def visualiseConstruction(self,request):
        l=[i['session_key'] for i in request.data['data']  ]
        evts=Evenement.objects.filter(session_key__in=l,numero=1)
        
    @list_route(['post'],url_path='donnees')
    @renderer_classes((JSONRenderer, StaticHTMLRenderer,))
    def donnees_sessions(self,request):
        evts=Evenement.objects.filter(session_key__in=request.data['data'] )\
                .select_related('user')\
                .prefetch_related('evenementspr','evenementepr','environnement','image',\
                                  'evenementspr__inputs','evenementspr__scripts')
        serializer=SimpleEvenementSerializer(evts,many=True)
        return Response(serializer.data)
        #return HttpResponse(data)

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def listeblock_cancel(request,task_id=None):
    data = 'Fail'
    app.control.revoke(task_id,terminate=True) #,signal='SIGUSR1' )
    data = "Cancelled"
    return Response(data)

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def listeblock_state(request,task_id=None):
    """ A view to report the progress to the user """
    data = 'Fail'
    task = AsyncResult(task_id)
    #print(task.state,task.result)
    if task.state=='REVOKED':
        data={'state':task.state}
    else:
        data = {'result':task.result,'state':task.state}
    return Response({'task_id':task_id,'data':data})            
        
@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def celery_listeblock(request,session_key=None):
    if 'job' in request.GET:
        print('JOB')
        job_id = request.GET['job']
        job = AsyncResult(job_id)
        data = {'result':job.result,'state':job.state}
        context = {
            'data':data,
            'task_id':job_id,
        }
        return Response(context)
    #job = add.delay(random.randint(1,100),random.randint(2,100),random.randint(100000,500000))
    save='save'in request.GET
    load='load' in request.GET
    job=reconstruit.delay(session_key,save=save,load=load)
    return HttpResponseRedirect(reverse('celery_listeblock') + '?job=' + job.id)


@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def task_cancel(request,task_id=None):
    data = 'Fail'
    app.control.revoke(task_id,terminate=True) #,signal='SIGUSR1' )
    data = "Cancelled"
    return Response(data)

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def task_state(request,task_id=None):
    """ A view to report the progress to the user """
    data = 'Fail'
    task = AsyncResult(task_id)
    #print(task.state,task.result)
    if task.state=='REVOKED':
        data={'state':task.state}
    else:
        data = {'result':task.result,'state':task.state}
    return Response({'task_id':task_id,'data':data})       

@api_view(('POST','GET'))
@renderer_classes((JSONRenderer,))
def testadd(request):
    if 'job' in request.GET:
        print('JOB')
        job_id = request.GET['job']
        job = AsyncResult(job_id)
        data = {'result':job.result,'state':job.state}
        context = {
            'data':data,
            'task_id':job_id,
        }
        return Response(context)
    if request.data != {}:
        data=request.data['data']
    else:
        data=request.query_params
    job=add.delay(int(data["x"]),int(data["y"]),int(data["n"]))
    return HttpResponseRedirect(reverse('testadd')+'?job='+job.id)

@api_view(('POST','GET'))
@renderer_classes((JSONRenderer,))
def graph_boucles(request):
    '''
    Recherche la premiere occurence d'une boucle ('doUntil','doForever','doRepeat')    
    et renvoi l'enselbe des évènements la précédent
    data:liste des session_key
    only: si présent, tableau de recherche (défaut:['doUntil','doForever','doRepeat']
    '''
    
    if 'job' in request.GET:
        print('JOB')
        job_id = request.GET['job']
        job = AsyncResult(job_id)
        data = {'result':job.result,'state':job.state}
        context = {
            'data':data,
            'task_id':job_id,
        }
        return Response(context)
    data=request.data['data']
    job=celery_graph_boucles.delay(data['session_keys'],data['only'] if 'only' in data else None)
    return HttpResponseRedirect(reverse('graph_boucles')+'?job='+job.id)
    
@api_view(('POST','GET'))
@renderer_classes((JSONRenderer,))
def reperes(request):
    '''
    Recherche la premiere occurence d'une boucle ('doUntil','doForever','doRepeat')    
    et renvoi l'enselbe des évènements la précédent
    data:liste des session_key
    only: si présent, tableau de recherche (défaut:['doUntil','doForever','doRepeat']
    '''
    
    if 'job' in request.GET:
        print('JOB')
        job_id = request.GET['job']
        job = AsyncResult(job_id)
        data = {'result':job.result,'state':job.state}
        context = {
            'data':data,
            'task_id':job_id,
        }
        return Response(context)
    data=request.data['data']
    print("data",data)
    job=celery_liste_reperes.delay(data)
    return HttpResponseRedirect(reverse('graph_boucles')+'?job='+job.id)