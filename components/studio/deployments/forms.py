from django import forms
from .models import DeploymentDefinition, DeploymentInstance


class DeploymentDefinitionForm(forms.ModelForm):
    class Meta:
        model = DeploymentDefinition
        fields = ('name', 'definition')


class DeploymentInstanceForm(forms.ModelForm):
    class Meta:
        model = DeploymentInstance
        fields = ('name', 'model', 'version', 'access', 'sample_input', 'sample_output', 'deployment')
