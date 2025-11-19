from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
import json
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
    TreeVariable,
    TreeVariableValue,
    SpeciesVariableDefault,
    Species,
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
    # Otimização: carrega apenas posições inicialmente
    trees = (
        Tree.objects.filter(**filters)
        .annotate(n_posts=Count("posts"))
        .values("id", "latitude", "longitude", "n_posts")
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


def api_tree_detail(request, tree_id):
    """API endpoint para buscar dados completos de uma árvore"""
    try:
        tree = Tree.objects.select_related("species").annotate(
            n_posts=Count("posts")
        ).get(id=tree_id)
        
        # Prepara dados da árvore
        tree_data = {
            "id": tree.id,
            "nome_popular": tree.nome_popular,
            "nome_cientifico": tree.nome_cientifico,
            "dap": str(tree.dap),
            "altura": str(tree.altura),
            "data_da_coleta": "",
            "latitude": tree.latitude,
            "longitude": tree.longitude,
            "numero": tree.N_placa,
            "n_comentarios": tree.n_posts,
            "color": "yellow" if tree.n_posts > 0 else "green",
            "plantado_por": tree.plantado_por,
            "imagens": [img.strip() for img in tree.imagem.split(',') if img.strip()] if tree.imagem else [],
            "laudos": [laudo.strip() for laudo in tree.laudo.split(',') if laudo.strip()] if tree.laudo else [],
            "services": tree.get_all_ecosystem_services(),
            # Compatibilidade com código antigo
            "co2": tree.stored_co2,
            "stormwater": tree.stormwater_intercepted,
            "conserved_energy": tree.conserved_energy,
            "biodiversity": tree.biodiversity,
        }
        
        return JsonResponse(tree_data)
    except Tree.DoesNotExist:
        return JsonResponse({"error": "Árvore não encontrada"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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


# ==================== GESTÃO DE SERVIÇOS ECOSSISTÊMICOS E VARIÁVEIS ====================

@gestor_required
def configurar_servicos_variaveis(request):
    """Página principal de configuração de serviços e variáveis"""
    servicos = EcosystemServiceConfig.objects.all().order_by('ordem_exibicao', 'nome')
    variaveis = TreeVariable.objects.all().order_by('nome')
    
    context = {
        'servicos': servicos,
        'variaveis': variaveis,
    }
    return render(request, "gestao/configuracoes.html", context)


@gestor_required
def criar_servico_ecossistemico(request):
    """Cria um novo serviço ecossistêmico"""
    if request.method == "POST":
        try:
            nome = request.POST.get('nome')
            codigo = request.POST.get('codigo')
            descricao = request.POST.get('descricao', '')
            categoria = request.POST.get('categoria', 'OUTROS')
            formula = request.POST.get('formula', '')
            coeficientes_json = request.POST.get('coeficientes', '{}')
            valor_monetario = float(request.POST.get('valor_monetario_unitario', 0))
            unidade_medida = request.POST.get('unidade_medida', 'unidade')
            referencia_cientifica = request.POST.get('referencia_cientifica', '')
            ativo = request.POST.get('ativo') == 'on'
            ordem_exibicao = int(request.POST.get('ordem_exibicao', 0))
            
            coeficientes = json.loads(coeficientes_json) if coeficientes_json else {}
            
            servico = EcosystemServiceConfig.objects.create(
                nome=nome,
                codigo=codigo,
                descricao=descricao,
                categoria=categoria,
                formula=formula,
                coeficientes=coeficientes,
                valor_monetario_unitario=valor_monetario,
                unidade_medida=unidade_medida,
                referencia_cientifica=referencia_cientifica,
                ativo=ativo,
                ordem_exibicao=ordem_exibicao,
                criado_por=request.user
            )
            
            messages.success(request, f"Serviço '{nome}' criado com sucesso!")
            return redirect('configurar_servicos_variaveis')
        except Exception as e:
            messages.error(request, f"Erro ao criar serviço: {str(e)}")
    
    return render(request, "gestao/form_servico.html", {'acao': 'criar'})


@gestor_required
def editar_servico_ecossistemico(request, servico_id):
    """Edita um serviço ecossistêmico existente"""
    servico = get_object_or_404(EcosystemServiceConfig, id=servico_id)
    
    if request.method == "POST":
        try:
            servico.nome = request.POST.get('nome')
            servico.codigo = request.POST.get('codigo')
            servico.descricao = request.POST.get('descricao', '')
            servico.categoria = request.POST.get('categoria', 'OUTROS')
            servico.formula = request.POST.get('formula', '')
            coeficientes_json = request.POST.get('coeficientes', '{}')
            servico.valor_monetario_unitario = float(request.POST.get('valor_monetario_unitario', 0))
            servico.unidade_medida = request.POST.get('unidade_medida', 'unidade')
            servico.referencia_cientifica = request.POST.get('referencia_cientifica', '')
            servico.ativo = request.POST.get('ativo') == 'on'
            servico.ordem_exibicao = int(request.POST.get('ordem_exibicao', 0))
            
            # Processa coeficientes - pode vir como JSON ou como arrays separados
            coeficientes = {}
            if coeficientes_json and coeficientes_json != '{}':
                try:
                    coeficientes = json.loads(coeficientes_json)
                except json.JSONDecodeError:
                    # Se não for JSON válido, tenta processar arrays
                    coef_nomes = request.POST.getlist('coef_nome[]')
                    coef_valores = request.POST.getlist('coef_valor[]')
                    for nome, valor in zip(coef_nomes, coef_valores):
                        if nome and valor:
                            try:
                                coeficientes[nome] = float(valor)
                            except ValueError:
                                coeficientes[nome] = valor
            
            servico.coeficientes = coeficientes
            servico.save()
            
            messages.success(request, f"Serviço '{servico.nome}' atualizado com sucesso!")
            return redirect('configurar_servicos_variaveis')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar serviço: {str(e)}")
    
    return render(request, "gestao/form_servico.html", {'acao': 'editar', 'servico': servico})


@gestor_required
def excluir_servico_ecossistemico(request, servico_id):
    """Exclui um serviço ecossistêmico"""
    servico = get_object_or_404(EcosystemServiceConfig, id=servico_id)
    
    if request.method == "POST":
        nome = servico.nome
        servico.delete()
        messages.success(request, f"Serviço '{nome}' excluído com sucesso!")
        return redirect('configurar_servicos_variaveis')
    
    return render(request, "gestao/confirmar_exclusao.html", {
        'objeto': servico,
        'tipo': 'serviço',
        'url_voltar': 'configurar_servicos_variaveis'
    })


@gestor_required
def criar_variavel_customizada(request):
    """Cria uma nova variável customizada"""
    if request.method == "POST":
        try:
            nome = request.POST.get('nome')
            codigo = request.POST.get('codigo')
            tipo_dado = request.POST.get('tipo_dado', 'FLOAT')
            unidade_medida = request.POST.get('unidade_medida', '')
            descricao = request.POST.get('descricao', '')
            valor_padrao_geral_str = request.POST.get('valor_padrao_geral', '')
            ativo = request.POST.get('ativo') == 'on'
            
            # Converte valor padrão conforme tipo
            valor_padrao_geral = None
            if valor_padrao_geral_str:
                if tipo_dado == 'FLOAT':
                    valor_padrao_geral = float(valor_padrao_geral_str)
                elif tipo_dado == 'INTEGER':
                    valor_padrao_geral = int(float(valor_padrao_geral_str))
                else:
                    valor_padrao_geral = valor_padrao_geral_str
            
            variavel = TreeVariable.objects.create(
                nome=nome,
                codigo=codigo,
                tipo_dado=tipo_dado,
                unidade_medida=unidade_medida,
                descricao=descricao,
                valor_padrao_geral=valor_padrao_geral,
                ativo=ativo
            )
            
            messages.success(request, f"Variável '{nome}' criada com sucesso!")
            return redirect('configurar_servicos_variaveis')
        except Exception as e:
            messages.error(request, f"Erro ao criar variável: {str(e)}")
    
    especies = Species.objects.all().order_by('name')
    return render(request, "gestao/form_variavel.html", {'acao': 'criar', 'especies': especies})


@gestor_required
def editar_variavel_customizada(request, variavel_id):
    """Edita uma variável customizada existente"""
    variavel = get_object_or_404(TreeVariable, id=variavel_id)
    especies = Species.objects.all().order_by('name')
    valores_por_especie = SpeciesVariableDefault.objects.filter(variable=variavel)
    
    if request.method == "POST":
        try:
            variavel.nome = request.POST.get('nome')
            variavel.codigo = request.POST.get('codigo')
            variavel.tipo_dado = request.POST.get('tipo_dado', 'FLOAT')
            variavel.unidade_medida = request.POST.get('unidade_medida', '')
            variavel.descricao = request.POST.get('descricao', '')
            valor_padrao_geral_str = request.POST.get('valor_padrao_geral', '')
            variavel.ativo = request.POST.get('ativo') == 'on'
            
            # Converte valor padrão conforme tipo
            if valor_padrao_geral_str:
                if variavel.tipo_dado == 'FLOAT':
                    variavel.valor_padrao_geral = float(valor_padrao_geral_str)
                elif variavel.tipo_dado == 'INTEGER':
                    variavel.valor_padrao_geral = int(float(valor_padrao_geral_str))
                else:
                    variavel.valor_padrao_geral = valor_padrao_geral_str
            else:
                variavel.valor_padrao_geral = None
            
            variavel.save()
            
            messages.success(request, f"Variável '{variavel.nome}' atualizada com sucesso!")
            return redirect('configurar_servicos_variaveis')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar variável: {str(e)}")
    
    return render(request, "gestao/form_variavel.html", {
        'acao': 'editar',
        'variavel': variavel,
        'especies': especies,
        'valores_por_especie': valores_por_especie
    })


@gestor_required
def excluir_variavel_customizada(request, variavel_id):
    """Exclui uma variável customizada"""
    variavel = get_object_or_404(TreeVariable, id=variavel_id)
    
    if request.method == "POST":
        nome = variavel.nome
        variavel.delete()
        messages.success(request, f"Variável '{nome}' excluída com sucesso!")
        return redirect('configurar_servicos_variaveis')
    
    return render(request, "gestao/confirmar_exclusao.html", {
        'objeto': variavel,
        'tipo': 'variável',
        'url_voltar': 'configurar_servicos_variaveis'
    })


@gestor_required
def definir_valor_especie(request, variavel_id):
    """Define valor padrão de uma variável para uma espécie"""
    variavel = get_object_or_404(TreeVariable, id=variavel_id)
    
    if request.method == "POST":
        try:
            species_id = request.POST.get('species_id')
            valor_str = request.POST.get('valor_padrao', '')
            
            species = get_object_or_404(Species, id=species_id)
            
            # Converte valor conforme tipo
            valor = None
            if valor_str:
                if variavel.tipo_dado == 'FLOAT':
                    valor = float(valor_str)
                elif variavel.tipo_dado == 'INTEGER':
                    valor = int(float(valor_str))
                else:
                    valor = valor_str
            
            # Cria ou atualiza valor padrão
            especie_default, created = SpeciesVariableDefault.objects.update_or_create(
                species=species,
                variable=variavel,
                defaults={'valor_padrao': valor}
            )
            
            acao = "criado" if created else "atualizado"
            messages.success(request, f"Valor padrão {acao} com sucesso!")
            return redirect('editar_variavel_customizada', variavel_id=variavel_id)
        except Exception as e:
            messages.error(request, f"Erro ao definir valor: {str(e)}")
    
    especies = Species.objects.all().order_by('name')
    return render(request, "gestao/form_valor_especie.html", {
        'variavel': variavel,
        'especies': especies
    })


@gestor_required
def remover_valor_especie(request, variavel_id, especie_id):
    """Remove valor padrão de uma variável para uma espécie"""
    variavel = get_object_or_404(TreeVariable, id=variavel_id)
    species = get_object_or_404(Species, id=especie_id)
    
    if request.method == "POST":
        try:
            SpeciesVariableDefault.objects.filter(variable=variavel, species=species).delete()
            messages.success(request, "Valor padrão removido com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao remover valor: {str(e)}")
    
    return redirect('editar_variavel_customizada', variavel_id=variavel_id)


@gestor_required
def validar_formula(request):
    """Valida uma fórmula via AJAX"""
    if request.method == "POST":
        try:
            formula = request.POST.get('formula', '')
            coeficientes_json = request.POST.get('coeficientes', '{}')
            
            import math
            
            # Dados de exemplo para teste
            dap = 30.0
            altura = 10.0
            biomassa = math.exp(-0.906586 + 1.60421 * math.log(dap) + 0.37162 * math.log(altura)) / 1000
            
            coeficientes = json.loads(coeficientes_json) if coeficientes_json else {}
            
            context = {
                'math': math,
                'dap': dap,
                'altura': altura,
                'biomassa': biomassa,
                'coeficientes': coeficientes,
            }
            
            # Expande coeficientes
            for key, value in coeficientes.items():
                context[key] = value
            
            # Adiciona variáveis customizadas (com valores de exemplo)
            variaveis = TreeVariable.objects.filter(ativo=True)
            for var in variaveis:
                if var.tipo_dado in ['FLOAT', 'INTEGER']:
                    context[var.codigo] = 1.0  # Valor de exemplo
                else:
                    context[var.codigo] = None
            
            # Tenta avaliar a fórmula
            resultado = eval(formula, {"__builtins__": {}}, context)
            
            if not isinstance(resultado, (int, float)) or math.isnan(resultado) or math.isinf(resultado):
                return JsonResponse({
                    'valido': False,
                    'erro': 'A fórmula retornou um valor inválido'
                })
            
            return JsonResponse({
                'valido': True,
                'resultado_exemplo': round(float(resultado), 4),
                'mensagem': f'Fórmula válida! Resultado de exemplo: {round(float(resultado), 4)}'
            })
            
        except SyntaxError as e:
            return JsonResponse({
                'valido': False,
                'erro': f'Erro de sintaxe: {str(e)}'
            })
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            return JsonResponse({
                'valido': False,
                'erro': f'Erro matemático: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'valido': False,
                'erro': f'Erro: {str(e)}'
            })
    
    return JsonResponse({'valido': False, 'erro': 'Método não permitido'})