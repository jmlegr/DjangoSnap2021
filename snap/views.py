from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse
import datetime
from django.contrib.auth.decorators import login_required
import json

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
        print('receives %s' % received_json_data)
        print ('from user: %s',request.user)
    return HttpResponse("OK")
    #