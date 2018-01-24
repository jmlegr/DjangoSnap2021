from django.shortcuts import render, render_to_response, get_object_or_404

# Create your views here.

from django.http import HttpResponse
import datetime
from django.contrib.auth.decorators import login_required
import json
from snap.models import InfoReceived, Document, Classe, Eleve, EvenementSPR
from snap.forms import DocumentForm

from django.template.loader import render_to_string
from django.core.files.storage import FileSystemStorage
#from wsgiref.util import FileWrapper
from rest_framework import viewsets, status, serializers
from snap.serializers import ProgrammeBaseSerializer, UserSerializer, GroupSerializer,\
            EvenementSerializer, ProgrammeBaseSuperuserSerializer,\
            EvenementEPRSerializer, EvenementENVSerializer, EvenementSPRSerializer,\
            BlockSerializer, EleveUserSerializer, EvenementSPROpenSerializer
from snap.models import ProgrammeBase, Evenement, EvenementEPR, EvenementENV,\
Block
from django.contrib.auth.models import User, Group
from django.http.response import HttpResponseRedirect
from django.urls.base import reverse
from django.db.models import Q
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class ProgrammeBaseViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour Programme de Base
    """
    queryset=ProgrammeBase.objects.all();
    #serializer_class=ProgrammeBaseSerializer
    def get_serializer_class(self):
        if self.request.user.is_superuser:
            return ProgrammeBaseSuperuserSerializer
        return ProgrammeBaseSerializer

class EvenementViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour Evenement
    """
    queryset=Evenement.objects.all()
    serializer_class=EvenementSerializer

class EvenementEPRViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour EvenementEPR (Evenement Etat du Programme)
    """
    queryset=EvenementEPR.objects.all()
    serializer_class=EvenementEPRSerializer

class EvenementENVViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour EvenementENV (Evenement Changement de l'environnement)
    """
    queryset=EvenementENV.objects.all()
    serializer_class=EvenementENVSerializer
    
    @list_route()
    def users(self,request):
        """
        renvoie la liste des utilisateurs ayant lancé une session snap
        """        
        lst=EvenementENV.objects.filter(type='LANCE').values_list('evenement__user',flat=True)
        users=User.objects.filter(id__in=lst)
        #users=User.objects.all()
        print (users)
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = EleveUserSerializer(page, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = EleveUserSerializer(users, many=True,context={'request': request})
        return Response(serializer.data)

    @list_route()
    def sessions(self,request):
        evs=EvenementENV.objects.filter(type='LANCE').order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
    @detail_route()
    def sessionsUser(self,request,pk=None):
        if (pk is None) or (pk=='0'):
            return self.sessions(request)
        try:
            u=User.objects.get(id=pk)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        evs=EvenementENV.objects.filter(type='LANCE').filter(evenement__user=u).order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
        

class EvenementSPROpenViewset(viewsets.ModelViewSet):
    """
    API Endpoint renvois les SPR "OPEN")
    """
    queryset=EvenementSPR.objects.filter(type='OPEN')
    serializer_class=EvenementSPROpenSerializer
    
    @list_route()
    def users(self,request):
        """
        renvoie la liste des utilisateurs ayant lancé une session snap
        """        
        lst=EvenementSPR.objects.filter(type='OPEN').values_list('evenement__user',flat=True)
        users=User.objects.filter(id__in=lst)
        #users=User.objects.all()
        print (users)
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = EleveUserSerializer(page, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = EleveUserSerializer(users, many=True,context={'request': request})
        return Response(serializer.data)
    
    @list_route()
    def opens(self,request):
        evs=EvenementSPR.objects.filter(type='OPEN').order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
    @detail_route()
    def openUser(self,request,pk=None):
        if (pk is None) or (pk=='0'):            
            return self.opens(request)
        try:
            u=User.objects.get(id=pk)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        evs=EvenementSPR.objects.filter(type='OPEN').filter(evenement__user=u).order_by('-evenement__creation')
        page = self.paginate_queryset(evs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(evs, many=True)
        return Response(serializer.data)
    
    @detail_route()
    def listeOpen(self,request,pk=None):
        """
        reconstitution du programme chargé
        """
        def traiteBlock(b):
            resultat={
                'id':b.id, 'JMLid':b.JMLid,
                'selector':b.selector, 'blockSpec':b.blockSpec,
                'typeMorph':b.typeMorph,
                'inputs':parcoursInput(b)
                }
            if b.nextBlock: nextBlock={'source':b.JMLid,'target':b.nextBlock.JMLid}
            else: nextBlock=None        
            return resultat, nextBlock
        def parcoursBlock(b):
            liste=[]
            nextLiens=[]
            while True:
                res,nextLien=traiteBlock(b)
                liste.append(res)
                if nextLien is not None: 
                    nextLiens.append(nextLien)
                if b.nextBlock:
                    b=b.nextBlock
                else:
                    break;        
            return liste,nextLiens
    
        def parcoursInput(b):
            inputs=[]
            nextBlocks=None
            for inputB in b.inputs.all():          
                inputs.append({'id':inputB.id,'JMLid':inputB.JMLid, 'typeMorph':inputB.typeMorph,
                           'rang':inputB.rang,
                         'contenu':inputB.contenu})                                    
            for inputBlock in b.inputsBlock.all():
            #recherche de l'input correspondant
                inputB=b.inputs.filter(JMLid=inputBlock.JMLid)            
                if inputB:
                    result,nextBlock=parcoursBlock(inputBlock)
                    inputs[inputB[0].rang]['contenu']=result
                    #if nextBlock is not None: 
                     #   nextLiens.append(nextBlock)
                        
                                 
            return inputs 
                        
        if pk is not None:        
            evo=EvenementSPR.objects.get(id=pk)
        else:
            evo=EvenementSPR.objects.filter(type='OPEN').latest('evenement__creation')
        block=evo.scripts.all()[0]
        liste,nextLiens=parcoursBlock(block)
        for i in liste:
            print(i)
        return render(request,'liste_open.html',{'tdOpen':self.renderOpen(liste),'nodes':liste,'links':nextLiens})

    def renderOpen(self,r,nbTd=1):
        ret=[]
        for i in r:
            if 'blockSpec' in i: ret.append(
                        {'nbTd':range(nbTd),
                         'id':i['id'], 'JMLid':i['JMLid'],
                         'selector':i['selector'], 'blockSpec':'%s' % i['blockSpec'],
                         'typeMorph':i['typeMorph'],             
                         })
            else:
                ret.append({'nbTd':range(nbTd+1),'contenu': '%s' % i})
            if 'inputs' in i:
                childs=[]
                for inp in i['inputs']:
                    if inp['typeMorph'] in ['InputSlotMorph',]: 
                        ret+=self.renderOpen([inp['contenu']],nbTd+1)                    
                    else:
                        ret+=self.renderOpen(inp['contenu'],nbTd+1)
        return ret
    def suivant(self,ev):
        try:
            suivant=EvenementSPR.objects.filter(type='OPEN',
                                            evenement__user=ev.evenement.user,
                                            evenement__creation__gt=ev.evenement.creation).earliest('evenement__creation')
        except:
            suivant=None
        return suivant
    
    def precedent(self,ev):
        precedent=EvenementSPR.objects.filter(type='OPEN',
                                            evenement__user=ev.evenement.user,
                                            evenement__creation__lt=ev.evenement.creation).latest('evenement__creation')
    
    @detail_route()
    def listeActions(self,request,pk):
        """
        renvoie la liste des actions du début du chargement (SPR d'id pk) 
        à la fin de la session ou au début du chargement suivant
        """
        ev=EvenementSPR.objects.get(id=pk)
        evs=self.suivant(ev)
        eleve=Eleve.objects.get(user=ev.evenement.user)
        if evs is not None:
            actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gt=ev.evenement.numero,
                                         creation__lt=evs.evenement.creation).order_by('numero')
        else:
            #c'est le dernier OPen
            actions=Evenement.objects.filter(user=ev.evenement.user,
                                         creation__gte=ev.evenement.creation,
                                         numero__gt=ev.evenement.numero).order_by('numero')
        return render(request,'liste_simple.html',{'evenements':actions,'eleve':eleve})
        #return Response(EvenementSerializer(actions,many=True).data)
                                   
    
class EvenementSPRViewset(viewsets.ModelViewSet):
    """
    API Endpoint pour EvenementENV (Evenement Changement de l'environnement)
    """
    queryset=EvenementSPR.objects.all()
    serializer_class=EvenementSPRSerializer

class BlockViewSet(viewsets.ModelViewSet):
    queryset=Block.objects.all()
    serializer_class=BlockSerializer
    
def current_datetime(request):
    now = datetime.datetime.now()
    html = "<html><body>It is now %s.</body></html>" % now
    return HttpResponse(html)

@login_required(login_url='/accounts/login/')
def testsnap(request):
    return render(request,'snap/snap.html')



def pageref(request):
    return render_to_response('refresh.html', {'value':'test'})
def pagedon(request):
    obj=InfoReceived.objects.all()
    if not obj.exists():
        return HttpResponse('.')
    else:
        html_result=render_to_string('don.html', {'autre':obj.count(),'data':obj})
        obj.delete()
        #return render_to_response(html_result)
        return HttpResponse(html_result)

def simple_upload(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)
        return render(request, 'simple_upload.html', {
            'uploaded_file_url': uploaded_file_url
        })
    return render(request, 'simple_upload.html')

def model_form_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            instance=form.save(commit=False)
            instance.user=request.user
            instance.save()
            return HttpResponse(json.dumps({'success': True,'id':instance.id}), content_type="application/json")
    #else:
    #    form = DocumentForm()
    #return render(request, 'model_form_upload.html', {
    #    'form': form
    #})

def return_fichier(request):
    if request.method == 'GET':
        eleve = get_object_or_404(Eleve, user=request.user)
        if eleve.prg is None:
                    return HttpResponse(json.dumps({'success': False, 'id':request.user.username}), content_type="application/json", status=status.HTTP_404_NOT_FOUND)
        # wrapper = FileWrapper(open('media/documents/sierpinski-programme1.xml'))
        wrapper = eleve.prg.file
        # content_type = mimetypes.guess_type(filename)[0]
        response = HttpResponse(wrapper, content_type='text/xml')
        # response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = "attachment; filename=%s" % 'gi'
        return response
def return_fichier_eleve(request,file_id):
    #print('ok',file_id)
    if request.method=='GET':
        doc=Document.objects.get(id=file_id);
        #wrapper = FileWrapper(open('media/documents/sierpinski-programme1.xml'))
        #wrapper = FileWrapper(open('media/%s' %doc.document))
        wrapper=doc.document
        #content_type = mimetypes.guess_type(filename)[0]
        response = HttpResponse(wrapper, content_type='text/xml')
        #response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = "attachment; filename=%s" % 'doc.description'
        return response
def return_files(request):
    if request.user.is_staff:
        fics=Document.objects.filter(Q(user=request.user) | Q(user__groups__name__in=['eleves',])).order_by('-uploaded_at')
        return render(request,'file_user_prof.html',{'files':fics});
    else:
        fics=Document.objects.filter(user=request.user).order_by('-uploaded_at')
        return render(request,'file_user.html',{'files':fics});
    

@login_required()
def login_redirect(request):
    if request.user.is_authenticated:
        ugroups = request.user.groups.values_list('name', flat=True)
        print('users',ugroups)
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse("admin:index"))
        elif "prof" in ugroups:
            return HttpResponseRedirect(reverse("admin:index"))
        elif "eleves" in ugroups:
            return HttpResponseRedirect(reverse("snaptest"))

def liste(request,nom=None):
    if nom is not None:
        user=User.objects.get(username=nom)
        ev=EvenementENV.objects.filter(type='LANCE',evenement__user=user).latest('evenement__creation')
        ev1=EvenementENV.objects.filter(type='LANCE',evenement__user=user,evenement__creation__lt=ev.evenement.creation).latest('evenement__creation')
    else:
        ev=EvenementENV.objects.filter(type='LANCE').latest('evenement__creation')
        user=ev.evenement.user
        ev1=EvenementENV.objects.filter(type='LANCE',evenement__user=user,evenement__creation__lt=ev.evenement.creation).latest('evenement__creation')
    eleve=user.eleve
    evs=Evenement.objects.filter(user=user,creation__gte=ev1.evenement.creation).order_by('time')
    
    return render(request,'liste_simple.html',{'evenements':evs,'eleve':eleve})

def session(request,id=None):
    if id is not None:
        ev=EvenementENV.objects.get(id=id)
        evs=Evenement.objects.filter(id=ev.evenement.id) | Evenement.objects.filter(user=ev.evenement.user,
                                     creation__gt=ev.evenement.creation,
                                     numero__gt=1).order_by('time')
                                     
        return render(request,'liste_simple.html',{'evenements':evs})
    return HttpResponse()
def listeSessions(request):
    return render(request,'liste_sessions.html')  

def listeOpens(request):
    return render(request,'liste_opens.html')
