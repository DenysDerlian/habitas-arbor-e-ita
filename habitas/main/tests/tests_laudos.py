from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Tree, Laudo

class TestLaudos(TestCase):

    def setUp(self):
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
            dap=10, altura=5, latitude=0.0, longitude=0.0
        )

    def test_criar_laudo(self):
        self.client.login(username="tec", password="123456")

        response = self.client.post(reverse("criar_laudo", args=[self.tree.id]), {
            "titulo": "Laudo 1",
            "descricao": "Desc"
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Laudo.objects.filter(titulo="Laudo 1").exists())

    def test_validar_laudo(self):
        laudo = Laudo.objects.create(
            titulo="Teste",
            descricao="d",
            autor=self.tecnico,
            tree=self.tree,
            status=Laudo.LaudoStatus.PENDENTE
        )

        self.client.login(username="gestor", password="123456")

        response = self.client.post(reverse("validar_laudo", args=[laudo.id]), {
            "acao": "aprovar",
            "observacoes": "OK"
        })

        self.assertEqual(response.status_code, 302)
        laudo.refresh_from_db()
        self.assertEqual(laudo.status, Laudo.LaudoStatus.APROVADO)
