from django.shortcuts import render, render_to_response

# Create your views here.

from django.http import HttpResponse
import datetime
from django.contrib.auth.decorators import login_required
import json
import random
from snap.models import InfoReceived
from django.template.loader import render_to_string

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
    return HttpResponse("OK %s" % info.id)
    #
    
def pageref(request):
    return render_to_response('refresh.html', {'value':'zyva'})
def pagedon(request):
    obj=InfoReceived.objects.all()
    if not obj.exists():
        return HttpResponse('.')
    else:
        html_result=render_to_string('don.html', {'autre':obj.count(),'data':obj})
        obj.delete()
        #return render_to_response(html_result)
        return HttpResponse(html_result)