from django.core.management.base import BaseCommand
from municipal_app.chatbot_rag import crear_indice_rag

class Command(BaseCommand):
    help = 'Crea o actualiza el índice FAISS para el chatbot RAG a partir de los documentos en base_conocimiento/'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando el proceso de indexación de documentos...'))
        try:
            crear_indice_rag()
            self.stdout.write(self.style.SUCCESS('¡Proceso de indexación completado exitosamente!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocurrió un error durante la indexación: {e}'))