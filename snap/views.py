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
from rest_framework import viewsets, status
from snap.serializers import ProgrammeBaseSerializer, UserSerializer, GroupSerializer,\
            EvenementSerializer, ProgrammeBaseSuperuserSerializer,\
            EvenementEPRSerializer, EvenementENVSerializer, EvenementSPRSerializer,\
            BlockSerializer
from snap.models import ProgrammeBase, Evenement, EvenementEPR, EvenementENV,\
Block
from django.contrib.auth.models import User, Group
from django.http.response import HttpResponseRedirect
from django.urls.base import reverse
from django.db.models import Q

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

@login_required(login_url='/accounts/login/')
def ajax(request):
    #if request.is_ajax():
    if request.method == 'POST':
        print ('Raw Data: "%s"' % request.body)
        data = request.body.decode('utf-8')
        received_json_data = json.loads(data)
        r=received_json_data
        print('receives %s' % received_json_data)
        print ('from user: %s',request.user)
        info=InfoReceived (action=r['action'],blockSpec=r['lastDroppedBlock']['blockSpec'],
                                  time=r['time'],block_id=r['lastDroppedBlock']['id'],user='%s' % request.user)
        info.save()
        ap=ActionProgrammation()
        ap.user=request.user
        ap.action=r['action']
        ap.time=r['time']
        ap.typeMorph=r['typeMorph']
        if 'sens' in r: ap.sens=r['sens']
        if 'situation' in r: ap.situation=r['situation']

        db=DroppedBlock()
        db.block_id=r['lastDroppedBlock']['id']
        db.blockSpec=r['lastDroppedBlock']['blockSpec']
        db.category=r['lastDroppedBlock']['category']
        rb=r['lastDroppedBlock']['bounds']
        origin=Point(x=rb['origin']['x'],y=rb['origin']['y'])
        origin.save()
        corner=Point(x=rb['corner']['x'],y=rb['corner']['y'])
        corner.save()
        b=Bounds(origin=origin,corner=corner)
        b.save()
        db.bounds=b
        if 'parent' in r['lastDroppedBlock']:
            db.parent_id=r['lastDroppedBlock']['parent']
        db.save()
        ap.lastDroppedBlock=db

        if 'inputs' in r['lastDroppedBlock']:
            for i in r['lastDroppedBlock']['inputs']:
                ip=Inputs(valeur=i['valeur'],type=i['type'])
                ip.save()
                db.inputs.add(ip)

        ap.save()


    return HttpResponse("OK %s" % info.id)
    #

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
    

def prof_base(request,classe=None):
    groupe=Group.objects.get(name='eleves');
    #eleves=User.objects.filter(groups__in=[groupe,])
    if classe is not None:
        theclasse=Classe.objects.get(nom=classe)
        eleves=Eleve.objects.filter(classe=theclasse)
        msg='élèves de la classe de '+classe
    else:
        eleves=Eleve.objects.all()
        msg='tous les élèves'
    prg=ProgrammeBaseEleve.objects.filter(eleve__in=eleves)
    return render(request,'prof_base.html',{'message':msg,'programmes':prg})

def tt(request):
    if request.method=='POST':
        form=PrgBaseForm(request.POST)
        if form.is_valid():
            return HttpResponse('ok')
    else:
        form=PrgBaseForm()
    return render(request,'pt.html',{'form':form})

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
