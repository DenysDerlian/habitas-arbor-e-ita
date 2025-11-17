from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    
    # Autenticação
    path('register/cidadao/', views.register_cidadao, name='register_cidadao'),
    path('register/tecnico/', views.register_tecnico, name='register_tecnico'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboards
    path('dashboard/gestor/', views.dashboard_gestor, name='dashboard_gestor'),
    path('dashboard/tecnico/', views.dashboard_tecnico, name='dashboard_tecnico'),
    
    # Gestão de Técnicos (Nível 1)
    path('gestao/tecnicos/pendentes/', views.listar_tecnicos_pendentes, name='listar_tecnicos_pendentes'),
    path('gestao/tecnicos/<int:user_id>/aprovar/', views.aprovar_tecnico, name='aprovar_tecnico'),
    
    # Laudos
    path('laudos/criar/<int:tree_id>/', views.criar_laudo, name='criar_laudo'),
    path('laudos/pendentes/', views.listar_laudos_pendentes, name='listar_laudos_pendentes'),
    path('laudos/<int:laudo_id>/validar/', views.validar_laudo, name='validar_laudo'),
    path('laudos/meus/', views.meus_laudos, name='meus_laudos'),
    path('laudos/<int:laudo_id>/editar/', views.editar_laudo, name='editar_laudo'),
    path('laudos/<int:laudo_id>/excluir/', views.excluir_laudo, name='excluir_laudo'),
    
    # Notificações
    path('notificacoes/criar/<int:tree_id>/', views.criar_notificacao, name='criar_notificacao'),
    path('notificacoes/', views.listar_notificacoes, name='listar_notificacoes'),
    path('notificacoes/<int:notificacao_id>/analisar/', views.analisar_notificacao, name='analisar_notificacao'),
    path('notificacoes/<int:notificacao_id>/resolver/', views.resolver_notificacao, name='resolver_notificacao'),

    # Política de Privacidade
    path('politica-privacidade/', views.politica_privacidade, name='politica_privacidade'),
]