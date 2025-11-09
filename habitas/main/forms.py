from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Laudo, Notificacao


class CidadaoRegistrationForm(UserCreationForm):
    """Formulário de registro para cidadãos (Nível 3)"""
    email = forms.EmailField(required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.user_type = CustomUser.UserType.CIDADAO
        user.aprovacao_status = CustomUser.ApprovalStatus.APROVADO
        if commit:
            user.save()
        return user


class TecnicoRegistrationForm(UserCreationForm):
    """Formulário de registro para técnicos (Nível 2)"""
    email = forms.EmailField(required=True)
    formacao = forms.CharField(max_length=255, required=True, label="Formação Profissional")
    registro_profissional = forms.CharField(max_length=100, required=True, label="Nº Registro Profissional")
    documento_comprobatorio = forms.FileField(
        required=True,
        label="Documento Comprobatório (PDF, JPG ou PNG)",
        help_text="Envie diploma, certificado ou documento de registro profissional"
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'formacao', 'registro_profissional', 
                  'documento_comprobatorio', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.user_type = CustomUser.UserType.TECNICO
        user.formacao = self.cleaned_data['formacao']
        user.registro_profissional = self.cleaned_data['registro_profissional']
        user.aprovacao_status = CustomUser.ApprovalStatus.PENDENTE
        if commit:
            user.save()
        return user


class LaudoForm(forms.ModelForm):
    """Formulário para criação de laudos técnicos"""
    class Meta:
        model = Laudo
        fields = ['titulo', 'descricao', 'arquivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


class NotificacaoForm(forms.ModelForm):
    """Formulário para notificações de cidadãos"""
    class Meta:
        model = Notificacao
        fields = ['tipo', 'titulo', 'descricao', 'foto']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


class ParecerTecnicoForm(forms.ModelForm):
    """Formulário para técnicos adicionarem pareceres"""
    class Meta:
        model = Notificacao
        fields = ['parecer_tecnico']
        widgets = {
            'parecer_tecnico': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


class AprovacaoTecnicoForm(forms.ModelForm):
    """Formulário para gestores aprovarem técnicos"""
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label="Observações"
    )
    
    class Meta:
        model = CustomUser
        fields = ['aprovacao_status']
        widgets = {
            'aprovacao_status': forms.Select(attrs={'class': 'form-control'}),
        }
