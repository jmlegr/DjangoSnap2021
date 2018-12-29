'''
Created on 16 déc. 2018

@author: duff
'''
from celery import shared_task,current_task
from snap.models import Evenement, EvenementEPR
from visualisation_boucles.reconstitution import SimpleListeBlockSnap



@shared_task
def reconstruit(session_key):    
    current_task.update_state(state='Initialisation',
                                meta={'evt_traites': 0,'nb_evts':None})
    #liste les derniers débuts de tous les élèves
    evts=[]
    if session_key.isdigit():
        #on a envoyé une id d'évènement EPR
        epr=EvenementEPR.objects.get(id=session_key)
        debut=epr.evenement
        evts=Evenement.objects.filter(session_key=debut.session_key,creation__gte=debut.creation,time__gte=debut.time).order_by('time')
    else:
        evts=Evenement.objects.filter(session_key=session_key).order_by('time')
        debut=evts[0]
    nb_evts=evts.count()
    current_task.update_state(state='Initialisation',
                                meta={'evt_traites': 0,'nb_evts':nb_evts})
    infos={}
    eprInfos={}  
    evtTypeInfos={}  
    user=debut.user
    infos['user']=user.username
    infos['date']=debut.creation
    
    #on va parcourir les évènement
    drops=[]
    listeBlocks=SimpleListeBlockSnap()
    #on traite les évènements
    dtime=None
    evtPrec=None
    evt_traites=0
    for evt in evts:
        evt_traites+=1
        if (evt_traites % 10 == 0):
            current_task.update_state(state='Traitement',
                                meta={'evt_traites': evt_traites,'nb_evts':nb_evts})
        #print('evt',evt,evt.type,evt.id)
        if dtime is None:
            dtime=evt.time
            theTime=0
        theTime=evt.time-dtime        
        
        evtType=evt.getEvenementType()
        evtTypeInfos['%s' % theTime]={'evenement':evt.id,
                                      'evenement_type':evt.type,
                                      'type':evtType.type,
                                      'detail':evtType.detail}
        history=None #memorise l'état undrop/redrop
    return {"session":session_key,'infos':evtTypeInfos}
    
@shared_task
def add(x,y,n):
    for i in range(n):
        if(i%30 == 0):
            process_percent = int(100 * float(i) / float(n))
            current_task.update_state(state='PROGRESS',
                                meta={'process_percent': process_percent,'i':i})
        a = x+y
    return {'x':x,'y':y,'resultat':x+y}
