from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse
import datetime
from django.contrib.auth.decorators import login_required

def current_datetime(request):
    now = datetime.datetime.now()
    html = "<html><body>It is now %s.</body></html>" % now
    return HttpResponse(html)

@login_required(login_url='/accounts/login/')
def testsnap(request):
    return render(request,'snap/snap.html')
