import math
import json
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator

# Create your models here.
BETA0 = -0.906586
BETA1 = 1.60421
BETA2 = 0.37162

PRECIPITATION = 1329  # Precipitação anual em São José dos Campos (L / m^2)
DIAMETER_RATIO = 4  # Razão média entre diâmetro da copa e diâmetro do tronco

RADIATION = 1661 # Radiação solar anual em São José dos Campos (kWh / m^2)
ENERGY_RATIO = 0.25 # Taxa de aproveitamento da energia das sombras


class CustomUser(AbstractUser):
    """Modelo de usuário customizado com 3 níveis de acesso"""
    
    class UserType(models.TextChoices):
        GESTOR = 'GESTOR', 'Gestor do Sistema (Nível 1)'
        TECNICO = 'TECNICO', 'Técnico Voluntário (Nível 2)'
        CIDADAO = 'CIDADAO', 'Cidadão (Nível 3)'
    
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.CIDADAO,
        verbose_name="Tipo de Usuário"
    )
    
    # Campos específicos para Técnicos (Nível 2)
    formacao = models.CharField(max_length=255, blank=True, verbose_name="Formação")
    registro_profissional = models.CharField(max_length=100, blank=True, verbose_name="Registro Profissional")
    documento_comprobatorio = models.FileField(
        upload_to='credenciais/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Documento Comprobatório"
    )
    
    class ApprovalStatus(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'
    
    aprovacao_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDENTE,
        verbose_name="Status de Aprovação"
    )
    aprovado_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tecnicos_aprovados',
        verbose_name="Aprovado por"
    )
    data_aprovacao = models.DateTimeField(null=True, blank=True, verbose_name="Data de Aprovação")
    
    def is_gestor(self):
        return self.user_type == self.UserType.GESTOR
    
    def is_tecnico(self):
        return self.user_type == self.UserType.TECNICO and self.aprovacao_status == self.ApprovalStatus.APROVADO
    
    def is_cidadao(self):
        return self.user_type == self.UserType.CIDADAO
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class Tree(models.Model):
    class OrigemChoices(models.TextChoices):
        NATIVA = 'nativa', 'Nativa'
        EXOTICA = 'exotica', 'Exótica'
        DESCONHECIDA = 'desconhecida', 'Desconhecida'

    origem = models.CharField(
        max_length=20,
        choices=OrigemChoices.choices,
        default=OrigemChoices.DESCONHECIDA,
        verbose_name='Origem'
    )
    N_placa = models.FloatField(default=0)
    nome_popular = models.CharField(max_length=255)
    nome_cientifico = models.CharField(max_length=255)
    dap = models.IntegerField()
    altura = models.FloatField()
    # data_da_coleta = models.DateField(blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    laudo = models.URLField(max_length=255, blank=True)
    imagem = models.URLField(max_length=255, blank=True)
    plantado_por = models.CharField(max_length=100, default="DCTA")
    species = models.ForeignKey('Species', null=True, on_delete=models.SET_NULL)

    @property
    def stored_co2(self) -> float:
        if self.dap <= 0 or self.altura <= 0:
            return 0

        return round(
            (
                math.exp(
                    BETA0 + BETA1 * math.log(self.dap) + BETA2 * math.log(self.altura)
                )
                / 1000
            ),
            4,
        )

    @property
    def stormwater_intercepted(self) -> float:
        if self.dap <= 0:
            return 0

        return math.pi * ((self.dap * DIAMETER_RATIO) / (2 * 100)) ** 2 * PRECIPITATION

    @property
    def conserved_energy(self) -> float:
        if self.dap <= 0:
            return 0

        return math.pi * ((self.dap * DIAMETER_RATIO) / (2 * 100)) ** 2 * RADIATION * ENERGY_RATIO

    @property
    def biodiversity(self) -> float:
        return self.species.bio_index if self.species is not None else 1
    
    # ============ MÉTODOS DINÂMICOS PARA SERVIÇOS ECOSSISTÊMICOS ============
    
    def get_ecosystem_service_value(self, codigo_servico):
        """Obtém o valor de um serviço ecossistêmico específico via configuração dinâmica"""
        try:
            config = EcosystemServiceConfig.objects.get(codigo=codigo_servico, ativo=True)
            return config.calcular(self)
        except EcosystemServiceConfig.DoesNotExist:
            # Fallback para métodos antigos (compatibilidade)
            if codigo_servico == 'co2_armazenado':
                return self.stored_co2
            elif codigo_servico == 'chuva_interceptada':
                return self.stormwater_intercepted
            elif codigo_servico == 'energia_conservada':
                return self.conserved_energy
            elif codigo_servico == 'biodiversidade':
                return self.biodiversity
            return 0.0
    
    def get_all_ecosystem_services(self):
        """Retorna dict com todos os serviços ecossistêmicos ativos"""
        servicos = EcosystemServiceConfig.objects.filter(ativo=True).order_by('ordem_exibicao')
        resultado = {}
        for servico in servicos:
            valor_fisico = servico.calcular(self)
            resultado[servico.codigo] = {
                'nome': servico.nome,
                'valor_fisico': valor_fisico,
                'valor_monetario': servico.calcular_valor_monetario(valor_fisico),
                'unidade': servico.unidade_medida,
                'codigo': servico.codigo,
                'categoria': servico.categoria,
            }
        return resultado
    
    def get_all_ecosystem_services_json(self):
        """Retorna JSON string dos serviços ecossistêmicos (para uso no template)"""
        return json.dumps(self.get_all_ecosystem_services(), ensure_ascii=False)


