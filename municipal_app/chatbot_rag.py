import os
import glob
import numpy as np
import faiss
import pickle
import google.generativeai as genai
from django.conf import settings

# --- Configuración Inicial ---

# La API Key se cargará desde settings.py de Django
API_KEY = getattr(settings, "GEMINI_API_KEY", None)

if not API_KEY:
    raise ValueError("La variable GEMINI_API_KEY no está configurada en settings.py.")

# Configurar el cliente de GenAI
genai.configure(api_key=API_KEY)


# --- Definición de Rutas y Modelos ---

# Rutas basadas en la estructura del proyecto Django
BASE_DIR = settings.BASE_DIR
DOCS_DIR = os.path.join(BASE_DIR, "base_conocimiento")
INDEX_DIR = os.path.join(BASE_DIR, "faiss_index")

MODEL_EMBEDDING = "text-embedding-004"
MODEL_CHAT = "gemini-flash-latest" # Usamos un modelo que soporta System Instructions


# ===========================
# PARTE 1: Gestión del Índice (Indexación)
# ===========================

def cargar_y_fragmentar_docs():
    """Lee archivos .txt de la carpeta y los divide en trozos (chunks)."""
    documentos = []
    archivos = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    
    for archivo in archivos:
        with open(archivo, 'r', encoding='utf-8') as f:
            texto = f.read()
            # Fragmentación simple por párrafos.
            chunks = [t.strip() for t in texto.split('\n\n') if t.strip()]
            documentos.extend(chunks)
            
    return documentos

def crear_indice_rag():
    """Crea el índice vectorial FAISS y guarda los textos."""
    textos = cargar_y_fragmentar_docs()
    if not textos:
        print("No se encontraron documentos para indexar en 'base_conocimiento/'.")
        return

    print(f"Generando embeddings para {len(textos)} fragmentos de texto...")
    
    try:
        # Generar embeddings para todos los textos
        response = genai.embed_content(
            model=MODEL_EMBEDDING,
            content=textos,
            task_type="retrieval_document"
        )
        embeddings_list = response['embedding']
    except Exception as e:
        print(f"Error al generar embeddings: {e}")
        return

    embeddings_np = np.array(embeddings_list, dtype='float32')
    dimension = embeddings_np.shape[1]

    # Crear y construir el índice FAISS
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)

    # Guardar el índice y los textos fragmentados
    if not os.path.exists(INDEX_DIR):
        os.makedirs(INDEX_DIR)
        
    faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))
    with open(os.path.join(INDEX_DIR, "textos.pkl"), "wb") as f:
        pickle.dump(textos, f)
        
    print(f"Índice RAG creado y guardado exitosamente en {INDEX_DIR}")


# ===========================
# PARTE 2: Consulta y Generación
# ===========================

# Caché en memoria para no recargar el índice en cada petición
_cached_index = None
_cached_texts = None

def cargar_recursos_rag():
    """Carga el índice y los textos en una caché en memoria."""
    global _cached_index, _cached_texts
    if _cached_index is None:
        try:
            _cached_index = faiss.read_index(os.path.join(INDEX_DIR, "index.faiss"))
            with open(os.path.join(INDEX_DIR, "textos.pkl"), "rb") as f:
                _cached_texts = pickle.load(f)
        except FileNotFoundError:
            return False
    return True

def buscar_contexto(pregunta, k=3):
    """Busca los fragmentos de texto más relevantes para una pregunta."""
    if not cargar_recursos_rag():
        return []

    # Generar embedding para la pregunta
    response = genai.embed_content(
        model=MODEL_EMBEDDING,
        content=pregunta,
        task_type="retrieval_query"
    )
    pregunta_emb = np.array([response['embedding']], dtype='float32')

    # Buscar en FAISS los k vecinos más cercanos
    distances, indices = _cached_index.search(pregunta_emb, k)
    
    # Devolver los textos correspondientes
    contextos = [_cached_texts[idx] for idx in indices[0] if idx != -1]
    return contextos

def generar_respuesta_rag(pregunta_usuario):
    """Genera una respuesta utilizando el contexto recuperado."""
    
    contexto = buscar_contexto(pregunta_usuario)
    if not contexto:
        contexto_str = "No se encontró información relevante en la base de conocimiento interna."
    else:
        contexto_str = "\n---\n".join(contexto)

    # Usar un modelo con System Instructions para un mejor control
    model = genai.GenerativeModel(
      MODEL_CHAT,
      system_instruction="""Eres Contabot, un asistente experto en temas contables y municipales de Argentina.
- Tu tarea es responder las preguntas del usuario basándote PRINCIPALMENTE en la INFORMACIÓN DE CONTEXTO que se te proporciona.
- Si la respuesta no está en el contexto, indícalo claramente diciendo "Según mis documentos, no tengo información sobre eso, pero...".
- Sé conciso, profesional y directo."""
    )

    prompt = f"""
INFORMACIÓN DE CONTEXTO:
{contexto_str}

PREGUNTA DEL USUARIO:
{pregunta_usuario}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error al contactar el modelo generativo: {e}"