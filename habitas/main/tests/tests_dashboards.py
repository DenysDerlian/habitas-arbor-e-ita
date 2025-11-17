from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser

class TestDashboards(TestCase):

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
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

    def test_dashboard_gestor_acesso(self):
        self.client.login(username="gestor", password="123456")
        response = self.client.get(reverse("dashboard_gestor"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_tecnico_acesso(self):
        self.client.login(username="tec", password="123456")
        response = self.client.get(reverse("dashboard_tecnico"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_gestor_negado_para_tecnico(self):
        self.client.login(username="tec", password="123456")
        response = self.client.get(reverse("dashboard_gestor"))
        self.assertEqual(response.status_code, 403)