class Post(models.Model):
    tree = models.ForeignKey(Tree, related_name="posts", on_delete=models.CASCADE)
    author = models.CharField(max_length=255)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    specialized = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_on",)


class Species(models.Model):
    name = models.TextField()
    bio_index = models.FloatField()


class Laudo(models.Model):
    """Modelo para laudos técnicos"""
    
    class LaudoStatus(models.TextChoices):
        RASCUNHO = 'RASCUNHO', 'Rascunho'
        PENDENTE = 'PENDENTE', 'Pendente de Aprovação'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'
    
    tree = models.ForeignKey('Tree', on_delete=models.CASCADE, related_name='laudos_tecnicos')
    autor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='laudos_criados')
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    arquivo = models.FileField(
        upload_to='laudos/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="Arquivo PDF do Laudo"
    )
    status = models.CharField(
        max_length=10,
        choices=LaudoStatus.choices,
        default=LaudoStatus.RASCUNHO
    )
    validado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laudos_validados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_validacao = models.DateTimeField(null=True, blank=True)
    observacoes_validacao = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Laudo Técnico'
        verbose_name_plural = 'Laudos Técnicos'
    
    def __str__(self):
        return f"{self.titulo} - {self.tree.nome_popular}"


class Notificacao(models.Model):
    """Modelo para notificações/denúncias de cidadãos"""
    
    class TipoNotificacao(models.TextChoices):
        DENUNCIA = 'DENUNCIA', 'Denúncia'
        EVENTO = 'EVENTO', 'Evento'
    
    class StatusNotificacao(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        EM_ANALISE = 'EM_ANALISE', 'Em Análise'
        RESOLVIDA = 'RESOLVIDA', 'Resolvida'
        ARQUIVADA = 'ARQUIVADA', 'Arquivada'
    
    tree = models.ForeignKey('Tree', on_delete=models.CASCADE, related_name='notificacoes')
    autor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notificacoes_criadas')
    tipo = models.CharField(max_length=10, choices=TipoNotificacao.choices)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    foto = models.ImageField(upload_to='notificacoes/', blank=True, null=True)
    status = models.CharField(
        max_length=15,
        choices=StatusNotificacao.choices,
        default=StatusNotificacao.PENDENTE
    )
    tecnico_responsavel = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificacoes_analisadas',
        limit_choices_to={'user_type': 'TECNICO'}
    )
    parecer_tecnico = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"


