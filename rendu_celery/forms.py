'''
Created on 16 déc. 2018

@author: duff
'''
from django import forms

class AddForm(forms.Form):
    x=forms.CharField(label='x')
    y=forms.CharField(label='y')
    n=forms.CharField(label="nb")
    