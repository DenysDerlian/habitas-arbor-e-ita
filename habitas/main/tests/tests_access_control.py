from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Tree, Laudo, Notificacao


class TestAccessControl(TestCase):

    def setUp(self):
        # Usuários
        self.cidadao = CustomUser.objects.create_user(
            username="cid",
            password="123",
            user_type=CustomUser.UserType.CIDADAO,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.tecnico = CustomUser.objects.create_user(
            username="tec",
            password="123",
            user_type=CustomUser.UserType.TECNICO,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.gestor = CustomUser.objects.create_user(
            username="gestor",
            password="123",
            user_type=CustomUser.UserType.GESTOR,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.tree = Tree.objects.create(
            N_placa="001",
            nome_popular="Ipê",
            nome_cientifico="Tabebuia",
            dap=10, altura=5, latitude=0, longitude=0
        )

        self.laudo = Laudo.objects.create(
            titulo="Teste",
            descricao="Desc",
            autor=self.tecnico,
            tree=self.tree,
            status=Laudo.LaudoStatus.PENDENTE
        )

        self.notificacao = Notificacao.objects.create(
            titulo="Notif",
            tipo="R",
            descricao="Desc",
            autor=self.cidadao,
            tree=self.tree
        )

    # ============================
    #    TESTES PARA DASHBOARDS
    # ============================

    def test_cidadao_tenta_acessar_dashboard_tecnico(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("dashboard_tecnico"))
        self.assertEqual(response.status_code, 403)

    def test_cidadao_tenta_acessar_dashboard_gestor(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("dashboard_gestor"))
        self.assertEqual(response.status_code, 403)

    def test_tecnico_tenta_acessar_dashboard_gestor(self):
        self.client.login(username="tec", password="123")
        response = self.client.get(reverse("dashboard_gestor"))
        self.assertEqual(response.status_code, 403)

    # ============================
    #   TESTES DE GESTÃO DE TÉCNICOS
    # ============================

    def test_cidadao_tenta_listar_tecnicos_pendentes(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("listar_tecnicos_pendentes"))
        self.assertEqual(response.status_code, 403)

    def test_tecnico_tenta_listar_tecnicos_pendentes(self):
        self.client.login(username="tec", password="123")
        response = self.client.get(reverse("listar_tecnicos_pendentes"))
        self.assertEqual(response.status_code, 403)

    # ============================
    #   TESTES DE LAUDOS
    # ============================

    def test_cidadao_tenta_criar_laudo(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("criar_laudo", args=[self.tree.id]))
        self.assertEqual(response.status_code, 403)

    def test_cidadao_tenta_validar_laudo(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("validar_laudo", args=[self.laudo.id]))
        self.assertEqual(response.status_code, 403)

    def test_tecnico_tenta_validar_laudo(self):
        self.client.login(username="tec", password="123")
        response = self.client.get(reverse("validar_laudo", args=[self.laudo.id]))
        self.assertEqual(response.status_code, 403)

    # ============================
    #   TESTES DE NOTIFICAÇÕES
    # ============================

    def test_cidadao_tenta_listar_notificacoes(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("listar_notificacoes"))
        self.assertEqual(response.status_code, 403)

    def test_cidadao_tenta_analisar_notificacao(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("analisar_notificacao", args=[self.notificacao.id]))
        self.assertEqual(response.status_code, 403)

    def test_cidadao_tenta_resolver_notificacao(self):
        self.client.login(username="cid", password="123")
        response = self.client.get(reverse("resolver_notificacao", args=[self.notificacao.id]))
        self.assertEqual(response.status_code, 403)

    def test_tecnico_tenta_resolver_notificacao(self):
        self.client.login(username="tec", password="123")
        response = self.client.get(reverse("resolver_notificacao", args=[self.notificacao.id]))
        self.assertEqual(response.status_code, 403)

    # ============================
    #   USUÁRIOS NÃO AUTENTICADOS
    # ============================

    def test_anon_tenta_acessar_rotas_protegidas(self):
        rotas = [
            reverse("dashboard_tecnico"),
            reverse("dashboard_gestor"),
            reverse("listar_tecnicos_pendentes"),
            reverse("listar_notificacoes"),
        ]

        for rota in rotas:
            response = self.client.get(rota)
            self.assertEqual(response.status_code, 302)  # redireciona para login
            self.assertTrue("/login/" in response.url)

