'''
Created on 16 déc. 2018

@author: duff
'''
'''
Created on 16 déc. 2018

@author: duff
'''
from celery import shared_task,current_task


@shared_task
def add(x,y,n):
    for i in range(n):
        if(i%30 == 0):
            process_percent = int(100 * float(i) / float(n))
            current_task.update_state(state='PROGRESS',
                                meta={'process_percent': process_percent,'i':i})
        a = x+y
    return {'x':x,'y':y,'resultat':x+y}