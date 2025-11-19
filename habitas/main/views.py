from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
import sys
from pathlib import Path
from .models import (
    Tree,
    Post,
    CustomUser,
    Laudo,
    Notificacao,
    HistoricoNotificacao,
    EcosystemServiceConfig,
)
from .forms import (
    CidadaoRegistrationForm,
    TecnicoRegistrationForm,
    LaudoForm,
    NotificacaoForm,
    ParecerTecnicoForm,
    AprovacaoTecnicoForm,
)
from .decorators import gestor_required, tecnico_required, gestor_ou_tecnico_required


def index(request):
    filters = {}
    if request.GET.get("nome_popular"):
        filters["nome_popular__icontains"] = request.GET["nome_popular"]
    if request.GET.get("nome_cientifico"):
        filters["nome_cientifico__icontains"] = request.GET["nome_cientifico"]
    if request.GET.get("plantado_por"):
        filters["plantado_por__icontains"] = request.GET["plantado_por"]
    if request.GET.get("species"):
        filters["nome_popular"] = request.GET["species"]
    if request.GET.get("origem"):
        filters["origem"] = request.GET["origem"]
    if request.GET.get("laudo_only"):
        filters["laudo__isnull"] = False
        filters["laudo__gt"] = ""
    if request.GET.get("altura_min"):
        filters["altura__gte"] = request.GET["altura_min"]
    if request.GET.get("altura_max"):
        filters["altura__lte"] = request.GET["altura_max"]
    if request.GET.get("dap_min"):
        filters["dap__gte"] = request.GET["dap_min"]
    if request.GET.get("dap_max"):
        filters["dap__lte"] = request.GET["dap_max"]
    trees = (
        Tree.objects.filter(**filters)
        .select_related("species")
        .annotate(n_posts=Count("posts"))
    )
    ecosystem_services = EcosystemServiceConfig.objects.filter(ativo=True).order_by(
        "ordem_exibicao"
    )
    species_list = (
        Tree.objects.values_list("nome_popular", flat=True)
        .distinct()
        .order_by("nome_popular")
    )
    context = {
        "trees": trees,
        "ecosystem_services": ecosystem_services,
        "species_list": species_list,
        "request": request,
    }
    return render(request, "index.html", context)


# ==================== AUTENTICAÇÃO ====================


def register_cidadao(request):
    """Registro de cidadãos (Nível 3)"""
    if request.method == "POST":
        form = CidadaoRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            login(request, user)
            messages.success(
                request, f"Cadastro realizado com sucesso! Bem-vindo, {user.username}!"
            )
            return redirect("index")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CidadaoRegistrationForm()

    return render(request, "auth/register_cidadao.html", {"form": form})


def register_tecnico(request):
    """Registro de técnicos (Nível 2)"""
    if request.method == "POST":
        form = TecnicoRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                "Solicitação enviada! Aguarde aprovação do gestor para acessar funcionalidades técnicas.",
            )
            return redirect("login")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TecnicoRegistrationForm()

    return render(request, "auth/register_tecnico.html", {"form": form})


