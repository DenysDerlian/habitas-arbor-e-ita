from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser

class TestAprovacaoTecnicos(TestCase):

    def setUp(self):
        self.gestor = CustomUser.objects.create_user(
            username="gestor",
            password="123456",
            user_type=CustomUser.UserType.GESTOR,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

        self.tecnico = CustomUser.objects.create_user(
            username="tec",
            password="123456",
            user_type=CustomUser.UserType.TECNICO,
            aprovacao_status=CustomUser.ApprovalStatus.PENDENTE
        )

    def test_listar_tecnicos_pendentes(self):
        self.client.login(username="gestor", password="123456")
        response = self.client.get(reverse("listar_tecnicos_pendentes"))
        self.assertContains(response, "tec")

    def test_aprovar_tecnico(self):
        self.client.login(username="gestor", password="123456")

        response = self.client.post(reverse("aprovar_tecnico", args=[self.tecnico.id]), {
            "aprovacao_status": CustomUser.ApprovalStatus.APROVADO
        })

        self.assertEqual(response.status_code, 302)
        self.tecnico.refresh_from_db()
        self.assertEqual(self.tecnico.aprovacao_status, CustomUser.ApprovalStatus.APROVADO)
