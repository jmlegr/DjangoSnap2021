from django.shortcuts import render
from celery.result import AsyncResult

# Create your views here.
from .tasks import add
from .forms import AddForm
from django.http.response import HttpResponseRedirect, HttpResponse
from django.urls.base import reverse
import json
from DjangoSnap.celery import app


def poll_cancel(request):
    data = 'Fail'
    if request.is_ajax():        
        if 'task_id' in request.POST.keys() and request.POST['task_id']:
            task_id = request.POST['task_id']
            app.control.revoke(task_id,terminate=True )
            data = "Cancelled"
        else:
            data = 'No task_id in the request'
    else:
        data = 'This is not an ajax request'

    json_data = json.dumps(data)
    return HttpResponse(json_data, content_type='application/json')

def poll_state(request):
    """ A view to report the progress to the user """
    data = 'Fail'
    if request.is_ajax():        
        if 'task_id' in request.POST.keys() and request.POST['task_id']:
            task_id = request.POST['task_id']
            task = AsyncResult(task_id)
            
            print(task,task.result,task.state)
            if task.state=='REVOKED':
                data={'state':task.state}
            else:
                data = {'result':task.result,'state':task.state}            
        else:
            data = 'No task_id in the request'
    else:
        data = 'This is not an ajax request'
    json_data = json.dumps(data)
    return HttpResponse(json_data, content_type='application/json')

def celery_add(request):
    if 'job' in request.GET:
        job_id = request.GET['job']
        job = AsyncResult(job_id)
        data = job.result or job.state
        context = {
            'data':data,
            'task_id':job_id,
        }
        return render(request,"show_t.html",context)
    elif 'n' in request.GET:
        n = request.GET['n']
        x = request.GET['x']
        y = request.GET['y']
        job = add.delay(int(x),int(y),int(n))
        return HttpResponseRedirect(reverse('celery_add') + '?job=' + job.id)
    else:
        form = AddForm()
        context = {
            'form':form,
        }
    return render(request,"post_form.html",context)