def user_login(request):
    """Login de usuários"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Bem-vindo, {user.username}!")

            # Redireciona baseado no tipo de usuário
            if user.is_gestor():
                return redirect("dashboard_gestor")
            elif user.is_tecnico():
                return redirect("dashboard_tecnico")
            else:
                return redirect("index")
        else:
            messages.error(request, "Usuário ou senha inválidos.")

    return render(request, "auth/login.html")


def user_logout(request):
    """Logout de usuários"""
    logout(request)
    messages.success(request, "Logout realizado com sucesso!")
    return redirect("index")


# ==================== DASHBOARDS ====================


@gestor_required
def dashboard_gestor(request):
    """Dashboard para gestores (Nível 1)"""
    context = {
        "total_trees": Tree.objects.count(),
        "tecnicos_pendentes": CustomUser.objects.filter(
            user_type=CustomUser.UserType.TECNICO,
            aprovacao_status=CustomUser.ApprovalStatus.PENDENTE,
        ).count(),
        "laudos_pendentes": Laudo.objects.filter(
            status=Laudo.LaudoStatus.PENDENTE
        ).count(),
        "notificacoes_pendentes": Notificacao.objects.filter(
            status=Notificacao.StatusNotificacao.PENDENTE
        ).count(),
    }
    return render(request, "dashboards/gestor.html", context)


@gestor_required
def atualizar_arvores(request):
    """Atualiza árvores do CSV usando o scraper"""
    if request.method != "POST":
        messages.error(request, "Método não permitido.")
        return redirect("dashboard_gestor")
    
    try:
        # Importa o módulo do scraper
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))
        
        from scrape_trees import run_scraper
        
        # Executa o scraper sem checagem de gaps (modo padrão)
        # verbose=False para não poluir o output do Django
        resultado = run_scraper(check_gaps=False, verbose=False)
        
        collected = resultado.get('collected', 0)
        not_found = resultado.get('not_found', 0)
        
        if collected > 0:
            messages.success(
                request,
                f"✅ Atualização concluída! {collected} nova(s) árvore(s) encontrada(s) e adicionada(s) ao banco de dados."
            )
        else:
            messages.info(
                request,
                f"ℹ️ Nenhuma nova árvore encontrada. {not_found} ID(s) verificados sem sucesso."
            )
        
    except Exception as e:
        messages.error(
            request,
            f"❌ Erro ao atualizar árvores: {str(e)}"
        )
        import traceback
        traceback.print_exc()
    
    return redirect("dashboard_gestor")


@tecnico_required
def dashboard_tecnico(request):
    """Dashboard para técnicos (Nível 2)"""
    context = {
        "meus_laudos": Laudo.objects.filter(autor=request.user).count(),
        "notificacoes_disponiveis": Notificacao.objects.filter(
            status=Notificacao.StatusNotificacao.PENDENTE
        ).count(),
        "minhas_analises": Notificacao.objects.filter(
            tecnico_responsavel=request.user
        ).count(),
    }
    return render(request, "dashboards/tecnico.html", context)


# ==================== GESTÃO DE TÉCNICOS (NÍVEL 1) ====================


@gestor_required
def listar_tecnicos_pendentes(request):
    """Lista técnicos aguardando aprovação"""
    tecnicos = CustomUser.objects.filter(
        user_type=CustomUser.UserType.TECNICO,
        aprovacao_status=CustomUser.ApprovalStatus.PENDENTE,
    )
    return render(request, "gestao/tecnicos_pendentes.html", {"tecnicos": tecnicos})


@gestor_required
def aprovar_tecnico(request, user_id):
    """Aprova ou rejeita técnico"""
    tecnico = get_object_or_404(
        CustomUser, id=user_id, user_type=CustomUser.UserType.TECNICO
    )

    if request.method == "POST":
        form = AprovacaoTecnicoForm(request.POST, instance=tecnico)
        if form.is_valid():
            tecnico = form.save(commit=False)
            tecnico.aprovado_por = request.user
            tecnico.data_aprovacao = timezone.now()
            tecnico.save()

            status_texto = tecnico.get_aprovacao_status_display()
            messages.success(
                request, f"Técnico {tecnico.username} foi {status_texto.lower()}."
            )
            return redirect("listar_tecnicos_pendentes")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AprovacaoTecnicoForm(instance=tecnico)

    return render(
        request, "gestao/aprovar_tecnico.html", {"form": form, "tecnico": tecnico}
    )


# ==================== LAUDOS TÉCNICOS ====================


@tecnico_required
def criar_laudo(request, tree_id):
    """Técnico cria laudo para árvore"""
    tree = get_object_or_404(Tree, id=tree_id)

    if request.method == "POST":
        form = LaudoForm(request.POST, request.FILES)
        if form.is_valid():
            laudo = form.save(commit=False)
            laudo.tree = tree
            laudo.autor = request.user

            # Gestores têm laudos aprovados automaticamente
            if request.user.is_gestor():
                laudo.status = Laudo.LaudoStatus.APROVADO
                laudo.validado_por = request.user
                laudo.data_validacao = timezone.now()
                messages.success(request, "Laudo criado e aprovado automaticamente!")
            else:
                laudo.status = Laudo.LaudoStatus.PENDENTE
                messages.success(request, "Laudo enviado para aprovação!")

            laudo.save()

            if request.user.is_gestor():
                return redirect("dashboard_gestor")
            else:
                return redirect("dashboard_tecnico")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LaudoForm()

    return render(request, "laudos/criar.html", {"form": form, "tree": tree})


@gestor_required
def listar_laudos_pendentes(request):
    """Gestor visualiza laudos pendentes"""
    laudos = Laudo.objects.filter(status=Laudo.LaudoStatus.PENDENTE).select_related(
        "tree", "autor"
    )
    return render(request, "laudos/pendentes.html", {"laudos": laudos})


@gestor_required
def validar_laudo(request, laudo_id):
    """Gestor aprova ou rejeita laudo"""
    laudo = get_object_or_404(Laudo, id=laudo_id)

    if request.method == "POST":
        acao = request.POST.get("acao")
        observacoes = request.POST.get("observacoes", "")

        if acao == "aprovar":
            laudo.status = Laudo.LaudoStatus.APROVADO
            messages.success(request, "Laudo aprovado!")
        elif acao == "rejeitar":
            laudo.status = Laudo.LaudoStatus.REJEITADO
            messages.warning(request, "Laudo rejeitado.")

        laudo.validado_por = request.user
        laudo.data_validacao = timezone.now()
        laudo.observacoes_validacao = observacoes
        laudo.save()

        return redirect("listar_laudos_pendentes")

    return render(request, "laudos/validar.html", {"laudo": laudo})


@tecnico_required
def meus_laudos(request):
    """Lista todos os laudos criados pelo técnico"""
    laudos = (
        Laudo.objects.filter(autor=request.user)
        .select_related("tree", "validado_por")
        .order_by("-data_criacao")
    )

    # Separar por status
    pendentes = laudos.filter(status=Laudo.LaudoStatus.PENDENTE)
    aprovados = laudos.filter(status=Laudo.LaudoStatus.APROVADO)
    rejeitados = laudos.filter(status=Laudo.LaudoStatus.REJEITADO)
    rascunhos = laudos.filter(status=Laudo.LaudoStatus.RASCUNHO)

    context = {
        "laudos": laudos,
        "pendentes": pendentes,
        "aprovados": aprovados,
        "rejeitados": rejeitados,
        "rascunhos": rascunhos,
    }

    return render(request, "laudos/meus_laudos.html", context)


@tecnico_required
def editar_laudo(request, laudo_id):
    """Técnico edita seu próprio laudo (apenas se ainda não aprovado)"""
    laudo = get_object_or_404(Laudo, id=laudo_id)

    # Verificar se o laudo pertence ao usuário
    if laudo.autor != request.user:
        messages.error(request, "Você não tem permissão para editar este laudo.")
        return redirect("meus_laudos")

    # Verificar se o laudo ainda pode ser editado (não aprovado/rejeitado)
    if laudo.status in [Laudo.LaudoStatus.APROVADO]:
        messages.error(request, "Laudos aprovados não podem ser editados.")
        return redirect("meus_laudos")

    if request.method == "POST":
        form = LaudoForm(request.POST, request.FILES, instance=laudo)
        if form.is_valid():
            laudo = form.save(commit=False)
            # Manter status pendente se já estava pendente
            laudo.status = Laudo.LaudoStatus.PENDENTE
            laudo.save()

            messages.success(request, "Laudo atualizado com sucesso!")
            return redirect("meus_laudos")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LaudoForm(instance=laudo)

    context = {
        "form": form,
        "laudo": laudo,
        "tree": laudo.tree,
        "is_edit": True,
    }

    return render(request, "laudos/criar.html", context)


@tecnico_required
def excluir_laudo(request, laudo_id):
    """Técnico exclui seu próprio laudo (apenas se ainda não aprovado)"""
    laudo = get_object_or_404(Laudo, id=laudo_id)

    # Verificar permissões
    if laudo.autor != request.user:
        messages.error(request, "Você não tem permissão para excluir este laudo.")
        return redirect("meus_laudos")

    if laudo.status in [Laudo.LaudoStatus.APROVADO]:
        messages.error(request, "Laudos aprovados não podem ser excluídos.")
        return redirect("meus_laudos")

    if request.method == "POST":
        titulo = laudo.titulo
        laudo.delete()
        messages.success(request, f'Laudo "{titulo}" excluído com sucesso.')
        return redirect("meus_laudos")

    return render(request, "laudos/excluir.html", {"laudo": laudo})


# ==================== NOTIFICAÇÕES ====================


@login_required
def criar_notificacao(request, tree_id):
    """Cidadão cria notificação"""
    tree = get_object_or_404(Tree, id=tree_id)

    if request.method == "POST":
        form = NotificacaoForm(request.POST, request.FILES)
        if form.is_valid():
            notificacao = form.save(commit=False)
            notificacao.tree = tree
            notificacao.autor = request.user
            notificacao.save()

            # Registra no histórico
            HistoricoNotificacao.objects.create(
                notificacao=notificacao,
                usuario=request.user,
                acao="Notificação criada",
            )

            messages.success(request, "Notificação enviada com sucesso!")
            return redirect("index")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = NotificacaoForm()

    return render(
        request,
        "notificacoes/criar.html",
        {"form": form, "tree": tree},
    )


@gestor_ou_tecnico_required
def listar_notificacoes(request):
    """Lista notificações para gestores e técnicos"""
    filters = {}
    if request.GET.get("status"):
        filters["status"] = request.GET.get("status")
    if request.GET.get("tipo"):
        filters["tipo"] = request.GET.get("tipo")

    if request.user.is_gestor():
        notificacoes = Notificacao.objects.filter(**filters)
    else:  # Técnico
        notificacoes = Notificacao.objects.filter(
            status__in=[
                Notificacao.StatusNotificacao.PENDENTE,
                Notificacao.StatusNotificacao.EM_ANALISE,
            ],
            **filters,
        ) | Notificacao.objects.filter(tecnico_responsavel=request.user, **filters)

    notificacoes = notificacoes.select_related(
        "tree", "autor", "tecnico_responsavel"
    ).order_by("-data_criacao")

    return render(request, "notificacoes/listar.html", {"notificacoes": notificacoes})


@gestor_ou_tecnico_required
def analisar_notificacao(request, notificacao_id):
    """Técnico analisa notificação"""
    notificacao = get_object_or_404(Notificacao, id=notificacao_id)

    if request.method == "POST":
        form = ParecerTecnicoForm(request.POST, instance=notificacao)
        if form.is_valid():
            notificacao = form.save(commit=False)
            notificacao.status = Notificacao.StatusNotificacao.EM_ANALISE
            notificacao.tecnico_responsavel = request.user
            notificacao.save()

            # Registra no histórico
            HistoricoNotificacao.objects.create(
                notificacao=notificacao,
                usuario=request.user,
                acao="Parecer técnico atualizado",
                observacao=notificacao.parecer_tecnico,
            )

            messages.success(request, "Parecer técnico enviado com sucesso!")
            return redirect("listar_notificacoes")
        else:
            # Mostra erros de validação
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ParecerTecnicoForm(instance=notificacao)

    return render(
        request,
        "notificacoes/analisar.html",
        {
            "form": form,
            "notificacao": notificacao,
            "historico": notificacao.historico.all(),
        },
    )


@gestor_required
def resolver_notificacao(request, notificacao_id):
    """Gestor resolve notificação"""
    notificacao = get_object_or_404(Notificacao, id=notificacao_id)

    if request.method == "POST":
        acao = request.POST.get("acao")
        observacao = request.POST.get("observacao", "")

        if acao == "resolver":
            notificacao.status = Notificacao.StatusNotificacao.RESOLVIDA
        elif acao == "arquivar":
            notificacao.status = Notificacao.StatusNotificacao.ARQUIVADA

        notificacao.save()

        HistoricoNotificacao.objects.create(
            notificacao=notificacao,
            usuario=request.user,
            acao=f"Notificação {acao}",
            observacao=observacao,
        )

        messages.success(request, f"Notificação {acao}!")
        return redirect("listar_notificacoes")

    return render(
        request,
        "notificacoes/resolver.html",
        {"notificacao": notificacao, "historico": notificacao.historico.all()},
    )

def politica_privacidade(request):
    """Exibe a política de privacidade"""
    return render(request, "privacy_policy.html")