from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser

class TestAuth(TestCase):

    def setUp(self):
        self.password = "teste12345"
        self.user = CustomUser.objects.create_user(
            username="user1",
            password=self.password,
            user_type=CustomUser.UserType.CIDADAO,
            aprovacao_status=CustomUser.ApprovalStatus.APROVADO
        )

    def test_login_sucesso(self):
        response = self.client.post(reverse("login"), {
            "username": "user1",
            "password": self.password
        })
        self.assertEqual(response.status_code, 302)  # Redireciona
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_login_falha(self):
        response = self.client.post(reverse("login"), {
            "username": "user1",
            "password": "senhaerrada"
        })
        self.assertContains(response, "Usuário ou senha inválidos.")

    def test_logout(self):
        self.client.login(username="user1", password=self.password)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse("_auth_user_id" in self.client.session)