class HistoricoNotificacao(models.Model):
    """Histórico de mudanças em notificações"""
    notificacao = models.ForeignKey(Notificacao, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    acao = models.CharField(max_length=255)
    observacao = models.TextField(blank=True)
    data = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data']
        verbose_name = 'Histórico'
        verbose_name_plural = 'Históricos'


class EcosystemServiceConfig(models.Model):
    """Configuração dinâmica de serviços ecossistêmicos"""
    
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Serviço")
    codigo = models.SlugField(max_length=100, unique=True, verbose_name="Código Único")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # Fórmula matemática (string Python que será avaliada)
    # Variáveis disponíveis: dap, altura, biomassa, tree
    # Exemplo: "math.exp(coeficientes['BETA0'] + coeficientes['BETA1'] * math.log(dap) + coeficientes['BETA2'] * math.log(altura)) / 1000"
    formula = models.TextField(verbose_name="Fórmula Python")
    
    # Coeficientes como JSON
    # Exemplo: {"BETA0": -0.906586, "BETA1": 1.60421, "BETA2": 0.37162, "PRECIPITATION": 1329}
    coeficientes = models.JSONField(default=dict, verbose_name="Coeficientes")
    
    # Valoração monetária
    valor_monetario_unitario = models.FloatField(default=0.0, verbose_name="Valor Monetário por Unidade (R$)")
    unidade_medida = models.CharField(max_length=50, default="unidade", verbose_name="Unidade de Medida")
    
    # Status
    ativo = models.BooleanField(default=True, verbose_name="Serviço Ativo")
    ordem_exibicao = models.IntegerField(default=0, verbose_name="Ordem de Exibição")
    
    # Metadados
    referencia_cientifica = models.CharField(max_length=500, blank=True, verbose_name="Referência Científica")
    categoria = models.CharField(
        max_length=50,
        choices=[
            ('SEQUESTRO', 'Sequestro/Armazenamento'),
            ('INTERCEPTACAO', 'Interceptação'),
            ('ENERGIA', 'Energia'),
            ('POLUICAO', 'Poluição'),
            ('OUTROS', 'Outros'),
        ],
        default='OUTROS',
        verbose_name="Categoria"
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicos_criados'
    )
    
    class Meta:
        ordering = ['ordem_exibicao', 'nome']
        verbose_name = 'Configuração de Serviço Ecossistêmico'
        verbose_name_plural = 'Configurações de Serviços Ecossistêmicos'
    
    def __str__(self):
        status = "✓" if self.ativo else "✗"
        return f"{status} {self.nome}"
    
    def calcular(self, tree):
        """Calcula o valor do serviço para uma árvore"""
        if not self.ativo:
            return 0.0
        
        try:
            import math
            
            dap = float(tree.dap) if tree.dap else 0
            altura = float(tree.altura) if tree.altura else 0
            
            # Validação: DAP e altura devem ser > 0 para cálculos com log
            # Retorna 0 imediatamente se dados inválidos
            if dap <= 0 or altura <= 0:
                return 0.0
            
            # Calcula biomassa se necessário (para novos serviços)
            if dap > 0 and altura > 0:
                biomassa = math.exp(
                    -0.906586 + 1.60421 * math.log(dap) + 0.37162 * math.log(altura)
                ) / 1000  # em toneladas
            else:
                biomassa = 0.0
            
            # Prepara contexto - IMPORTANTE: manter compatibilidade com código atual
            coeficientes = self.coeficientes if self.coeficientes else {}
            context = {
                'math': math,
                'dap': dap,
                'altura': altura,
                'biomassa': biomassa,
                'tree': tree,  # Para acessar species, etc.
                'coeficientes': coeficientes,  # Para fórmulas que usam coeficientes["KEY"]
                'hasattr': hasattr,  # Para uso em fórmulas que verificam atributos
                'getattr': getattr,  # Para uso em fórmulas que acessam atributos
            }
            
            # Expande coeficientes individualmente também (para compatibilidade)
            for key, value in coeficientes.items():
                context[key] = value
            
            # Avalia a fórmula com tratamento de erros matemáticos
            try:
                resultado = eval(self.formula, {"__builtins__": {}}, context)
                # Validação do resultado
                if not isinstance(resultado, (int, float)) or math.isnan(resultado) or math.isinf(resultado):
                    return 0.0
                # Arredondamento igual ao código original
                return round(float(resultado), 4)
            except (ValueError, ZeroDivisionError, OverflowError) as math_error:
                # Erro matemático (log de número <= 0, divisão por zero, overflow)
                # Retorna 0 silenciosamente - não loga para não poluir console
                return 0.0
            
        except (ValueError, ZeroDivisionError, OverflowError) as math_error:
            # Erro matemático capturado no nível externo também
            # Silenciosamente retorna 0
            return 0.0
        except Exception as e:
            # Apenas loga erros não-matemáticos para debug
            print(f"Erro ao calcular {self.nome} para árvore {tree.id}: {e}")
            import traceback
            traceback.print_exc()
            return 0.0
    
    def calcular_valor_monetario(self, valor_fisico):
        """Calcula o valor monetário do serviço"""
        return round(valor_fisico * self.valor_monetario_unitario, 2)


class EcosystemServiceHistory(models.Model):
    """Histórico de mudanças em configurações de serviços"""
    servico = models.ForeignKey(
        EcosystemServiceConfig,
        on_delete=models.CASCADE,
        related_name='historico'
    )
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    acao = models.CharField(max_length=255, verbose_name="Ação Realizada")
    valores_anteriores = models.JSONField(blank=True, null=True, verbose_name="Valores Anteriores")
    valores_novos = models.JSONField(blank=True, null=True, verbose_name="Valores Novos")
    observacao = models.TextField(blank=True, verbose_name="Observação")
    data = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data']
        verbose_name = 'Histórico de Configuração'
        verbose_name_plural = 'Históricos de Configurações'
    
    def __str__(self):
        return f"{self.servico.nome} - {self.acao} - {self.data.strftime('%d/%m/%Y %H:%M')}"
