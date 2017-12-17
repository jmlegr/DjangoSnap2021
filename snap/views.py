from django.shortcuts import render, render_to_response, redirect

# Create your views here.

from django.http import HttpResponse
import datetime
from django.contrib.auth.decorators import login_required
import json
import random
from snap.models import InfoReceived, ActionProgrammation, DroppedBlock, Bounds, \
                        Inputs, Point
from snap.forms import DocumentForm
                        
from django.template.loader import render_to_string
from django.core.files.storage import FileSystemStorage

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
            return HttpResponse(json.dumps({'success': True,'file':instance.document.name}), content_type="application/json")
    #else:
    #    form = DocumentForm()
    #return render(request, 'model_form_upload.html', {
    #    'form': form
    #})
    

