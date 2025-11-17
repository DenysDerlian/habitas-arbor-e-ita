from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Tree, Notificacao

class TestNotificacoes(TestCase):

    def setUp(self):
        self.cidadao = CustomUser.objects.create_user(
            username="cid", password="123456",
            user_type=CustomUser.UserType.CIDADAO,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.tecnico = CustomUser.objects.create_user(
            username="tec", password="123456",
            user_type=CustomUser.UserType.TECNICO,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.gestor = CustomUser.objects.create_user(
            username="gestor", password="123456",
            user_type=CustomUser.UserType.GESTOR,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.tree = Tree.objects.create(
            N_placa="001", nome_popular="Ipê", nome_cientifico="Tabebuia",
            dap=10, altura=5, latitude=0, longitude=0
        )

    def test_criar_notificacao(self):
        self.client.login(username="cid", password="123456")

        response = self.client.post(reverse("criar_notificacao", args=[self.tree.id]), {
            "tipo": "R",
            "titulo": "Galho caído",
            "descricao": "..."
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Notificacao.objects.filter(titulo="Galho caído").exists())

    def test_analisar_notificacao(self):
        notif = Notificacao.objects.create(
            titulo="Teste",
            tipo="R",
            descricao="d",
            autor=self.cidadao,
            tree=self.tree,
        )

        self.client.login(username="tec", password="123456")

        response = self.client.post(reverse("analisar_notificacao", args=[notif.id]), {
            "parecer_tecnico": "Tudo ok",
            "status": Notificacao.StatusNotificacao.EM_ANALISE
        })

        self.assertEqual(response.status_code, 302)
        notif.refresh_from_db()
        self.assertEqual(notif.tecnico_responsavel, self.tecnico)

    def test_resolver_notificacao(self):
        notif = Notificacao.objects.create(
            titulo="Teste",
            tipo="R",
            descricao="d",
            autor=self.cidadao,
            tree=self.tree,
            status=Notificacao.StatusNotificacao.EM_ANALISE,
            tecnico_responsavel=self.tecnico
        )

        self.client.login(username="gestor", password="123456")

        response = self.client.post(reverse("resolver_notificacao", args=[notif.id]), {
            "acao": "resolver",
            "observacao": "Resolvido."
        })

        notif.refresh_from_db()
        self.assertEqual(notif.status, Notificacao.StatusNotificacao.RESOLVIDA)
