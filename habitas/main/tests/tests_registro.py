from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser
from django.core.files.uploadedfile import SimpleUploadedFile

class TestRegistro(TestCase):

    def test_registro_cidadao(self):
        response = self.client.post(reverse("register_cidadao"), {
            "username": "novo",
            "email": "teste@x.com",
            "password1": "abc12345tt",
            "password2": "abc12345tt",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(username="novo").exists())

    def test_registro_tecnico(self):
        arquivo = SimpleUploadedFile("doc.pdf", b"arquivo teste", content_type="application/pdf")

        response = self.client.post(reverse("register_tecnico"), {
            "username": "tecnico1",
            "email": "tec@x.com",
            "formacao": "Agronomia",
            "registro_profissional": "12345",
            "documento_comprobatorio": arquivo,
            "password1": "abc12345tt",
            "password2": "abc12345tt",
        })

        self.assertEqual(response.status_code, 302)
        tecnico = CustomUser.objects.get(username="tecnico1")
        self.assertEqual(tecnico.aprovacao_status, CustomUser.ApprovalStatus.PENDENTE)
